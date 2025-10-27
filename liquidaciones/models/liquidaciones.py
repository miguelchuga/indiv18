# -*- encoding: utf-8 -*-

from odoo.addons import decimal_precision as dp
from odoo import models, fields, api, _
from odoo.exceptions import UserError ,ValidationError
from contextlib import ExitStack, contextmanager
from odoo.tools import (
    date_utils,
    email_split,
    float_compare,
    float_is_zero,
    format_amount,
    format_date,
    formatLang,
    frozendict,
    get_lang,
    is_html_empty,
    sql
)


class AccountMoveLineMC(models.Model):
    _name = "account.move.line"
    _inherit = "account.move.line"

    liquidacion_pass = fields.Boolean(string='Liquidacion Pass', default=False)
    liquidaciones_id = fields.Many2one("liquidaciones.liquidaciones", string="Liquidacion", readonly=False)


class AccountMoveMC(models.Model):
    _name = "account.move"
    _inherit = "account.move"


    @contextmanager
    def _check_balanced(_oldself, container):
        ''' Assert the move is fully balanced debit = credit.
        An error is raised if it's not the case.
        '''
        with self._disable_recursion(container, 'check_move_validity', default=True, target=False) as disabled:
            yield
            if disabled:
                return

        unbalanced_moves = self._get_unbalanced_moves(container)
        if unbalanced_moves:
            error_msg = _("An error has occurred.")
            for move_id, sum_debit, sum_credit in unbalanced_moves:
                move = self.browse(move_id)
                error_msg += _(
                    "\n\n"
                    "The move (%s) is not balanced.\n"
                    "The total of debits equals %s and the total of credits equals %s.\n"
                    "You might want to specify a default account on journal \"%s\" to automatically balance each move.",
                    move.display_name,
                    format_amount(self.env, sum_debit, move.company_id.currency_id),
                    format_amount(self.env, sum_credit, move.company_id.currency_id),
                    move.journal_id.name)
            raise UserError(error_msg)

        moves = self.filtered(lambda move: move.line_ids)
        if not moves:
            return

 #       self.env['account.move.line'].flush(['debit', 'credit', 'move_id'])
#        self.env['account.move'].flush(['journal_id'])
        self.env['account.move.line'].invalidate_cache(['debit', 'credit', 'move_id'])

        self._cr.execute('''
            SELECT line.move_id, ROUND(SUM(line.debit - line.credit), currency.decimal_places)
            FROM account_move_line line
            JOIN account_move move ON move.id = line.move_id
            JOIN account_journal journal ON journal.id = move.journal_id
            JOIN res_company company ON company.id = journal.company_id
            JOIN res_currency currency ON currency.id = company.currency_id
            WHERE line.move_id IN %s
            GROUP BY line.move_id, currency.decimal_places
            HAVING ROUND(SUM(line.debit - line.credit), currency.decimal_places) != 0.0;
        ''', [tuple(self.ids)])
        for record in self:
#            if record.journal_id.code=='LIQ':
            apunte=record.line_ids.filtered(lambda m: not m.account_id.reconcile)
            dif_asiento = record._cr.fetchall()
            if dif_asiento:
                _dif = [res[1] for res in dif_asiento][0]
                _credit = apunte.credit
                _debit = apunte.debit
                if _credit != 0:
                    _credit = apunte.credit + _dif
                if _debit != 0:
                    _debit = apunte.debit + _dif
                if not apunte.liquidacion_pass:
                    apunte.write({'credit': _credit,'debit':_debit,'liquidacion_pass':True})


    @contextmanager
    def _check_balanced(self, container):
        ''' Assert the move is fully balanced debit = credit.
        An error is raised if it's not the case.
        '''
        with self._disable_recursion(container, 'check_move_validity', default=True, target=False) as disabled:
            yield
            if disabled:
                return
        print(self)
        unbalanced_moves = self._get_unbalanced_moves(container)
        if unbalanced_moves:
            error_msg = _("An error has occurred.")
            for move_id, sum_debit, sum_credit in unbalanced_moves:
                move = self.browse(move_id)
                error_msg += _(
                    "\n\n"
                    "The move (%s) is not balanced.\n"
                    "The total of debits equals %s and the total of credits equals %s.\n"
                    "You might want to specify a default account on journal \"%s\" to automatically balance each move.",
                    move.display_name,
                    format_amount(self.env, sum_debit, move.company_id.currency_id),
                    format_amount(self.env, sum_credit, move.company_id.currency_id),
                    move.journal_id.name)
            raise UserError(error_msg)
        
    @api.model_create_multi
    def create(self, vals):
        rec = super(AccountMoveMC,self).create(vals)
        return rec

    def action_post(self):
        res = super(AccountMoveMC, self).action_post()
        return res
        


