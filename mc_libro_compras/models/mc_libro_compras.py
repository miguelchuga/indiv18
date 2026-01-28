# -*- coding: utf-8 -*-

from odoo import models, fields, api, _, SUPERUSER_ID, tools

from odoo.exceptions import UserError

from odoo.exceptions import UserError
from datetime import datetime
import pytz
import re

from lxml import etree
from datetime import datetime
from dateutil.relativedelta import relativedelta

from odoo.tools import float_is_zero, float_compare
from odoo.tools.misc import formatLang
 
from odoo import api, fields, models
from datetime import datetime
import pytz
import base64
import io
from PyPDF2 import PdfReader, PdfWriter, PageObject
from reportlab.pdfgen import canvas
from odoo import models, fields, api 
import logging

from reportlab.lib.colors import white

_logger = logging.getLogger(__name__)

class MCLibroCompras(models.Model):
    
    _name = "mc_libro_compras.mc_libro_compras"
    _description = "Libro de compras Guatemala"
    _inherit = ['mail.thread', 'mail.activity.mixin', 'image.mixin']


    @api.depends('fecha_desde')   
    def _fecha_desde_mda(self):
        for record in self:
            if record.fecha_desde:
                dt = str(record.fecha_desde).split('-')
                record.fecha_desde_mda = dt[2]+'-'+dt[1]+'-'+dt[0]   
            else:
                record.fecha_desde_mda = ''

    @api.depends('fecha_hasta')   
    def _fecha_hasta_mda(self):
        for record in self:
            if record.fecha_hasta:
                dt = str(record.fecha_hasta).split('-')
                record.fecha_hasta_mda = dt[2]+'-'+dt[1]+'-'+dt[0]   
            else:
                record.fecha_hasta_mda = ''

    name = fields.Text(string='Descripción', required=True)
    fecha_desde = fields.Date(string='Fecha desde' , required=True)
    fecha_hasta = fields.Date(string='Fecha hasta' , required=True)
    libro_line_ids = fields.One2many('mc_libro_compras.mc_libro_compras_line','libro_id', string=' ')
    libro_total_ids = fields.One2many('mc_libro_compras.mc_libro_compras_total','libro_id', string=' ')  
    libro_top_proveedores_ids = fields.One2many('mc_libro_compras.mc_libro_compras_top_proveedores','libro_id', string=' ')                            
    company_id  = fields.Many2one('res.company', string='Empresa', required=True, readonly=True,default=lambda self: self.env.company)
 
    tipo_fecha = fields.Selection([('documento', 'Documento'), ('contable', 'Contable')], 'Tipo fecha ', select=True,)
    file_xlsx = fields.Binary('Archivo de excel')
    nombre_archivo = fields.Char('nombre de archivo')
 
    fecha_desde_mda = fields.Char('Fecha desde mda', compute=_fecha_desde_mda,copy=False,store=True)
    fecha_hasta_mda = fields.Char('Fecha hasta mda', compute=_fecha_hasta_mda,copy=False,store=True)

 
    journal_ids = fields.Many2many('account.journal','libro_compras_journal_rel',string='Diarios',domain="[('type','=','purchase')]")
    nombre_establecimiento = fields.Char('Nombre establecimiento',)

    total_local_bienes_gravados = fields.Float(string='Local bienes gravados')
    total_local_servicios_gravados = fields.Float(string='Local servicios gravados')
    total_local_bienes_exentos = fields.Float(string='Local bienes exentos')
    total_local_servicios_exentos = fields.Float(string='Local servicios exentos')
    total_importacion_bienes_gravados = fields.Float(string='Importación bienes gravados')
    total_importacion_servicios_gravados = fields.Float(string='Importación servicios gravados')
    total_importacion_bienes_exentos = fields.Float(string='Importación bienes exentos')
    total_importacion_servicios_exentos = fields.Float(string='Importación servicios exentos')
    total_iva = fields.Float(string='IVA')
    total_iva_local = fields.Float(string='IVA local')
    total_iva_importacion = fields.Float(string='IVA Importación')

    total_total = fields.Float(string='Total')
    total_lineas = fields.Integer(string='Total lineas')
     
    folio = fields.Integer('Folio inicial:')
    file_name = fields.Char('Nombre del archivo',readonly=True, copy=False)
    file_pdf = fields.Binary(string='Libro compras foliado',readonly=True, copy=False)

    def foliar(self, nuevo_inicio=1, margen_derecho_cm=1.76, margen_superior_cm=16.8):
        """
        Reemplaza los números de folio existentes en el PDF original con una nueva numeración.
        Actualiza el campo 'folios_reemplazados' en consecuencia.

        :param nuevo_inicio: Número desde el cual comenzará la nueva numeración.
        :param margen_derecho_cm: Margen desde el borde derecho en centímetros.
        :param margen_superior_cm: Margen desde el borde inferior en centímetros.
        """
        for record in self:
            if not record.file_pdf:
                continue

            try:
                # Decodificar el PDF de Base64 a bytes
                decoded_pdf = base64.b64decode(record.file_pdf)

                # Convertir márgenes de cm a puntos
                margen_derecho = self.cm_a_puntos(margen_derecho_cm)
                margen_superior = self.cm_a_puntos(margen_superior_cm)

                # Reemplazar folios en el PDF
                modified_pdf_bytes = self._reemplazar_folio_en_pdf(
                    pdf_bytes=decoded_pdf,
                    inicio=record.folio,
                    margen_derecho=margen_derecho,
                    margen_superior=margen_superior
                )

                # Codificar el PDF modificado a Base64
                record.file_pdf = base64.b64encode(modified_pdf_bytes)
  
            except Exception as e:
                _logger.error(f"Error al reemplazar folios en el documento {record.name}: {e}")



    def cm_a_puntos(self, cm):
        """
        Convierte centímetros a puntos.

        :param cm: Medida en centímetros.
        :return: Medida en puntos.
        """
        return cm * 28.3465

    def imprimir(self):
        lines = self.env['mc_libro_compras.mc_libro_compras'].browse(self.id)          

        valor = self.env['report.libro_compras.report_librocompras_xls'].generate_xlsx_report(lines=lines)

        hora_gt = pytz.timezone('America/Guatemala')
        fecha_gt = datetime.now(hora_gt)
        fecha_actual = fecha_gt.strftime('%Y-%m-%d %H:%M:%S')
        self.nombre_archivo = f'Libro de compras generado {fecha_actual}.xlsx'
        self.file_xlsx = valor
 


    def genera_libro(self):

        self.env["mc_libro_compras.mc_libro_compras_line"].search([('libro_id','=',self.id)]).unlink()
        
        # Asfalgua
