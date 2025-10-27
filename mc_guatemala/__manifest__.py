# -*- coding: utf-8 -*-

{
    'name': 'Extra para localizacion Guatemala - MC-Sistemas-sbg',
    'version': '2.0.0',
    'license': "AGPL-3",
    'author': 'MC-Sistemas',
    'summary': 'Datos extras para la localizacion de Guatemala para Mc-Sistemas, S.A. ',
    'description' : """
========================
- Odoo para Guatemala
========================
    """,
    'website': 'http://mcsistemas.net',
    'category': 'Accounting & Finance',
    'depends': ["base",
                "sale",
                "account",
                'purchase',
                'account_tax_python',
    ],
    'data': [
       # 'views/account_account_view.xml',
        'views/res_partner_view.xml',
        'views/account_tax_view.xml',
        'views/account_journal_view.xml',
        'views/account_payment_view.xml',
        'views/account_payment_transferencia_view.xml',        
        #'views/account_payment_tipo_cambio_view.xml',
        'views/account_move_view.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
