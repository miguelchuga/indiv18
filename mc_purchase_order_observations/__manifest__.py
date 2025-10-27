# -*- coding: utf-8 -*-

{
    'name': 'Agregar campo Observaciones a Purchase Order.',
    'version': '2.0.0',
    'author': 'MC-Sistemas',
    'summary': 'Agregar campo Observaciones a Órdenes de Compra.',
    'description' : """
========================
- Odoo para Guatemala
========================
    """,
    'website': 'http://mcsistemas.net',
    'category': 'Purchase',
    'depends': ["purchase"],
    'data': [
        'views/purchase_order_view.xml'
    ],
    'installable': True,
    'application': True,
    'auto_install': False
}