# -*- coding: utf-8 -*-

from odoo import models, fields, api

class SaleOrdeLine(models.Model):
    _inherit = 'sale.order.line'

    markup = fields.Float('Markup',digits=(12,4))
    change_price_unit = fields.Boolean('Change PRice Unit', default=False)
    change_markup = fields.Boolean('Change Markup', default=False)
    # standard_price = fields.Float('Coste', related='product_id.standard_price',store=True)
    standard_price = fields.Float('Coste con Iva')
    
    @api.onchange('product_id')
    def _onchange_standard_price(self):

        if self.product_id:

            porcentaje = self.env['account.tax'].search([('tipo_impuesto','=','iva'),('description','=','IVA por Cobrar'),('type_tax_use','=','purchase'),('company_id','=',self.env.company.id)]).amount
            iva_decimal = porcentaje/100
            iva = self.product_id.standard_price * iva_decimal
            costo_con_iva = self.product_id.standard_price + iva
            costo_con_iva = round(costo_con_iva,5)
            self.standard_price = costo_con_iva


    @api.onchange('markup')
    def _onchange_markup(self):

        if self.product_id and self.markup:
        
            if self.change_price_unit:
                self.change_price_unit == False
            else:

                coste_ini = self.product_id.standard_price
                porcentaje = self.env['account.tax'].search([('tipo_impuesto','=','iva'),('description','=','IVA por Cobrar'),('type_tax_use','=','purchase'),('company_id','=',self.env.company.id)]).amount
                iva_decimal = porcentaje/100
                iva = self.product_id.standard_price * iva_decimal
                costo_con_iva = self.product_id.standard_price + iva
                coste = round(costo_con_iva,5)
                self.price_unit = 0 if coste_ini == None else coste/self.markup
                self.change_markup = True


    @api.onchange('price_unit')
    def _onchange_price_unit(self):

        if self.product_id and self.price_unit:

            if self.change_markup:
                self.change_markup = False
            else:

                coste_ini = self.product_id.standard_price
                porcentaje = self.env['account.tax'].search([('tipo_impuesto','=','iva'),('description','=','IVA por Cobrar'),('type_tax_use','=','purchase'),('company_id','=',self.env.company.id)]).amount
                iva_decimal = porcentaje/100
                iva = self.product_id.standard_price * iva_decimal
                costo_con_iva = self.product_id.standard_price + iva
                coste = round(costo_con_iva,5)
        
                self.markup = 0 if coste_ini == None else (coste/self.price_unit)
                self.change_price_unit = True

            