# -*- encoding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from . import util


class SaleOrder(models.Model):
    _name = 'sale.order'
    _inherit = 'sale.order'

    @api.depends('amount_total')
    def _calcular_dos_decinales(self):
        for rec in self:
            rec.x_amount_total_2decimal = rec.currency_id.symbol+' '+format(rec.amount_total, ',.2f')

#16    x_amount_total_2decimal = fields.Char('Total 2decimales', compute=_calcular_dos_decinales, copy=False,store=True)
    x_amount_total_2decimal = fields.Char('Total 2decimales', )

class SaleOrderLine(models.Model):
    _name = 'sale.order.line'
    _inherit = 'sale.order.line'

    @api.depends('price_total')
    def _calcular_dos_decinales(self):
        for rec in self:
            rec.x_price_total_2decimal = rec.currency_id.symbol+' '+format(rec.price_total, ',.2f')

#16    x_price_total_2decimal = fields.Char('Price total 2decimales', compute=_calcular_dos_decinales, copy=False,
#                                                 store=True)
    x_price_total_2decimal = fields.Char('Price total 2decimales', )

