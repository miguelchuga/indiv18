# -*- encoding: utf-8 -*-
from odoo import models, fields, api, _

class purchase_order(models.Model):

    _name = 'purchase.order'
    _inherit = 'purchase.order'

    observaciones = fields.Char(string='Observaciones')