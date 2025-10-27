# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import RedirectWarning, UserError, ValidationError, AccessError

class mpfel_mpfel_settings(models.Model):
    _name = "mpfel.settings"
    _description = "Megaprint FEL settings"

    ws_url_token = fields.Char('Token web service URL')
    ws_url_document = fields.Char('Document web service URL')
    ws_url_void = fields.Char('Void document web service URL')
    ws_url_pdf = fields.Char('PDF document web service URL')
    ws_url_signer = fields.Char('Signer web service URL')
    ws_timeout = fields.Integer('Web service timeout')
    user = fields.Char('User')
    api_key = fields.Char('API Key')
    token = fields.Char('Token')
    token_due_date = fields.Datetime('Token due date')
    megaprint_vat = fields.Char('Megaprint VAT')
    certificate_file = fields.Char('Certificate file')
    path_xml = fields.Char('path xml file')
    certificate_password = fields.Char('Certificate password')
    signing_type = fields.Selection([
        ('LOCAL', 'Sign documents using local program'),
        ('WS', 'Sign documents using Web Service'),
    ])
    signer_location = fields.Char('Signer program location')
    organization_code = fields.Char('Organization code')
    vat_affiliation = fields.Selection([
        ('GEN', 'GEN'),
        ('EXE', 'EXE'),
        ('PEQ', 'PEQ'),
    ], string='VAT affiliation')
    isr_scenery = fields.Char('ISR scenery')
    isr_phrases = fields.Char('ISR phrases')
    excempt_scenery = fields.Char('Excempt scenery')

