# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
#from odoo.exceptions import UserError
from odoo.exceptions import RedirectWarning, UserError, ValidationError, AccessError
import requests
import xml.etree.cElementTree as ElementTree
from datetime import datetime,timedelta
import time
import pytz
import uuid
import xmltodict
import os
import json
import base64
#import pyPdf
import html

from tempfile import gettempdir
from xml.sax.saxutils import unescape


class mpfel_settings(models.Model):
    _name = "mpfel.settings"
    _description = "Megaprint FEL settings"

    ws_url_token = fields.Char('Token web service URL', default = 'https://')
    ws_url_document = fields.Char('Document web service URL', default = 'https://')
    ws_url_void = fields.Char('Void document web service URL', default = 'https://')
    ws_url_pdf = fields.Char('PDF document web service URL', default = 'https://')
    ws_url_signer = fields.Char('Signer web service URL', default = 'https://')
    ws_timeout = fields.Integer('Web service timeout', default=300)
    user = fields.Char('User')
    api_key = fields.Char('API key')
    token = fields.Char('Token')
    token_due_date = fields.Datetime('Token due date')
    megaprint_vat = fields.Char('Megaprint VAT')
    certificate_file = fields.Char('Certificate file')
    path_xml = fields.Char('path xml file')
    certificate_password = fields.Char('Certificate password')
    signing_type = fields.Selection([
        ('LOCAL', 'Sign documents using local program'),
        ('WS', 'Sign documents using Web Service'),
    ], string='Signing type', default='LOCAL')
    signer_location = fields.Char('Signer program location')
    organization_code = fields.Char('Organization code', default='1')
    vat_affiliation = fields.Selection([
        ('GEN', 'GEN'),
        ('EXE', 'EXE'),
        ('PEQ', 'PEQ'),
    ], string='VAT affiliation', default='GEN')
    isr_scenery = fields.Char('ISR sceneries')
    isr_phrases = fields.Char('ISR phrases')
    excempt_scenery = fields.Char('Excempt scenery')
    company_id = fields.Many2one('res.company', string='Empresa')


    nit_certificador = fields.Char('Nit empresa certificadora')
    nombre_certificador = fields.Char('Nombre empresa certificadora ')
    frase_certificador = fields.Char('Frase empresa o cliente')

    #INFILE
    user = fields.Char('Certification user')
    sign_user = fields.Char('Sign user')
    sign_key = fields.Char('Sign key')
    certification_key = fields.Char('Certification key')
    infile_vat = fields.Char('InFile VAT')
    provider = fields.Selection([
        ('megaprint', 'Megaprint'),
        ('infile', 'Infile'),
    ], string='Proveedor', default='megaprint')


    def get_token2(self):
        if self.ws_url_token and self.provider == 'megaprint':
            if self.user:
                if self.api_key:
                    headers = {
                        'Content-Type': 'application/xml',
                    }
                    data = "<SolicitaTokenRequest><usuario>{}</usuario><apikey>{}</apikey></SolicitaTokenRequest>".format(
                        self.user, self.api_key)
                    try:
                        response = requests.post(self.ws_url_token, headers=headers, data=data)
                        if response.ok:
                            text = xmltodict.parse(response.text)
                            token = text['SolicitaTokenResponse']['token']
                            due_date_tag = text['SolicitaTokenResponse']['vigencia']
                            if due_date_tag:
                                token_due_date = datetime.strptime(due_date_tag[0:19],'%Y-%m-%dT%H:%M:%S')#.replace(tzinfo=pytz.timezone(self.env.user.tz))
#                                self.token_due_date = token_due_date
                                _data = {'token':token,
                                         'token_due_date': token_due_date
                                         }
                                self.write(_data)

                    except ValidationError as e:
                        raise ValidationError(_('MPFEL: Error consuming web service: {}').format(e.message))
                else:
                    raise ValidationError(_('MPFEL: API key not set'))
            else:
                raise ValidationError(_('MPFEL: User not set'))
        else:
            raise ValidationError(_('MPFEL: Web service URL for tokens not set'))

    def sign_document(self, invoice):

        def escape_string_nombre2(value):
            if not value:
                value = ""
            return html.escape(value).encode("ascii", "xmlcharrefreplace").decode("utf-8")

        def escape_string(value):
            if not value:
                value = ''
            return value.replace('&', '&amp;').replace('>', '&gt;').replace('<', '&lt').replace('"','&quot;').replace("'", '&apos;').replace("é", '&#233;').replace("É", '&#201;').replace("Ó", '&#211;').replace("Í", '&#205;')

        def escape_tildes(value):
            if not value:
                value=""
            return value.replace('ñ','&#241;').replace('Ñ', '&#209;').replace("á", '&#225;').replace("é", '&#233;').replace("í", '&#237;').replace("ó", '&#243;').replace("Ó", '&#211;').replace("ú", '&#250;').replace("É", '&#201;').replace("Í", '&#205;')

#        replace('Ñ', '&#209;').
        _pos_id = self.env['ir.config_parameter'].search([('key', '=', 'pos')]).ids[0]
        _generico_id = self.env['ir.config_parameter'].search([('key', '=', 'generico')]).ids[0]

        _tiene_pos = self.env['ir.config_parameter'].browse([_pos_id])
        _tiene_generico = self.env['ir.config_parameter'].browse([_generico_id])



        if not invoice.invoice_date:
            if invoice.invoice_date_due:
                _due_date = invoice.invoice_date_due
            else:
                _due_date = fields.datetime.now(pytz.timezone('America/Guatemala')).strftime("%Y-%m-%d")

            _data = {'invoice_date': fields.datetime.now(pytz.timezone('America/Guatemala')).strftime("%Y-%m-%d"),
                     'invoice_date_due': _due_date,
                     }
            invoice.write(_data)

        token = None
        if not invoice.journal_id.mpfel_type:
            return
        elif invoice.journal_id.mpfel_type == '':
            return
        elif invoice.mpfel_sat_uuid:
            return
        elif not invoice.invoice_date:
            raise UserError(_('Missing document date'))
        elif self.provider in ('infile','megaprint'):
            if self.provider in ('infile','megaprint'):
                if not invoice.mpfel_uuid:
                    invoice.mpfel_uuid = str(uuid.uuid4()).upper()

                #
                # Líneas del documento
                #
                excempt = False
                excempt_phrase = False
                xml_lines = ''
                taxes = []
                line_number = 0
                taxes_total = 0
                total_fesp = 0
                #impuestos facturas especiales
                if invoice.journal_id.mpfel_type in ['FESP']:
                    _iva_especial = 0
                    _isr_especial = 0
                    for line in invoice.line_ids:
                        if line.tax_line_id:
                            if line.tax_line_id.mpfel_sat_code == 'IVA':
                                _iva_especial = line.debit
                            if line.tax_line_id.mpfel_sat_code == 'ISR':
                                _isr_especial = line.credit

                # para hoteles turismo
                _iva_hospedaje = 0
                _turismo_hospedaje = 0
                _tiene_turismo = False
                _total_turismo_hospedaje = 0
                _error_de_unidad_de_medida = False
                line_taxes = 0
                for line in invoice.invoice_line_ids:
                    line_number += 1
                    if line.tax_ids:
                        line_gross = round(line.price_total, 6)
                        line_discount = round(line.price_discount, 6)
                    else:
                        line_gross = round(line.price_total, 6)
                        line_discount = round(line.price_discount, 6)

                    if not line.product_uom_id:
                        _error_de_unidad_de_medida = True
                        raise ValidationError(_('PRODUCTO: Hay productos sin unidad de medida...'))

                    #verifica si la linea tiene impuesto turismo para hoteles
                    if line.tax_ids:
                        price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
                        _taxes = line.tax_ids.compute_all(price, invoice.currency_id, line.quantity,product=line.product_id, partner=line.move_id.partner_id)
                        for tax in _taxes['taxes']:
                            tax_id = self.env['account.tax'].search([('id', '=', tax['id'])])
                            if invoice.journal_id.mpfel_type == 'FESP' and tax_id.mpfel_sat_code != 'IVA':
                                continue

                            if tax_id.mpfel_sat_code == 'TURISMO HOSPEDAJE':
                                _turismo_hospedaje = tax['amount']
                                _total_turismo_hospedaje += tax['amount']
                                _tiene_turismo = True
                            else:
                                _turismo_hospedaje = 0
                                _tiene_turismo = False

                    xml_lines += """<dte:Item BienOServicio="{BienOServicio}" NumeroLinea="{NumeroLinea}">
                            <dte:Cantidad>{Cantidad}</dte:Cantidad>
                            <dte:UnidadMedida>{UnidadMedida}</dte:UnidadMedida>
                            <dte:Descripcion>{Descripcion}</dte:Descripcion>
                            <dte:PrecioUnitario>{PrecioUnitario}</dte:PrecioUnitario>
                            <dte:Precio>{Precio}</dte:Precio>
                            <dte:Descuento>{Descuento}</dte:Descuento>{TituloImpuestos}""".format(
                        BienOServicio='B' if line.product_id.type == 'consu' or line.product_id.default_code == 'BIEN' else 'S',
                        NumeroLinea=line_number,
                        Cantidad=round(line.quantity,6),
                        UnidadMedida=line.product_uom_id.name[:3] if line.product_uom_id.name[:3] else 'UNI',
                        Descripcion=escape_string_nombre2(line.name),
                        PrecioUnitario=round(line.price_unit,6),  #if not _tiene_turismo  else (round(line.price_unit,6) + _iva_hospedaje   ),
                        Precio=(round(round(line.price_unit,6)*round(line.quantity,6),6))  if invoice.journal_id.mpfel_type != 'FESP' and not _tiene_turismo  else (round(line.price_unit,6)), #+ _iva_hospedaje   ),
                        Descuento=line_discount,
                        TituloImpuestos='' if invoice.journal_id.mpfel_type in ['NABN'] else '<dte:Impuestos>'
                    )
                    #cuando es factura especial solo lleva una linea y pone el precio unitario
                    total_fesp = round(line.price_unit,6)


                    if invoice.journal_id.mpfel_type not in ['NABN']:
                        _iva = 0
