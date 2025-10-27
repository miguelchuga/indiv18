# -*- encoding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

class AccountPayment(models.Model):
    _inherit = 'account.payment'

    liquidaciones_id = fields.Many2one("liquidaciones.liquidaciones", string="Liquidacion", readonly=False, states={'reconciled': [('readonly', True)]}, ondelete='restrict')


    def write(self, vals):
        res = super(AccountPayment, self).write(vals)
        self.move_id.write({'liquidaciones_id': False})
        return res
