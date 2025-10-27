# -*- encoding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime
from . import util


class AccountBankStatementMC(models.Model):
    _name = "account.bank.statement"
    _inherit = 'account.bank.statement'


    def button_validate(self):
        if any(statement.state != 'posted' or not statement.all_lines_reconciled for statement in self):
            raise UserError(_('All the account entries lines must be processed in order to validate the statement.'))

        for statement in self:

            # Chatter.
            statement.message_post(body=_('Statement %s confirmed.', statement.name))
 

        self._check_balance_end_real_same_as_computed()
        self.write({'state': 'confirm', 'date_done': fields.Datetime.now()})

class AccountPayment(models.Model):
    
    _name = 'account.payment'
    _inherit = 'account.payment'

    @api.depends('x_no_negociable')
    def _calcular_frase_letras(self):
        for pay in self:
            if pay.x_no_negociable:
                pay.x_frase_no_negociable = "** NO NEGOCIABLE **"
            else:
                pay.x_frase_no_negociable = " "

    @api.depends('date')
    def _calcular_fecha_letras(self):
        for pay in self:
            if pay.date:
               pay.x_fecha_letras =  util.fecha_a_letras(pay.date)
            else:
                pay.x_fecha_letras = ''

    @api.depends('date')
    def _calcular_fecha_letras2(self):
        for pay in self:
            if pay.date:
                pay.x_fecha_letras2 =  util.fecha_a_letras(pay.date)
            else:
                pay.x_fecha_letras2 = ''

    #@api.one
    @api.depends('amount')
    def _calcular_letras(self):
        for record in self:
            record.numeros_a_letras =  util.num_a_letras(record.amount)

    #@api.one
    @api.depends('amount')
    def _calcular_letras_dolar(self):
        for record in self:
            record.numeros_a_letras_dolar =  util.num_a_letras_dolar(record.amount)

    #@api.one
    def _calcular_fechas(self):
        for record in self:
            record.x_fecha_pago =  'Guatemala, ' +str(record.date.day)+' de '+util.mes_a_letras(record.date.month)+' de '+str(record.date.year)


    def action_post_17(self):
        res = super(AccountPayment, self).action_post()
        payment_method_check = self.env.ref('account_check_printing.account_payment_method_check')
        for payment in self.filtered(lambda p: p.payment_method_id == payment_method_check and p.check_manual_sequencing):
            if not payment.check_number:
                sequence = payment.journal_id.check_sequence_id
                payment.check_number = sequence.next_by_id()
        return res

    #@api.onchange('partner_id')
    #def _onchange_partner_id(self):
    #    if not self.x_account_id and self.payment_type == 'outbound':
    #        self.x_account_id = self.partner_id.property_account_payable_id.id

    #@api.multi
    def unlink17(self):
        if any(bool(rec.move_line_ids) for rec in self):
            raise UserError(_("You can not delete a payment that is already posted"))
        if self.ids:
            for i in self.ids:
                _payment_id = self.env['account.payment'].browse(i)
                if _payment_id.state == 'draft':
                    _payment_id.write({'move_name':""}) 
                    print(_payment_id.move_name)

        return super(AccountPayment, self).unlink()


    @api.depends('amount')
    def _calcular_importe_dos_decinales(self):
        for rec in self:
            rec.x_importe_2decimal = format(rec.amount, ',.2f')
            #rec.x_importe_2decimal = rec.currency_id.symbol+' '+format(rec.amount, ',.2f')



    x_recibo_caja = fields.Char('Recibo de caja' , copy=False)
    x_deposito = fields.Char('No. deposito', copy=False)
    x_cheque_manual = fields.Char('No. cheque manual', copy=False)
    numeros_a_letras = fields.Char('Letras', compute=_calcular_letras,store=True, copy=False)
    #numeros_a_letras = fields.Char('Letras')

    numeros_a_letras_dolar = fields.Char('Letras Dolar', compute=_calcular_letras_dolar,store=True, copy=False)
    #numeros_a_letras_dolar = fields.Char('Letras')

    x_frase_no_negociable = fields.Char('Frase no negociable')
    x_frase_no_negociable = fields.Char('Frase no negociable',compute=_calcular_frase_letras,store=True, copy=False)

    x_no_negociable = fields.Boolean('NO NEGOCIABLE : ', default=True , copy=False)
    x_account_id = fields.Many2one('account.account', string='Cuenta')
    x_fecha_recibo = fields.Date(string='Fecha recibo' , copy=False)
    x_emitir_otro = fields.Char(string='Emitir cheque a ')
    x_fecha_pago = fields.Char(string='Fecha Letras',compute=_calcular_fechas, copy=False,store=True)
    #x_fecha_pago = fields.Char(string='Fecha Letras',)

    destination_account_id = fields.Many2one(
        comodel_name='account.account',
        string='Destination Account',
        store=True, readonly=False,
        compute='_compute_destination_account_id',
        domain="[('account_type', 'in', ('asset_receivable', 'liability_payable'))]",
        check_company=True)


    x_fecha_letras = fields.Char('Fecha letras', compute=_calcular_fecha_letras, copy=False, store=True)
    #x_fecha_letras = fields.Char('Fecha letras', )

    x_fecha_letras2 = fields.Char('Fecha letras 2', compute=_calcular_fecha_letras2, copy=False, store=True)
    #x_fecha_letras2 = fields.Char('Fecha letras 2', )

    x_importe_2decimal = fields.Char('Importe 2decimales', compute=_calcular_importe_dos_decinales, copy=False,store=True)
    #x_importe_2decimal = fields.Char('Importe 2decimales', )

    x_account_id = fields.Many2one('account.account', string='Cuenta',domain="[('cambia_en_pagos','=',True)]",)

    #x_account_id = fields.Many2one('account.account', string='Cuenta')

    #x_cuentas_pagos_id = fields.Many2one('mc_guatemala.cuentas_pagos', string='Tipo cuenta')


    x_cuentas_pagos_id = fields.Many2one(
        'mc_guatemala.cuentas_pagos',
        string='Cuenta/pagos',
        domain="[('payment_type', '=', payment_type ),('partner_id', '=', partner_id ) ]",
    )
    amount_currency = fields.Monetary('Monto moneda')
  

    manual_currency_rate_active = fields.Boolean('Aplica tipo cambio manual')
    manual_currency_rate = fields.Float('Tasa', digits=(12, 6))
    amount_currency = fields.Monetary('Monto moneda')
    check_active_currency = fields.Boolean('Verifique moneda activa')
                
    @api.onchange('x_cuentas_pagos_id')
    def _onchange_x_cuenta_id(self):
        for record in self:
            if record.x_cuentas_pagos_id:
                record.x_account_id = record.x_cuentas_pagos_id.account_id.id
                

    @api.depends('partner_id','payment_type')
    def _compute_cuenta_pagos_id(self):
        for record in self.filtered(lambda r: r.journal_id.type not in r._get_valid_journal_types()):
            record.journal_id = record._search_default_journal()




    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        if not self.x_account_id and self.payment_type == 'outbound':
            self.x_account_id = self.partner_id.property_account_payable_id.id
        if not self.x_account_id and self.payment_type == 'inbound':
            self.x_account_id = self.partner_id.property_account_receivable_id.id


