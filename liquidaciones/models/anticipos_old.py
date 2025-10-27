# -*- encoding: utf-8 -*-

from odoo.addons import decimal_precision as dp
from odoo import models, fields, api,_
from jinja2.lexer import _describe_token_type
#from dateutil import relativedelta
from dateutil.relativedelta import relativedelta
from maxminddb.types import Record
from pip._vendor.rich.progress import track
from pip._vendor.pkg_resources import require
from datetime import datetime,timedelta
import time
import pytz
from odoo.tools import float_round

from odoo.exceptions import UserError ,ValidationError



class AccountMoveMC(models.Model):
    _name = "account.move"
    _inherit = "account.move"

    anticipo_id = fields.Many2one("liquidaciones.anticipos", string="Anticipos", )

class AccountMoveLineMC(models.Model):
    _name = "account.move.line"
    _inherit = "account.move.line"

    anticipo_id = fields.Many2one("liquidaciones.anticipos", string="Anticipos", )

class AccountPayment(models.Model):
    _inherit = 'account.payment'

    anticipo_id = fields.Many2one("liquidaciones.anticipos", string="Anticipos", ) 

class LiquidacionesAnticipos(models.Model):
    _name = 'liquidaciones.anticipos'
    _description = 'Anticipos'
    _order = 'date desc'



    def unlink(self):
        for record in self: 
            if record.state=='conciliado': 
                raise UserError(_("No puede borrar si esta conciliado..."))
        return super(LiquidacionesAnticipos, self).unlink()
    


    @api.depends('account_partner_id','invoice_ids','state','payment_ids','account_ajuste_id','account_anticipo_id')
    def _cacular_total_facturas(self):
        for record in self:
            #FACTURAS
            #FACTURAS DE PROVEEDOR
            if record.account_partner_id.account_type == 'liability_payable' and record.account_anticipo_id.account_type == 'asset_receivable':
                move_lines_facturas = record.invoice_ids.line_ids.filtered(lambda m: m.account_id.reconcile and m.account_id.id == record.account_partner_id.id)
                _credit = sum(move_lines_facturas.mapped('credit'))
                record.total_facturas = _credit


    @api.depends('account_anticipo_id','payment_ids','state')
    def _cacular_total_cheques(self):
        for record in self:
            if record.account_anticipo_id.account_type == 'asset_receivable' and record.account_partner_id.account_type == 'liability_payable':
                move_lines_cheques = record.payment_ids.move_id.line_ids.filtered(lambda m: m.account_id.reconcile and m.account_id.id == record.account_anticipo_id.id)
                ch_debit = sum(move_lines_cheques.mapped('debit'))
                record.total_cheques = ch_debit


    @api.depends('payment_ids','invoice_ids','state')
    def _cacular_total_descuadre(self):
        for record in self:
            if record.state=='conciliado':
                return
            record.total_descuadre = (record.total_facturas-record.total_cheques)


    @api.depends('partner_id')
    def _cacular_company(self):
        for record in self: 
            record.company_id = record.partner_id.company_id.id
 


    date = fields.Date(string="Fecha", required=True)
    name = fields.Char(string="Descripcion", required=True)

    invoice_ids = fields.One2many("account.move", "anticipo_id", string="Facturas")
    payment_ids = fields.One2many("account.payment", "anticipo_id", string="Cheques")

    #company_id = fields.Many2one("res.company", string="Company",compute=_cacular_company , store=True)
    company_id  = fields.Many2one('res.company', string='Empresa', required=True, readonly=True,default=lambda self: self.env.company)

    journal_id = fields.Many2one("account.journal", string="Diario", required=True)
    move_id = fields.Many2one("account.move", string="Asiento")
