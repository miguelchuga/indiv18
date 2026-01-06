from odoo import models, fields, api

class Diario(models.TransientModel):
    _name = "wizard.libro.diario"
    _description = "Libro Contable Diario"

    date_from = fields.Date('Start Date')
    date_to = fields.Date('End Date')
    company_id = fields.Many2one(comodel_name='res.company', string='Compañia')
    

    
    def export_xls(self):
        context = self._context
        datas = {'ids': context.get('active_ids', [])}
        datas['model'] = 'account.move'
        datas['form'] = self.read()[0]
        for field in datas['form'].keys():
            if isinstance(datas['form'][field], tuple):
                datas['form'][field] = datas['form'][field][0]
        if context.get('xls_export'):
            return self.env.ref('mc_reportes_xlsx_libros_contables.libro_diario_xlsx').report_action(self,data=datas)


class Mayor(models.TransientModel):
    _name = "wizard.libro.mayor"
    _description = "Libro Contable Mayor"

    date_from = fields.Date('Start Date')
    date_to = fields.Date('End Date')
    company_id = fields.Many2one(comodel_name='res.company', string='Compañia')

    
    def export_xls(self):
        context = self._context
        datas = {'ids': context.get('active_ids', [])}
        datas['model'] = 'account.move'
        datas['form'] = self.read()[0]
        for field in datas['form'].keys():
            if isinstance(datas['form'][field], tuple):
                datas['form'][field] = datas['form'][field][0]
        if context.get('xls_export'):
            return self.env.ref('mc_reportes_xlsx_libros_contables.libro_mayor_xlsx').report_action(self,data=datas)