# -*- coding: utf-8 -*-
# Part of AlmightyCS. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api
import odoo.addons.decimal_precision as dp


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'
 
    @api.depends('currency_id', 'company_id.currency_id')
    def _compute_not_company_currency(self):
        for rec in self:
            rec.not_company_currency = rec.currency_id and rec.currency_id != rec.company_id.currency_id

    @api.depends('amount_total', 'custom_rate')
    def _compute_amount_total_company_currency(self):
        for rec in self:
            if rec.not_company_currency and rec.use_custom_rate:
                rec.amount_total_company_currency = rec.amount_total * (rec.custom_rate or 1)
            elif rec.not_company_currency:
                rec.amount_total_company_currency = rec.amount_total * (rec.acs_currency_rate or 1)
            else:
                rec.amount_total_company_currency = rec.amount_total

    @api.depends('currency_id')
    def _acs_compute_currency_rate(self):
        for rec in self:
            rec.acs_currency_rate = 1 / (rec.currency_rate or 1)

    not_company_currency = fields.Boolean('Use Custom Currency Rate', compute='_compute_not_company_currency')
    use_custom_rate = fields.Boolean('Use Custom Rate')
    custom_rate = fields.Float(string='Custom Rate', digits=(12, 6), readonly=True)
    acs_currency_rate = fields.Float(string="System Currency Rate", compute='_acs_compute_currency_rate', digits=(12, 6))
    amount_total_company_currency = fields.Float(
        compute='_compute_amount_total_company_currency')
    company_currency_id = fields.Many2one("res.currency", related='company_id.currency_id', 
        string="System Currency")

    @api.onchange('currency_id','use_custom_rate')
    def onchange_currency(self):
        self.custom_rate = self.currency_id and self.currency_id.with_context(data=self.date_order).rate or 1

    def _prepare_invoice(self):
        result = super(PurchaseOrder, self)._prepare_invoice()
        result.update({
            'use_custom_rate': self.use_custom_rate,
            'custom_rate': self.custom_rate,
            'currency_id': self.currency_id and self.currency_id.id or False,
        })
        return result


class AccountMove(models.Model):
    _inherit = 'account.move'

    @api.onchange('purchase_vendor_bill_id', 'purchase_id')
    def _onchange_purchase_auto_complete(self):
        purchase_id = self.purchase_id or self.purchase_vendor_bill_id and self.purchase_vendor_bill_id.purchase_order_id
        if purchase_id:
            self.not_company_currency = purchase_id.not_company_currency
            self.use_custom_rate = purchase_id.use_custom_rate
            self.custom_rate = purchase_id.custom_rate
        return super(AccountMove, self)._onchange_purchase_auto_complete()


class StockMove(models.Model):
    _inherit = 'stock.move'

    def _get_price_unit(self):
        self.ensure_one()
        if self.purchase_line_id and self.product_id.id == self.purchase_line_id.product_id.id:
            return super(StockMove, self.with_context(
                use_custom_rate=self.purchase_line_id.order_id.use_custom_rate,
                custom_rate=self.purchase_line_id.order_id.custom_rate))._get_price_unit()
        return super(StockMove, self)._get_price_unit()


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    def _get_stock_move_price_unit(self):
        return super(PurchaseOrderLine, self.with_context(
            use_custom_rate=self.order_id.use_custom_rate,
            custom_rate=self.order_id.custom_rate,
            company_id=self.order_id.company_id.id))._get_stock_move_price_unit()

