# -*- coding: utf-8 -*-

{
    'name': 'Templates Libros Contables',
    'description': 'Genera libros fiscales para guatemala',
    'summary': 'Contiene los libros foliados',
    'category': 'All',
    'version': '1.0',
    'website': 'http://mcsistemas.odoo.com',
    "license": "AGPL-3",
    'author': 'MC',
    'depends': [
        'report_extend_bf',
#       'mc_reporte_libros_contables',
        "sale",
        "sale_management",
        "mc_libro_compras",
        "mc_libro_ventas",
#       "mc_reporte_libros_contables",
    ],
    'data': [
        'data/templates.xml',
        'report.xml',
    ],
    'images': [],
    'application': True,
}
