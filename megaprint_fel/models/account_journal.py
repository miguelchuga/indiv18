# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class mpfel_account_journal(models.Model):
    _name = "account.journal"
    _inherit = "account.journal"

    mpfel_type = fields.Selection([
        ('', ''),
        ('FACT', 'FACT'),
        ('FCAM', 'FCAM'),
#        ('FPEQ', 'FPEQ'),
#        ('FCAP', 'FCAP'),
        ('FESP', 'FESP'),
        ('NABN', 'NABN'),
#        ('RDON', 'RDON'),
#        ('RECI', 'RECI'),
        ('NDEB', 'NDEB'),
        ('NCRE', 'NCRE'),
    ], string='FEL Invoice type', default='')
    tipo_venta = fields.Char('FC=Factura NC=Nota Credito', size=10)
    mpfel_previous_authorization = fields.Char('Previous invoice authorization')
    mpfel_previous_serial = fields.Char('Previous invoice serial Megaprint')
    ws_url_pdf = fields.Char('PDF document web service URL', default = 'https://')
    mpfel_exportacion = fields.Boolean(string='es exportación?' )
#    infilefel_previous_authorization = fields.Char('Previous invoice authorization')
    infilefel_previous_serial = fields.Char('Previous invoice serial Infile')
    infilefel_establishment_code = fields.Char('Establishment code')
    infilefel_establishment_street = fields.Char('Establishment street')
    infilefel_comercial_name = fields.Char('Comercial name')
    infilefel_phone_number = fields.Char('Phone Number')

    frase_xml = fields.Char('Frase xml')


    nit_certificador = fields.Char('Nit Certificador')
    nombre_certificador = fields.Char('Nombre certificador')
    frase_certificador = fields.Char('Frase certificador')


