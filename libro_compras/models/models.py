# -*- coding: utf-8 -*-

# from odoo import models, fields, api


# class mc_libro_compras_v13(models.Model):
#     _name = 'mc_libro_compras_v13.mc_libro_compras_v13'
#     _description = 'mc_libro_compras_v13.mc_libro_compras_v13'

#     name = fields.Char()
#     value = fields.Integer()
#     value2 = fields.Float(compute="_value_pc", store=True)
#     description = fields.Text()
#
#     @api.depends('value')
#     def _value_pc(self):
#         for record in self:
#             record.value2 = float(record.value) / 100
