
from odoo import fields, models, api, _
from odoo.osv.expression import get_unaccent_wrapper

class res_partner(models.Model):
    _inherit = 'res.partner'

    x_dpi = fields.Char('DPI')
    x_id_extrangero = fields.Char('ID Extrangero')