#        valor_negativo_linea = self.env['ir.config_parameter'].search([('key', '=', 'libro_compras_valor_negativo_linea')])
#        no_usar_tasa_de_cambio = self.env['ir.config_parameter'].search([('key', '=', 'libro_compras_no_usar_tasa_de_cambio')])
        no_usar_signo_transaccion = self.env['ir.config_parameter'].search([('key', '=', 'libro_compras_no_usar_signo_transaccion')])
        
        sign = 1

        # Se debe agregar este parametro en : Ajustes / tecnico / Parametros del sistema
        # key = vat
        # value = True
        # cuando se usa res.partner el campo VAT  o cuando se usa el campo ref
        vat_id = self.env['ir.config_parameter'].search([('key', '=', 'vat')]).ids[0]
        _usa_vat = self.env['ir.config_parameter'].browse([vat_id])
        proveedor_neo = self.env['ir.config_parameter'].search([('key', '=', 'proveedor_neo')])
        _proveedor_neo = self.env['ir.config_parameter'].browse([proveedor_neo])

        # en la version 13.0 name  <> '/' quiere decir una factura que no esta validada antes se tomaba como borrador
        if self.tipo_fecha == 'documento':
            sql = """
            SELECT company_id, id, date_invoice, date,state
              FROM "MC_libro_compras"
             WHERE   company_id = %s AND date_invoice >= %s AND date_invoice <= %s
             """
            self.env.cr.execute(sql, (self.company_id.id,self.fecha_desde,self.fecha_hasta,))
        else:
            sql = """
            SELECT company_id, id, date_invoice, date,state
              FROM "MC_libro_compras"
             WHERE   company_id = %s AND date >= %s AND date <= %s
             """
            self.env.cr.execute(sql, (self.company_id.id,self.fecha_desde,self.fecha_hasta,))

        doc_count = 0


        #totales del encabezado
        total_local_bienes_gravados = 0
        total_local_servicios_gravados = 0
        total_local_bienes_exentos = 0
        total_local_servicios_exentos = 0
        total_importacion_bienes_gravados = 0
        total_importacion_servicios_gravados = 0
        total_importacion_bienes_exentos = 0   
        total_importacion_servicios_exentos = 0
        total_iva = 0
        total_total = 0
        total_lineas= 0
        total_iva_local = 0
        total_iva_importacion = 0

        invoice_ids = self.env['account.move'].search([('date', '>=', self.fecha_desde),('date', '<=', self.fecha_hasta) ,('state','=','posted') , ('move_type','in',('in_invoice','in_refund')), ('journal_id','in',self.journal_ids.ids)   ])

        #Verificacio del establecimiento cuando es el mismo que lo ponga en una variable
        _establecimiento_unico = True
        _establecimiento = ''
        _uno = 1
        if not self.journal_ids:
            raise UserError(_("ERROR: Debe seleccionar al menos un diario"))


        if self.journal_ids:
            for j in self.journal_ids:
                if _uno == 1:
                    _establecimiento = j.establecimiento
                _uno = _uno + 1
                if _establecimiento != j.establecimiento:
                    _establecimiento_unico = False

        if _establecimiento_unico:
            self.nombre_establecimiento = ' / '+    self.journal_ids[0].nombre_establecimiento if self.journal_ids[0].nombre_establecimiento  else ''
        else:
            self.nombre_establecimiento = ''


        for query_line in invoice_ids: #self.env.cr.dictfetchall():

            doc_count += 1
            invoice_id = self.env['account.move'].browse([query_line['id']])
            
            if no_usar_signo_transaccion.value=='True':
                sign = invoice_id.move_type in ['in_refund', 'out_refund'] and -1 or 1

            if invoice_id.name:
                _name = invoice_id.name
            else:
                _name = 'Anulado / Borrador'

                #depende los parametros de la empresa ver arriba
            if _usa_vat.value == 'True':
                _nit_dpi = invoice_id.partner_id.vat
            else:
                _nit_dpi = invoice_id.partner_id.ref
            _proveedor = invoice_id.partner_id.name


            _local_bienes_gravados = 0
            _local_bienes_gravados_combustible = 0
            _local_bienes_exentos = 0
            _local_servicios_gravados = 0
            _local_servicios_exentos = 0
            
            _local_bienes_pequenio_contribuyente = 0
            _local_servicios_pequenio_contribuyente = 0            

            _importacion_bienes_gravados = 0
            _importacion_bienes_gravados_total = 0
            
            _importacion_bienes_exentos = 0
            _importacion_bienes_exentos_total = 0
            
            _importacion_servicios_gravados = 0
            _importacion_servicios_exentos = 0
            _activos_fijos = 0

            _idp = 0
            _timbre_prensa = 0
            _tasa_municipal = 0
            _inguat = 0
            _retension_isr = 0
            _retension_iva = 0
            _iva = 0
            _iva_local = 0
            _iva_importacion = 0

            _total = 0
