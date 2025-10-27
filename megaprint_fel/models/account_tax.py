# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class mpfel_account_tax(models.Model):
    _name = "account.tax"
    _inherit = "account.tax"

    mpfel_sat_code = fields.Char('SAT Code')
