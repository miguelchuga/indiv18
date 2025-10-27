# -*- encoding: utf-8 -*-
import json
from odoo import api, fields, models, _, Command

from werkzeug.urls import url_parse
from odoo.tools.safe_eval import safe_eval, time

from odoo.http import request, content_disposition
from odoo import http
from odoo.tools import html_escape
from odoo.addons.web.controllers.report import ReportController as RC

import logging
_logger = logging.getLogger(__name__)

import base64
from PyPDF2 import PdfReader, PdfWriter, PageObject
from reportlab.pdfgen import canvas
import io

import pytz

class ReportControllerExtend(RC):
    @http.route([
        '/report/<converter>/<reportname>',
        '/report/<converter>/<reportname>/<docids>',
    ], type='http', auth='user', website=True)
    def report_routes(self, reportname, docids=None, converter=None, **data):
        report = request.env['ir.actions.report']._get_report_from_name(reportname)
        if report.report_libreoffice:
            context = dict(request.env.context)
            if docids:
                docids = [int(i) for i in docids.split(',')]
            if data.get('options'):
                data.update(json.loads(data.pop('options')))
            if data.get('context'):
                data['context'] = json.loads(data['context'])
                context.update(data['context'])
            mimetype, out, report_name, ext = report.with_context(context).render_any_docs(reportname, docids, data=data)
            pdfhttpheaders = [('Content-Type', mimetype), ('Content-Length', len(out))]
            return request.make_response(out, headers=pdfhttpheaders)
        return super(ReportControllerExtend, self).report_routes(reportname, docids, converter, **data)

    @http.route(['/report/download'], type='http', auth="user")
    def report_download(self, data, context=None, token=None, readonly=True):
        requestcontent = json.loads(data)
        url, type = requestcontent[0], requestcontent[1]
        reportname = '???'
        try:
            if type in ['qweb-pdf']:
                pattern = '/report/pdf/' if type == 'qweb-pdf' else '/report/text/'
                reportname = url.split(pattern)[1].split('?')[0]
                docids = None
                if '/' in reportname:
                    reportname, docids = reportname.split('/')

                report = request.env['ir.actions.report']._get_report_from_name(reportname)
                if report.report_libreoffice:
                    default_output_file = 'odt'

                    if docids:
                        # Generic report:
                        response = self.report_routes(reportname, docids=docids, converter=None, context=context)
                    else:
                        # Particular report:
                        data = url_parse(url).decode_query(cls=dict)  # decoding the args represented in JSON
                        # Muy raro el funcionamiento el solo echo de realizar un print(dict(data)) genera un error
                        response = self.report_routes(reportname, converter=None, **dict(data))

                    extension = report.output_file or default_output_file
                    filename = "%s.%s" % (report.name, extension)

                    if docids:
                        ids = [int(x) for x in docids.split(",")]
                        obj = request.env[report.model].browse(ids)

                        #solo para el estado de cuenta que ponga la fecha de la impresion
#                        if obj._name=='mc_plan_pago.mc_plan_pago':
#                            obj.write({'x_fecha_documento':fields.datetime.now(pytz.timezone('America/Guatemala')).strftime("%Y-%m-%d"), })
#                        obj = request.env[report.model].browse(ids)

                        if report.print_report_name and not len(obj) > 1:
                            report_name = safe_eval(report.print_report_name, {'object': obj, 'time': time})
                            filename = "%s.%s" % (report_name, extension)
                    response.headers.add('Content-Disposition', content_disposition(filename))
                    content_pdf = base64.b64encode(response.data) 

                    if obj._name=='libro.mayor':
                        obj.write({'file_pdf': content_pdf ,
                                   'file_name': 'libro_mayor_foliado.pdf', 
                                   })

                    if obj._name=='libro.diario':                 
                        obj.write({'file_pdf': content_pdf ,
                                   'file_name': 'libro_diario_foliado.pdf', 
                                   })
                    if obj._name=='mc_libro_ventas.mc_libro_ventas':
                        obj.write({'file_pdf': content_pdf ,
                                   'file_name': 'libro_ventas_foliado.pdf', 
                                   })
                    if obj._name=='mc_libro_compras.mc_libro_compras':
                        obj.write({'file_pdf': content_pdf ,
                                   'file_name': 'libro_compras_foliado.pdf', 
                                   })

                    return response
        except Exception as e:
            _logger.warning("Error while generating report %s", reportname)
            se = http.serialize_exception(e)
            error = {
                'code': 200,
                'message': "Odoo Server Error",
                'data': se
            }
            return request.make_response(html_escape(json.dumps(error)))
        return super(ReportControllerExtend, self).report_download(data, context, token=None, readonly=True)
