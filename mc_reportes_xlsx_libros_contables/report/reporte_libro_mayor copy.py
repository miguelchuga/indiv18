# -*- coding: utf-8 -*-

from odoo import models 
import xlsxwriter
import xlwt
from xlwt.Utils import rowcol_to_cell
from xlsxwriter.utility import xl_rowcol_to_cell
import datetime
import base64
from io import BytesIO
import ast

class LibroMayor(models.AbstractModel):
    _name = 'report.mc_reportes_xlsx_libros_contables.libro_mayor_xlsx.xlsx'
    _inherit = 'report.report_xlsx.abstract'
    _description = "Libro contable mayor"

    def generate_xlsx_report(self, lines):

        output = BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        fecha_inicio = lines.fecha_inicio
        fecha_final = lines.fecha_final

        ffi = str(fecha_inicio).split('-')
        fechaInicial = ffi[2]+'-'+ffi[1]+'-'+ffi[0]

        fff = str(fecha_final).split('-')
        fechaFinal = fff[2]+'-'+fff[1]+'-'+fff[0]
        
        sheet = workbook.add_worksheet('Libro Mayor')

        #Formatos
        formatEncabezado = workbook.add_format({
            'font_size': 13,
            'align':'center'
        })

        formatTituloCampo = workbook.add_format({
            'font_size': 12,
            'align':'center',
            'bottom': True,
            'top': True
        })

        formatoSubTotal = workbook.add_format({
            'bold': True,
            'top': True
        })

        formatoSubTotalCantidades = workbook.add_format({
            'bold': True,
            'top': True,
            'num_format': '#,##0.00'
        })

        formatoTotal = workbook.add_format({
            'bold': True,
            'top': True,
            'bottom': True,
        })

        formatoTotalCantidades = workbook.add_format({
            'bold': True,
            'top': True,
            'bottom': True,
            'num_format': '#,##0.00'
        })        

        formatoTituloCuenta = workbook.add_format({
            'bold': True
        })

        formatoCantidadCuenta = workbook.add_format({
            'bold': True,
            'align': 'right',
            'num_format': '#,##0.00'
        })

        formatoCantidades = workbook.add_format({
            'align': 'right',
            'num_format': '#,##0.00'
        })

        sheet.set_column('A:A',10)
        sheet.set_column('B:B',15)
        sheet.set_column('C:C',40)
        sheet.set_column('D:D',15)
        sheet.set_column('E:E',15)
        sheet.set_column('F:F',15)
        sheet.set_column('G:G',15)

        #Titulo de Reporte
        sheet.merge_range('C2:E2',lines.company_id.name,formatEncabezado)
        sheet.merge_range('C3:E3',lines.company_id.vat,formatEncabezado)
        sheet.merge_range('C4:E4','MAYOR GENERAL',formatEncabezado)
        sheet.merge_range('C5:E5',f'del {fechaInicial} al {fechaFinal}',formatEncabezado)
        sheet.merge_range('C6:E6','(CANTIDADES EXPRESADAS EN QUETZALES)',formatEncabezado)

        #Encabezado de Columnas
        sheet.write('A8','Partida',formatTituloCampo)
        sheet.write('B8','Doc. No.',formatTituloCampo)
        sheet.write('C8','Concepto',formatTituloCampo)
        sheet.write('D8','Cargos',formatTituloCampo)
        sheet.write('E8','Abonos',formatTituloCampo)
        sheet.write('F8','Acum. Mes',formatTituloCampo)
        sheet.write('G8','Acum. Año',formatTituloCampo)

        # _sql_data = '''select *
        #             from libro_mayor_detalle lmd 
        #             where cast(lmd."date"::text as date) between cast(%s::text as date) and cast(%s::text as date)
        #             order by lmd.id'''
        
        # self.env.cr.execute(_sql_data,(fecha_inicio,fecha_final,))

        code = ''
        date = '1900-01-01'
        row = 8
        inicio = 1
        sub_total_cargos = 0
        sub_total_abonos = 0
        total_cargos = 0
        total_abonos = 0
        sub_total_acumulado_mes = 0
        sub_total_acumulado_anio = 0
        total_acumulado_mes = 0
        total_acumulado_anio = 0

        for line in lines.libro_line:

            if line.code != code:

                #Esta condicion es para agregar los totales al final del grupo por cuenta
                if inicio != 1:
                    sheet.write(row,2,'Totales',formatoSubTotal)
                    sheet.write(row,3,sub_total_cargos,formatoSubTotalCantidades)
                    sheet.write(row,4,sub_total_abonos,formatoSubTotalCantidades)
                    sheet.write(row,5,sub_total_acumulado_mes,formatoSubTotalCantidades)
                    sheet.write(row,6,sub_total_acumulado_anio,formatoSubTotalCantidades)
                    sub_total_cargos = 0
                    sub_total_abonos = 0
                    row += 2

                #Se agrega el titulo de Saldo Inicial
                sheet.write(row,0,line.code,formatoTituloCuenta)
                #sheet.write(row,2,ast.literal_eval(line.account)['es_GT'],formatoTituloCuenta)
                sheet.write(row,2,line.account,formatoTituloCuenta)                
                sheet.write(row,4,'Saldo Inicial ....',formatoTituloCuenta)
                sheet.write(row,6,line.saldo_mes_anterior,formatoCantidadCuenta)
                code = line.code
                row += 1

            #Se agrega el subgrupo por fecha
            if str(line.date) != date:
                dt = str(line.date).split('-')
                fecha = dt[2]+'/'+dt[1]+'/'+dt[0]
                sheet.write(row,0,fecha)
                date = str(line.date)
                row += 1

            sheet.write(row,0,line.poliza)
            sheet.write(row,1,line.documento)
            sheet.write(row,2,line.concepto)
            sheet.write(row,3,line.debit,formatoCantidades)
            sheet.write(row,4,line.credit,formatoCantidades)
            sheet.write(row,5,line.acumulado_mes_cuenta,formatoCantidades)
            sheet.write(row,6,line.acumulado_anio_cuenta,formatoCantidades)

            sub_total_cargos += line.debit
            sub_total_abonos += line.credit
            total_cargos += line.debit
            total_abonos += line.credit
            sub_total_acumulado_mes = line.subtotal_acumulado_mes
            sub_total_acumulado_anio = line.subtotal_acumulado_anio
            total_acumulado_mes = line.total_acumulado_mes
            total_acumulado_anio = line.total_acumulado_anio
            row += 1

            inicio += 1

        #SubTotales de la ultima cuenta
        sheet.write(row,2,'Totales',formatoSubTotal)
        sheet.write(row,3,sub_total_cargos,formatoSubTotalCantidades)
        sheet.write(row,4,sub_total_abonos,formatoSubTotalCantidades)
        sheet.write(row,5,sub_total_acumulado_mes,formatoSubTotalCantidades)
        sheet.write(row,6,sub_total_acumulado_anio,formatoSubTotalCantidades)
        row += 1

        #Totales
        sheet.write(row,2,'Total General',formatoTotal)
        sheet.write(row,3,total_cargos,formatoTotalCantidades)
        sheet.write(row,4,total_abonos,formatoTotalCantidades)
        sheet.write(row,5,total_acumulado_mes,formatoTotalCantidades)
        sheet.write(row,6,total_acumulado_anio,formatoTotalCantidades)


        workbook.close()
        output.seek(0)
        archivo_xlsx = base64.b64encode(output.read())
        return archivo_xlsx