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
 

class LibroDiario(models.Model):
    _name = 'libro.diario'
    _description = 'Información de Libro Diario'
    _inherit = ['mail.thread', 'mail.activity.mixin']



    @api.depends('fecha_inicio')   
    def _fecha_inicio_mda(self):
        for record in self:
            if record.fecha_inicio:
                dt = str(record.fecha_inicio).split('-')
                record.fecha_inicio_mda = dt[2]+'-'+dt[1]+'-'+dt[0]   
            else:
                record.fecha_inicio_mda = ''

    @api.depends('fecha_final')   
    def _fecha_final_mda(self):
        for record in self:
            if record.fecha_final:
                dt = str(record.fecha_final).split('-')
                record.fecha_final_mda = dt[2]+'-'+dt[1]+'-'+dt[0]   
            else:
                record.fecha_final_mda = ''

    name = fields.Char(string='MES')
    fecha_inicio = fields.Date(string='Fecha Inicial')
    fecha_final = fields.Date(string='Fecha Final')
    company_id  = fields.Many2one('res.company', string='Empresa', required=True, readonly=True,default=lambda self: self.env.company)
    #account_id  = fields.Many2one('account.account', string='Cuenta',)

    libro_line = fields.One2many(comodel_name='libro.diario.detalle', inverse_name='libro_id', string='Detalle')
    file_xlsx = fields.Binary('Archivo de excel')
    nombre_archivo = fields.Char('nombre de archivo')
    folio = fields.Integer('Folio inicial:')
    total_debit = fields.Float(string='Total debitos')
    total_credit = fields.Float(string='Total creditos')

    file_name = fields.Char('Nombre del archivo',readonly=True, copy=False)
    file_pdf = fields.Binary(string='Libro diario foliado',readonly=True, copy=False)
    


    fecha_inicio_mda = fields.Char('Fecha inicio mda', compute=_fecha_inicio_mda,copy=False,store=True)
    fecha_final_mda = fields.Char('Fecha final mda', compute=_fecha_final_mda,copy=False,store=True)
 
    def foliar(self):
        for record in self:
            if not record.file_pdf or record.folio==0:
                continue  # Salta si no hay PDF original
            
            # Decodificar el PDF de Base64 a bytes
            decoded_pdf = base64.b64decode(record.file_pdf)

            # Agregar folios al PDF
            modified_pdf_bytes = self._agregar_folio_a_pdf(
                pdf_bytes=decoded_pdf,
                inicio=record.folio,
                margen_derecho=50,     # Ajusta según tus necesidades
                margen_superior=70    # Aumenta este valor para posicionar el folio más abajo
            )

            # Codificar el PDF modificado a Base64
            record.file_pdf = base64.b64encode(modified_pdf_bytes)
            msg = "Se ha foliado el Libro Diario inició con el numero... %s" % str(record.folio)
            record.message_post(body=msg )


    def imprimir(self):
        lines = self.env['libro.diario'].browse(self.id)          

        valor = self.env['report.mc_reportes_xlsx_libros_contables.libro_diario_xlsx.xlsx'].generate_xlsx_report(lines=lines)

        hora_gt = pytz.timezone('America/Guatemala')
        fecha_gt = datetime.now(hora_gt)
        fecha_actual = fecha_gt.strftime('%Y-%m-%d %H:%M:%S')
        self.nombre_archivo = f'Libro de diario generado {fecha_actual}.xlsx'
        self.file_xlsx = valor
    
    def generar_libro(self):
        
        if len(self.libro_line) > 0:
            self.env['libro.diario.detalle'].search([('libro_id','=',self.id)]).unlink()

        _sql_data = '''
                    select
                    ifp.move_id,ifp.aml_move_id,
                    ifp.code,
                    ifp.account AS account,
                    ifp.partida as poliza,
                    ifp.documento,
                    ifp.concepto,
                    ifp.debit,
                    ifp.credit,
                    ifp."date",
                    ifp.total
                    from (
                    select am.id move_id,aml.id aml_move_id,
                    aa.id as account_id,
                    aa.code,
                    aa."name_account" as account,
                    mp."name" as partida,
                    am."name" as documento,
                    aml."name" as concepto,
                    aml.debit,
                    aml.credit,
                    aml."date",
                    am.amount_total_signed AS total
                    from account_move am 
                    inner join account_move_line aml
                    on am.id = aml.move_id 
                    inner join (SELECT id, code, name AS name_account, company_id FROM public."MC_account_account"  )aa  
                    on aml.account_id = aa.id 
                    inner join account_journal aj 
                    on am.journal_id = aj.id
                    left join mc_poliza_diarios mp 
                    on aj.x_poliza_id = mp.id 
                    --where aj.x_poliza_id is not null
                    Where am.company_id =  %s and cast(aml."date"::text as date) between cast(%s::text as date) and cast(%s::text as date)
                    order by cast(aj.x_poliza_id::text as numeric), aml."date", am.id,aml.id ) as ifp
                '''
