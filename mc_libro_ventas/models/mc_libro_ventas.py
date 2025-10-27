


# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

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

from odoo.exceptions import UserError, RedirectWarning, ValidationError

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


class MCLibroVentas(models.Model):

    _name = "mc_libro_ventas.mc_libro_ventas"
    _description = "Libro de ventas Guatemala"
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

    journal_ids = fields.Many2many('account.journal','libro_ventas_journal_rel',string='Diarios',domain="[('type','=','sale')]")
    nombre_establecimiento = fields.Char('Nombre establecimiento',)
        
    libro_line_ids = fields.One2many('mc_libro_ventas.mc_libro_ventas_line','libro_id', string=' ')                            
    company_id  = fields.Many2one('res.company', string='Empresa', required=True, readonly=True,default=lambda self: self.env.company)

    tipo_fecha = fields.Selection([('documento', 'Documento'), ('contable', 'Contable')], 'Tipo fecha ', select=True,)
    file_xlsx = fields.Binary('Archivo de excel')
    nombre_archivo = fields.Char('nombre de archivo')


    fecha_desde_mda = fields.Char('Fecha desde mda', compute=_fecha_desde_mda,copy=False,store=True)
    fecha_hasta_mda = fields.Char('Fecha hasta mda', compute=_fecha_hasta_mda,copy=False,store=True)

    #totales generales
    total_local_bienes_gravados = fields.Float(string='Local bienes gravados')
    total_local_servicios_gravados = fields.Float(string='Local servicios gravados')
    total_local_bienes_exentas = fields.Float(string='Local bienes exentas')
    total_local_servicios_exentas = fields.Float(string='Local servicios exentas')

    total_exportacion_bienes_gravados = fields.Float(string='Exportación bienes gravados')
    total_exportacion_servicios_gravados = fields.Float(string='Exportación servicios gravados')
    total_exportacion_bienes_exentos = fields.Float(string='Exportación bienes exentos')
    total_exportacion_servicios_exentos = fields.Float(string='Exportación servicios exentos')

    total_local_notas_abono = fields.Float(string='Notas de abono local')
    total_exportacion_notas_abono = fields.Float(string='Notas de Abono exportación')

    total_retension_isr = fields.Float(string='Retensión ISR')
    total_retension_iva = fields.Float(string='Retensión IVA')

    total_iva = fields.Float(string='IVA')
    total_total = fields.Float(string='Total')
    total_lineas = fields.Integer(string='Total lineas')

    cantidad_retencion_iva = fields.Integer(string='Cantidad retención iva')
    total_retencion_iva = fields.Float(string='Total retención iva')

    cantidad_exencion_iva = fields.Integer(string='Cantidad exención iva')
    total_exencion_iva = fields.Float(string='Total exención iva')


    folio = fields.Integer('Folio inicial:')
    file_name = fields.Char('Nombre del archivo',readonly=True, copy=False)
    file_pdf = fields.Binary(string='Libro ventas foliado',readonly=True, copy=False)


    def foliar(self, nuevo_inicio=1, margen_derecho_cm=1.76, margen_superior_cm=17):
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
        lines = self.env['mc_libro_ventas.mc_libro_ventas'].browse(self.id)          

        valor = self.env['report.libro_ventas.report_libroventas_xls'].generate_xlsx_report(lines=lines)

        hora_gt = pytz.timezone('America/Guatemala')
        fecha_gt = datetime.now(hora_gt)
        fecha_actual = fecha_gt.strftime('%Y-%m-%d %H:%M:%S')
        self.nombre_archivo = f'Libro de ventas generado {fecha_actual}.xlsx'
        self.file_xlsx = valor


    def genera_libro(self):

        self.env["mc_libro_ventas.mc_libro_ventas_line"].search([('libro_id','=',self.id)]).unlink()
        
        if self.tipo_fecha == 'documento':
            sql = """
            SELECT company_id, id, date_invoice, date,state
              FROM "MC_libro_ventas"
             WHERE state <> 'draft' and company_id =  %s and date >= %s and date <= %s and journal_id in %s
             """
            self.env.cr.execute(sql, (self.company_id.id,self.fecha_desde,self.fecha_hasta,))
        else:
            sql = """
            SELECT company_id, id, date_invoice, date,state
              FROM "MC_libro_ventas"
             WHERE state <> 'draft' and company_id =  %s and date >= %s and date <= %s  and journal_id in %s
             """
        #self.env.cr.execute(sql, (self.company_id.id,self.fecha_desde,self.fecha_hasta,self.journal_ids))

        doc_count = 0
        
        invoice_ids = self.env['account.move'].search([('date', '>=', self.fecha_desde),('date', '<=', self.fecha_hasta) ,('state','=','posted') , ('move_type','in',('out_invoice','out_refund')), ('journal_id','in',self.journal_ids.ids)   ])


        #totales generales
        total_local_bienes_gravados = 0
        total_local_servicios_gravados = 0
        total_local_bienes_exentas = 0
        total_local_servicios_exentas = 0
        total_exportacion_bienes_gravados = 0
        total_exportacion_servicios_gravados = 0
        total_exportacion_bienes_exentos = 0
        total_exportacion_servicios_exentos = 0
        total_local_notas_abono = 0
        total_exportacion_notas_abono = 0
        total_retension_isr = 0
        total_retension_iva = 0
        total_iva = 0
        total_total = 0
        total_lineas = 0

        _cantidad_retencion_iva = 0
        _total_retencion_iva = 0.00

        _cantidad_exencion_iva = 0
        _total_exencion_iva = 0.00

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
            
        #for query_line in self.env.cr.dictfetchall():
        for invoice_id in invoice_ids:
            doc_count += 1
            #invoice_id = query_line #self.env['account.move'].browse([query_line['id']])
            #if invoice_id.id != 409:
            #    continue
            sign = invoice_id.move_type in ['in_refund', 'out_refund'] and -1 or 1
          
            #para NEO
            _neo = self.env['ir.model.fields'].search([ ('name', '=', 'x_es_generico'),('model', '=', 'res.partner') ]).ids
            _neo = False
            #cuando ventas tenemos fel
            _fel = self.env['ir.model.fields'].search([ ('name', '=', 'mpfel_sat_uuid'),('model', '=', 'account.move') ]).ids

            if _neo:
                if invoice_id.partner_id.x_es_generico: 
                    _nit_dpi = invoice_id.x_nit_generico
                    _nombre = invoice_id.x_nombre_generico
                else:
                    _nit_dpi = invoice_id.partner_id.ref
                    _nombre = invoice_id.partner_id.name
            else:
                _nit_dpi = invoice_id.partner_id.vat
                _nombre = invoice_id.partner_id.name

            if  _fel:           
                if  invoice_id.mpfel_sat_uuid:
                    _serie = invoice_id.mpfel_serial
                    _name = invoice_id.name
                    _documento = invoice_id.mpfel_number
                else:                
                    _serie = invoice_id.serie_gt
                    _name = invoice_id.name
                    _documento = invoice_id.documento_gt
            else:
                    _serie = invoice_id.serie_gt
                    _name = invoice_id.name
                    _documento = invoice_id.documento_gt

            if not invoice_id.name:
                _documento = ''
                _name = 'ANULADA'

            if invoice_id.state == 'cancel':
                
                _estado = 'A'
                _name = 'ANULADA'
                _nombre = 'ANULADA'
                #_documento = invoice_id.move_name
                _nit_dpi = ''
            else:
                _estado = 'E'

            _local_bienes_gravados = 0
            _local_servicios_gravados = 0
            _local_bienes_exentas = 0
            _local_servicios_exentas = 0

            _exportacion_bienes_gravados = 0
            _exportacion_servicios_gravados = 0
            _exportacion_bienes_exentos = 0
            _exportacion_servicios_exentos = 0

            _local_notas_abono = 0
            _exportacion_notas_abono = 0

            _retension_isr = 0
            _retension_iva = 0
            _iva = 0
            _total = 0
            _otra_moneda = 0
            _tipo_cambio = 1
            
            _descuento_redondeo = 0 

            if self.env.user.company_id.currency_id.id != invoice_id.currency_id.id:
                print (invoice_id.id)
                _tipo_cambio = 0.00
                _otra_moneda = 0.00

                if invoice_id.amount_total > 0:
                    _tipo_cambio = invoice_id.amount_total_signed / invoice_id.amount_total
                    _otra_moneda = invoice_id.amount_total

            if invoice_id.state == 'cancel':            
                _otra_moneda = 0.00
                
            else:                
                _total = (invoice_id.amount_total_signed * sign)

                for l in invoice_id.invoice_line_ids:
                    invoice_line_id = self.env['account.move.line'].browse([ l.id ])
                  
                    # Define si el producto es bien o servicios.
                    _tipo = 'servicio'
                    if invoice_line_id.product_id.type == 'service':
                        if invoice_line_id.product_id.default_code == 'Local-Bienes':
                            _tipo = 'bien'
                        else:
                            _tipo = 'servicio'
                    else:
                        _tipo = 'bien'
    
                    _tiene_iva = False
                    for t in invoice_line_id.tax_ids:
                        tax_id = self.env['account.tax'].browse([t.id])

                        if tax_id.tipo_impuesto == 'iva':
                            _tiene_iva = True
                        if tax_id.tipo_impuesto == 'idp':
                            _tipo = 'bien'
                            _es_idp = True

                    # Este valor ya viene negativo de la factura, si está positivo no es un error de este proceso, se debe hacer un update al documento.
                    precio_subtotal = abs(invoice_line_id.balance )*sign
                    
                    # Local.
                    if invoice_id.journal_id.tipo_venta == 'NA' or invoice_id.journal_id.tipo_venta == 'NAE':
                        _local_notas_abono += precio_subtotal   
                    else:
                        if invoice_line_id.product_id.default_code in ('REDONDEO','DESCUENTO'):
                            _descuento_redondeo += precio_subtotal
                        else:
                            if invoice_id.journal_id.local == 'Local' and _tipo == 'bien' and _tiene_iva:
                                _local_bienes_gravados += precio_subtotal
                            if invoice_id.journal_id.local == 'Local' and _tipo == 'bien' and not _tiene_iva:
                                _local_bienes_exentas += precio_subtotal
                            if invoice_id.journal_id.local == 'Local' and _tipo == 'servicio' and _tiene_iva:
                                _local_servicios_gravados += precio_subtotal
                            if invoice_id.journal_id.local == 'Local' and _tipo == 'servicio' and not _tiene_iva:
                                _local_servicios_exentas += precio_subtotal
                            # Exportación.
                            if invoice_id.journal_id.local == 'Exportacion' and _tipo == 'bien' and _tiene_iva:
                                _exportacion_bienes_gravados += precio_subtotal
                            if invoice_id.journal_id.local == 'Exportacion' and _tipo == 'bien' and not _tiene_iva:
                                _exportacion_bienes_exentos += precio_subtotal
                            if invoice_id.journal_id.local == 'Exportacion' and _tipo == 'servicio' and _tiene_iva:
                                _exportacion_servicios_gravados += precio_subtotal
                            if invoice_id.journal_id.local == 'Exportacion' and _tipo == 'servicio' and not _tiene_iva:
                                _exportacion_servicios_exentos += precio_subtotal
    
                # Suma los impuestos.
                for t in invoice_id.line_ids:    
                    if t.tax_line_id.tipo_impuesto == 'retiva':
                        _retension_iva = _retension_iva +(abs(t.balance) * sign)
                    if t.tax_line_id.tipo_impuesto == 'retisr':
                       _retension_isr = _retension_isr +(abs(t.balance) * sign)
                    if t.tax_line_id.tipo_impuesto == 'iva':
                        if invoice_id.move_type == 'out_refund':
                            _iva = _iva + (abs(t.balance) * sign)
                        else:
                            _iva = _iva + (abs(t.balance) * sign)

            if _local_bienes_gravados > 0:
                _local_bienes_gravados += _descuento_redondeo
            else:
                _local_servicios_gravados += _descuento_redondeo


            invoice_line = {'libro_id':self.id,
                'correlativo': doc_count,
                'name': _name,
                'invoice_id': invoice_id.id,
                'partner_id': invoice_id.partner_id.id,
                'journal_id': invoice_id.journal_id.id,
                'company_id': invoice_id.company_id.id,
                'fecha_documento': invoice_id.invoice_date,
                'fecha_contable': invoice_id.invoice_date,
                'documento': _documento,
                'nit_dpi': _nit_dpi,
                'nombre': _nombre,
                'establecimiento': invoice_id.journal_id.establecimiento,
                'tipo_documento': invoice_id.journal_id.tipo_venta,
                'asiste_libro': invoice_id.journal_id.asiste_libro,
                'tipo_transaccion': invoice_id.journal_id.tipo_transaccion,
                'serie_venta': _serie,
                'estado': _estado,
                'local_bienes_gravados': _local_bienes_gravados,
                'local_servicios_gravados': _local_servicios_gravados,
                'local_bienes_exentas': _local_bienes_exentas,
                'local_servicios_exentas': _local_servicios_exentas,
                'local_notas_abono':_local_notas_abono,
                'exportacion_bienes_gravados': _exportacion_bienes_gravados,
                'exportacion_servicios_gravados': _exportacion_servicios_gravados,
                'exportacion_bienes_exentos': _exportacion_bienes_exentos,
                'exportacion_servicios_exentos': _exportacion_servicios_exentos,
                'retension_isr': _retension_isr,
                'retension_iva': _retension_iva,
                'iva': _iva,
                'total': ((_total-abs(_descuento_redondeo))*sign)+_retension_isr+_retension_iva, # Se aplica la funcion abs() a la variables "descuento_redondeo" ya que ese valor viene negativo
                'otra_moneda': _otra_moneda,
                'tipo_cambio': _tipo_cambio
            }

            #totales generales
            total_local_bienes_gravados += _local_bienes_gravados
            total_local_servicios_gravados += _local_servicios_gravados
            total_local_bienes_exentas += _local_bienes_exentas
            total_local_servicios_exentas += _local_servicios_exentas
            total_exportacion_bienes_gravados += _exportacion_bienes_gravados
            total_exportacion_servicios_gravados += _exportacion_servicios_gravados
            total_exportacion_bienes_exentos =+ _exportacion_bienes_exentos
            total_exportacion_servicios_exentos =+ _exportacion_servicios_exentos
            total_local_notas_abono += _local_notas_abono
            total_exportacion_notas_abono +=  0
            total_retension_isr += _retension_isr
            total_retension_iva += _retension_iva
            total_iva += _iva
            total_total +=  (_total-abs(_descuento_redondeo))*sign
            total_lineas += 1

            self.env['mc_libro_ventas.mc_libro_ventas_line'].create(invoice_line)
            payments_ids = self.env['account.payment'].search([('date', '>=', self.fecha_desde),('date', '<=', self.fecha_hasta) , ('payment_type','=','inbound'),('state','=','posted')])
            ret_ids  = payments_ids.filtered(lambda m: m.journal_id.es_retencion_iva == 'si') 
            _cantidad_retencion_iva = len(ret_ids)
            _total_retencion_iva = sum(ret_ids.mapped('amount'))
            ret_ids  = payments_ids.filtered(lambda m: m.journal_id.es_exencion_iva == 'si') 
            _cantidad_exencion_iva = len(ret_ids)
            _total_exencion_iva = sum(ret_ids.mapped('amount'))
   
            self.update({'total_local_bienes_gravados':total_local_bienes_gravados,
                         'total_local_servicios_gravados':total_local_servicios_gravados,
                         'total_local_bienes_exentas':total_local_bienes_exentas,
                         'total_local_servicios_exentas':total_local_servicios_exentas,
                         'total_exportacion_bienes_gravados':total_exportacion_bienes_gravados,
                         'total_exportacion_servicios_gravados':total_exportacion_servicios_gravados,
                         'total_exportacion_bienes_exentos':total_exportacion_bienes_exentos,
                         'total_exportacion_servicios_exentos':total_exportacion_servicios_exentos,
                         'total_local_notas_abono':total_local_notas_abono,
                         'total_exportacion_notas_abono':total_exportacion_notas_abono,
                         'total_retension_isr':total_retension_isr,
                         'total_retension_iva':total_retension_iva,
                         'total_iva':total_iva,
                         'total_total':total_total,
                         'total_lineas':total_lineas,
                         'cantidad_retencion_iva':_cantidad_retencion_iva,
                         'total_retencion_iva':_total_retencion_iva,
                         'cantidad_exencion_iva':_cantidad_exencion_iva,
                         'total_exencion_iva':_total_exencion_iva
                         })

        self.total_exportacion_bienes_exentos  = sum(self.libro_line_ids.mapped('exportacion_bienes_exentos'))
        self.total_exportacion_servicios_exentos  = sum(self.libro_line_ids.mapped('exportacion_servicios_exentos'))

 
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


    
class MCLibroVentasLine(models.Model):
    
    _name = "mc_libro_ventas.mc_libro_ventas_line"
    _description = "Libro de ventas Guatemala Line"
    _order = "fecha_documento desc"



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

                
    correlativo = fields.Integer(string='Correlativo')
    name = fields.Text(string='Descripción', required=True)
    establecimiento = fields.Char(string='Establecimiento')
    invoice_id  = fields.Many2one('account.move', string='Factura')
    partner_id  = fields.Many2one('res.partner', string='Empresa')
    journal_id  = fields.Many2one('account.journal', string='Diario')
    company_id  = fields.Many2one('res.company', string='Empresa')

    fecha_documento = fields.Date(string='Fecha documento')
    fecha_contable = fields.Date(string='Fecha contable')
    asiste_libro = fields.Char(string='Asiste libro')
    tipo_transaccion = fields.Char(string='Tipo transacción')
    tipo_documento = fields.Char(string='Tipo de documento')
    serie_venta = fields.Char(string='Serie de venta')
    documento = fields.Char(string='No. Documento')
    nit_dpi = fields.Char(string='NIT o DPI')
    nombre = fields.Char(string='Nombre del cliente')

    local_bienes_gravados = fields.Float(string='Local bienes gravados')
    local_servicios_gravados = fields.Float(string='Local servicios gravados')
    local_bienes_exentas = fields.Float(string='Local bienes exentas')
    local_servicios_exentas = fields.Float(string='Local servicios exentas')

    exportacion_bienes_gravados = fields.Float(string='Exportación bienes gravados')
    exportacion_servicios_gravados = fields.Float(string='Exportación servicios gravados')
    exportacion_bienes_exentos = fields.Float(string='Exportación bienes exentos')
    exportacion_servicios_exentos = fields.Float(string='Exportación servicios exentos')

    local_notas_abono = fields.Float(string='Notas de abono local')
    exportacion_notas_abono = fields.Float(string='Notas de Abono exportación')

    retension_isr = fields.Float(string='Retensión ISR')
    retension_iva = fields.Float(string='Retensión IVA')

    iva = fields.Float(string='IVA')
    total = fields.Float(string='Total')
    otra_moneda = fields.Float(string='Valor en otra moneda')
    tipo_cambio = fields.Float(string='Tipo cambio')
    
    libro_id = fields.Many2one('mc_libro_ventas.mc_libro_ventas', string='ventas referencia', ondelete='cascade', index=True)

    estado = fields.Char(string='Estado')

    fecha_documento_mda = fields.Char('Fecha documento mda', compute=_fecha_documento_mda,copy=False,store=True)
    fecha_contable_mda = fields.Char('Fecha contable mda', compute=_fecha_contable_mda,copy=False,store=True)
