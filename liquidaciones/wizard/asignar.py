# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

class Asignar(models.TransientModel):
    _name = "liqudaciones.asignar"
    _description = "Asignar liquidación"

    bolson_id = fields.Many2one("liqudaciones.liqudaciones", string="Liquidación")

    
    def asignar(self):
        for rec in self:
            for invoice in self.env['account.move'].browse(self.env.context.get('active_ids', [])):
                if rec.bolson_id:
                    invoice.bolson_id = rec.bolson_id.id
        return {'type': 'ir.actions.act_window_close'}
