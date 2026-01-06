from odoo import api, fields, models
from datetime import datetime
import pytz
import base64
import io
from PyPDF2 import PdfReader, PdfWriter, PageObject
from reportlab.pdfgen import canvas
from odoo import models, fields, api 

from reportlab.lib.colors import white


class LibroMayor(models.Model):
    _name = 'libro.mayor'
    _description = 'Información de Libro Mayor'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'image.mixin']




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
    company_id = fields.Many2one(comodel_name='res.company', string='Compañia')
    libro_line = fields.One2many(comodel_name='libro.mayor.detalle', inverse_name='libro_id', string='Detalle')
    file_xlsx = fields.Binary('Archivo de excel')
    nombre_archivo = fields.Char('nombre de archivo')
    folio = fields.Integer('Folio inicial:')

    total_debit = fields.Float(string='Total debitos')
    total_credit = fields.Float(string='Total creditos')

    file_name = fields.Char('Nombre del archivo',readonly=True, copy=False)
    file_pdf = fields.Binary(string='Libro mayor foliado',readonly=True, copy=False)


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
        lines = self.env['libro.mayor'].browse(self.id)          

        valor = self.env['report.mc_reportes_xlsx_libros_contables.libro_mayor_xlsx.xlsx'].generate_xlsx_report(lines=lines)

        hora_gt = pytz.timezone('America/Guatemala')
        fecha_gt = datetime.now(hora_gt)
        fecha_actual = fecha_gt.strftime('%Y-%m-%d %H:%M:%S')
        self.nombre_archivo = f'Libro mayor generado {fecha_actual}.xlsx'
        self.file_xlsx = valor

    
    def generar_libro(self):
        
        if len(self.libro_line) > 0:
            self.env['libro.mayor.detalle'].search([('libro_id','=',self.id)]).unlink()

        _sql_data = '''
               select *
                from (
                select g.code, account, g.date, g.partida as poliza, g.documento, g.concepto, g.debit, g.credit, 
                sum(g.debit-g.credit) over(partition by g.code order by g.code,g.documento) as acumulado_mes_cuenta,
                sum(g.debit-g.credit) over(partition by g.code ) as subtotal_acumulado_mes,
                g.saldo_mes_anterior,
                sum(case when g.cont=1 then g.saldo_mes_anterior+(g.debit-g.credit) else g.debit-g.credit end) over(partition by g.code order by g.code,g.documento) as acumulado_anio_cuenta,
                sum(case when g.cont=1 then g.saldo_mes_anterior+(g.debit-g.credit) else g.debit-g.credit end) over(partition by g.code ) as subtotal_acumulado_anio
                from(
                select t1.code, t1.cont,  account, t1.date, t1.partida, t1.documento, t1.concepto, t1.debit, t1.credit, 
                coalesce(t2.saldo,0) as saldo_mes_anterior
                from (----t1
                select
                aa.code,
                COALESCE(aa."name"->>'es_GT',aa."name"->>'en_US') as account,
                aml."date",
                date_part('month',cast((date_trunc('month',cast(%s::text as date)) -'1sec' ::interval)::text as date)) as mes,
                date_part('year',cast((date_trunc('month',cast(%s::text as date)) -'1sec' ::interval)::text as date)) as anio,
                mp."name" as partida,
                am."name" as documento,
                aml."name" as concepto,
                aml.debit,
                aml.credit,
                rank()over(partition by aa.code order by am."name") as cont
                from account_move am 
                inner join account_move_line aml 
                on am.id = aml.move_id 
                inner join account_journal aj 
                on aml.journal_id = aj.id 
                inner join (SELECT id, code, name, company_id FROM public."MC_account_account")aa 
                on aml.account_id = aa.id AND aa.company_id = %s
                left  join mc_poliza_diarios mp 
                on mp.id = aj.x_poliza_id 
                where am.state = 'posted' 
                --and aj.x_poliza_id is not null
                and cast(aml."date"::text as date) between cast(%s::text as date) and cast(%s::text as date)
                order by cast(aa.code::text as numeric), aml."date"
                ) as t1 ---------------t1
                left join
                ( --------t2
                select t.anio, t.mes, t.code, t.nombre_cuenta, t.saldo_mes, 
                sum(t.saldo_mes)over(partition by t.code order by t.anio,t.mes,t.code) as saldo 
                from (--//////////////
                select piv.anio,piv.mes,piv.code,piv.nombre_cuenta, coalesce(s.saldo_mes,0) as saldo_mes
                from (--**************
                select p.anio, p.mes, p.code, p.nombre_cuenta
                from ( -------
                select aa.code, COALESCE(aa."name"->>'es_GT',aa."name"->>'en_US') as nombre_cuenta
                ,date_part('month',generate_series('2021-01-01',current_date,'1 month'::interval)::date) as mes
                ,date_part('year',generate_series('2021-01-01',current_date,'1 month'::interval)::date) as anio
                from (SELECT id, code, name, company_id FROM public."MC_account_account")aa Where aa.company_id = %s 
                ) as p 
                ) as piv --**************
                left join
                ( --##############
                select inf.anio, inf.mes, inf.code, inf.cuenta, inf.saldo_mes
                from(
                select 
                date_part('month',cast(aml."date"::text as date)) as mes,
                date_part('year',cast(aml."date"::text as date)) as anio,
                aa.code, COALESCE(aa."name"->>'es_GT',aa."name"->>'en_US') as cuenta,
                sum(aml.debit)-sum(aml.credit) as saldo_mes
                from account_move_line aml
                inner join (SELECT id, code, name, company_id FROM public."MC_account_account")aa  
                on aml.account_id = aa.id  and  aa.company_id = %s 
                inner join account_move am 
                on aml.move_id = am.id
                where am.state = 'posted'
                group by
                date_part('year',cast(aml."date"::text as date)),
                date_part('month',cast(aml."date"::text as date)),
                aa.code, aa."name"
                ) as inf
                order by  inf.anio, inf.mes,cast(inf.code::text as numeric)
                ) as s --##############
                on piv.anio = s.anio
                and piv.mes = s.mes
                and piv.code = s.code
                order by piv.code, --by cast(piv.code::text as numeric),
                
                piv.anio, piv.mes
                ) as t --//////////////
                ) as t2 ---------------t2
                on t1.anio = t2.anio
                and t1.mes = t2.mes
                and t1.code = t2.code
                ) as g 
                ) as c1, 
                (
                select sum (tam.subtotal_acumulado_mes) as total_acumulado_mes
                from(
                select
                distinct sum(g.debit-g.credit) over(partition by g.code ) as subtotal_acumulado_mes
                from(
                select t1.code, t1.cont, t1.account, t1.date, t1.partida, t1.documento, t1.concepto, t1.debit, t1.credit, 
                coalesce(t2.saldo,0) as saldo_mes_anterior
                from (----t1
                select
                aa.code,
                COALESCE(aa."name"->>'es_GT',aa."name"->>'en_US') as account,
                aml."date",
                date_part('month',cast((date_trunc('month',cast(%s::text as date)) -'1sec' ::interval)::text as date)) as mes,
                date_part('year',cast((date_trunc('month',cast(%s::text as date)) -'1sec' ::interval)::text as date)) as anio,
                aj.x_poliza_id as partida,
                am."name" as documento,
                aml."name" as concepto,
                aml.debit,
                aml.credit,
                rank()over(partition by aa.code order by am."name") as cont
                from account_move am 
                inner join account_move_line aml 
                on am.id = aml.move_id 
                inner join account_journal aj 
                on aml.journal_id = aj.id 
                inner join (SELECT id, code, name, company_id FROM public."MC_account_account")aa 
                on aml.account_id = aa.id  and  aa.company_id = %s
                where am.state = 'posted'
                --and aj.x_poliza_id is not null
                and cast(aml."date"::text as date) between cast(%s::text as date) and cast(%s::text as date)
                order by cast(aa.code::text as numeric), aml."date"
                ) as t1 ---------------t1
                left join
                ( --------t2
                select t.anio, t.mes, t.code, t.nombre_cuenta, t.saldo_mes, 
                sum(t.saldo_mes)over(partition by t.code order by t.anio,t.mes,t.code) as saldo 
                from (--//////////////
                select piv.anio,piv.mes,piv.code,piv.nombre_cuenta, coalesce(s.saldo_mes,0) as saldo_mes
                from (--**************
                select p.anio, p.mes, p.code, p.nombre_cuenta
                from ( -------
                select aa.code, COALESCE(aa."name"->>'es_GT',aa."name"->>'en_US') as nombre_cuenta
                ,date_part('month',generate_series('2021-01-01',current_date,'1 month'::interval)::date) as mes
                ,date_part('year',generate_series('2021-01-01',current_date,'1 month'::interval)::date) as anio
                from (SELECT id, code, name, company_id FROM public."MC_account_account")aa where aa.company_id = %s
                ) as p 
                ) as piv --**************
                left join
                ( --##############
                select inf.anio, inf.mes, inf.code, inf.cuenta, inf.saldo_mes
                from(
                select 
                date_part('month',cast(aml."date"::text as date)) as mes,
                date_part('year',cast(aml."date"::text as date)) as anio,
                aa.code, COALESCE(aa."name"->>'es_GT',aa."name"->>'en_US') as cuenta,
                sum(aml.debit)-sum(aml.credit) as saldo_mes
                from account_move_line aml
                inner join (SELECT id, code, name, company_id FROM public."MC_account_account")aa 
                on aml.account_id = aa.id  and aa.company_id = %s
                inner join account_move am 
                on aml.move_id = am.id
                where am.state = 'posted'
                group by
                date_part('year',cast(aml."date"::text as date)),
                date_part('month',cast(aml."date"::text as date)),
                aa.code, aa."name"
                ) as inf
                order by  inf.anio, inf.mes,cast(inf.code::text as numeric)
                ) as s --##############
                on piv.anio = s.anio
                and piv.mes = s.mes
                and piv.code = s.code
                order by piv.code, --by cast(piv.code::text as numeric),
                
                piv.anio, piv.mes
                ) as t --//////////////
                ) as t2 ---------------t2
                on t1.anio = t2.anio
                and t1.mes = t2.mes
                and t1.code = t2.code
                ) as g ) as tam 
                ) as c2,
                (
                select sum (taa.subtotal_acumulado_anio) as total_acumulado_anio
                from(
                select
                distinct sum(case when g.cont=1 then g.saldo_mes_anterior+(g.debit-g.credit) else g.debit-g.credit end) over(partition by g.code ) as subtotal_acumulado_anio
                from(
                select t1.code, t1.cont, t1.account, t1.date, t1.partida, t1.documento, t1.concepto, t1.debit, t1.credit, 
                coalesce(t2.saldo,0) as saldo_mes_anterior
                from (----t1
                select
                aa.code,
                COALESCE(aa."name"->>'es_GT',aa."name"->>'en_US') as account,
                aml."date",
                date_part('month',cast((date_trunc('month',cast(%s::text as date)) -'1sec' ::interval)::text as date)) as mes,
                date_part('year',cast((date_trunc('month',cast(%s::text as date)) -'1sec' ::interval)::text as date)) as anio,
                aj.x_poliza_id as partida,
                am."name" as documento,
                aml."name" as concepto,
                aml.debit,
                aml.credit,
                rank()over(partition by aa.code order by am."name") as cont
                from account_move am 
                inner join account_move_line aml 
                on am.id = aml.move_id 
                inner join account_journal aj 
                on aml.journal_id = aj.id 
                inner join (SELECT id, code, name, company_id FROM public."MC_account_account")aa 
                on aml.account_id = aa.id  and aa.company_id = %s
                where am.state = 'posted'
                --and aj.x_poliza_id is not null
                and cast(aml."date"::text as date) between cast(%s::text as date) and cast(%s::text as date)
                order by cast(aa.code::text as numeric), aml."date"
                ) as t1 ---------------t1
                left join
                ( --------t2
                select t.anio, t.mes, t.code, t.nombre_cuenta, t.saldo_mes, 
                sum(t.saldo_mes)over(partition by t.code order by t.anio,t.mes,t.code) as saldo 
                from (--//////////////
                select piv.anio,piv.mes,piv.code,piv.nombre_cuenta, coalesce(s.saldo_mes,0) as saldo_mes
                from (--**************
                select p.anio, p.mes, p.code, p.nombre_cuenta
                from ( -------
                select aa.code, COALESCE(aa."name"->>'es_GT',aa."name"->>'en_US') as nombre_cuenta
                ,date_part('month',generate_series('2021-01-01',current_date,'1 month'::interval)::date) as mes
                ,date_part('year',generate_series('2021-01-01',current_date,'1 month'::interval)::date) as anio
                from (SELECT id, code, name, company_id FROM public."MC_account_account")aa where   aa.company_id = %s
                ) as p 
                ) as piv --**************
                left join
                ( --##############
                select inf.anio, inf.mes, inf.code, inf.cuenta, inf.saldo_mes
                from(
                select 
                date_part('month',cast(aml."date"::text as date)) as mes,
                date_part('year',cast(aml."date"::text as date)) as anio,
                aa.code, COALESCE(aa."name"->>'es_GT',aa."name"->>'en_US') as cuenta,
                sum(aml.debit)-sum(aml.credit) as saldo_mes
                from account_move_line aml
                inner join (SELECT id, code, name, company_id FROM public."MC_account_account")aa 
                on aml.account_id = aa.id  and aa.company_id = %s
                inner join account_move am 
                on aml.move_id = am.id
                where am.state = 'posted'
                group by
                date_part('year',cast(aml."date"::text as date)),
                date_part('month',cast(aml."date"::text as date)),
                aa.code, aa."name"
                ) as inf
                order by  inf.anio, inf.mes,cast(inf.code::text as numeric)
                ) as s --##############
                on piv.anio = s.anio
                and piv.mes = s.mes
                and piv.code = s.code
                order by piv.code, --by cast(piv.code::text as numeric)
                
                piv.anio, piv.mes
                ) as t --//////////////
                ) as t2 ---------------t2
                on t1.anio = t2.anio
                and t1.mes = t2.mes
                and t1.code = t2.code
                ) as g ) as taa
                ) as c3
                '''

        self.env.cr.execute(_sql_data,( self.fecha_inicio,self.fecha_inicio,self.company_id.id,
                                       self.fecha_inicio,self.fecha_final,self.company_id.id,
                                       self.company_id.id,
                                       self.fecha_inicio,self.fecha_inicio,self.company_id.id,
                                       self.fecha_inicio,self.fecha_final,self.company_id.id,
                                       self.company_id.id,
                                       self.fecha_inicio,self.fecha_inicio,self.company_id.id,
                                       self.fecha_inicio,self.fecha_final,self.company_id.id,
                                       self.company_id.id
                                       ))
        _documento_debit = 0
        _documento_credit = 0
        _cuenta_credit = 0
        _cuenta_debit = 0
        _total_debit = 0
        _total_credit = 0
        _cuenta_id = 0
        inicio = 1

        _acumulado_anio_cuenta = 0
        _subtotal_acumulado_mes = 0
        _subtotal_acumulado_anio = 0

        lista = []
        for line in self.env.cr.dictfetchall():

            if inicio==1:
                detalle = (0,0,{
                        'code':line['code'],
                        'account': line['account'],                        
                        'concepto': 'Saldo Inicial ....',
                        'saldo_mes_anterior' : line['saldo_mes_anterior'],
                        'tipo_linea':'s',
                })
                lista.append(detalle)


            if _cuenta_id != line['code']:
                if inicio != 1:
                    detalle = (0,0,{
                        'concepto': 'Total por cuenta : ',
                        'debit': _cuenta_debit,
                        'credit': _cuenta_credit,
                        'acumulado_anio_cuenta':   _acumulado_anio_cuenta,
                        'subtotal_acumulado_mes':  _subtotal_acumulado_mes,
                        'subtotal_acumulado_anio': _subtotal_acumulado_anio,
                        'tipo_linea':'c',
                    })
                    lista.append(detalle)
                if inicio!=1:
                    detalle = (0,0,{
                        'code':line['code'],
                        'account': line['account'],                        
                        'concepto': 'Saldo Inicial ....',
                        'saldo_mes_anterior' : line['saldo_mes_anterior'],
                        'tipo_linea':'s',
                    })
                    lista.append(detalle)

                    _cuenta_debit = 0
                    _cuenta_credit = 0
                _cuenta_id = line['code']


            detalle = (0,0,{
                'code':line['code'],
                'account': line['account'],
                'date' : line['date'],
                'poliza': line['poliza'],
                'documento':line['documento'],
                'concepto': line['concepto'],
                'debit': line['debit'],
                'credit': line['credit'],
                'acumulado_mes_cuenta':line['acumulado_mes_cuenta'],
                'subtotal_acumulado_mes':line['subtotal_acumulado_mes'],
                'saldo_mes_anterior' : line['saldo_mes_anterior'],
                'acumulado_anio_cuenta': line['acumulado_anio_cuenta'],
                'subtotal_acumulado_anio': line['subtotal_acumulado_anio'],
                'total_acumulado_mes': line['total_acumulado_mes'],
                'total_acumulado_anio': line['total_acumulado_anio'],
                'tipo_linea':'l'

            })
            lista.append(detalle)
            inicio += 1

            _acumulado_anio_cuenta = line['acumulado_anio_cuenta']
            _subtotal_acumulado_mes = line['subtotal_acumulado_mes']
            _subtotal_acumulado_anio = line['subtotal_acumulado_anio']

            _cuenta_debit   += line['debit']
            _cuenta_credit  += line['credit']

            _total_debit   += line['debit']
            _total_credit  += line['credit']

    #agrega el ultimo total del documento
        detalle = (0,0,{
                    'concepto': 'Total por cuenta : ',
                    'debit': _cuenta_debit,
                    'credit': _cuenta_credit,
                    'acumulado_anio_cuenta': line['acumulado_anio_cuenta'],
                    'subtotal_acumulado_mes':line['subtotal_acumulado_mes'],
                    'subtotal_acumulado_anio': line['subtotal_acumulado_anio'],
                    'tipo_linea':'c'
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
    _name = 'libro.mayor.detalle'
    _description = 'Detalle del libro mayor'


    @api.depends('date')    
    def _fecha_date_mda(self):
        for record in self:
            if record.date:
                dt = str(record.date).split('-')
                record.fecha_date_mda = dt[2]+'-'+dt[1]+'-'+dt[0] 
            else:
                record.fecha_date_mda = ''

    libro_id = fields.Many2one(comodel_name='libro.mayor', string='libro_id')
    code = fields.Char(string='Código')
    account = fields.Char(string='Cuenta')
    date = fields.Date(string='Fecha')
    poliza = fields.Char(string='Poliza')
    documento = fields.Char(string='Documento')
    concepto = fields.Char(string='Concepto')
    debit = fields.Float(string='Cargo')
    credit = fields.Float(string='Abono')
    acumulado_mes_cuenta = fields.Float(string='Acumulado Mes Cuenta')
    subtotal_acumulado_mes = fields.Float(string='SubTotal Acumulado Mes')
    saldo_mes_anterior = fields.Float(string='Saldo Mes Anterior')
    acumulado_anio_cuenta = fields.Float(string='Acumulado Año Cuenta')
    subtotal_acumulado_anio = fields.Float(string='SubTotal Acumulado Anio')
    total_acumulado_mes = fields.Float(string='Total Acumulado Mes')
    total_acumulado_anio = fields.Float(string='Total Acumulado Anio')

    fecha_date_mda = fields.Char('Fecha mda', compute=_fecha_date_mda,copy=False,store=True) 
 

    tipo_linea = fields.Selection(
        string='Tipo Lonea',
        selection=[('l', 'Linea Detalle'), ('d', 'Total Documento'),('c', 'Total Cuenta'),('t', 'Total General'),('s', 'Saldo inicial')]
    )
    