#            _currency_id = invoice_id.currency_id.with_context(date=invoice_id.date_invoice)
            
            # Si la moneda de la compra es quetzales. 
            if self.env.user.company_id.currency_id.id == invoice_id.currency_id.id:
                # El valor en otra moneda es 0.
                _otra_moneda = 0
                
            else:
                # El valor en otra moneda es el monto de la factura.
                _otra_moneda = invoice_id.amount_total 

            for l in invoice_id.invoice_line_ids:

                invoice_line_id = l #self.env['account.move.line'].browse([ l.id ])

                precio_subtotal = abs(invoice_line_id.balance ) #invoice_line_id.price_subtotal

                _polizas_importacion = True

                # Define si el producto es bien o servicio.
                _tipo = 'servicio'
                if invoice_line_id.product_id.type == 'service':
                    if invoice_line_id.product_id.default_code == 'Local-Bienes':
                        _tipo = 'bien'
                    else:
                        if invoice_line_id.product_id.default_code == 'Local-Activos':
                            _tipo = 'activos'
                        else:
                            _tipo = 'servicio'
                else:
                    _tipo = 'bien'

                _tiene_iva = False
                _es_idp = False
                
                for t in invoice_line_id.tax_ids:
                    tax_id = self.env['account.tax'].browse([ t.id ])
                    
                    if tax_id.tipo_impuesto == 'iva':
                        _tiene_iva = True
                    if tax_id.tipo_impuesto == 'idp':
                        _tipo = 'bien'
                        _es_idp = True
                
                # SE EVALUA EL TIPO DE VENTA "FPC" PARA PEQUEÑO CONTRIBUYENTE.
                if   invoice_id.journal_id.tipo_venta == 'FPC':
                    if invoice_id.journal_id.local == 'Local' and _tipo == 'bien' and _tiene_iva:
                        _local_bienes_pequenio_contribuyente += precio_subtotal
                    #LOCAL BIENES EXENTO.
                    if invoice_id.journal_id.local == 'Local' and _tipo == 'bien' and not _tiene_iva:
                        _local_bienes_pequenio_contribuyente += precio_subtotal
                    #LOCAL SERVICIOS GRAVADO.
                    if invoice_id.journal_id.local == 'Local' and _tipo == 'servicio' and _tiene_iva:
                        _local_servicios_pequenio_contribuyente += precio_subtotal
                    #LOCAL SERVICIOS exentos.
                    if invoice_id.journal_id.local == 'Local' and _tipo == 'servicio' and not _tiene_iva:
                        _local_servicios_pequenio_contribuyente += precio_subtotal
                else:                    
                    # LOCAL.
                    # LOCAL BIENES GRAVADOS.
                    if invoice_id.journal_id.local == 'Local' and _tipo == 'bien' and _tiene_iva:
                        if _es_idp:
                            _local_bienes_gravados_combustible += precio_subtotal
                        else:
                            _local_bienes_gravados += precio_subtotal
                    # LOCAL BIENES EXENTO.
                    if invoice_id.journal_id.local == 'Local' and _tipo == 'bien' and not _tiene_iva:
                        _local_bienes_exentos += precio_subtotal
                    # LOCAL SERVICIOS GRAVADO.
                    if invoice_id.journal_id.local == 'Local' and _tipo == 'servicio' and _tiene_iva:
                        _local_servicios_gravados += precio_subtotal
                    # LOCAL SERVICIOS EXENTOS.
                    if invoice_id.journal_id.local == 'Local' and _tipo == 'servicio' and not _tiene_iva:
                        _local_servicios_exentos += precio_subtotal
                    if invoice_id.journal_id.local == 'Local' and _tipo == 'activos':
                        _activos_fijos += precio_subtotal

                #  Si es una importación.
                if _polizas_importacion:
                    if invoice_id.journal_id.local == 'Importacion' and _tipo == 'bien' and _tiene_iva:
                        _importacion_bienes_gravados += precio_subtotal
                    # IMPORTACION BIENES EXENTO.
                    if invoice_id.journal_id.local == 'Importacion' and _tipo == 'bien' and not _tiene_iva:
                        _importacion_bienes_exentos += precio_subtotal
                    # IMPORTACION SERVICIOS GRAVADO.
                    if invoice_id.journal_id.local == 'Importacion' and _tipo == 'servicio' and _tiene_iva:
                        _importacion_servicios_gravados += precio_subtotal
                    # IMPORTACION SERVICIOS exentos.
                    if invoice_id.journal_id.local == 'Importacion' and _tipo == 'servicio' and not _tiene_iva:
                        _importacion_servicios_exentos += precio_subtotal

                    # estos campos debieron llamarse _importacion_gravados_total y _importacion_exentos_total
                    _importacion_bienes_gravados_total = (_importacion_bienes_gravados + _importacion_servicios_gravados) 
                    _importacion_bienes_exentos_total = (_importacion_bienes_exentos + _importacion_servicios_exentos)

            # Suma los impuestos.
            for t in invoice_id.line_ids:
                print(t)

                if t.tax_line_id.tipo_impuesto == 'retiva':
                    _retension_iva = _retension_iva + abs(t.balance)
                if t.tax_line_id.tipo_impuesto == 'retisr':
                   _retension_isr = _retension_isr + abs(t.balance)
                if t.tax_line_id.tipo_impuesto == 'municipal':
                   _tasa_municipal = _tasa_municipal + abs(t.balance)
                if t.tax_line_id.tipo_impuesto == 'idp':
                   _idp = _idp + abs(t.balance)
                if t.tax_line_id.tipo_impuesto == 'prensa':
                   _timbre_prensa = _timbre_prensa + abs(t.balance)
                if t.tax_line_id.tipo_impuesto == 'inguat':
                   _inguat = _inguat + abs(t.balance)
                if t.tax_line_id.tipo_impuesto == 'iva':
                   _iva = _iva + abs(t.balance)
            
            # Si es una Factura Especial.
            if invoice_id.journal_id.tipo_venta == 'FE':
                # precio_subtotal.              
                _total = invoice_id.amount_untaxed + _iva
            # Si no es una factura especial.
            else:
                # Compra en quetzales.
                if _otra_moneda == 0:
                    # El total de la factura es sin valores exentos y sin IDP.
                    _total = invoice_id.amount_total - _tasa_municipal - _idp
                # Compra en dólares.
                else:
                    # Si la compra en dólares es local.
                    if invoice_id.journal_id.local == 'Local':
                        _total = abs(invoice_id.amount_untaxed_signed) + _iva
                    # Si es una importación.
                    else:
                        _total = abs(invoice_id.amount_untaxed_signed)

            if invoice_id.journal_id.local=='Importacion':
                _suma_iva = _iva
            else:
                _suma_iva = 0.00

            _field = self.env['ir.model.fields'].search([('name', '=', 'mpfel_sat_uuid')])
            if not _field:
                _serie = invoice_id.serie_gt
                _documento = invoice_id.documento_gt
            else:
                if  invoice_id.mpfel_sat_uuid:
                    _serie = invoice_id.serie_gt #invoice_id.infile_serial 
                    _documento = invoice_id.documento_gt #invoice_id.infile_number
                else:                
                    _serie = invoice_id.serie_gt
                    _documento = invoice_id.documento_gt
          
            # Separa el iva de locales e importaciones.
            total_gravado = 0
            total_exentos = 0
            total_gravado_importacion = 0
            total_gravado_importacion = ( _importacion_bienes_gravados * sign)+(_importacion_servicios_gravados * sign)
            total_gravado = (_local_bienes_gravados * sign)+(_local_bienes_gravados_combustible * sign)+(_local_servicios_gravados * sign)
            total_exentos = (_local_bienes_exentos+_local_servicios_exentos+_importacion_bienes_exentos+_importacion_servicios_exentos)

            if total_gravado != 0:
                _iva_local = (_iva * sign)
            if total_gravado_importacion != 0:
                _iva_importacion = (_iva * sign) 

            invoice_line = {'libro_id':self.id,
                'name': _name,
                'invoice_id': invoice_id.id,
                'partner_id': invoice_id.partner_id.id ,
                'journal_id': invoice_id.journal_id.id,
                'company_id': invoice_id.company_id.id,
                'correlativo': doc_count,
                'fecha_documento': invoice_id.invoice_date,
                'fecha_contable': invoice_id.date,

                'serie': _serie if _serie else '',
                'documento': _documento if _documento else '',

                'nit_dpi': _nit_dpi if _nit_dpi else '' ,
                'proveedor': _proveedor if _proveedor else '' ,
                'docto_odoo': invoice_id.name,
                'establecimiento': invoice_id.journal_id.establecimiento,
                'tipo_transaccion': invoice_id.journal_id.tipo_transaccion,
                'asiste_libro': invoice_id.journal_id.asiste_libro,
                'local_bienes_gravados': _local_bienes_gravados * sign,
                'local_bienes_pequenio_contribuyente': _local_bienes_pequenio_contribuyente * sign,                
                'local_bienes_gravados_combustible': _local_bienes_gravados_combustible * sign,
                'local_bienes_exentos': _local_bienes_exentos * sign,
                'local_servicios_gravados': _local_servicios_gravados * sign,
                'local_servicios_pequenio_contribuyente':_local_servicios_pequenio_contribuyente * sign,                
                'local_servicios_exentos': _local_servicios_exentos * sign,
                'importacion_bienes_gravados': _importacion_bienes_gravados * sign,
                'importacion_bienes_gravados_total': _importacion_bienes_gravados_total * sign,
                'importacion_bienes_exentos': _importacion_bienes_exentos * sign,
                'importacion_bienes_exentos_total': _importacion_bienes_exentos_total * sign,                
                'importacion_servicios_gravados': _importacion_servicios_gravados * sign,
                'importacion_servicios_exentos': _importacion_servicios_exentos * sign,
                'activos_fijos': _activos_fijos * sign,
                'idp': _idp * sign,
                'timbre_prensa': _timbre_prensa * sign,
                'tasa_municipal': _tasa_municipal * sign,
                'inguat': _inguat * sign,
                'retension_isr': _retension_isr * sign,
                'retension_iva': _retension_iva * sign,
                'iva': _iva * sign, 

                'iva_local': _iva_local, 
                'iva_importacion': _iva_importacion, 

                'total': ((_total + _retension_iva + _retension_isr+_suma_iva)-total_exentos)     * sign,
                
                'otra_moneda': _otra_moneda * sign,
                'base': (_local_bienes_gravados + _local_bienes_gravados_combustible + _local_servicios_gravados) * sign
            }


            #totales del encabezado
            total_local_bienes_gravados += (_local_bienes_gravados * sign)
            total_local_servicios_gravados += (_local_servicios_gravados * sign)
            total_local_bienes_exentos += (_local_bienes_exentos * sign)
            total_local_servicios_exentos += (_local_servicios_exentos * sign)
            total_importacion_bienes_gravados += (_importacion_bienes_gravados * sign)
            total_importacion_servicios_gravados += (_importacion_servicios_gravados * sign)
            total_importacion_bienes_exentos += (_importacion_bienes_exentos * sign)
            total_importacion_servicios_exentos += (_importacion_servicios_exentos * sign)
            total_iva += (_iva * sign)
            total_total += ((_total + _retension_iva + _retension_isr+_suma_iva) * sign)
            total_lineas += 1
            total_iva_local += _iva_local
            total_iva_importacion += _iva_importacion

            self.env['mc_libro_compras.mc_libro_compras_line'].create(invoice_line)
             

        self.update({'total_local_bienes_gravados':total_local_bienes_gravados,
                     'total_local_servicios_gravados':total_local_servicios_gravados,
                     'total_local_bienes_exentos':total_local_bienes_exentos,
                     'total_local_servicios_exentos':total_local_servicios_exentos,
                     'total_importacion_bienes_gravados':total_importacion_bienes_gravados,
                     'total_importacion_servicios_gravados':total_importacion_servicios_gravados,
                     'total_importacion_bienes_exentos':total_importacion_bienes_exentos,
                     'total_importacion_servicios_exentos':total_importacion_servicios_exentos,
                     'total_iva':total_iva,
                     'total_iva_local':total_iva_local,
                     'total_iva_importacion':total_iva_importacion,
                     'total_total':total_total,
                     'total_lineas':total_lineas,})

        # Elimina total.
        sql = """
                DELETE
                  FROM mc_libro_compras_mc_libro_compras_total
                 WHERE libro_id = %s
              """
        
        self.env.cr.execute(sql, (self.id,))
              
        sql = """
                SELECT SUM(local_bienes_gravados) AS local_bienes_gravados, SUM(local_bienes_pequenio_contribuyente) AS local_bienes_pequenio_contribuyente, SUM(local_bienes_gravados_combustible) AS local_bienes_gravados_combustible
                     , SUM(local_bienes_exentos) AS local_bienes_exentos, SUM(local_servicios_gravados) AS local_servicios_gravados, SUM(local_servicios_pequenio_contribuyente) AS local_servicios_pequenio_contribuyente
                     , SUM(local_servicios_exentos) AS local_servicios_exentos, SUM(importacion_bienes_gravados) AS importacion_bienes_gravados, SUM(importacion_bienes_gravados_total) AS importacion_bienes_gravados_total
                     , SUM(importacion_bienes_exentos) AS importacion_bienes_exentos, SUM(importacion_bienes_exentos_total) AS importacion_bienes_exentos_total, SUM(importacion_servicios_gravados) AS importacion_servicios_gravados
                     , SUM(importacion_servicios_exentos) AS importacion_servicios_exentos, SUM(activos_fijos) AS activos_fijos, SUM(idp) AS idp
                     , SUM(timbre_prensa) AS timbre_prensa, SUM(tasa_municipal) AS tasa_municipal, SUM(inguat) AS inguat
                     , SUM(retension_isr) AS retension_isr, SUM(retension_iva) AS retension_iva, SUM(iva) AS iva
                     , SUM(total) AS total, SUM(otra_moneda) AS otra_moneda, SUM(base) AS base
                  FROM mc_libro_compras_mc_libro_compras_line
                 WHERE company_id = %s AND fecha_documento >= %s AND fecha_documento <= %s
                GROUP BY libro_id
              """
        
        self.env.cr.execute(sql, (self.company_id.id,self.fecha_desde,self.fecha_hasta,))

        for query_line in self.env.cr.dictfetchall():
             
            invoice_line = {'libro_id':self.id,
                'local_bienes_gravados': query_line['local_bienes_gravados'],
                'local_bienes_pequenio_contribuyente': query_line['local_bienes_pequenio_contribuyente'],                
                'local_bienes_gravados_combustible': query_line['local_bienes_gravados_combustible'],
                'local_bienes_exentos': query_line['local_bienes_exentos'],
                'local_servicios_gravados': query_line['local_servicios_gravados'],
                'local_servicios_pequenio_contribuyente': query_line['local_servicios_pequenio_contribuyente'],                
                'local_servicios_exentos': query_line['local_servicios_exentos'],
                'importacion_bienes_gravados': query_line['importacion_bienes_gravados'],
                'importacion_bienes_gravados_total': query_line['importacion_bienes_gravados_total'],
                'importacion_bienes_exentos': query_line['importacion_bienes_exentos'],
                'importacion_bienes_exentos_total': query_line['importacion_bienes_exentos_total'],                
                'importacion_servicios_gravados': query_line['importacion_servicios_gravados'],
                'importacion_servicios_exentos': query_line['importacion_servicios_exentos'],
                'activos_fijos': query_line['activos_fijos'],
                'idp': query_line['idp'],
                'timbre_prensa': query_line['timbre_prensa'],
                'tasa_municipal': query_line['tasa_municipal'],
                'inguat': query_line['inguat'],
                'retension_isr': query_line['retension_isr'],
                'retension_iva': query_line['retension_iva'],
                'iva': query_line['iva'],
                'total': query_line['total'],
                'otra_moneda': query_line['otra_moneda'],
                'base': query_line['base']
            }

            self.env['mc_libro_compras.mc_libro_compras_total'].create(invoice_line)
            
            print (invoice_line)
        
        # Elimina top.
        sql = """
                DELETE
                  FROM mc_libro_compras_mc_libro_compras_top_proveedores
                 WHERE libro_id = %s
              """
                
        self.env.cr.execute(sql, (self.id,))

        sql = """
            Select t.company_id,t.libro_id,t.nit_dpi, t.name, t.cantidad, t.total 
                   From (Select company_id,libro_id,nit_dpi, proveedor AS name, count(libro_id) cantidad, sum(base) total From mc_libro_compras_mc_libro_compras_line where asiste_libro <> 'FE' group by company_id,libro_id,nit_dpi, proveedor)t
            Where t.company_id = %s and t.libro_id = %s
            order by t.total DESC LIMIT 10
              """

        self.env.cr.execute(sql, (self.company_id.id,self.id))
        
        doc_count = 0
        
        for query_line in self.env.cr.dictfetchall():
             
            doc_count += 1
             
            invoice_line = {'libro_id':self.id,
                'correlativo': doc_count,                            
                'nit_dpi': query_line['nit_dpi'],
                'proveedor': query_line['name'],
                'cantidad': query_line['cantidad'],                
                'base': query_line['total']
            }

            self.env['mc_libro_compras.mc_libro_compras_top_proveedores'].create(invoice_line)


    def _reemplazar_folio_en_pdf(self, pdf_bytes, inicio=1, margen_derecho=50, margen_superior=100):
        """
        Reemplaza los números de folio en un PDF, superponiendo un rectángulo blanco sobre el folio existente
        y agregando un nuevo folio con la numeración deseada.

        :param pdf_bytes: Bytes del PDF original.
        :param inicio: Número desde el cual comenzará la nueva numeración.
        :param margen_derecho: Espacio en puntos desde el borde derecho donde se colocará el nuevo folio.
        :param margen_superior: Espacio en puntos desde el borde inferior donde se colocará el nuevo folio.
        :return: Bytes del PDF modificado.
        """
        reader = PdfReader(io.BytesIO(pdf_bytes))
        writer = PdfWriter()
        num_paginas = len(reader.pages)

        for i in range(num_paginas):
            pagina_original = reader.pages[i]

            # Obtener el tamaño de la página
            width = float(pagina_original.mediabox.width)
            height = float(pagina_original.mediabox.height)

            _logger.info(f"Procesando página {i + 1} de {num_paginas} con tamaño {width}x{height} puntos.")

            # Crear un PDF en memoria para superponer el rectángulo blanco y el nuevo folio
            packet = io.BytesIO()
            can = canvas.Canvas(packet, pagesize=(width, height))

            # Superponer un rectángulo blanco sobre el folio existente
            # Ajusta las coordenadas y dimensiones según el diseño de tu PDF
            rect_width = 110  # Ancho del rectángulo blanco en puntos
            rect_height = 5  # Alto del rectángulo blanco en puntos

            # Calcula rect_x y rect_y para posicionar el rectángulo correctamente
            rect_x = width - margen_derecho - rect_width  # Posición X del rectángulo
            rect_y = margen_superior - 15                # Posición Y del rectángulo

            can.setFillColor(white)
            can.rect(rect_x, rect_y, rect_width, rect_height, fill=1, stroke=0)

            # Configurar el nuevo texto "Folio: X"
            folio_texto = f"Folio: {i + inicio}"
            font = "Helvetica-Bold"
            tamaño_fuente = 12
            can.setFont(font, tamaño_fuente)
            text_width = can.stringWidth(folio_texto, font, tamaño_fuente)

            # Posición del texto (superior derecho, más abajo)
            x = width - text_width - margen_derecho
            y = margen_superior  # Directamente margen_superior desde el borde inferior

            can.setFillColorRGB(0, 0, 0)  # Color negro para el texto
            can.drawString(x, y, folio_texto)
            can.save()

            # Mover el buffer al inicio
            packet.seek(0)
            overlay_pdf = PdfReader(packet)
            pagina_overlay = overlay_pdf.pages[0]

            # Combinar la página original con el overlay
            pagina_combinada = PageObject.create_blank_page(
                width=pagina_original.mediabox.width,
                height=pagina_original.mediabox.height
            )

            pagina_combinada.merge_page(pagina_original)
            pagina_combinada.merge_page(pagina_overlay)

            # Añadir la página combinada al writer
            writer.add_page(pagina_combinada)

            _logger.info(f"Folio agregado en la página {i + 1}.")

        # Escribir el PDF de salida en memoria
        output_stream = io.BytesIO()
        writer.write(output_stream)
        modified_pdf_bytes = output_stream.getvalue()

        _logger.info("Todos los folios han sido agregados exitosamente.")

        return modified_pdf_bytes