#                        _turismo_hospedaje = 0
                        if line.tax_ids:
                            price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
                            _taxes = line.tax_ids.compute_all(price, invoice.currency_id, line.quantity,
                                                              product=line.product_id, partner=line.move_id.partner_id)
                            for tax in _taxes['taxes']:
                                tax_id = self.env['account.tax'].search([('id', '=', tax['id'])])
                                if invoice.journal_id.mpfel_type == 'FESP' and tax_id.mpfel_sat_code != 'IVA':
                                    continue

                                line_taxes += round(tax['amount'],6)
                                xml_lines += """<dte:Impuesto>
                                     <dte:NombreCorto>{NombreCorto}</dte:NombreCorto>
                                     <dte:CodigoUnidadGravable>{CodigoUnidadGravable}</dte:CodigoUnidadGravable>
                                     <dte:MontoGravable>{MontoGravable}</dte:MontoGravable>
                                     <dte:MontoImpuesto>{MontoImpuesto}</dte:MontoImpuesto>
                                     </dte:Impuesto>
                                     """.format(
                                         NombreCorto=tax_id.mpfel_sat_code,
                                         CodigoUnidadGravable='1',
                                         MontoGravable=round(line.price_subtotal,6) if not _tiene_turismo else round(line.price_subtotal+_turismo_hospedaje,6) ,
                                         MontoImpuesto= round(tax['amount'],6) if invoice.journal_id.mpfel_type != 'FESP'  else _iva_especial,
                                         )
                                tax_added = False
                                for tax_sum in taxes:
                                    if tax_sum['NombreCorto'] == tax_id.mpfel_sat_code:
                                        tax_added = True
                                        tax_sum['Valor'] += tax['amount']
                                if not tax_added:
                                    taxes.append({
                                        'NombreCorto': tax_id.mpfel_sat_code,
                                        'Valor':  tax['amount']
                                    })
                        else:
                            line_taxes = 0

                    if invoice.journal_id.mpfel_type not in ['NABN'] and line_taxes == 0:
                        excempt = True
                        xml_lines += """<dte:Impuesto>
                                <dte:NombreCorto>{NombreCorto}</dte:NombreCorto>
                                <dte:CodigoUnidadGravable>{CodigoUnidadGravable}</dte:CodigoUnidadGravable>
                                <dte:MontoGravable>{MontoGravable}</dte:MontoGravable>
                                <dte:MontoImpuesto>{MontoImpuesto}</dte:MontoImpuesto>
                            </dte:Impuesto>
                        """.format(
                            NombreCorto='IVA',
                            CodigoUnidadGravable='2',
                            MontoGravable= round(line.price_subtotal,6),
                            MontoImpuesto=0
                        )
                        tax_added = False
                        for tax_sum in taxes:
                            if tax_sum['NombreCorto'] == 'IVA':
                                tax_added = True
                                tax_sum['Valor'] += 0
                        if not tax_added:
                            taxes.append({
                                'NombreCorto': 'IVA',
                                'Valor': 0
                            })

                    _total_ = 0
                    if _tiene_turismo:
                        _total_ = round(line.n_total_linea + _turismo_hospedaje, 6)
                    else:
                        _total_ = round(line.price_total,2)
                    if invoice.journal_id.mpfel_type == 'FESP':
                        _total_ = total_fesp

                    xml_lines += """{TituloImpuestos}
                            <dte:Total>{Total}</dte:Total>
                        </dte:Item>
                    """.format(TituloImpuestos='' if invoice.journal_id.mpfel_type in ['NABN'] else '</dte:Impuestos>',
                               Total=_total_ )

                #
                # Frases
                #
                xml_phrases = ''
                #se agrega esto para poner esta parte del xml personalizado
                if invoice.journal_id.frase_xml:
                    xml_phrases = invoice.journal_id.frase_xml

                #
                # Encabezado del documento
                #
                sign_date = datetime.now().replace(tzinfo=pytz.UTC).astimezone(pytz.timezone(self.env.user.tz))

                sign_date_utc = datetime.now().replace(tzinfo=pytz.UTC)
                current_date = sign_date.strftime('%Y-%m-%dT%H:%M:%S-06:00')
                current_time = sign_date.strftime('T%H:%M:%S-06:00')
                invoice_sign_date = str(invoice.invoice_date) + current_time
                date_sign = invoice_sign_date
                _NITReceptor = ''
                _TipoEspecial = ''

                if invoice.journal_id.mpfel_type == 'FESP':
                    # Factura especial
                    _TipoEspecial = """ TipoEspecial="CUI" """
                    _NombreReceptor = escape_string_nombre2(invoice.partner_id.name)
                    if invoice.partner_id.vat or invoice.partner_id.x_id_extrangero :
                        _NITReceptor = 'CF'
                    else:
                        _TipoEspecial = """ TipoEspecial="CUI" """
                        _NITReceptor = invoice.partner_id.x_dpi

                    _DireccionReceptor = escape_string_nombre2(
                        (invoice.partner_id.street if invoice.partner_id.street else '') + (
                            ' ' + invoice.partner_id.street2 if invoice.partner_id.street2 else ''))
                else:
                    if _tiene_generico.value == 'True':
                        _NombreReceptor = escape_string_nombre2(invoice.partner_id.name if not invoice.x_nombre_generico else invoice.x_nombre_generico)
                        if not invoice.partner_id.x_es_generico:
                            _NITReceptor = invoice.partner_id.vat.replace('-', '') if invoice.partner_id.vat else 'CF'
                        else:
                            _NITReceptor = invoice.x_nit_generico.replace('-', '')
                        _DireccionReceptor = escape_string_nombre2(invoice.partner_id.street if not invoice.x_nombre_generico else invoice.x_direccion_generico)
                    else:
                        #cambio de fel 16012023
                        _NITReceptor = ''
                        _TipoEspecial = ''
                        _NombreReceptor = escape_string_nombre2(invoice.partner_id.name)
                        _DireccionReceptor= escape_string_nombre2((invoice.partner_id.street if invoice.partner_id.street else '') + (' ' + invoice.partner_id.street2 if invoice.partner_id.street2 else ''))
                        if invoice.partner_id.vat:
                            _NITReceptor = invoice.partner_id.vat.replace('-', '') if invoice.partner_id.vat else 'CF'
                        else:
                            if invoice.partner_id.x_dpi:
                                _TipoEspecial = """ TipoEspecial="CUI" """
                                _NITReceptor = invoice.partner_id.x_dpi
                            else:
                                _TipoEspecial = """ TipoEspecial="EXT" """
                                _NITReceptor = invoice.partner_id.x_id_extrangero

                exportacion = ''
                if invoice.journal_id.mpfel_exportacion :
                    exportacion = """ Exp="SI" """
                elif invoice.journal_id.mpfel_type == 'NCRE' and invoice.reversed_entry_id.journal_id.mpfel_exportacion:
                        exportacion = """ Exp="SI" """

                xml = """<?xml version="1.0" encoding="UTF-8"?><dte:GTDocumento Version="0.1" xmlns:dte="http://www.sat.gob.gt/dte/fel/0.2.0" xmlns:xd="http://www.w3.org/2000/09/xmldsig#">
                <dte:SAT ClaseDocumento="dte">
                    <dte:DTE ID="DatosCertificados">
                        <dte:DatosEmision ID="DatosEmision">
                            <dte:DatosGenerales CodigoMoneda="{CodigoMoneda}" {EXP} FechaHoraEmision="{FechaHoraEmision}" {NumeroAcceso} Tipo="{Tipo}"/>
                            <dte:Emisor AfiliacionIVA="{AfiliacionIVA}" CodigoEstablecimiento="{CodigoEstablecimiento}" CorreoEmisor="{CorreoEmisor}" NITEmisor="{NITEmisor}" NombreComercial="{NombreComercial}" NombreEmisor="{NombreEmisor}">
                                <dte:DireccionEmisor>
                                    <dte:Direccion>{DireccionEmisor}</dte:Direccion>
                                    <dte:CodigoPostal>{CodigoPostalEmisor}</dte:CodigoPostal>
                                    <dte:Municipio>{MunicipioEmisor}</dte:Municipio>
                                    <dte:Departamento>{DepartamentoEmisor}</dte:Departamento>
                                    <dte:Pais>{PaisEmisor}</dte:Pais>
                                </dte:DireccionEmisor>
                            </dte:Emisor>
                            <dte:Receptor CorreoReceptor="{CorreoReceptor}" {TipoEspecial}  IDReceptor="{NITReceptor}" NombreReceptor="{NombreReceptor}"  >
                                <dte:DireccionReceptor>
                                    <dte:Direccion>{DireccionReceptor}</dte:Direccion>
                                    <dte:CodigoPostal>{CodigoPostal}</dte:CodigoPostal>
                                    <dte:Municipio>{Municipio}</dte:Municipio>
                                    <dte:Departamento>{Departamento}</dte:Departamento>
                                    <dte:Pais>{Pais}</dte:Pais>
                                </dte:DireccionReceptor>
                            </dte:Receptor>
                            {Frases}
                            <dte:Items>
                                {Items}
                            </dte:Items>
                            <dte:Totales>
                                {TituloImpuestos}""".format(
                    CodigoMoneda=invoice.currency_id.name,
                    EXP=exportacion, #if invoice.journal_id.mpfel_exportacion or invoice.mpfel_sat_uuid_ncre else '',
                    FechaHoraEmision=invoice_sign_date,
                    NumeroAcceso='',
                    Tipo=invoice.journal_id.mpfel_type,
                    AfiliacionIVA=self.vat_affiliation,
                    CodigoEstablecimiento=invoice.journal_id.infilefel_establishment_code,
                    CorreoEmisor=invoice.company_id.email if invoice.company_id.email else '',
                    NITEmisor=invoice.company_id.vat.replace('-', '') if invoice.company_id.vat else 'C/F',
                    NombreComercial=escape_string_nombre2(invoice.journal_id.infilefel_comercial_name),
                    NombreEmisor=escape_string_nombre2(invoice.company_id.name),
                    DireccionEmisor=escape_string_nombre2(invoice.journal_id.infilefel_establishment_street),
                    CodigoPostalEmisor=invoice.company_id.zip if invoice.company_id.zip else '01001',
                    MunicipioEmisor=escape_string(invoice.company_id.city if invoice.company_id.city else ''),
                    DepartamentoEmisor=escape_string_nombre2(
                        invoice.company_id.state_id.name if invoice.company_id.state_id else ''),
                    PaisEmisor=invoice.company_id.country_id.code if invoice.company_id.country_id else '',
                    DireccionReceptor=_DireccionReceptor,
                    CorreoReceptor='',#invoice.partner_id.email if invoice.partner_id.email else '',
                    TipoEspecial=_TipoEspecial,
                    NITReceptor=_NITReceptor,

                    NombreReceptor=_NombreReceptor,#escape_string(invoice.partner_id.name),
                    #_TipoEspecial='TipoEspecial="CUI" ' if invoice.journal_id.mpfel_type == 'FESP' else '',

                    CodigoPostal=invoice.partner_id.zip if invoice.partner_id.zip else '01001',
                    Municipio=escape_string(invoice.partner_id.city) if invoice.partner_id.city else '',
                    Departamento=escape_string(invoice.partner_id.state_id.name) if invoice.partner_id.state_id else '',
                    Pais=invoice.partner_id.country_id.code if invoice.partner_id.country_id else '',
                    Frases=xml_phrases,
                    Items=xml_lines,
                    TituloImpuestos='' if invoice.journal_id.mpfel_type in ['NABN'] else '<dte:TotalImpuestos>'
                )

                if not invoice.journal_id.mpfel_type in ['NABN']:
                    for tax in taxes:
                        xml += '<dte:TotalImpuesto NombreCorto="{NombreCorto}" TotalMontoImpuesto="{TotalMontoImpuesto}"/>'.format(
                            NombreCorto=tax['NombreCorto'],
                            TotalMontoImpuesto= round(tax['Valor'],6) if invoice.journal_id.mpfel_type != 'FESP' else _iva_especial
                        )

                extras = ''
                complemento = ''
                es_exportacion = False
                if invoice.reversed_entry_id and invoice.journal_id.mpfel_type == 'NCRE' and invoice.reversed_entry_id.journal_id.mpfel_exportacion:
                    _x_nombreconsignatario=invoice.reversed_entry_id.x_nombreconsignatario
                    _x_direccionconsignatario=invoice.reversed_entry_id.x_direccionconsignatario
                    _x_codigoconsignatario=invoice.reversed_entry_id.x_codigoconsignatario
                    _x_nombrecomprador=invoice.reversed_entry_id.x_nombrecomprador
                    _x_direccioncomprador=invoice.reversed_entry_id.x_direccioncomprador
                    _x_codigocomprador=invoice.reversed_entry_id.x_codigocomprador
                    _x_otrareferencia=invoice.reversed_entry_id.x_otrareferencia
                    _x_incoterms_id=invoice.reversed_entry_id.x_incoterms_id.code
                    _x_nombreexportador=invoice.reversed_entry_id.x_nombreexportador
                    _x_codigoexportador=invoice.reversed_entry_id.x_codigoexportador
                    es_exportacion = True
                if invoice.journal_id.mpfel_exportacion:
                    _x_nombreconsignatario=invoice.x_nombreconsignatario
                    _x_direccionconsignatario=invoice.x_direccionconsignatario
                    _x_codigoconsignatario=invoice.x_codigoconsignatario
                    _x_nombrecomprador=invoice.x_nombrecomprador
                    _x_direccioncomprador=invoice.x_direccioncomprador
                    _x_codigocomprador=invoice.x_codigocomprador
                    _x_otrareferencia=invoice.x_otrareferencia
                    _x_incoterms_id=invoice.x_incoterms_id.code
                    _x_nombreexportador=invoice.x_nombreexportador
                    _x_codigoexportador=invoice.x_codigoexportador
                    es_exportacion = True

                if es_exportacion:
                    complemento += """
                      <dte:Complemento IDComplemento="1" NombreComplemento="EXPORTACION" URIComplemento="http://www.sat.gob.gt/face2/ComplementoExportaciones/0.1.0">
                        <cex:Exportacion xmlns:cex="http://www.sat.gob.gt/face2/ComplementoExportaciones/0.1.0" Version="1">
                             <cex:NombreConsignatarioODestinatario>{x_nombreconsignatario}</cex:NombreConsignatarioODestinatario>
                             <cex:DireccionConsignatarioODestinatario>{x_direccionconsignatario}</cex:DireccionConsignatarioODestinatario>
                             <cex:CodigoConsignatarioODestinatario>{x_codigoconsignatario}</cex:CodigoConsignatarioODestinatario>
                             <cex:NombreComprador>{x_nombrecomprador}</cex:NombreComprador>
                             <cex:DireccionComprador>{x_direccioncomprador}</cex:DireccionComprador>
                             <cex:CodigoComprador>{x_codigocomprador}</cex:CodigoComprador>
                             <cex:OtraReferencia>{x_otrareferencia}</cex:OtraReferencia>
                             <cex:INCOTERM>{x_incoterms_id}</cex:INCOTERM>
                             <cex:NombreExportador>{x_nombreexportador}</cex:NombreExportador>
                             <cex:CodigoExportador>{x_codigoexportador}</cex:CodigoExportador>
                        </cex:Exportacion>
                      </dte:Complemento>
                    """.format(x_nombreconsignatario=_x_nombreconsignatario,
                               x_direccionconsignatario=_x_direccionconsignatario,
                               x_codigoconsignatario=_x_codigoconsignatario,
                               x_nombrecomprador=_x_nombrecomprador,
                               x_direccioncomprador=_x_direccioncomprador,
                               x_codigocomprador=_x_codigocomprador,
                               x_otrareferencia=_x_otrareferencia,
                               x_incoterms_id=_x_incoterms_id,
                               x_nombreexportador=_x_nombreexportador,
                               x_codigoexportador=_x_codigoexportador)


                if invoice.journal_id.mpfel_type == 'FCAM' :
                        complemento += """
                                    <dte:Complemento IDComplemento="AbonosFacturaCambiaria" NombreComplemento="AbonosFacturaCambiaria" URIComplemento="http://www.sat.gob.gt/dte/fel/CompCambiaria/0.1.0">
                                        <cfc:AbonosFacturaCambiaria xmlns:cfc="http://www.sat.gob.gt/dte/fel/CompCambiaria/0.1.0" Version="1">
                                            <cfc:Abono>
                                                <cfc:NumeroAbono>1</cfc:NumeroAbono>
                                                <cfc:FechaVencimiento>{FechaVencimiento}</cfc:FechaVencimiento>
                                                <cfc:MontoAbono>{Monto}</cfc:MontoAbono>
                                            </cfc:Abono>
                                        </cfc:AbonosFacturaCambiaria>
                                    </dte:Complemento>""".format(FechaVencimiento=invoice.invoice_date_due,
                                                              Monto=round(invoice.amount_total,6))

                if invoice.journal_id.mpfel_type in ['FESP']:
                    complemento += """
                                    <dte:Complemento IDComplemento="1" NombreComplemento="RETENCION" URIComplemento="http://www.sat.gob.gt/face2/ComplementoFacturaEspecial/0.1.0">
                                        <cfe:RetencionesFacturaEspecial xmlns:cfe="http://www.sat.gob.gt/face2/ComplementoFacturaEspecial/0.1.0" Version="1">
                                            <cfe:RetencionISR>{ISRespecial}</cfe:RetencionISR>
                                            <cfe:RetencionIVA>{IVAespecial}</cfe:RetencionIVA>
                                            <cfe:TotalMenosRetenciones>{TOTALespecial}</cfe:TotalMenosRetenciones>
                                        </cfe:RetencionesFacturaEspecial>
                                    </dte:Complemento>""".format(ISRespecial=round(_isr_especial,6), IVAespecial=round(_iva_especial,6),
                                                              TOTALespecial=round(invoice.amount_total,6))

                if invoice.journal_id.mpfel_type in ['NCRE', 'NDEB']:
                    _NumeroDocumentoOrigen = ''
                    _SerieDocumentoOrigen = ''
                    original_document = ''
                    reason = ''
                    date_original = ''

                    if invoice.reversed_entry_id:
                        original_document = invoice.reversed_entry_id.name
                        if invoice.journal_id.mpfel_type in ['NCRE','NDEB']:
                            if invoice.reversed_entry_id.mpfel_sat_uuid:
                                _NumeroDocumentoOrigen = invoice.reversed_entry_id.mpfel_number
                                _SerieDocumentoOrigen = invoice.reversed_entry_id.mpfel_serial
                                original_document = invoice.reversed_entry_id.mpfel_sat_uuid
                                reason = 'MotivoAjuste="{}"'.format('Reversion de: '+invoice.ref)
                                date_original = invoice.reversed_entry_id.invoice_date
                        complemento += """
                                        <dte:Complemento IDComplemento="ReferenciasNota"  NombreComplemento="ReferenciasNota"  URIComplemento="http://www.sat.gob.gt/face2/ComplementoReferenciaNota/0.1.0">
                                            <cno:ReferenciasNota xmlns:cno="http://www.sat.gob.gt/face2/ComplementoReferenciaNota/0.1.0"
                                                Version="1" 
                                                NumeroAutorizacionDocumentoOrigen="{DocumentoOrigen}"
                                                NumeroDocumentoOrigen="{_NumeroDocumentoOrigen}"
                                                SerieDocumentoOrigen="{_SerieDocumentoOrigen}"                                            
                                                FechaEmisionDocumentoOrigen="{FechaEmision}" {MotivoAjuste}
                                            /> </dte:Complemento>""".format(DocumentoOrigen=original_document if original_document else '',
                                                          _NumeroDocumentoOrigen=_NumeroDocumentoOrigen if _NumeroDocumentoOrigen else '',
                                                          _SerieDocumentoOrigen=_SerieDocumentoOrigen if _SerieDocumentoOrigen else '',
                                                          FechaEmision=date_original if date_original else '',
                                                          MotivoAjuste=reason,
                                                          )

                    else:
                        raise UserError(_('Esta nota no tiene documento de origen.......'))

                if invoice.journal_id.mpfel_type in ['FCAM','NCRE','NDEB','FESP']   or invoice.journal_id.mpfel_exportacion:
                    complemento = """
                                     <dte:Complementos>
                                        {_complementos}
                                     </dte:Complementos>""".format(_complementos=complemento)

                # PARA GENERAR EL PDF NECESITA LOS DATOS EXTRAS EN ADENDAS nuevas para cleanmaster
                if not invoice.journal_id.ws_url_pdf:
                    adendas = ''
                    adendasitem = ''
                else:
                    adendas = """<dte:Adenda>
	   		    <dte:AdendaDetail id="AdendaSummary">
				    <dte:AdendaSummary>
					    <dte:Valor1>{ciudad}</dte:Valor1>
                        <dte:Valor2>{Vendedor}</dte:Valor2>
                        <dte:Valor3>{exento}</dte:Valor3>
                        <dte:Valor4>{gravado}</dte:Valor4>
                        <dte:Valor5>{recibido}</dte:Valor5>
                        <dte:Valor6>{pedido}</dte:Valor6>
                        <dte:Valor7>{tipo}</dte:Valor7>
                        <dte:Valor8>{impreso}</dte:Valor8>
                        <dte:Valor9>{atendio}</dte:Valor9>
                        <dte:Valor10>{departamento}</dte:Valor10>

				    </dte:AdendaSummary>
  			    <dte:AdendaItems>
                """.format(ciudad=invoice.partner_id.city,  
                           Vendedor=escape_string_nombre2(invoice.user_id.name), 
                           exento=format(invoice.x_exento_total, ',.2f'),
                           gravado=format(invoice.x_gravado_total, ',.2f'),
                           recibido=invoice_sign_date,
                           pedido=invoice.invoice_origin,
                           tipo=invoice.invoice_payment_term_id.name,
                           impreso=invoice_sign_date,
                           atendio=invoice.env.user.name,
                           departamento=invoice.partner_id.state_id.name

                           )
                    #adendas cleanmaster
                    adendasitem = ''
                    line_number = 0
                    for line in invoice.invoice_line_ids:
                        line_number += 1
                        line_str = str(line_number)
                        item = line.product_id.default_code
                        adendasitem += """
		   		        <dte:AdendaItem LineaReferencia="{Line_str}">
					        <dte:Valor1>{Item}</dte:Valor1>
				        </dte:AdendaItem>
                        """.format(Line_str=line_str, Line_strA=line_str, Line_strB=line_str, Item=item)

                    adendasitem += """</dte:AdendaItems>
		                </dte:AdendaDetail>
		            </dte:Adenda>
                    """

                xml += """{TituloImpuestos}
                                <dte:GranTotal>{GranTotal}</dte:GranTotal>
                                </dte:Totales>{Complementos}
                            </dte:DatosEmision>
                        </dte:DTE>  
                            {adendas}
                            {adendasitem}
                    </dte:SAT>
                  </dte:GTDocumento>""".format(
                    TituloImpuestos='' if invoice.journal_id.mpfel_type in ['NABN'] else '</dte:TotalImpuestos>',
                    GranTotal=round(invoice.amount_total+_total_turismo_hospedaje,6) if invoice.journal_id.mpfel_type != 'FESP' else total_fesp,
                    Complementos=complemento, adendas=adendas, adendasitem=adendasitem)

                source_xml = xml

                #tmp_dir = self.path_xml
                error_message = ''
                if invoice.journal_id.tipo_venta == 'ND':
                    _data = {
                        'mpfel_sign_date': invoice_sign_date,
                        'mpfel_source_xml': source_xml,
                    }
                    invoice.write(_data)
                else:
                    _data = {
                        'mpfel_sign_date': invoice_sign_date,
                        'mpfel_source_xml': source_xml,
                    }
                    invoice.write(_data)
            #else:
            #    raise ValidationError(_('MPFEL: Token expired'))
        else:
            raise ValidationError(_('MPFEL: Token not set'))



    def firmar_documento(self, invoice):
        def escape_string_nombre2(value):
            if not value:
                value = ""
            return html.escape(value).encode("ascii", "xmlcharrefreplace").decode("utf-8")

        def escape_string(value):
            if not value:
                value = ''
            return value.replace('&', '&amp;').replace('>', '&gt;').replace('<', '&lt').replace('"','&quot;').replace("'", '&apos;').replace("é", '&#233;').replace("É", '&#201;').replace("Ó", '&#211;').replace("Í", '&#205;')

        def escape_tildes(value):
            if not value:
                value=""
            return value.replace('ñ','&#241;').replace('Ñ', '&#209;').replace("á", '&#225;').replace("é", '&#233;').replace("í", '&#237;').replace("ó", '&#243;').replace("Ó", '&#211;').replace("ú", '&#250;').replace("É", '&#201;').replace("Í", '&#205;')

        if  self.provider == 'megaprint':
            sign_document = False
            headers = {
                'Content-Type': 'application/xml',
                'Authorization': 'Bearer {}'.format(self.token)
            }
            data = """<?xml version="1.0" encoding="UTF-8" ?>
                       <FirmaDocumentoRequest id="{}">
                       <xml_dte><![CDATA[{}]]></xml_dte>
                    </FirmaDocumentoRequest>
                """.format(invoice.mpfel_uuid, invoice.mpfel_source_xml)
            response = requests.post(self.ws_url_signer, data=data, headers=headers)
            result = xmltodict.parse(response.text)

            if result[u'FirmaDocumentoResponse'][u'tipo_respuesta'] == '1':
                error_message = u''
                error_message += '\n{} \n{}'.format(result[u'FirmaDocumentoResponse'][u'listado_errores'], invoice.mpfel_source_xml)
                raise UserError(error_message)
            else:
                doc = result[u'FirmaDocumentoResponse'][u'xml_dte']
                doc = escape_tildes(doc)

            if response.ok:
                _data = {
                    'mpfel_signed_xml': doc,
                }
                invoice.write(_data)
            else:
                raise ValidationError(_('MPFEL Signer: {}').format(result['message']))

        if self.provider == 'infile':
            xml = invoice.mpfel_source_xml
            data = {
                'llave': self.sign_key,
                'archivo': base64.b64encode(xml.encode('utf-8')).decode('utf-8'),
                'codigo': invoice.id,  # self.organization_code,   #'1001',  ##invoice.infilefel_uuid,
                'alias': self.sign_user,
                "es_anulacion": 'N'
            }
            sign_response = requests.post(url=self.ws_url_signer, json=data)
            result = json.loads(sign_response.text)
            if result['resultado']:
                xmlb64 = result['archivo']
                xml = base64.b64decode(xmlb64).decode('utf-8')
                sign_document = True
            else:
                raise UserError(_('Error signing document: {}').format(result['descripcion']))

        if self.provider == 'infile':
            if sign_document:
                headers = {
                    'usuario': self.certification_key,
                    'llave': self.user,
                    'identificador': invoice.mpfel_uuid,
                    'Content-Type': 'application/json',
                }
                data = {
                    'nit_emisor': invoice.company_id.vat.replace('-', '') if invoice.company_id.vat else 'C/F',
                    'correo_copia': 'miguelchuga@gmail.com',
                    'xml_dte': xmlb64
                }
                try:
                    response = requests.post(self.ws_url_document, headers=headers, data=json.dumps(data))
                    if response.ok:
                        result = json.loads(response.text)
                        if result['resultado']:

                            _sat_uuid = str(result['uuid']).split('-')
                            _mpfel_number = ''
                            _mpfel_serial = ''
                            _count = 0
                            for a in _sat_uuid:
                                if _count == 0:
                                    _mpfel_serial = a
                                if _count == 1 or _count == 2:
                                    _mpfel_number += a
                                _count += 1

                            if invoice.journal_id.ws_url_pdf:
                                url = invoice.journal_id.ws_url_pdf % (str(result['uuid']))
                                response = requests.get(url)
                                content_pdf = ''

                                if response.status_code == 200:
                                    content_pdf = base64.b64encode(response.content)

                            invoice.write({
                                'mpfel_pdf': content_pdf if invoice.journal_id.ws_url_pdf else '',
                                'mpfel_file_name': str(
                                    result['uuid']) + '.' + 'pdf' if invoice.journal_id.ws_url_pdf else '',
#                                'mpfel_sign_date': invoice_sign_date,
                                'mpfel_sat_uuid': result['uuid'],
                                #'mpfel_source_xml': source_xml,
                                'mpfel_signed_xml': xml,
                                'mpfel_result_xml': result['xml_certificado'],

                                'mpfel_serial': _mpfel_serial,
                                'mpfel_number': str(int(_mpfel_number, 16)),
                                #                                'number': _mpfel_serial + '-' + str(int(_mpfel_number, 16)),
                                'name': _mpfel_serial + '-' + str(int(_mpfel_number, 16)),
                                #                                'move_name': _mpfel_serial + '-' + str(int(_mpfel_number, 16)),
                            })
                            self._pos(invoice)
                        else:
                            error_message = u''
                            if type(result['descripcion_errores']) is list:
                                for message in result['descripcion_errores']:
                                    error_message += '\n{}: {}'.format(message['fuente'], message['mensaje_error'])
                            else:
                                error_message += '\n{}: {}'.format(
                                    result['RegistraDocumentoXMLResponse']['listado_errores']['error']['cod_error'],
                                    result['RegistraDocumentoXMLResponse']['listado_errores']['error']['desc_error'])
                            raise UserError(error_message)
                    else:
                        raise UserError(
                            _('infilefel: Response error consuming web service: {}').format(str(response.text)))
                except Exception as e:
                    error_message = ''
                    if hasattr(e, 'object'):
                        if hasattr(e, 'reason'):
                            error_message = u"{}: {}".format(e.reason, e.object)
                        else:
                            error_message = u" {}".format(e.object)
                    elif hasattr(e, 'message'):
                        error_message = e.message
                    elif hasattr(e, 'name'):
                        error_message = e.name
                    else:
                        error_message = e
                    raise UserError(_('infilefel: Error consuming web service: {}').format(error_message))
            else:
                raise UserError(_('infilefel Signer: {}').format(result['message']))


    def registrar_documento(self, invoice):
        def escape_string_nombre2(value):
            if not value:
                value = ""
            return html.escape(value).encode("ascii", "xmlcharrefreplace").decode("utf-8")

        def escape_string(value):
            if not value:
                value = ''
            return value.replace('&', '&amp;').replace('>', '&gt;').replace('<', '&lt').replace('"', '&quot;').replace(
                "'", '&apos;').replace("é", '&#233;').replace("É", '&#201;').replace("Ó", '&#211;').replace("Í",
                                                                                                            '&#205;')

        def escape_tildes(value):
            if not value:
                value = ""
            return value.replace('ñ', '&#241;').replace('Ñ', '&#209;').replace("á", '&#225;').replace("é",
                                                                                                      '&#233;').replace(
                "í", '&#237;').replace("ó", '&#243;').replace("Ó", '&#211;').replace("ú", '&#250;').replace("É",
                                                                                                            '&#201;').replace(
                "Í", '&#205;')

        #        replace('Ñ', '&#209;').
        _pos_id = self.env['ir.config_parameter'].search([('key', '=', 'pos')]).ids[0]
        _generico_id = self.env['ir.config_parameter'].search([('key', '=', 'generico')]).ids[0]

        _tiene_pos = self.env['ir.config_parameter'].browse([_pos_id])
        _tiene_generico = self.env['ir.config_parameter'].browse([_generico_id])

        token = None
        error_message = ''
        if not invoice.journal_id.mpfel_type:
            return
        elif invoice.journal_id.mpfel_type == '':
            return
        elif invoice.mpfel_sat_uuid:
            return
        elif not invoice.invoice_date:
            raise UserError(_('Missing document date'))
        if self.provider == 'megaprint':
            if self.token_due_date >= fields.Datetime.now() :
                if invoice.mpfel_uuid and invoice.mpfel_signed_xml:
                    if self.token:
                        headers = {
                            'Content-Type': 'application/xml',
                            'Authorization': 'Bearer {}'.format(self.token)
                        }
                        data = '<?xml version="1.0" encoding="UTF-8" standalone="no"?> <RegistraDocumentoXMLRequest id="{}"><xml_dte><![CDATA[{}]]></xml_dte></RegistraDocumentoXMLRequest>'.format(
                            invoice.mpfel_uuid, invoice.mpfel_signed_xml)

                        try:
                            response = requests.post(self.ws_url_document, headers=headers, data=data)
                            final = unescape(response.text)
                            if response.ok:
                                pos = final.find('<listado_errores>')
                                errores = []
                                if pos >= 0:
                                    end = final.find('</listado_errores>', pos)
                                    errores = unescape(final[pos:end + 18])
                                    errores_dic = xmltodict.parse(errores)

                                if not errores:
                                    pos = final.find('<dte:GTDocumento')
                                    if pos >= 0:
                                        end = final.find('</dte:GTDocumento>', pos)
                                        doc = final[pos:end + 18]  # unescape(final[pos:end + 18])
                                    doc_dic = xmltodict.parse(doc)
                                if errores:
                                    error_message = u''
                                    error_message += '\n{} \n{} \n{}'.format(errores, invoice.mpfel_source_xml, invoice.mpfel_signed_xml)
                                    raise UserError(error_message)

                                if not errores:
                                    _mpfel_serial = ''
                                    _mpfel_number = ''
                                    _sat_uuid = str(
                                        doc_dic[u'dte:GTDocumento'][u'dte:SAT'][u'dte:DTE'][u'dte:Certificacion'][
                                            u'dte:NumeroAutorizacion']['#text']).split('-')
                                    _count = 0
                                    for a in _sat_uuid:
                                        if _count == 0:
                                            _mpfel_serial = a
                                        if _count == 1 or _count == 2:
                                            _mpfel_number += a
                                        _count += 1

                                    if invoice.journal_id.ws_url_pdf:
                                        pdf_headers = {
                                            'Content-Type': 'application/xml',
                                            'Authorization': 'Bearer {}'.format(self.token)
                                        }
                                        _sat_uid = str(
                                            doc_dic[u'dte:GTDocumento'][u'dte:SAT'][u'dte:DTE'][
                                                u'dte:Certificacion'][
                                                u'dte:NumeroAutorizacion']['#text'])
                                        pdf_data = """<RetornaPDFRequest>
                                                   <uuid>{ThisisaUUID}</uuid>
                                                </RetornaPDFRequest>
                                              """.format(
                                            ThisisaUUID=_sat_uid
                                        )
                                        pdf_response = requests.post(url=invoice.journal_id.ws_url_pdf,
                                                                     headers=pdf_headers, data=pdf_data)
                                        result_pdf = xmltodict.parse(pdf_response.text)
                                        _pdf = result_pdf['RetornaPDFResponse']['pdf']

                                    if invoice.journal_id.tipo_venta == 'ND':
                                        _data = {
                                            'mpfel_pdf': _pdf if invoice.journal_id.ws_url_pdf else '',
                                            'mpfel_file_name': _sat_uid + '.' + 'pdf' if invoice.journal_id.ws_url_pdf else '',
                                            'mpfel_sat_uuid': str(
                                                doc_dic[u'dte:GTDocumento'][u'dte:SAT'][u'dte:DTE'][
                                                    u'dte:Certificacion'][u'dte:NumeroAutorizacion'][
                                                    '#text']),
                                            'mpfel_result_xml': final,
                                            'mpfel_serial': _mpfel_serial,
                                            'mpfel_number': str(int(_mpfel_number, 16)),
                                            'ref': _mpfel_serial + '-' + str(int(_mpfel_number, 16)),
                                            'name': _mpfel_serial + '-' + str(int(_mpfel_number, 16)),

                                            'date_sign': doc_dic[u'dte:GTDocumento'][u'dte:SAT'][u'dte:DTE'][
                                                u'dte:Certificacion'][u'dte:FechaHoraCertificacion']  # date_sign,
                                        }
                                    else:
                                        _data = {
                                            'mpfel_pdf': _pdf if invoice.journal_id.ws_url_pdf else '',
                                            'mpfel_file_name': _sat_uid + '.' + 'pdf' if invoice.journal_id.ws_url_pdf else '',
                                            'mpfel_sat_uuid': str(
                                                doc_dic[u'dte:GTDocumento'][u'dte:SAT'][u'dte:DTE'][
                                                    u'dte:Certificacion'][u'dte:NumeroAutorizacion'][
                                                    '#text']),
                                            'mpfel_result_xml': final,
                                            'mpfel_serial': _mpfel_serial,
                                            'serie_gt': _mpfel_serial,
                                            'documento_gt': str(int(_mpfel_number, 16)),
                                            'ref': _mpfel_serial + '-' + str(int(_mpfel_number, 16)),
                                            'name': _mpfel_serial + '-' + str(int(_mpfel_number, 16)),
                                            'payment_reference': _mpfel_serial + '-' + str(int(_mpfel_number, 16)),
                                            'mpfel_number': str(int(_mpfel_number, 16)),
                                            'date_sign': doc_dic[u'dte:GTDocumento'][u'dte:SAT'][u'dte:DTE'][
                                                u'dte:DatosEmision'][u'dte:DatosGenerales'][u'@FechaHoraEmision'],
                                            'mpfel_sign_date': doc_dic[u'dte:GTDocumento'][u'dte:SAT'][u'dte:DTE'][
                                                u'dte:Certificacion'][u'dte:FechaHoraCertificacion']
                                        }

                                    invoice.write(_data)
                                    #cuando no hay POS instalado mejor comentarear esta linea
                                    self._pos(invoice)

                            else:
                                raise ValidationError(
                                    _('MPFEL: Response error consuming web service: {}').format(str(response.text)))
                        except ValidationError as e:
                            if len(error_message) <= 2:
                                error_message = ''
                            if hasattr(e, 'object'):
                                if hasattr(e, 'reason'):
                                    error_message += u"{}: {}".format(e.reason, e.object)
                                else:
                                    error_message += u" {}".format(e.object)
                            elif hasattr(e, 'message'):
                                error_message += e.message
                            elif hasattr(e, 'name'):
                                error_message += e.name
                            else:
                                error_message += e
                            raise ValidationError(_('MPFEL: Error consuming web service: {}').format(error_message))
                    else:
                        raise ValidationError(_('MPFEL: API key not set'))
                else:
                    raise ValidationError(_('Documento no ha sido firmado...'))
            else:
                raise ValidationError(_('MPFEL: Token expired'))

    def _pos(self,invoice):
        _pos_id = self.env['ir.config_parameter'].search([('key', '=', 'pos')]).ids[0]
        _generico_id = \
            self.env['ir.config_parameter'].search([('key', '=', 'generico')]).ids[0]

        _tiene_pos = self.env['ir.config_parameter'].browse([_pos_id])
        _tiene_generico = self.env['ir.config_parameter'].browse([_generico_id])

        if _tiene_pos.value == 'True':
            _order_id_ = self.env['pos.order'].search(
                [('account_move', '=', invoice.id)])
            if _order_id_:
                _pos_order_id = self.env['pos.order'].browse([_order_id_.id])
                _infilefel_comercial_name = invoice.journal_id.infilefel_comercial_name
                _serie_venta = invoice.mpfel_serial
                _infilefel_establishment_street = invoice.journal_id.infilefel_establishment_street
                _infile_number = str(int(invoice.mpfel_number, 16))
                _infilefel_sat_uuid =invoice.mpfel_sat_uuid
                _infilefel_sign_date = invoice.mpfel_sign_date
                _nit_empresa = invoice.company_id.vat
                _nombre_empresa = invoice.company_id.name
                _numero_pedido = _pos_order_id.name
                _nombre_cajero = _pos_order_id.user_id.display_name
                _metodo_pago = _pos_order_id.payment_ids[0].payment_method_id.name


                if _tiene_generico.value == 'True':
                    _nombre_cliente = invoice.partner_id.name if not _order_id_.nombre else _order_id_.nombre
                    _nit = invoice.partner_id.vat if not _order_id_.nombre else _order_id_.nit
                    _direccion_cliente = invoice.partner_id.street if not _order_id_.nombre else _order_id_.direccion
                else:
                    _nombre_cliente = invoice.partner_id.name
                    _nit = invoice.partner_id.vat
                    _direccion_cliente = invoice.partner_id.street

                _fecha_factura = invoice.invoice_date
                _forma_pago = _forma_pago = _pos_order_id.payment_ids[
                    0].payment_method_id.name

                _caja = _pos_order_id.config_id.name
                _vendedor = _pos_order_id.create_uid.name
                _nit_certificador = self.nit_certificador
                _nombre_certificador = self.nombre_certificador
                _frase_certificador = self.frase_certificador
                _pos_order_id.write({'frase_certificador': _frase_certificador,
                                                                         'nombre_certificador': _nombre_certificador,
                                                                         'nit_certificador': _nit_certificador, 'vendedor': _vendedor,
                                                                         'caja': _caja, 'forma_pago': _forma_pago,
                                                                         'fecha_factura': _fecha_factura,
                                                                         'direccion_cliente': _direccion_cliente, 'nit': _nit,
                                                                        'nombre_cliente': _nombre_cliente,
                                                                        'infilefel_sat_uuid': _infilefel_sat_uuid,
                                                                        'infilefel_sign_date': _infilefel_sign_date,
                                                                        'infile_number': _infile_number,
                                                                        'nombre_empresa': _nombre_empresa, 'nit_empresa': _nit_empresa,
                                                                        'infilefel_comercial_name': _infilefel_comercial_name,
                                                                        'serie_venta': _serie_venta,
                                                                        'infilefel_establishment_street': _infilefel_establishment_street,})

    def void_document(self, invoice):
        if self.provider == 'megaprint':
            self.void_document_megaprint(invoice)
        if self.provider == 'infile':
            self.void_document_infile(invoice)


    def pdf_document(self, invoice):
        for rec in self:
            if invoice.journal_id.ws_url_pdf and invoice.mpfel_sat_uuid:
                url = invoice.journal_id.ws_url_pdf % (invoice.mpfel_sat_uuid)
                response = requests.get(url)
                content_pdf = ''
                if response.status_code == 200:
                    content_pdf = base64.b64encode(response.content)
                    invoice.write({'mpfel_pdf': content_pdf,
                                   'mpfel_file_name': invoice.mpfel_sat_uuid + '.' + 'pdf' })
            print(invoice)

    def void_document_infile(self, invoice):
        token = None
        if not invoice.journal_id.mpfel_type:
            return
        elif not invoice.invoice_date:
            raise UserError(_('Missing document date'))
        else:
            if not invoice.mpfel_void_uuid:
                invoice.mpfel_void_uuid = str(uuid.uuid4())

            sign_date = datetime.now().replace(tzinfo=pytz.UTC).astimezone(pytz.timezone('America/Guatemala'))

            sign_date_utc = datetime.now().replace(tzinfo=pytz.UTC)
            current_date = sign_date.strftime('%Y-%m-%dT%H:%M:%S-06:00')
            current_time = datetime.now().replace(tzinfo=pytz.UTC).astimezone(pytz.timezone('America/Guatemala')).strftime('%H:%M:%S-06:00')

            invoice_sign_date = invoice.mpfel_sign_date #.strftime('%Y-%m-%dT%H:%M:%S-06:00')
            void_sign_date = invoice.invoice_date.strftime('%Y-%m-%dT') + current_time

            xml = """<?xml version="1.0" encoding="UTF-8"?><dte:GTAnulacionDocumento Version="0.1" xmlns:dte="http://www.sat.gob.gt/dte/fel/0.1.0" xmlns:xd="http://www.w3.org/2000/09/xmldsig#" xmlns:n1="http://www.altova.com/samplexml/other-namespace" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">

                <dte:SAT>
                    <dte:AnulacionDTE ID="DatosCertificados">
                        <dte:DatosGenerales ID="DatosAnulacion"
                            NumeroDocumentoAAnular="{NumeroDocumentoAAnular}"
                            NITEmisor="{NITEmisor}"
                            IDReceptor="{IDReceptor}"
                            FechaEmisionDocumentoAnular="{FechaEmisionDocumentoAnular}"
                            FechaHoraAnulacion="{FechaHoraAnulacion}"
                            MotivoAnulacion="Cancelacion"
                        />
                    </dte:AnulacionDTE>
                </dte:SAT></dte:GTAnulacionDocumento>""".format(
                NumeroDocumentoAAnular=invoice.mpfel_sat_uuid,
                NITEmisor=invoice.company_id.vat.replace('-', '').upper() if invoice.company_id.vat.upper() else 'C/F',
                IDReceptor=invoice.partner_id.vat.replace('-', '').upper()  if invoice.partner_id.vat.upper() else 'CF',
                FechaEmisionDocumentoAnular=invoice_sign_date,
                FechaHoraAnulacion=void_sign_date,
                NITCertificador=invoice.company_id.vat.replace('-', '') if invoice.company_id.vat else 'C/F',
                NombreCertificador=invoice.company_id.name,
                FechaHoraCertificacion=void_sign_date,
            )

            source_xml = xml

            sign_document = False
            if 1==2:#self.signing_type == 'LOCAL':
                tmp_dir = gettempdir()
                source_xml_file = os.path.join(tmp_dir, '{}_source.xml'.format(invoice.mpfel_void_uuid))
                signed_xml_file = os.path.join(tmp_dir, '{}.xml'.format(invoice.mpfel_void_uuid))
                with open(source_xml_file, 'w') as xml_file:
                    xml_file.write(xml)
                # os.system('java -jar {} {} {} {} {}'.format('/Users/oscar/Desarrollo/java/Xadesinfilefel.jar', source_xml_file, '/tmp/39796558-28d66a63138ff444.pfx', "'Neo2018$1'", invoice.infilefel_uuid))
                os.system("java -jar {} {} {} '{}' {} {} {}".format(self.signer_location, source_xml_file,
                                                                    self.certificate_file, self.certificate_password,
                                                                    invoice.infilefel_void_uuid, tmp_dir,
                                                                    'DatosGenerales'))

                if os.path.isfile(signed_xml_file):
                    with open(signed_xml_file, 'r') as myfile:
                        xml = myfile.read()
                    sign_document = True
                else:
                    raise UserError(_('infilefel: Signed XML file not found'))
            else:

                data = {
                    'llave': self.sign_key,
                    'archivo': base64.b64encode(xml.encode('utf-8')).decode('utf-8'),
                    'codigo': '1001',#invoice.infilefel_void_uuid,
                    'alias': self.sign_user,
                    "es_anulacion": 'S'
                }
                sign_response = requests.post(url=self.ws_url_signer, json=data)
                result = json.loads(sign_response.text)
                if result['resultado']:
                    xmlb64 = result['archivo']
                    xml = base64.b64decode(xmlb64).decode('utf-8')
                    sign_document = True
                else:
                    raise UserError(_('Error signing document: {}').format(result['descripcion']))

            if sign_document:

                headers = {
                    'usuario': self.certification_key,
                    'llave':  self.user,
                    'identificador': invoice.mpfel_uuid,
                    'Content-Type': 'application/json',
                }
                data = {
                    'nit_emisor': invoice.company_id.vat.replace('-', '') if invoice.company_id.vat else 'C/F',
                    'correo_copia': 'ORamirezO@gmail.com',
                    'xml_dte': xmlb64
                }
                try:
                    response = requests.post(self.ws_url_void, headers=headers, data=json.dumps(data))
                    if response.ok:
                        result = json.loads(response.text)
                        if result['resultado']:
                            invoice.write({
                                'mpfel_void_sat_uuid': result['uuid'],
                                'mpfel_void_source_xml': source_xml,
                                'mpfel_void_signed_xml': xml,
                                'mpfel_void_result_xml': result['xml_certificado'],
                            })
                            invoice.button_draft()
                            invoice.button_cancel()

                        else:
                            error_message = u''
                            if type(result['descripcion_errores']) is list:
                                for message in result['descripcion_errores']:
                                    error_message += '\n{}: {}'.format(message['fuente'], message['mensaje_error'])
                            else:
                                error_message += '\n{}: {}'.format(
                                    result['RegistraDocumentoXMLResponse']['listado_errores']['error']['cod_error'],
                                    result['RegistraDocumentoXMLResponse']['listado_errores']['error'][
                                        'desc_error'])
                            raise UserError(error_message)
                    else:
                        raise UserError(
                            _('infilefel: Response error consuming web service: {}').format(str(response.text)))

                except Exception as e:
                    error_message = ''
                    if hasattr(e, 'object'):
                        if hasattr(e, 'reason'):
                            error_message = u"{}: {}".format(e.reason, e.object)
                        else:
                            error_message = u" {}".format(e.object)
                    elif hasattr(e, 'message'):
                        error_message = e.message
                    elif hasattr(e, 'name'):
                        error_message = e.name
                    else:
                        error_message = e
                    raise UserError(_('infilefel: Error consuming web service: {}').format(error_message))
            else:
                raise UserError(_('infilefel: API key not set'))

    def void_document_megaprint(self, invoice):

        def escape_string(value):
            return value.replace('&', '&amp;').replace('>', '&gt;').replace('<', '&lt').replace('"', '&quot;').replace(
                "'", '&apos;').encode('utf-8')

        es_neo = self.env['ir.config_parameter'].search([('key', '=', 'neo')])
        token = None
        _uuid = str(uuid.uuid4()).upper()
        if not invoice.journal_id.mpfel_type:
            return
        elif invoice.journal_id.mpfel_type == '':
            return
        elif not invoice.invoice_date:
            raise UserError(_('Missing document date'))
        elif self.token_due_date:
            if self.token_due_date >= fields.Datetime.now():
                if not invoice.mpfel_void_uuid:
                    invoice.mpfel_void_uuid = _uuid

                current_date = datetime.now().replace(tzinfo=pytz.utc).astimezone(pytz.timezone(self.env.user.tz))
                current_time = current_date.strftime('T%H:%M:%S-06:00')

                # cambio de fel 16012023
                _NITReceptor = ''
                if invoice.partner_id.vat:
                    _NITReceptor = invoice.partner_id.vat.replace('-', '') if invoice.partner_id.vat else 'CF'
                else:
                    if invoice.partner_id.x_dpi:
                        _NITReceptor = invoice.partner_id.x_dpi
                    else:
                        _NITReceptor = invoice.partner_id.x_id_extrangero

                xml = """
                <ns:GTAnulacionDocumento xmlns:ns="http://www.sat.gob.gt/dte/fel/0.1.0" xmlns:ds="http://www.w3.org/2000/09/xmldsig#" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" Version="0.1">
                   <ns:SAT>
                      <ns:AnulacionDTE ID="DatosCertificados">
                         <ns:DatosGenerales ID="DatosAnulacion" 
                           NumeroDocumentoAAnular="{NumeroDocumentoAAnular}"
                           NITEmisor="{NITEmisor}" 
                           IDReceptor="{IDReceptor}"
                           FechaEmisionDocumentoAnular="{FechaEmisionDocumentoAnular}"
                           FechaHoraAnulacion="{FechaHoraAnulacion}"
                           MotivoAnulacion="Anulacion" />
                      </ns:AnulacionDTE>
                   </ns:SAT>
                </ns:GTAnulacionDocumento>""".format(
                    NumeroDocumentoAAnular=invoice.mpfel_sat_uuid,
                    NITEmisor=invoice.company_id.vat.replace('-', '') if invoice.company_id.vat else 'C/F',
                    IDReceptor=_NITReceptor,
                    FechaEmisionDocumentoAnular=invoice.date_sign,
                    FechaHoraAnulacion=current_date.replace(microsecond=1).isoformat().replace('.000001', '.000'),
                    MotivoAnulacion='ANULACION',
                )
                headers = {
                    'Content-Type': 'application/xml',

                    'Authorization': 'Bearer {}'.format(self.token)
                }
                data = """<?xml version="1.0" encoding="UTF-8" ?>
                    <FirmaDocumentoRequest id="{}">
                    <xml_dte><![CDATA[{}]]></xml_dte>
                    </FirmaDocumentoRequest>
                """.format(_uuid, xml)
                response = requests.post(self.ws_url_signer, data=data, headers=headers)
                result = xmltodict.parse(response.text)
                xml2 = unescape(response.text).encode('utf-8')

                xml3 = response.text.replace('&lt;', '<')
                xml3 = xml3.replace('&gt;', '>')
                xml2 = xml3

                source_xml = xml
                sign_document = False
                if result[u'FirmaDocumentoResponse'][u'listado_errores'] == None:
                    sign_document = True
                else:
                    raise ValidationError(
                        _('MPFEL: Response error consuming web service: {} \n{}').format(str(response.text),source_xml))



                error_message = ''
                if sign_document:
                    pos = xml2.find('<ns:GTAnulacionDocumento')
                    if pos >= 0:
                        end = xml2.find('</ns:GTAnulacionDocumento>', pos)
                        doc = unescape(xml2[pos:end + 26])

                    headers = {
                        'Content-Type': 'application/xml',
                        'Authorization': 'Bearer {}'.format(self.token)
                    }
                    data = '<?xml version="1.0" encoding="UTF-8" standalone="no"?><AnulaDocumentoXMLRequest id="{}"><xml_dte><![CDATA[{}]]></xml_dte></AnulaDocumentoXMLRequest>'.format(
                        invoice.mpfel_void_uuid.upper(), doc)

                    try:
                        response = requests.post(self.ws_url_void, headers=headers, data=data)
                        if response.ok:
                            result = xmltodict.parse(response.text)
                            if result['AnulaDocumentoXMLResponse']['tipo_respuesta'] == '1':
                                error_message = ''
                                if bool(result['AnulaDocumentoXMLResponse']['listado_errores']['error']):
                                    error_message += '\n{}: {}\n{}'.format(
                                        result['AnulaDocumentoXMLResponse']['listado_errores']['error']['cod_error'],
                                        result['AnulaDocumentoXMLResponse']['listado_errores']['error']['desc_error'],source_xml)
                                else:
                                    error_message += '\n{}: {}\n{}'.format(
                                        result['AnulaDocumentoXMLResponse']['listado_errores']['error']['cod_error'],
                                        result['AnulaDocumentoXMLResponse']['listado_errores']['error']['desc_error'],source_xml)
                                raise UserError(error_message)
                            else:
                                invoice.write({
                                    'mpfel_void_sat_uuid': result['AnulaDocumentoXMLResponse']['uuid'],
                                    'mpfel_void_source_xml': source_xml,
                                    'mpfel_void_signed_xml': doc,
                                    'mpfel_void_result_xml': result['AnulaDocumentoXMLResponse']['xml_dte'],
                                })
                                invoice.button_draft()
                                invoice.button_cancel()

                        else:
                            raise ValidationError(
                                _('MPFEL: Response error consuming web service: {}').format(str(response.text)))
                    except ValidationError as e:
                        if len(error_message) <= 2:
                            error_message = ''
                        if hasattr(e, 'object'):
                            if hasattr(e, 'reason'):
                                error_message += u"{}: {}".format(e.reason, e.object)
                            else:
                                error_message += u" {}".format(e.object)
                        elif hasattr(e, 'message'):
                            error_message += e.message
                        elif hasattr(e, 'name'):
                            error_message += e.name
                        else:
                            error_message += e
                        raise ValidationError(_('MPFEL: Error consuming web service: {}').format(error_message))
                else:
                    raise ValidationError(_('MPFEL: API key not set'))
            else:
                raise ValidationError(_('MPFEL: Token expired'))
        else:
            raise ValidationError(_('MPFEL: Token not set'))
