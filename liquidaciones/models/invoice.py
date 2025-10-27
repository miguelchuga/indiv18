# -*- encoding: utf-8 -*-


from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class AccountInvoice(models.Model):
    _inherit = 'account.move'

    liquidaciones_id = fields.Many2one("liquidaciones.liquidaciones", string="Liquidacion", readonly=False, states={'paid': [('readonly', True)]}, ondelete='restrict')
#    account_id = fields.Many2one(comodel_name='account.account', string='Cuenta',related="partner_id.property_account_payable_id")
    
