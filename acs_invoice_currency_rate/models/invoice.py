# -*- coding: utf-8 -*-
# Part of AlmightyCS. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api
from functools import lru_cache


class AccountMove(models.Model):
    _inherit = 'account.move'

    @api.depends('currency_id', 'company_id.currency_id')
    def _compute_not_company_currency(self):
        for rec in self:
            rec.not_company_currency = rec.currency_id and rec.currency_id != rec.company_id.currency_id

    @api.depends('currency_id', 'not_company_currency', 'use_custom_rate', 'invoice_date')
    def _compute_currency_rate(self):
        for rec in self:
            rate = rec.currency_id.with_context(data=rec.invoice_date).rate
            rec.currency_rate = rate or rec.currency_id.rate

    @api.depends('amount_total', 'custom_rate')
    def _compute_amount_total_company_currency(self):
        for rec in self:
            if rec.not_company_currency:
                rec.amount_total_company_currency = rec.amount_total * rec.custom_rate
            else:
                rec.amount_total_company_currency = rec.amount_total

    not_company_currency = fields.Boolean('Use Custom Currency Rate', compute='_compute_not_company_currency')
    currency_rate = fields.Float(string='System Currency Rate',compute='_compute_currency_rate',
        digits=(12, 6), readonly=True, store=True, help="Currency rate of this invoice")
    use_custom_rate = fields.Boolean('Use Custom Rate')
    custom_rate = fields.Float(string='Custom Rate', digits=(12, 6), readonly=True)
    #amount_residual_signed canbe used insted but it will have minus sign in vendor bill so added new field
    amount_total_company_currency = fields.Float(string="Amount in company Currency",
        compute='_compute_amount_total_company_currency')

    def _inverse_amount_total(self):
        for move in self:
            super(AccountMove, move.with_context(
                use_custom_rate=move.use_custom_rate,
                custom_rate=move.custom_rate))._inverse_amount_total()

    @api.onchange('date', 'currency_id', 'use_custom_rate')
    def _onchange_currency(self):
        if self.env.context.get('default_custom_rate'):
            self.custom_rate = self.env.context.get('default_custom_rate')
        else:
            if self.currency_id.with_context(data=self.invoice_date).rate:
                self.custom_rate = self.currency_id.with_context(data=self.invoice_date).rate


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    @api.depends('currency_id', 'company_id', 'move_id.date', 'use_custom_rate', 'custom_rate')
    def _compute_currency_rate(self):
        for line in self:
            super(AccountMoveLine, line.with_context(
                use_custom_rate=line.move_id.use_custom_rate,
                custom_rate=line.move_id.custom_rate))._compute_currency_rate()

    use_custom_rate = fields.Boolean(related="move_id.use_custom_rate", string='Use Custom Rate', store=True)
    custom_rate = fields.Float(related="move_id.custom_rate", string='Custom Rate', store=True)