class Liquidaciones(models.Model):
    _name = 'liquidaciones.liquidaciones'
    _description = 'liquidaciones de facturas y cheques'
    _order = 'fecha desc'

    @api.depends('facturas','cheques','state')
    def _cacular_total_facturas(self):
        for record in self:
            if record.state=='conciliado':
                return
            record.total_facturas = 0
            #FACTURAS
            move_lines_facturas = record.facturas.line_ids.filtered(lambda m: m.account_id.reconcile  and m.move_id.move_type == 'in_invoice' and m.account_id.account_type == 'liability_payable'  )
            fac_debit  = sum(move_lines_facturas.mapped('debit'))
            fac_credit = sum(move_lines_facturas.mapped('credit'))
            record.total_facturas += (fac_credit-fac_debit)

    @api.depends('facturas','cheques','state')
    def _cacular_total_asientos(self):
        for record in self:
            if record.state=='conciliado':
                 return
            record.total_asientos = 0
            move_lines_facturas = record.facturas.line_ids.filtered(lambda m: m.account_id.reconcile and m.move_id.move_type == 'entry' and m.account_id.account_type == 'liability_payable')

            fac_debit  = sum(move_lines_facturas.mapped('debit'))
            fac_credit = sum(move_lines_facturas.mapped('credit'))
            record.total_asientos += (fac_credit-fac_debit)


    @api.depends('cheques','facturas','state')
    def _cacular_total_cheques(self):
        for record in self:
            if record.state=='conciliado':
                return
            record.total_cheques = 0
            move_lines_cheques = record.cheques.move_id.line_ids.filtered(lambda m: m.account_id.reconcile and m.account_id.account_type == 'liability_payable')
            che_debit  = sum(move_lines_cheques.mapped('debit'))
            che_credit = sum(move_lines_cheques.mapped('credit'))
            record.total_cheques -= (che_debit-che_credit)

    @api.depends('cheques','facturas','state')
    def _cacular_total_descuadre(self):
        for record in self:
            if record.state=='conciliado':
                return
            record.total_descuadre = (record.total_facturas+record.total_asientos+record.total_cheques)

    fecha = fields.Date(string="Fecha", required=True)
    name = fields.Char(string="Descripcion", required=True)
    facturas = fields.One2many("account.move", "liquidaciones_id", string="Facturas")
    cheques = fields.One2many("account.payment", "liquidaciones_id", string="Cheques")
    #company_id = fields.Many2one("res.company", string="Company")
    company_id  = fields.Many2one('res.company', string='Empresa', required=True, readonly=True,default=lambda self: self.env.company)

    diario = fields.Many2one("account.journal", string="Diario", required=True)
    asiento = fields.Many2one("account.move", string="Asiento")
    #usuario_id = fields.Many2one("res.users", string="Usuario")
    usuario_id  = fields.Many2one('res.users', string='Usuario', required=True, readonly=True,default=lambda self: self.env.user)

    cuenta_desajuste = fields.Many2one("account.account", string="Cuenta de desajuste")
    state = fields.Selection(selection=[
        ('abierto', 'Abierto'),
        ('conciliado', 'Conciliado')
    ], string='Status', required=True, readonly=True, copy=False,
        default='abierto')
    company_currency_id = fields.Many2one(related='company_id.currency_id', string='Company Currency',
                                          readonly=True, store=True,
                                          help='Utility field to express amount currency')
    total_facturas = fields.Float('Total facturas', digits=dp.get_precision('Total descuadre'),compute=_cacular_total_facturas, store=True)
    total_asientos = fields.Float('Total asientos contables', digits=dp.get_precision('Total descuadre'),compute=_cacular_total_asientos , store=True)
    total_cheques = fields.Float('Total cheques',digits=dp.get_precision('Total descuadre'),compute=_cacular_total_cheques , store=True)
    total_descuadre = fields.Float(string='Total descuadre', default=0.0, digits=dp.get_precision('Total descuadre'),compute=_cacular_total_descuadre , store=True)

    move_line_ids = fields.One2many("account.move.line", "liquidaciones_id", string="Apuntes")


    def conciliar(self):
        for rec in self:
