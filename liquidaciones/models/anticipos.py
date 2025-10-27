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

    anticipo_id =      fields.Many2one("liquidaciones.anticipos", string="Anticipos", readonly=False, states={'paid': [('readonly', True)]}, ondelete='restrict' )

class AccountMoveLineMC(models.Model):
    _name = "account.move.line"
    _inherit = "account.move.line"

    anticipo_id = fields.Many2one("liquidaciones.anticipos", string="Anticipos", )

class AccountPayment(models.Model):
    _inherit = 'account.payment'

    anticipo_id = fields.Many2one("liquidaciones.anticipos", string="Anticipos",readonly=False, states={'reconciled': [('readonly', True)]}, ondelete='restrict' ) 

 
class LiquidacionesAnticipos(models.Model):
    _name = 'liquidaciones.anticipos'
    _description = 'Anticipos'
    _order = 'date desc'



    def unlink(self):
        for record in self: 
            if record.state=='conciliado': 
                raise UserError(_("No puede borrar si esta conciliado..."))
        return super(LiquidacionesAnticipos, self).unlink()
    

    date = fields.Date(string="Fecha", required=True)
    name = fields.Char(string="Descripcion", required=True)
    invoice_ids = fields.One2many("account.move", "anticipo_id", string="Facturas")
    payment_ids = fields.One2many("account.payment", "anticipo_id", string="Cheques")
    company_id  = fields.Many2one('res.company', string='Empresa', required=True, readonly=True,default=lambda self: self.env.company)
    journal_id = fields.Many2one("account.journal", string="Diario", required=True)
    move_id = fields.Many2one("account.move", string="Asiento")
    usuario_id  = fields.Many2one('res.users', string='Usuario', required=True, readonly=True,default=lambda self: self.env.user)
    partner_id = fields.Many2one("res.partner", string="Proveedor")
    account_ajuste_id = fields.Many2one("account.account", string="Cuenta de desajuste")
    account_partner_id = fields.Many2one("account.account", string="Cuenta de Cliente/Proveedor")
    account_anticipo_id = fields.Many2one("account.account", string="Cuenta de anticipo")
    state = fields.Selection(selection=[
        ('abierto', 'Abierto'),
        ('conciliado', 'Conciliado')
    ], string='Status', required=True, readonly=True, copy=False,
        default='abierto')
    total_facturas = fields.Float('Creditos', digits=dp.get_precision('Total descuadre'),compute='_total_facturas', store=True,)
    total_cheques = fields.Float('Debitos',digits=dp.get_precision('Total descuadre'),compute='_total_cheques', store=True,)
    total_descuadre = fields.Float(string='Saldo', default=0.0, digits=dp.get_precision('Total descuadre'),compute='_total_descuadre', store=True,)
    x_conciliado = fields.Boolean(string='Conciliado',default=False)
    anticipo_line_ids = fields.One2many(comodel_name='liquidaciones.anticipos.detalle', inverse_name='anticipo_id', string='Detalle')


    @api.depends('anticipo_line_ids',)
    def _total_facturas(self):
        _total_facturas = 0
        for record in self.anticipo_line_ids:
            _total_facturas += record.credit
        self.total_facturas = _total_facturas

    @api.depends('anticipo_line_ids',)
    def _total_cheques(self):
        _total_cheques = 0
        for record in self.anticipo_line_ids:
            _total_cheques += record.debit
        self.total_cheques = _total_cheques

    @api.depends('anticipo_line_ids')
    def _total_descuadre(self):
        _total_descuadre = 0
        for record in self:
            _total_descuadre = record.total_cheques - record.total_facturas
        record.total_descuadre = _total_descuadre

    def cancelar(self):
        for record in self:
            record.move_id.button_draft()
            record.move_id.unlink()
            apuntes_ids = self.env['account.move.line'].search([('anticipo_id', '=', record.id)])
            apuntes_ids.remove_move_reconcile()
            for r in apuntes_ids:
                r.write({'anticipo_id': None})
            self.env["liquidaciones.anticipos.detalle"].search([('anticipo_id','=',record.id)]).unlink()
            record.state = 'abierto'
            record.total_facturas = 0
            record.total_cheques = 0
            record.total_descuadre = 0
 
    def conciliar(self):
        for record in self:
            if  record.anticipo_line_ids:
                nuevas_lineas = []              
                for line in record.anticipo_line_ids:
                    nuevas_lineas.append((0, 0, {
                        'name': record.name,
                        'debit':  line.apunte_id.credit  if line.apunte_id.credit !=0 else 0 ,
                        'credit': line.apunte_id.debit   if line.apunte_id.debit  !=0 else 0 ,
                        'account_id': line.apunte_id.account_id.id,
                        'partner_id': record.partner_id.id,
                        'journal_id': record.journal_id.id,
                        'date_maturity': record.date,
                        'anticipo_id': record.id,
                        }))
                if record.total_descuadre != 0:
                    nuevas_lineas.append((0, 0, {
                       'name': 'Diferencial en ' + record.name,
                       'debit': record.total_descuadre if record.total_descuadre > 0 else 0,
                       'credit': -1 * record.total_descuadre if record.total_descuadre < 0 else 0,
                       'account_id': record.account_ajuste_id.id,
                       'partner_id': record.partner_id.id,
                       'date_maturity': record.date,
                    }))
                move = self.env['account.move'].create({
                    'line_ids': nuevas_lineas,
                    'ref': record.name,
                    'date': record.date,
                    'journal_id': record.journal_id.id,
                    'company_id': record.company_id.id,
                    'anticipo_id': record.id,
                    })
                move.action_post()
                record.move_id = move.id 
                for rec in move.line_ids:
                    if not rec.anticipo_id:
                        _conciliado = 'NO'
                    else:
                        _conciliado = rec.matching_number
                    detalle = {'anticipo_id':record.id,
                            'apunte_id':rec.id,
                            'move_id':rec.move_id.id,
                            'account_id':rec.account_id.id,
                            'date':rec.date,
                            'etiqueta':rec.name,
                            'debit':rec.debit,
                            'credit':rec.credit,
                            'saldo':rec.amount_residual,
                            'conciliado':_conciliado,
                            }
                    self.env['liquidaciones.anticipos.detalle'].create(detalle)
                #facturas
                credit_ids = self.env['account.move.line'].search([('id','in',record.anticipo_line_ids.apunte_id.ids),('account_id','=',record.account_partner_id.id),('anticipo_id','=',record.id)])
                credit_ids.reconcile()
                #pagos
                debit_ids = self.env['account.move.line'].search([('id','in',record.anticipo_line_ids.apunte_id.ids),('account_id','=',record.account_anticipo_id.id),('anticipo_id','=',record.id)])
                debit_ids.reconcile()
                record.state = 'conciliado'

    def apuntes(self):
        for record in self:
            if record.state == 'conciliado':
                raise UserError(_("Anticipo ya conciliado....."))
                continue
            self.env["liquidaciones.anticipos.detalle"].search([('anticipo_id','=',record.id)]).unlink()
            apuntes_ids = self.env['account.move.line'].search([('anticipo_id', '=', record.id)])
            for r in apuntes_ids:
                r.write({'anticipo_id': None})

            apuntes_conciliar_ids = self.env['account.move.line'].search([('account_id', 'in', (record.account_partner_id.id, record.account_anticipo_id.id )),('parent_state','=','posted'),('amount_residual','!=',0),('partner_id','=',record.partner_id.id) ]).filtered(lambda x: x.balance or x.amount_currency)

            for rec in apuntes_conciliar_ids:

                rec.write({'anticipo_id': record.id})

                detalle = {'anticipo_id':record.id,
                            'apunte_id':rec.id,
                            'move_id':rec.move_id.id,
                            'account_id':rec.account_id.id,
                            'date':rec.date,
                            'etiqueta':rec.name,
                            'debit':rec.debit,
                            'credit':rec.credit,
                            'saldo':rec.amount_residual,
                            'conciliado':rec.matching_number,
                            }
                self.env['liquidaciones.anticipos.detalle'].create(detalle)
