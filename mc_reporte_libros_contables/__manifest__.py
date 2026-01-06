# -*- coding: utf-8 -*-
{
    'name': "Reporte Libros Contables",
    'summary': " Generación de reporte libros Contables Mayor y Diario.",
    'description': "Generación de reporte libros Contables Mayor y Diario.",
    'license': "AGPL-3",
    'author': "MC-Sistemas",
    'website': "http://",
    'category': 'Reporte',
    'version': '0.1',
    'depends': ['base','account', 'web'],
    'data': [
        'security/ir.model.access.csv',
        'views/libro_mayor.xml',
        'views/libro_diario.xml',
        'views/journal_view.xml',
    ],
    'installable': True,
    'auto_install': True,
}
