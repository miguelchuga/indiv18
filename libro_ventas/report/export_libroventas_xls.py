from odoo import models
import xlsxwriter
import xlwt
from xlwt.Utils import rowcol_to_cell
from xlsxwriter.utility import xl_rowcol_to_cell
import datetime
import base64
from io import BytesIO

class ConciliacionBancariaXls(models.AbstractModel):
    _name = 'report.libro_ventas.report_libroventas_xls'
    _inherit = 'report.report_xlsx.abstract'
    _description = "Libro de ventas xls"


    def generate_xlsx_report(self, lines):

        output = BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})

        sheet = workbook.add_worksheet('Libro de Ventas')
        #sheet2 = workbook.add_worksheet('Top 10')

        format21 = workbook.add_format({'font_size': 10, 'align': 'center', 'right': True, 'left': True,'bottom': True, 'top': True, 'bold': True})
        formatleft21 = workbook.add_format({'font_size': 10, 'align': 'left', 'right': True, 'left': True,'bottom': True, 'top': True, 'bold': True})
        formatright21 = workbook.add_format({'font_size': 10, 'align': 'right', 'right': True, 'left': True,'bottom': True, 'top': True, 'bold': True})
        formatcenter21 = workbook.add_format({'font_size': 10, 'align': 'center', 'right': True, 'left': True,'bottom': True, 'top': True, 'bold': True})
        font_size_12 = workbook.add_format({'bottom': True, 'top': True, 'right': True, 'left': True, 'align': 'left', 'font_size': 12})
        font_size_10 = workbook.add_format({'bottom': True, 'top': True, 'right': True, 'left': True, 'align': 'left', 'font_size': 10})
        fontSize10Normal = workbook.add_format({'align': 'left', 'font_size': 10})
        fontSizeCenter10 = workbook.add_format({'bottom': True, 'top': True, 'right': True, 'left': True, 'align': 'center', 'font_size': 10})
        fontSizeRight10 = workbook.add_format({'bottom': True, 'top': True, 'right': True, 'left': True, 'align': 'right', 'font_size': 10})
        format_date = workbook.add_format({'num_format':'dd-mm-yyyy','bottom': True, 'top': True, 'right': True, 'left': True, 'align': 'left', 'font_size': 10})
        
        
        #Encabezado Reporte
        sheet.write('A1','Empresa: ',formatright21)
        sheet.merge_range('B1:G1',lines.company_id.name,formatleft21)
        
        sheet.write('A2','Nit: ',formatright21)
        sheet.merge_range('B2:G2',lines.company_id.vat,font_size_10)

        sheet.write('A3','Dirección: ',formatright21)
        sheet.merge_range('B3:G3',lines.company_id.street,font_size_10)

        #Titulo
        sheet.merge_range('A5:B5','LIBRO DE VENTAS',formatleft21)
        sheet.write('D5','Desde: ',formatright21)
        sheet.merge_range('E5:F5',lines.fecha_desde,format_date)
        sheet.write('H5','Hasta: ',formatright21)
        sheet.merge_range('I5:J5',lines.fecha_hasta,format_date)

        #Encabezado Detalle

        rec_row = 6

        sheet.write(rec_row,0,' # ',fontSizeCenter10)
        sheet.write(rec_row,1,'FECHA',formatcenter21)
        sheet.write(rec_row,2,'NOMBRE',formatcenter21)

        sheet.write(rec_row,3,'TIPO DOCTO.',formatcenter21)

        sheet.write(rec_row,4,'SERIE',formatcenter21)
        sheet.write(rec_row,5,'NRO.',formatcenter21)
        sheet.write(rec_row,6,'NIT',formatcenter21)
        sheet.write(rec_row,7,'BIENES',formatcenter21)
        sheet.write(rec_row,8,'SERVICIOS',formatcenter21)
        #sheet.write(rec_row,8,'ACTIVOS',formatcenter21)
        sheet.set_column(6,8,15,None)
        #sheet.write(rec_row,9,'COMBUSTIBLE',formatcenter21)
        sheet.set_column(6,9,15,None)
        #sheet.write(rec_row,10,'PEQ. CONT.',formatcenter21)
        sheet.write(rec_row,9,'IVA',formatcenter21)
        sheet.write(rec_row,10,'TOTAL',formatcenter21)
        sheet.write(rec_row, 11, 'EXENTO', formatcenter21)

        rec_row += 1

        lw3 = []
        w3 = 0
        
        #Se obtiene el mayor numero de caracteres de toda la columna
        w1 = max([len(str(l.fecha_documento)) for l in lines.libro_line_ids])
        w2 = max([len(l.nombre) for l in lines.libro_line_ids])
        for l in lines.libro_line_ids:
            if l.invoice_id.serie_gt:
                lw3.append(len(l.invoice_id.serie_gt))
        w3 = max(lw3) if lw3 else 10
        #w4 = max([len(str(l.correlativo)) for l in lines.libro_line_ids])
        w5 = max([len(str(l.nit_dpi)) for l in lines.libro_line_ids])

        #Se configura columna con el dato anterior para que se ajuste la informacion en la celda
        sheet.set_column('B:B',w1,None)    
        sheet.set_column('C:C',w2,None)
        sheet.set_column('D:D',w3,None)
        #sheet.set_column('E:E',w4,None)
        sheet.set_column('F:F',w5,None)


        #Variables para Totales al final del Detalle
        totBienes = totServicios = totPequenio = totIva = totTotal = 0
        correlativoNo = 1
        #Variables para Resumen
        #Totales para Documentos tipo Factura
        totFactDoc = totBienesFa = totServiciosFa = totActivoFc = totCombustibleFa = totPeqContFa = totIvaFa = totTotalFa = totNotasAbono = 0
        #Totales para Documentos tipo Nota de Credito
        totNcDoc = totBienesNc = totServiciosNc = totActivoNc = totCombustibleNc = totPeqContNc = totIvaNc = totTotalNc = 0
        #Totales para Documentos tipo Nota de Debito
        totNbDoc = totBienesNb = totServiciosNb = totActivoNb = totCombustibleNc = totPeqContNb = totIvaNb = totTotalNb = 0

        #Tatales del Resumen Final
        totDoc = totBienRes = totSerRes = totActRes = totCombRes = totPequRes = totIvaRes = totTotRes = 0

        #Lineas de Detalle
        for line in lines.libro_line_ids:
            sheet.write(rec_row,0,correlativoNo,fontSizeCenter10)
            correlativoNo += 1
            sheet.write(rec_row,1,line.fecha_documento,format_date)

            sheet.write(rec_row,2,line.nombre,font_size_10)

            sheet.write(rec_row,3,line.asiste_libro,fontSizeRight10)

            sheet.write(rec_row,4,line.serie_venta,font_size_10)
            sheet.write(rec_row,5,line.documento,font_size_10)
            sheet.write(rec_row,6,line.nit_dpi,font_size_10)

            if line.asiste_libro != 'NB':
                total_bienes = line.local_bienes_gravados + line.local_bienes_exentas  + line.exportacion_bienes_exentos

            if line.asiste_libro == 'NB':
                sheet.write(rec_row, 7, 0.00, fontSizeRight10)
            else:
                sheet.write(rec_row,7,total_bienes,fontSizeRight10)
            if line.asiste_libro != 'NB':
                totBienes += total_bienes

            if line.asiste_libro != 'NB':
                total_servicios = line.local_servicios_gravados + line.local_servicios_exentas + line.exportacion_servicios_gravados + line.exportacion_servicios_exentos
            if line.asiste_libro == 'NB':
                sheet.write(rec_row, 8, 0.00, fontSizeRight10)
            else:
                sheet.write(rec_row,8,total_servicios,fontSizeRight10)
            if line.asiste_libro != 'NB':
                totServicios += total_servicios

            #sheet.write(rec_row,8,line.activos_fijos,fontSizeRight10)
            #sheet.write(rec_row,9,line.idp,fontSizeRight10)
            
            #total_pequenio = line.local_bienes_pequenio_contribuyente + line.local_servicios_pequenio_contribuyente
            #sheet.write(rec_row,10,total_pequenio,fontSizeRight10)
            #totPequenio += total_pequenio

            sheet.write(rec_row,9,line.iva,fontSizeRight10)
            totIva += line.iva

            sheet.write(rec_row,10,line.total,fontSizeRight10)
            totTotal += line.total

            #cuando es NOTA DE DEBITO lo pone al final de la fila como excento
            if line.asiste_libro == 'NB':
                sheet.write(rec_row,11,(line.local_servicios_gravados + line.local_servicios_exentas + line.exportacion_servicios_gravados + line.exportacion_servicios_exentos + line.local_bienes_gravados + line.local_bienes_exentas  + line.exportacion_bienes_exentos)
,fontSizeRight10)
            else:
                sheet.write(rec_row,11,0.00,fontSizeRight10)

            if line.asiste_libro == 'NB':
                totNotasAbono += (line.local_servicios_gravados + line.local_servicios_exentas + line.exportacion_servicios_gravados + line.exportacion_servicios_exentos + line.local_bienes_gravados + line.local_bienes_exentas  + line.exportacion_bienes_exentos)


            if line.asiste_libro == 'NC':
                totNcDoc += 1
                totBienesNc += total_bienes
                totServiciosNc += total_servicios
                #totActivoNc += line.activos_fijos
                #totCombustibleNc += line.idp
                #totPeqContNc += total_pequenio
                totIvaNc += line.iva
                totTotalNc += line.total
            else:
                totFactDoc += 1
                totBienesFa += total_bienes
                totServiciosFa += total_servicios
                #totActivoFc += line.activos_fijos
                #totCombustibleFa += line.idp
                #totPeqContFa += total_pequenio
                totIvaFa += line.iva
                totTotalFa += line.total

            totDoc = totNcDoc + totFactDoc
            totBienRes = totBienesNc + totBienesFa
            totSerRes = totServiciosNc + totServiciosFa
            #totActRes = totActivoNc + totActivoFc
            #totCombRes = totCombustibleNc + totCombustibleFa
            #totPequRes = totPeqContNc + totPeqContFa
            totIvaRes = totIvaNc + totIvaFa
            totTotRes = totTotalNc + totTotalFa

            rec_row += 1

        sheet.write(rec_row,6,'TOTAL',font_size_10)
        sheet.write(rec_row,7,totBienes,fontSizeRight10)
        
        sheet.write(rec_row,8,totServicios,fontSizeRight10)
        #sheet.write(rec_row,10,totPequenio,fontSizeRight10)
        sheet.write(rec_row,9,totIva,fontSizeRight10)
        sheet.write(rec_row,10,totTotal,fontSizeRight10)
        sheet.write(rec_row,11,totNotasAbono,fontSizeRight10)




        #Encabezado Resumen
        rec_row += 3
        sheet.write(rec_row,5,'RESUMEN',formatcenter21)
        sheet.write(rec_row,6,'DOC CNT',formatcenter21)
        sheet.write(rec_row,7,'BIENES',formatcenter21)
        sheet.write(rec_row,8,'SERVICIOS',formatcenter21)
        #sheet.write(rec_row,8,'ACTIVOS',formatcenter21)
        #sheet.write(rec_row,9,'COMBUSTIBLE',formatcenter21)
        #sheet.write(rec_row,10,'PEQ. CONT.',formatcenter21)
        sheet.write(rec_row,9,'IVA',formatcenter21)
        sheet.write(rec_row,10,'TOTAL',formatcenter21)


        #Valores del Resumen
        rec_row += 1
        sheet.write(rec_row,5,'FACT',formatcenter21)
        sheet.write(rec_row,6,totFactDoc,fontSizeRight10)
        sheet.write(rec_row,7,totBienesFa,fontSizeRight10)
        sheet.write(rec_row,8,totServiciosFa,fontSizeRight10)
        #sheet.write(rec_row,8,totActivoFc,fontSizeRight10)
        #sheet.write(rec_row,9,totCombustibleFa,fontSizeRight10)
        #sheet.write(rec_row,10,totPeqContFa,fontSizeRight10)
        sheet.write(rec_row,9,totIvaFa,fontSizeRight10)
        sheet.write(rec_row,10,totTotalFa,fontSizeRight10)

        rec_row += 1
        sheet.write(rec_row,5,'N/C',formatcenter21)
        sheet.write(rec_row,6,totNcDoc,fontSizeRight10)
        sheet.write(rec_row,7,totBienesNc,fontSizeRight10)
        sheet.write(rec_row,8,totServiciosNc,fontSizeRight10)
        #sheet.write(rec_row,8,totActivoNc,fontSizeRight10)
        #sheet.write(rec_row,9,totCombustibleNc,fontSizeRight10)
        #sheet.write(rec_row,10,totPeqContNc,fontSizeRight10)
        sheet.write(rec_row,9,totIvaNc,fontSizeRight10)
        sheet.write(rec_row,10,totTotalNc,fontSizeRight10)

        rec_row += 1
        sheet.write(rec_row,5,'TOTAL',formatcenter21)
        sheet.write(rec_row,6,totDoc,fontSizeRight10)
        sheet.write(rec_row,7,totBienRes,fontSizeRight10)
        sheet.write(rec_row,8,totSerRes,fontSizeRight10)
        #sheet.write(rec_row,8,totActRes,fontSizeRight10)
        #sheet.write(rec_row,9,totCombRes,fontSizeRight10)
        #sheet.write(rec_row,10,totPequRes,fontSizeRight10)
        sheet.write(rec_row,9,totIvaRes,fontSizeRight10)
        sheet.write(rec_row,10,totTotRes,fontSizeRight10)
        


        # #Encabezado Reporte
        # sheet2.write('A1','Empresa: ',formatright21)
        # sheet2.merge_range('B1:G1',lines.company_id.name,formatleft21)
        
        # sheet2.write('A2','Nit: ',formatright21)
        # sheet2.merge_range('B2:G2',lines.company_id.vat,font_size_10)

        # sheet2.write('A3','Dirección: ',formatright21)
        # sheet2.merge_range('B3:G3',lines.company_id.street,font_size_10)

        # #Titulo
        # sheet2.merge_range('A5:B5','TOP 10 PROVEEDORES',formatleft21)
        # sheet2.write('D5','Desde: ',formatright21)
        # sheet2.merge_range('E5:F5',lines.fecha_desde,format_date)
        # sheet2.write('H5','Hasta: ',formatright21)
        # sheet2.merge_range('I5:J5',lines.fecha_hasta,format_date)

        # rec_row = 6

        # sheet2.write(rec_row,0,'NOMBRE',formatcenter21)
        # sheet2.write(rec_row,1,'NIT',formatcenter21)
        # sheet2.write(rec_row,2,'TOTAL',formatcenter21)
        # sheet2.write(rec_row,3,'DOCS. CNT.',formatcenter21)

        # s21 = max([len(str(l.proveedor)) for l in lines.libro_top_proveedores_ids])
        # sheet2.set_column('A:A',s21,None)

        # s22 = max([len(str(l.nit_dpi)) for l in lines.libro_top_proveedores_ids])
        # sheet2.set_column('B:B',s22,None)

        # rec_row += 2
        # for line in lines.libro_top_proveedores_ids:
            
        #     sheet2.write(rec_row,0,line.proveedor,font_size_10)
        #     sheet2.write(rec_row,1,line.nit_dpi,font_size_10)
        #     sheet2.write(rec_row,2,line.base,fontSizeRight10)
        #     sheet2.write(rec_row,3,line.cantidad,fontSizeRight10)

        #     rec_row += 1


        workbook.close()
        output.seek(0)
        archivo_xlsx = base64.b64encode(output.read())
        return archivo_xlsx