#        if self.account_id:
#            _account = self.account_id.id
#        else:
#            _account = 0

        self.env.cr.execute(_sql_data,( self.company_id.id,self.fecha_inicio,self.fecha_final))


        _documento_debit = 0
        _documento_credit = 0
        _cuenta_credit = 0
        _cuenta_debit = 0
        _total_debit = 0
        _total_credit = 0
        _move_id = 0
        inicio = 1

        lista = []
        for line in self.env.cr.dictfetchall():

            if _move_id != line['move_id']:
                if inicio != 1:
                    detalle = (0,0,{
                        'concepto': 'Total por documento : ',
                        'debit': _documento_debit,
                        'credit': _documento_credit,
                        'tipo_linea':'d',
                    })
                    lista.append(detalle)
                    _documento_debit = 0
                    _documento_credit = 0
                _move_id = line['move_id']

 
            detalle = (0,0,{
                'code':line['code'],
                'account': line['account'],
                'poliza': line['poliza'],
                'documento':line['documento'],
                'concepto': line['concepto'],
                'debit': line['debit'],
                'credit': line['credit'],
                'date': line['date'],
                'total': abs(line['total']),
                'tipo_linea':'l'
            })
            lista.append(detalle)
            inicio += 1

            _documento_debit   += line['debit']
            _documento_credit  += line['credit']

            _total_debit   += line['debit']
            _total_credit  += line['credit']

        #agrega el ultimo total del documento
        detalle = (0,0,{
                    'concepto': 'Total por documento : ',
                    'debit': _documento_debit,
                    'credit': _documento_credit,
                    'tipo_linea':'d'
                })
        lista.append(detalle)

        self.update({'total_debit':_total_debit,
                     'total_credit':_total_credit,
            'libro_line': lista})

        return



    def _agregar_folio_a_pdf(self, pdf_bytes, inicio=1, margen_derecho=50, margen_superior=70):
        """
        Agrega números de página con el prefijo "Folio:" en el encabezado derecho de cada página de un PDF,
        posicionados más abajo en la página, trabajando directamente con bytes en memoria.

        :param pdf_bytes: Bytes del archivo PDF original.
        :param inicio: Número desde el cual comenzará la numeración.
        :param margen_derecho: Puntos desde el borde derecho donde se colocará el texto.
        :param margen_superior: Puntos desde el borde superior donde se colocará el texto.
        :return: Bytes del archivo PDF modificado.
        """
        reader = PdfReader(io.BytesIO(pdf_bytes))
        writer = PdfWriter()
        num_paginas = len(reader.pages)

        for i in range(num_paginas):
            pagina_original = reader.pages[i]

            # Obtener el tamaño de la página
            width = float(pagina_original.mediabox.width)
            height = float(pagina_original.mediabox.height)

            # Crear un PDF en memoria con el número de página
            packet = io.BytesIO()
            can = canvas.Canvas(packet, pagesize=(width, height))

            # Superponer un rectángulo blanco sobre el folio existente
            # Debes conocer las coordenadas y dimensiones del folio existente
            # Aquí asumimos que el folio está en una posición fija
            # Ajusta las coordenadas (x, y, width, height) según tu caso
            rect_x = width - margen_derecho - 100  # Ajusta según la posición
            rect_y = height - margen_superior - 15  # Ajusta según la posición
            rect_width = 100  # Ancho del rectángulo
            rect_height = 40  # Alto del rectángulo

            can.setFillColor(white)
            can.rect(rect_x, rect_y, rect_width, rect_height, fill=1, stroke=0)


            # Configurar el texto "Folio: X"
            folio_texto = f"Folio: {i + inicio}"
            font = "Helvetica-Bold"
            tamaño_fuente = 12
            can.setFont(font, tamaño_fuente)
            text_width = can.stringWidth(folio_texto, font, tamaño_fuente)

            # Posición del texto (superior derecho, más abajo)
            x = width - text_width - margen_derecho
            y = height - margen_superior

            can.setFillColorRGB(0, 0, 0)  # Color negro para el texto
            can.drawString(x, y, folio_texto)
            can.save()

            # Mover el buffer al inicio
            packet.seek(0)
            folio_pdf = PdfReader(packet)
            pagina_folio = folio_pdf.pages[0]

            # Crear una nueva página combinada
            pagina_combinada = PageObject.create_blank_page(
                width=pagina_original.mediabox.width,
                height=pagina_original.mediabox.height
            )

            # Añadir la página original
            pagina_combinada.merge_page(pagina_original)

            # Añadir la página del folio
            pagina_combinada.merge_page(pagina_folio)

            # Añadir la página combinada al writer
            writer.add_page(pagina_combinada)

            #_logger.info(f"Procesando página {i + 1} de {num_paginas}...")

        # Escribir el PDF de salida en memoria
        output_stream = io.BytesIO()
        writer.write(output_stream)
        modified_pdf_bytes = output_stream.getvalue()

        return modified_pdf_bytes

 
class LibroMayorDetalle(models.Model):
    _name = 'libro.diario.detalle'
    _description = 'Detalle del libro diario'


    @api.depends('date')    
    def _fecha_date_mda(self):
        for record in self:
            if record.date:
                dt = str(record.date).split('-')
                record.fecha_date_mda = dt[2]+'-'+dt[1]+'-'+dt[0] 
            else:
                record.fecha_date_mda = ''

    libro_id = fields.Many2one(comodel_name='libro.diario', string='libro_id')
    code = fields.Char(string='Código')
    account = fields.Char(string='Cuenta')
    poliza = fields.Char(string='Poliza')
    documento = fields.Char(string='Documento')
    concepto = fields.Char(string='Concepto')
    debit = fields.Float(string='Debito')
    credit = fields.Float(string='Credito')
    date = fields.Date(string='Fecha')
    total = fields.Float(string='Total docto')
    
    tipo_linea = fields.Selection(
        string='Tipo Lonea',
        selection=[('l', 'Linea Detalle'), ('d', 'Total Documento'),('c', 'Total Cuenta'),('t', 'Total General')]
    )
    
    fecha_date_mda = fields.Char('Fecha mda', compute=_fecha_date_mda,copy=False,store=True) 


