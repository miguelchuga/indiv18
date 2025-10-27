# -*- encoding: utf-8 -*-

{
    'name' : 'Liquidaciones',
    'version' : '1.0',
    'category': 'Custom',
    'description': """Manejo de cajas chicas y liquidaciones version 2""",
    'author': '',
    'website': '',
    'depends' : [ 'account','account_accountant' ],
    'data' : [
        'views/liquidacion_view.xml',
        'views/anticipos_view.xml',
        'views/invoice_view.xml',
        'views/payment_view.xml',
        'security/ir.model.access.csv',
        'security/liquidaciones_security.xml',
        'wizard/asignar_view.xml',
    ],
    'installable': True,
    'certificate': '',
}
