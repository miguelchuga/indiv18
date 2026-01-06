# -*- coding: utf-8 -*-
{
    'name': "Reportes Contables-Excel",
    'summary': "Generacion de Reportes en Excel de Libros contables Diario y Mayor",
    'description': "Generacion de Reportes en Excel de Libros contables Diario y Mayor",
    'license': "AGPL-3",
    'author': "Erik Yol",
    'website': "MCSistemas",
    'category': 'Reports',
    'version': '0.1',
    'depends': ['base','account','report_xlsx','mc_reporte_libros_contables'],
    'data': [
        # 'security/ir.model.access.csv',
        'views/report_menu.xml',
    ],
    'images': ['static/description/banner.png'],    
    'installable': True,
    'auto_install': True,
}