#    usuario_id = fields.Many2one("res.users", string="Usuario")
    usuario_id  = fields.Many2one('res.users', string='Usuario', required=True, readonly=True,default=lambda self: self.env.user)

    partner_id = fields.Many2one("res.partner", string="Cliente/Proveedor")
    account_ajuste_id = fields.Many2one("account.account", string="Cuenta de desajuste")
    account_partner_id = fields.Many2one("account.account", string="Cuenta de Cliente/Proveedor")
    account_anticipo_id = fields.Many2one("account.account", string="Cuenta de anticipo")
    state = fields.Selection(selection=[
        ('abierto', 'Abierto'),
        ('conciliado', 'Conciliado')
    ], string='Status', required=True, readonly=True, copy=False,
        default='abierto')

    total_facturas = fields.Float('Total facturas', digits=dp.get_precision('Total descuadre'),compute=_cacular_total_facturas, store=True)
    total_cheques = fields.Float('Total cheques',digits=dp.get_precision('Total descuadre'),compute=_cacular_total_cheques , store=True)
    total_descuadre = fields.Float(string='Total descuadre', default=0.0, digits=dp.get_precision('Total descuadre'),compute=_cacular_total_descuadre , store=True)
    x_conciliado = fields.Boolean(string='Conciliado',default=False)


    def conciliar(self):
        for record in self:
            #if record.state != 'abierto':
            #    continue


            zona_gt = pytz.timezone('America/Guatemala')
            fecha_actual =   datetime.now(zona_gt).date()
            _debito = 0.00
            _credito = 0.00
            nuevas_lineas = []
            #ANTICIPOS DE PROVEEDOR
            if record.account_partner_id.account_type == 'liability_payable' and record.account_anticipo_id.account_type == 'asset_receivable':
                move_lines_ids = record.payment_ids.move_id.line_ids.filtered(lambda m: m.account_id.id == record.account_anticipo_id.id and m.account_id.reconcile and m.account_id.account_type == 'asset_receivable' and m.parent_state == 'posted' )
                for l in move_lines_ids: 
                    l.anticipo_id = record.id
                move_lines_ids = record.invoice_ids.line_ids.filtered(lambda m: m.account_id.id == record.account_partner_id.id and m.account_id.reconcile and m.account_id.account_type == 'liability_payable' and m.move_id.move_type == 'in_invoice'   and m.parent_state == 'posted' )
                for l in move_lines_ids: 
                    l.anticipo_id = record.id 

                nuevas_lineas = []
                nuevas_lineas.append((0, 0, {
                    'name': record.name,
                    'debit': record.total_facturas,
                    'credit': 0.00,
                    'account_id': record.account_partner_id.id,
                    'partner_id': record.partner_id.id,
                    'journal_id': record.journal_id.id,
                    'date_maturity': fecha_actual,
                    'anticipo_id':record.id,
                    }))
                nuevas_lineas.append((0, 0, {
                    'name': record.name,
                    'debit': 0.00,
                    'credit': abs(record.total_cheques),
                    'account_id': record.account_anticipo_id.id,
                    'partner_id': record.partner_id.id,
                    'journal_id': record.journal_id.id,
                    'date_maturity': fecha_actual,
                    'anticipo_id':record.id,
                    }))

                move = self.env['account.move'].create({
                    'line_ids': nuevas_lineas,
                    'ref': record.name,
                    'date': fecha_actual,
                    'journal_id': record.journal_id.id,
                    'company_id': record.company_id.id,
                    })
                move.action_post()
                #reconcilia cuenta por cobrar
                self.env['account.move.line'].search([('anticipo_id', '=', record.id),('account_id', '=', record.account_partner_id.id),('parent_state','=','posted') ]).sorted(key='partner_id').reconcile()
                #reconcilia cuenta por pagar (anticipos)
                self.env['account.move.line'].search([('anticipo_id', '=', record.id),('account_id', '=', record.account_anticipo_id.id),('parent_state','=','posted') ]).sorted(key='partner_id').reconcile()
                record.state = 'conciliado'      
                record.x_conciliado = True          
                record.move_id = move.id 


    def cancelar(self):
        for rec in self:
            if not rec.move_id:
                continue
            rec.invoice_ids.line_ids.filtered(lambda m: m.account_id.reconcile  and m.account_id.account_type == 'liability_payable' and m.move_id.move_type == 'in_invoice').write({'anticipo_id':  self.id})
            rec.payment_ids.move_id.line_ids.filtered(lambda m: m.account_id.reconcile ).write({'anticipo_id':  self.id})
 
            rec.env['account.move.line'].search([('anticipo_id', '=', self.id), ('account_id.reconcile', '=',True) ,]).sorted(key='partner_id').remove_move_reconcile()


            rec.move_id.button_draft()
            rec.move_id.button_cancel()
            for line in rec.move_id.line_ids:
                line.write({'anticipo_id': None })

            #rec.write({'asiento': rec.asiento.id, 'state': 'abierto'})

        return True

