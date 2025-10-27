#!/usr/bin/python
# -*- coding: utf-8 -*-
import re
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.exceptions import ValidationError


class account_journal(models.Model):

    _name = 'account.journal'
    _inherit = 'account.journal'

    tipo_gasto = fields.Selection([('Bienes', 'Bienes'), ('Servicios',
                                  'Servicios')], 'Tipo Gasto')
    gravado = fields.Selection([('si', 'Si'), ('no', 'No')],
                               default='si')
    
    es_retencion_iva = fields.Selection([('si', 'Si'), ('no', 'No')],
                               default='no', string='Es retención de IVA')

    es_exencion_iva = fields.Selection([('si', 'Si'), ('no', 'No')],
                               default='no', string='Es exención de IVA')

    local = fields.Selection([('Local', 'Local'), ('Importacion',
                             'Importacion'),('Exportacion',
                             'Exportacion')], 'Local')
    tipo_transaccion = fields.Char('Tipo transaccion', size=10)
    establecimiento = fields.Char('Establecimiento', size=10)
    nombre_establecimiento = fields.Char('Nombre establecimiento',)
    asiste_libro = fields.Char('Código Asiste libro', size=10)
    imprime_libro = fields.Selection([('Si', 'Si')], 'Imprime en Libro '
            )
    serie_venta = fields.Char('Serie venta', size=30)
    tipo_venta = fields.Char('FC=Factura NC=Nota Credito', size=10)
    retencion_iva_cliente = fields.Selection([('Si', 'Si')],
            'Retención IVA - Cliente ')
    gface_electronico = fields.Boolean('Documento electronico GFACE ')



    def _inverse_check_next_number(self):
        for journal in self:
            if journal.check_next_number and not re.match(r'^[0-9]+$', journal.check_next_number):
                raise ValidationError(_('Next Check Number should only contains numbers.'))
#            if int(journal.check_next_number) < journal.check_sequence_id.number_next_actual:
#                raise ValidationError(_(
#                    "The last check number was %s. In order to avoid a check being rejected "
#                    "by the bank, you can only use a greater number.",
#                    journal.check_sequence_id.number_next_actual
#               ))
            if journal.check_sequence_id:
                journal.check_sequence_id.sudo().number_next_actual = int(journal.check_next_number)
                journal.check_sequence_id.sudo().padding = len(journal.check_next_number)