#    @api.onchange('partner_id')
#    def _onchange_partner_id(self):
#        if not self.x_account_id and self.payment_type == 'outbound':
#            self.x_account_id = self.partner_id.property_account_payable_id.id


    def _compute_check_number(self):
        for pay in self:
            if not pay.check_number:
                if pay.journal_id.check_manual_sequencing and pay.payment_method_code == 'check_printing':
                    sequence = pay.journal_id.check_sequence_id
                    pay.check_number = sequence.get_next_char(sequence.number_next_actual)
                else:
                    pay.check_number = False

    def _inverse_check_number(self):
        for payment in self:
            if not payment.check_number:
                if payment.check_number:
                    sequence = payment.journal_id.check_sequence_id.sudo()
                    sequence.padding = len(payment.check_number)

    @api.depends('journal_id', 'partner_id', 'partner_type','x_cuentas_pagos_id','x_account_id')
    def _compute_destination_account_id(self):
        self.destination_account_id = False
        for pay in self:
            if pay.partner_type == 'customer':
                # Receive money from invoice or send money to refund it.
                if pay.partner_id:
                    pay.destination_account_id = pay.partner_id.with_company(pay.company_id).property_account_receivable_id
                    if pay.x_account_id.id != pay.destination_account_id.id:
                        pay.destination_account_id = pay.x_account_id
                    else:
                        pay.destination_account_id = pay.partner_id.property_account_receivable_id
                else:
                    pay.destination_account_id = self.env['account.account'].with_company(pay.company_id).search([
                        *self.env['account.account']._check_company_domain(pay.company_id),
                        ('account_type', '=', 'asset_receivable'),
                        ('deprecated', '=', False),
                    ], limit=1)
            elif pay.partner_type == 'supplier':
                # Send money to pay a bill or receive money to refund it.
                if pay.partner_id:
                    pay.destination_account_id = pay.partner_id.with_company(pay.company_id).property_account_payable_id
                    if pay.x_account_id.id !=pay.destination_account_id.id:
                        pay.destination_account_id = pay.x_account_id
                    else:
                        pay.destination_account_id = pay.partner_id.property_account_payable_id
                else:
                    pay.destination_account_id = self.env['account.account'].with_company(pay.company_id).search([
                        *self.env['account.account']._check_company_domain(pay.company_id),
                        ('account_type', '=', 'liability_payable'),
                        ('deprecated', '=', False),
                    ], limit=1)


    @api.constrains('check_number', 'journal_id')
    def _constrains_check_number(self):
        print(self)
        return

    def _constrains_check_number2(self):
        if not self:
            return
        try:
            self.mapped(lambda p: str(int(p.check_number)))
        except ValueError:
            raise ValidationError(_('Check numbers can only consist of digits'))
        self.flush()
        self.env.cr.execute("""
            SELECT payment.check_number, move.journal_id
              FROM account_payment payment
              JOIN account_move move ON move.id = payment.move_id
              JOIN account_journal journal ON journal.id = move.journal_id,
                   account_payment other_payment
              JOIN account_move other_move ON other_move.id = other_payment.move_id
             WHERE payment.check_number::INTEGER = other_payment.check_number::INTEGER
               AND move.journal_id = other_move.journal_id
               AND payment.id != other_payment.id
               AND payment.id IN %(ids)s
               AND move.state = 'posted'
               AND other_move.state = 'posted'
        """, {
            'ids': tuple(self.ids),
        })
        res = self.env.cr.dictfetchall()
        if res:
            raise ValidationError(_(
                'The following numbers are already used:\n%s',
                '\n'.join(_(
                    '%(number)s in journal %(journal)s',
                    number=r['check_number'],
                    journal=self.env['account.journal'].browse(r['journal_id']).display_name,
                ) for r in res)
            ))