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

from odoo import fields, models, api, _
from odoo.osv.expression import get_unaccent_wrapper

class res_partner(models.Model):

    _inherit = 'res.partner'

    x_codigo_interno = fields.Char('Código Interno')
#    x_nombre_comercial = fields.Char('Nombre Comercial')
    x_dpi = fields.Char('DPI')
    x_pasaporte = fields.Char('Pasaporte')
#    x_contacto_directo = fields.Char('Contacto Directo')
#    x_gira = fields.Char('Gira')
#    x_calificacion = fields.Char('Calificación')
#    x_codigo_vendedor = fields.Char('Código Vendedor')
#    x_fecha_nacimiento = fields.Date(string='Fecha Nacimiento', copy=False)
    cuentas_pagos_ids = fields.One2many('mc_guatemala.cuentas_pagos','partner_id', string='Detalle')


    @api.model
    def name_search14(self, name, args=None, operator='ilike', limit=100):

        if args is None:
            args = []
        if name and operator in ('=', 'ilike', '=ilike', 'like', '=like'):
            self.check_access_rights('read')
            where_query = self._where_calc(args)
            self._apply_ir_rules(where_query, 'read')
            from_clause, where_clause, where_clause_params = where_query.get_sql()
            where_str = where_clause and (" WHERE %s AND " % where_clause) or ' WHERE '

            # search on the name of the contacts and of its company
            search_name = name
            if operator in ('ilike', 'like'):
                search_name = '%%%s%%' % name
            if operator in ('=ilike', '=like'):
                operator = operator[1:]

            unaccent = get_unaccent_wrapper(self.env.cr)

            query = """SELECT id
                         FROM res_partner
                      {where} ( {name} {operator} {percent})
                           OR ({ref} {operator} {percent})
                           OR ({vat} {operator} {percent})
                           -- don't panic, trust postgres bitmap
                     ORDER BY {name} {operator} {percent} desc,
                              {name}
                    """.format(where=where_str,
                               operator=operator,

                               display_name=unaccent('display_name'),
                               reference=unaccent('ref'),
                               vat=unaccent('vat'),
                               percent=unaccent('%s'))

            where_clause_params += [search_name]*4
            if limit:
                query += ' limit %s'
                where_clause_params.append(limit)
            self.env.cr.execute(query, where_clause_params)
            partner_ids = map(lambda x: x[0], self.env.cr.fetchall())

            if partner_ids:
                return self.browse(partner_ids).name_get()
            else:
                return []
        return super(res_partner, self).name_search(name, args, operator=operator, limit=limit)
    



class MCcuentasPagos(models.Model):
    
    _name = "mc_guatemala.cuentas_pagos"
    _description = "Cuentas para un cliente en pagos"

    name = fields.Text(string='Descripción', required=True)
    partner_id = fields.Many2one('res.partner', string='Cliente/proveedor', )
    account_id  = fields.Many2one('account.account', string='Cuenta',)
    payment_type = fields.Selection([
        ('outbound', 'Send'),
        ('inbound', 'Receive'),
    ], string='Tipo Pago', default='inbound', required=True,)