class MCLibroComprasLine(models.Model):
    
    _name = "mc_libro_compras.mc_libro_compras_line"
    _description = "Libro de compras Guatemala Line"
    _order = "correlativo desc, fecha_documento desc"


    @api.depends('fecha_documento')   
    def _fecha_documento_mda(self):
        for record in self:
            if record.fecha_documento:
                dt = str(record.fecha_documento).split('-')
                record.fecha_documento_mda = dt[2]+'-'+dt[1]+'-'+dt[0]   
            else:
                record.fecha_documento_mda = ''
    
    @api.depends('fecha_contable')   
    def _fecha_contable_mda(self):
        for record in self:
            if record.fecha_contable:
                dt = str(record.fecha_contable).split('-')
                record.fecha_contable_mda = dt[2]+'-'+dt[1]+'-'+dt[0]   
            else:
                record.fecha_contable_mda = ''

    name = fields.Text(string='Descripción', required=True)
    invoice_id  = fields.Many2one('account.move', string='Factura')
    partner_id  = fields.Many2one('res.partner', string='Empresa')
    journal_id  = fields.Many2one('account.journal', string='Diario')
    company_id  = fields.Many2one('res.company', string='Empresa')

    correlativo = fields.Integer(string='Correlativo')
    fecha_documento = fields.Date(string='Fecha documento')
    fecha_contable = fields.Date(string='Fecha contable')
    
    fecha_documento_mda = fields.Char('Fecha documento mda', compute=_fecha_documento_mda,copy=False,store=True)
    fecha_contable_mda = fields.Char('Fecha contable mda', compute=_fecha_contable_mda,copy=False,store=True)

    serie = fields.Char(string='Serie')
    documento = fields.Char(string='Documento')
    nit_dpi = fields.Char(string='Nit o DPI')
    proveedor = fields.Char(string='Nombre del proveedor')
    docto_odoo = fields.Char(string='Docto. Odoo')
    establecimiento = fields.Char(string='Establecimiento')
    tipo_transaccion = fields.Char(string='Tipo transaccion')
    asiste_libro = fields.Char(string='Asiste libro')

    idp = fields.Float(string='IDP')
    timbre_prensa = fields.Float(string='Timbre prensa')
    tasa_municipal = fields.Float(string='Tasa municipal')
    inguat = fields.Float(string='Inguat')
    retension_isr = fields.Float(string='Retension ISR')
    retension_iva = fields.Float(string='Retension IVA')

    local_bienes_gravados = fields.Float(string='Local bienes gravados')
    local_bienes_gravados_combustible = fields.Float(string='Local bienes gravado combustible')
    local_bienes_exentos = fields.Float(string='Local bienes exentos')
    local_bienes_pequenio_contribuyente = fields.Float(string = 'Local bienes Pequeño Contribuyente')#SE AGREGA CAMPO DE BIEN PARA PEQUEÑO CONTRIBUYENTE
        
    local_servicios_gravados = fields.Float(string='Local servicios gravados')
    local_servicios_exentos = fields.Float(string='Local servicios exentos')
    local_servicios_pequenio_contribuyente = fields.Float(string = 'Local servicios Pequeño Contribuyente')#SE AGREGA CAMPO DE SERVICIO PARA PEQUEÑO CONTRIBUYENTE
    
    importacion_bienes_gravados = fields.Float(string='Importación bienes gravados')
    importacion_bienes_gravados_total = fields.Float(string='TOTAL IMPORTACION GRAVADOS')

    importacion_bienes_exentos = fields.Float(string='Importación bienes exentos')
    importacion_bienes_exentos_total = fields.Float(string='TOTAL IMPORTACIN EXENTOS')

    importacion_servicios_gravados = fields.Float(string='Importación servicios gravados')
    importacion_servicios_exentos = fields.Float(string='Importación servicios exentos')
    activos_fijos = fields.Float(string='Activos fijos')

    iva = fields.Float(string='IVA')
    iva_local = fields.Float(string='IVA local')
    iva_importacion = fields.Float(string='IVA Importación')

    total = fields.Float(string='Total')
    otra_moneda = fields.Float(string='Valor en otra moneda')
    base = fields.Float(string='Monto base top proveedores')
    
    libro_id = fields.Many2one('mc_libro_compras.mc_libro_compras', string='Compras referencia', ondelete='cascade', index=True)
    