#            if rec.diario.code != 'LIQ':
#                raise UserError('Tener un diario liquidaciones...' )

            apuntes = []

            fdebit = 0
            move_lines_facturas = self.facturas.line_ids.filtered(lambda m: m.account_id.reconcile and m.account_id.account_type == 'liability_payable' and not m.reconciled and m.move_id.move_type in ('in_invoice','entry'))
            apuntes.append(move_lines_facturas)
            fac_debit = sum(move_lines_facturas.mapped('debit'))
            fac_credit = sum(move_lines_facturas.mapped('credit'))
            total = fac_credit-fac_debit
            fcredit = fac_credit-fac_debit


            move_lines_facturas = self.cheques.move_id.line_ids.filtered(lambda m: m.account_id.reconcile and m.account_id.account_type == 'liability_payable' and not m.reconciled )
            apuntes.append(move_lines_facturas)
            che_debit = sum(move_lines_facturas.mapped('debit'))
            che_credit = sum(move_lines_facturas.mapped('credit'))
            total -= che_debit - che_credit
            fdebit -= che_debit - che_credit
#           raise UserError('El cheque %s ya esta conciliado' % (c.name))
            nuevas_lineas = []

            for apunte in apuntes:
                for linea in apunte:
                    nuevas_lineas.append((0, 0, {
                    'name': linea.name,
                    'debit': linea.credit,
                    'credit': linea.debit,
                    'account_id': linea.account_id.id,
                    'partner_id': linea.partner_id.id,
                    'journal_id': rec.diario.id,
                    'date_maturity': rec.fecha,
                    'liquidaciones_id':self.id,
                    }))
                    linea.write({'liquidaciones_id': self.id})
            if total != 0:
                nuevas_lineas.append((0, 0, {
                    'name': 'Diferencial en ' + rec.name,
                    'debit': -1 * self.total_descuadre if self.total_descuadre < 0 else 0,
                    'credit': self.total_descuadre if self.total_descuadre > 0 else 0,
                    'account_id': rec.cuenta_desajuste.id,
                    'date_maturity': rec.fecha,
                    'liquidaciones_id': self.id,
                }))
                linea.write({'liquidaciones_id': self.id})

            move = self.env['account.move'].create({
                'line_ids': nuevas_lineas,
                'ref': rec.name,
                'date': rec.fecha,
                'journal_id': rec.diario.id,
                'company_id': rec.diario.company_id.id

            })


            move.action_post()
            self.env['account.move.line'].search([('liquidaciones_id', '=', self.id),('parent_state', '=', 'posted'),
                                                  ('account_id.reconcile', '=', True) , ('account_id.account_type', '=', 'liability_payable') ]).sorted(
                key='partner_id').reconcile()
            #move.post()
            self.write({'asiento': move.id, 'state':'conciliado'})
        return True

    
    def cancelar(self):
        for rec in self:
            rec.facturas.line_ids.filtered(lambda m: m.account_id.reconcile  and m.account_id.account_type == 'liability_payable' and m.move_id.move_type == 'in_invoice').write({'liquidaciones_id':  self.id})
            rec.cheques.move_id.line_ids.filtered(lambda m: m.account_id.reconcile ).write({'liquidaciones_id':  self.id})
 
            rec.env['account.move.line'].search([('liquidaciones_id', '=', self.id), ('account_id.reconcile', '=',True) , ('account_id.account_type', '=', 'liability_payable')]).sorted(key='partner_id').remove_move_reconcile()

            rec.asiento.button_draft()
            rec.asiento.button_cancel()
            for line in rec.asiento.line_ids:
                line.write({'liquidaciones_id': None })

            rec.write({'asiento': rec.asiento.id, 'state': 'abierto'})

        return True
