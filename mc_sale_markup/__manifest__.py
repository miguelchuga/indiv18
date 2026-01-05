# -*- coding: utf-8 -*-
{
    'name': "Sale - Markup",
    'summary': """Campo Markup que se utiliza para determinar ganancia de venta por producto""",
    'description': """Campo Markup que se utiliza para determinar ganancia de venta por producto""",
    'author': "Erik Yol",
    'website': "http://",
    'category': 'Sale',
    'license': "AGPL-3",
    'version': '0.1',
    'depends': ['base','sale'],
    'data': [
        'security/ir.model.access.csv',
        'views/sale.xml',
        'report/sale_report_templates.xml',
        'report/sale_report.xml',
        'report/export_order_xls.xml',
    ],
    "external_dependencies": {
        "python": [
            "openpyxl",
        ],
    },
    'installable': True,    
    'auto_install': True,
    'application': False
}
