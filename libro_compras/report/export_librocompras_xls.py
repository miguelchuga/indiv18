from odoo import models
import xlsxwriter
import xlwt
from xlwt.Utils import rowcol_to_cell
from xlsxwriter.utility import xl_rowcol_to_cell
import datetime
import base64
from io import BytesIO

class ConciliacionBancariaXls(models.AbstractModel):
    _name = 'report.libro_compras.report_librocompras_xls'
    _inherit = 'report.report_xlsx.abstract'
    _description = "Libro compras" 

    def generate_xlsx_report(self, lines):

        output = BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
                
        sheet = workbook.add_worksheet('Libro de Compras')
        sheet2 = workbook.add_worksheet('Top 10')

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
        sheet.merge_range('A5:B5','LIBRO DE COMPRAS',formatleft21)
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
        sheet.write(rec_row,9,'IMPORTACIÓN',formatcenter21)
        sheet.write(rec_row,10,'ACTIVOS',formatcenter21)
        sheet.set_column(6,8,15,None)
        sheet.write(rec_row,11,'COMBUSTIBLE',formatcenter21)
        sheet.set_column(6,9,15,None)
        sheet.write(rec_row,12,'PEQ. CONT.',formatcenter21)
        sheet.write(rec_row,13,'IVA',formatcenter21)
        sheet.write(rec_row,14,'TOTAL',formatcenter21)
        sheet.write(rec_row,15,'EXENTOS',formatcenter21)
        sheet.write(rec_row,16,'IDP',formatcenter21)

        rec_row += 1

        lw3 = []
        w3 = 0
        
        #Se obtiene el mayor numero de caracteres de toda la columna
        w1 = max([len(str(l.fecha_documento)) for l in lines.libro_line_ids])
        w2 = max([len(l.proveedor) for l in lines.libro_line_ids])
        for l in lines.libro_line_ids:
            if l.serie:
                lw3.append(len(l.serie))
        w3 = max(lw3) if lw3 else 10
        #w4 = max([len(str(l.correlativo)) for l in lines.libro_line_ids])
        w5 = max([len(str(l.nit_dpi)) for l in lines.libro_line_ids])

        #Se configura columna con el dato anterior para que se ajuste la informacion en la celda
        sheet.set_column('B:B',w1,None)    
        sheet.set_column('C:C',w2,None)
        sheet.set_column('D:D',w3,None)
        sheet.set_column('O:O',12,None)
        sheet.set_column('F:F',w5,None)
        sheet.set_column('Q:Q',12,None)


        #Variables para Totales al final del Detalle
        totBienes = totServicios = totPequenio = totIva = totTotal = totIdp = 0
        correlativoNo = 1
        #Variables para Resumen
        #Totales para Documentos tipo Factura
        totFactDoc = totBienesFa = totServiciosFa = totImportFa = totActivoFc = totCombustibleFa = totPeqContFa = totIvaFa = totIdpFa = totTotalFa = totExentoFa = 0
        #Totales para Documentos tipo Nota de Credito
        totNcDoc = totBienesNc = totServiciosNc = totImportNc = totActivoNc = totCombustibleNc = totPeqContNc = totIvaNc = totIdpNc = totTotalNc = totExentoNc = 0
        #Totales del Resumen Final
        totDoc = totBienRes = totSerRes = totImpRes = totActRes = totCombRes = totPequRes = totIvaRes = totIdpRes = totTotRes = totExcRes = 0
        #VARIABLES TOTALES BIENES, SERVICIOS Y EXENTO
        total_bienes = total_servicios = total_exento = 0

        #Lineas de Detalle
        for line in lines.libro_line_ids:
            sheet.write(rec_row,0,correlativoNo,fontSizeCenter10)
            correlativoNo += 1
            sheet.write(rec_row,1,line.fecha_documento,format_date)

            sheet.write(rec_row,2,line.proveedor,font_size_10)
            sheet.write(rec_row,3,line.asiste_libro,fontSizeRight10)

            sheet.write(rec_row,4,line.serie,font_size_10)
            sheet.write(rec_row,5,line.documento,font_size_10)
            sheet.write(rec_row,6,line.nit_dpi,font_size_10)

            total_bienes = line.local_bienes_gravados + line.local_bienes_exentos + line.importacion_bienes_exentos
            sheet.write(rec_row,7,total_bienes,fontSizeRight10)
            totBienes += total_bienes

            total_servicios = line.local_servicios_gravados + line.local_servicios_exentos + line.importacion_servicios_gravados + line.importacion_servicios_exentos
            sheet.write(rec_row,8,total_servicios,fontSizeRight10)
            totServicios += total_servicios

            sheet.write(rec_row,9,line.importacion_bienes_gravados,fontSizeRight10)

            sheet.write(rec_row,10,line.activos_fijos,fontSizeRight10)
            sheet.write(rec_row,11,line.local_bienes_gravados_combustible,fontSizeRight10)
            
            total_pequenio = line.local_bienes_pequenio_contribuyente + line.local_servicios_pequenio_contribuyente
            sheet.write(rec_row,12,total_pequenio,fontSizeRight10)
            totPequenio += total_pequenio

            sheet.write(rec_row,13,line.iva,fontSizeRight10)
            totIva += line.iva

            sheet.write(rec_row,14,line.total,fontSizeRight10)
            totTotal += line.total

            total_exento = line.timbre_prensa + line.tasa_municipal + line.inguat
            sheet.write(rec_row,15,total_exento,fontSizeRight10)
            sheet.write(rec_row,16,line.idp,fontSizeRight10)

            totIdp += line.idp

            if line.asiste_libro == 'NC':
                totNcDoc += 1
                totBienesNc += total_bienes
                totServiciosNc += total_servicios
                totImportNc += line.importacion_bienes_gravados
                totActivoNc += line.activos_fijos
                totCombustibleNc += line.local_bienes_gravados_combustible
                totPeqContNc += total_pequenio
                totIvaNc += line.iva
                totIdpNc += line.idp
                totTotalNc += line.total
                totExentoNc += total_exento
            else:
                totFactDoc += 1
                totBienesFa += total_bienes
                totServiciosFa += total_servicios
                totImportFa += line.importacion_bienes_gravados
                totActivoFc += line.activos_fijos
                totCombustibleFa += line.local_bienes_gravados_combustible
                totPeqContFa += total_pequenio
                totIvaFa += line.iva
                totIdpFa += line.idp
                totTotalFa += line.total
                totExentoFa += total_exento

            totDoc = totNcDoc + totFactDoc
            totBienRes = totBienesNc + totBienesFa
            totSerRes = totServiciosNc + totServiciosFa
            totImpRes = totImportNc + totImportFa
            totActRes = totActivoNc + totActivoFc
            totCombRes = totCombustibleNc + totCombustibleFa
            totPequRes = totPeqContNc + totPeqContFa
            totIvaRes = totIvaNc + totIvaFa
            totIdpRes = totIdpNc + totIdpFa
            totTotRes = totTotalNc + totTotalFa
            totExcRes = totExentoNc + totExentoFa

            rec_row += 1

        #TOTALES DEL DETALLE
        sheet.write(rec_row,6,'TOTAL',font_size_10)
        sheet.write(rec_row,7,totBienes,fontSizeRight10)
        sheet.write(rec_row,8,totServicios,fontSizeRight10)
        sheet.write(rec_row,9,totImpRes,fontSizeRight10)
        sheet.write(rec_row,10,totActRes,fontSizeRight10)
        sheet.write(rec_row,11,totCombRes,fontSizeRight10)
        sheet.write(rec_row,12,totPequenio,fontSizeRight10)
        sheet.write(rec_row,13,totIva,fontSizeRight10)
        sheet.write(rec_row,14,totTotal,fontSizeRight10)
        sheet.write(rec_row,15,totExcRes,fontSizeRight10)
        sheet.write(rec_row, 16, totIdpRes, fontSizeRight10)


        #Encabezado Resumen
        rec_row += 3
        sheet.write(rec_row,5,'RESUMEN',formatcenter21)
        sheet.write(rec_row,6,'DOC CNT',formatcenter21)
        sheet.write(rec_row,7,'BIENES',formatcenter21)
        sheet.write(rec_row,8,'SERVICIOS',formatcenter21)
        sheet.write(rec_row,9,'IMPORTACIONES',formatcenter21)
        sheet.write(rec_row,10,'ACTIVOS',formatcenter21)
        sheet.write(rec_row,11,'COMBUSTIBLE',formatcenter21)
        sheet.write(rec_row,12,'PEQ. CONT.',formatcenter21)
        sheet.write(rec_row,13,'IVA',formatcenter21)
        sheet.write(rec_row,14,'TOTAL',formatcenter21)
        sheet.write(rec_row,15,'TOTAL IDP',formatcenter21)


        #Valores del Resumen
        rec_row += 1
        sheet.write(rec_row,5,'FACT',formatcenter21)
        sheet.write(rec_row,6,totFactDoc,fontSizeRight10)
        sheet.write(rec_row,7,totBienesFa,fontSizeRight10)
        sheet.write(rec_row,8,totServiciosFa,fontSizeRight10)
        sheet.write(rec_row,9,totImportFa,fontSizeRight10)
        sheet.write(rec_row,10,totActivoFc,fontSizeRight10)
        sheet.write(rec_row,11,totCombustibleFa,fontSizeRight10)
        sheet.write(rec_row,12,totPeqContFa,fontSizeRight10)
        sheet.write(rec_row,13,totIvaFa,fontSizeRight10)
        sheet.write(rec_row,14,totTotalFa,fontSizeRight10)
        sheet.write(rec_row,15,totIdpFa,fontSizeRight10)


        rec_row += 1
        sheet.write(rec_row,5,'N/C',formatcenter21)
        sheet.write(rec_row,6,totNcDoc,fontSizeRight10)
        sheet.write(rec_row,7,totBienesNc,fontSizeRight10)
        sheet.write(rec_row,8,totServiciosNc,fontSizeRight10)
        sheet.write(rec_row,9,totImportNc,fontSizeRight10)

        sheet.write(rec_row,10,totActivoNc,fontSizeRight10)
        sheet.write(rec_row,11,totCombustibleNc,fontSizeRight10)
        sheet.write(rec_row,12,totPeqContNc,fontSizeRight10)
        sheet.write(rec_row,13,totIvaNc,fontSizeRight10)
        sheet.write(rec_row,14,totTotalNc,fontSizeRight10)
        sheet.write(rec_row,15,totIdpNc,fontSizeRight10)


        rec_row += 1
        sheet.write(rec_row,5,'TOTAL',formatcenter21)
        sheet.write(rec_row,6,totDoc,fontSizeRight10)
        sheet.write(rec_row,7,totBienRes,fontSizeRight10)
        sheet.write(rec_row,8,totSerRes,fontSizeRight10)
        sheet.write(rec_row,9,totImpRes,fontSizeRight10)
        sheet.write(rec_row,10,totActRes,fontSizeRight10)
        sheet.write(rec_row,11,totCombRes,fontSizeRight10)
        sheet.write(rec_row,12,totPequRes,fontSizeRight10)
        sheet.write(rec_row,13,totIvaRes,fontSizeRight10)
        sheet.write(rec_row,14,totTotRes,fontSizeRight10)
        sheet.write(rec_row,15,totIdpRes,fontSizeRight10)

        

        ############# HOJA 2 ############# 

        #Encabezado Reporte
        sheet2.write('A1','Empresa: ',formatright21)
        sheet2.merge_range('B1:G1',lines.company_id.name,formatleft21)
        
        sheet2.write('A2','Nit: ',formatright21)
        sheet2.merge_range('B2:G2',lines.company_id.vat,font_size_10)

        sheet2.write('A3','Dirección: ',formatright21)
        sheet2.merge_range('B3:G3',lines.company_id.street,font_size_10)

        #Titulo
        sheet2.merge_range('A5:B5','TOP 10 PROVEEDORES',formatleft21)
        sheet2.write('D5','Desde: ',formatright21)
        sheet2.merge_range('E5:F5',lines.fecha_desde,format_date)
        sheet2.write('H5','Hasta: ',formatright21)
        sheet2.merge_range('I5:J5',lines.fecha_hasta,format_date)

        rec_row = 6

        sheet2.write(rec_row,0,'NOMBRE',formatcenter21)
        sheet2.write(rec_row,1,'NIT',formatcenter21)
        sheet2.write(rec_row,2,'TOTAL',formatcenter21)
        sheet2.write(rec_row,3,'DOCS. CNT.',formatcenter21)

        s21 = max([len(str(l.proveedor)) for l in lines.libro_top_proveedores_ids], default=0)
        #s21 = max([len(str(l.proveedor)) for l in lines.libro_top_proveedores_ids])
        sheet2.set_column('A:A',s21,None)

        s22 = max([len(str(l.nit_dpi)) for l in lines.libro_top_proveedores_ids], default=0)
        sheet2.set_column('B:B',s22,None)

        rec_row += 2
        for line in lines.libro_top_proveedores_ids:
            
            sheet2.write(rec_row,0,line.proveedor,font_size_10)
            sheet2.write(rec_row,1,line.nit_dpi,font_size_10)
            sheet2.write(rec_row,2,line.base,fontSizeRight10)
            sheet2.write(rec_row,3,line.cantidad,fontSizeRight10)

            rec_row += 1


        workbook.close()
        output.seek(0)
        archivo_xlsx = base64.b64encode(output.read())
        return archivo_xlsx