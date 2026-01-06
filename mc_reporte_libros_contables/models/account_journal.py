from odoo import api, fields, models


class Journal(models.Model):
    _inherit = 'account.journal'

    #x_studio_poliza = fields.Many2one(comodel_name='mc.poliza', string='Poliza')
    #x_studio_poliza = fields.Many2one("mc.poliza", string="Poliza", )

    x_studio_poliza = fields.Many2one(comodel_name='mc.poliza', string='Poliza')
    x_poliza_id = fields.Many2one("mc.poliza_diarios", string="Poliza", )

class Poliza(models.Model):
    _name = 'mc.poliza_diarios'
    _description = 'Polizas de Diario y Mayor'

    name = fields.Char(string='Poliza')
    
    
