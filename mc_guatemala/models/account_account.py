#!/usr/bin/python
# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError

class AccountAccount(models.Model):
    _inherit = 'account.account'
    
    cambia_en_pagos = fields.Boolean('Cambia en pagos ')

 
class AccountAccount(models.Model):
    _inherit = 'account.analytic.account'
    


    @api.depends('name')
    def _calcular_nombre(self):
        for rec in self:
            rec.nombre =  rec.name #query_line['name'],

#            sql = ''' Select id,name ->> 'es_GT'::text AS name from account_analytic_account where id = %s''' 
#            self.env.cr.execute(sql, (rec.ids[0],))
#            for query_line in self.env.cr.dictfetchall():
#                rec.nombre =  rec.name #query_line['name'],
#                print(rec)

    nombre = fields.Char('Nombre cuenta ',compute=_calcular_nombre, copy=False, store=True)

 