# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2012-TODAY Acespritech Solutions Pvt Ltd
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
{
    'name': 'Genera libro de compras para Guatemala, Mc-Sistemas, Junio 2020',
    'version': '1.0',
    'category': 'Accounting',
    'description': """Genera Libro de comrpas para Guatemala por Mc-Sistemas""",
    'summary': 'Desarrollo especial. Mc-Sistemas,s.a.',
    'license': "AGPL-3",
    'author': 'Mc-sistemas, S.A.',
    'website': 'http://mc-sistemas.net',
    'depends': ['base', 'account','web','libro_compras'],

    'price': 30,
    'currency': 'GTQ',
    'data': [
        'data/parameters.xml',
        'views/mc_libro_compras_view.xml'
    ],
    'images': ['static/description/main_screenshot.png'],
    'installable': True,
    'auto_install': False,
}
 
