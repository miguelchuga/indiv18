# -*- coding: utf-8 -*-
# from odoo import http


# class LibroVentas(http.Controller):
#     @http.route('/libro_ventas/libro_ventas/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/libro_ventas/libro_ventas/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('libro_ventas.listing', {
#             'root': '/libro_ventas/libro_ventas',
#             'objects': http.request.env['libro_ventas.libro_ventas'].search([]),
#         })

#     @http.route('/libro_ventas/libro_ventas/objects/<model("libro_ventas.libro_ventas"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('libro_ventas.object', {
#             'object': obj
#         })
