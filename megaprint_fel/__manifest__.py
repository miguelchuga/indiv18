# -*- coding: utf-8 -*-
{
    'name': "Megaprint / INFILE para  FEL ",
    'summary': """
        Generación de Factura Electrónica en Línea (FEL) de Megaprint
    """,
    'description': """
        Conexión a servicios de Megaprint para generación de Factura Electrónica en Línea (FEL)
    """,
    'license': "AGPL-3",
    'author': "Mc-sistemas",
    'website': "",
    'category': 'Sales',
    'sequence': 20,
    'version': '0.1',
    'depends': ['base','base_setup','account','stock'],
    'data': [
        "data/parameters.xml",
#        "security/ir.model.access.csv",
        'views/mpfel_settings.xml',
        'views/account_tax.xml',
        'views/account_journal.xml',
        'views/account_invoice.xml',
    ],
    'installable': True,
    'auto_install': False,
}