#            _total_facturas = round(sum(record.anticipo_line_ids.mapped('credit')),2)
#            _total_cheques  = round(sum(record.anticipo_line_ids.mapped('debit')),2)
#            _total_descuadre = round((_total_cheques - _total_facturas),2)
#            record.total_facturas = _total_facturas
#            record.total_cheques  = _total_cheques
#            record.total_descuadre = _total_descuadre
 

class LiquiacionAnticiposDetalle(models.Model):
    _name = 'liquidaciones.anticipos.detalle'
    _description = 'Detalle Anticipos'
    _order = 'account_id'

    anticipo_id = fields.Many2one(comodel_name='liquidaciones.anticipos', string='Anticipo')
    apunte_id   = fields.Many2one("account.move.line", string="Apunte")
    move_id     = fields.Many2one("account.move", string="Asiento")
    account_id  = fields.Many2one("account.account", string="Cuenta")
    date        = fields.Date(string='Fecha',default=fields.Date.context_today,)
    etiqueta    = fields.Char(string='Etiqueta')
    debit       = fields.Float(string='Debito',)
    credit       = fields.Float(string='Credito',)
    saldo       = fields.Float(string='Saldo',)
    conciliado  = fields.Char(string='Concilado')

    def unlink(self):
        for record in self: 
            record.apunte_id.write({'anticipo_id': None})
            print(record)
        ret = super(LiquiacionAnticiposDetalle, self).unlink()
        return ret

#            if record.state=='conciliado': 
#                raise UserError(_("No puede borrar si esta conciliado..."))
#        return super(LiquidacionesAnticipos, self).unlink()