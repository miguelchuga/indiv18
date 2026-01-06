# -*- coding: utf-8 -*-
from odoo import http

# class ReporteLibroMayor(http.Controller):
#     @http.route('/reporte_libro_mayor/reporte_libro_mayor/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/reporte_libro_mayor/reporte_libro_mayor/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('reporte_libro_mayor.listing', {
#             'root': '/reporte_libro_mayor/reporte_libro_mayor',
#             'objects': http.request.env['reporte_libro_mayor.reporte_libro_mayor'].search([]),
#         })

#     @http.route('/reporte_libro_mayor/reporte_libro_mayor/objects/<model("reporte_libro_mayor.reporte_libro_mayor"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('reporte_libro_mayor.object', {
#             'object': obj
#         })