class MCLibroComprasTotal(models.Model):
    
    _name = "mc_libro_compras.mc_libro_compras_total"
    _description = "Libro de compras Guatemala total"

    idp = fields.Float(string='IDP')
    timbre_prensa = fields.Float(string='Timbre prensa')
    tasa_municipal = fields.Float(string='Tasa municipal')
    inguat = fields.Float(string='Inguat')
    retension_isr = fields.Float(string='Retension ISR')
    retension_iva = fields.Float(string='Retension IVA')

    local_bienes_gravados = fields.Float(string='Local bienes gravados')
    local_bienes_gravados_combustible = fields.Float(string='Local bienes gravado combustible')
    local_bienes_exentos = fields.Float(string='Local bienes exentos')
    local_bienes_pequenio_contribuyente = fields.Float(string = 'Local bienes Pequeño Contribuyente')
        
    local_servicios_gravados = fields.Float(string='Local servicios gravados')
    local_servicios_exentos = fields.Float(string='Local servicios exentos')
    local_servicios_pequenio_contribuyente = fields.Float(string = 'Local servicios Pequeño Contribuyente')
    
    importacion_bienes_gravados = fields.Float(string='Importación bienes gravados')
    importacion_bienes_gravados_total = fields.Float(string='Importación bienes gravados total')

    importacion_bienes_exentos = fields.Float(string='Importación bienes exentos')
    importacion_bienes_exentos_total = fields.Float(string='Importación bienes exentos total')

    importacion_servicios_gravados = fields.Float(string='Importación servicios gravados')
    importacion_servicios_exentos = fields.Float(string='Importación servicios exentos')
    activos_fijos = fields.Float(string='Activos fijos')

    iva = fields.Float(string='IVA')

    total = fields.Float(string='Total')
    otra_moneda = fields.Float(string='Valor en otra moneda')
    base = fields.Float(string='Monto base top proveedores')
    
    libro_id = fields.Many2one('mc_libro_compras.mc_libro_compras', string='Compras Total', ondelete='cascade', index=True)
    
class MCLibroComprasTop(models.Model):
    
    _name = "mc_libro_compras.mc_libro_compras_top_proveedores"
    _description = "Libro de compras Guatemala top proveedores"
    _order = "correlativo asc"

    correlativo = fields.Integer(string='Correlativo')  
    nit_dpi = fields.Char(string='Nit o DPI')
    proveedor = fields.Char(string='Nombre del proveedor')
    cantidad = fields.Integer(string='Cantidad')
    base = fields.Float(string='Monto base top proveedores')
    
    libro_id = fields.Many2one('mc_libro_compras.mc_libro_compras', string='Compras referencia', ondelete='cascade', index=True)
    
class PurchaseOrderLine(models.Model):
    
    _inherit = 'account.tax'
    
    tipo_impuesto = fields.Selection([('idp', 'IDP'), ('prensa', 'Timbre prensa'), 
                                      ('municipal', 'Tasa municipal'), ('inguat', 'Inguat'), 
                                      ('retisr', 'Retensión isr'), ('retiva', 'Retensión IVA'),('iva', 'IVA')], 'Tipo impuesto ', select=True)




 
