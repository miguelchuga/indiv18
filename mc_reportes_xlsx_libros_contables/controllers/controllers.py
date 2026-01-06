# -*- coding: utf-8 -*-
from odoo import http

# class McReportesXlsxLibrosContables(http.Controller):
#     @http.route('/mc_reportes_xlsx_libros_contables/mc_reportes_xlsx_libros_contables/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/mc_reportes_xlsx_libros_contables/mc_reportes_xlsx_libros_contables/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('mc_reportes_xlsx_libros_contables.listing', {
#             'root': '/mc_reportes_xlsx_libros_contables/mc_reportes_xlsx_libros_contables',
#             'objects': http.request.env['mc_reportes_xlsx_libros_contables.mc_reportes_xlsx_libros_contables'].search([]),
#         })

#     @http.route('/mc_reportes_xlsx_libros_contables/mc_reportes_xlsx_libros_contables/objects/<model("mc_reportes_xlsx_libros_contables.mc_reportes_xlsx_libros_contables"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('mc_reportes_xlsx_libros_contables.object', {
#             'object': obj
#         })