#!/usr/bin/python
# -*- coding: utf-8 -*-
import re

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.tools.safe_eval import safe_eval


from odoo.exceptions import ValidationError
from odoo.tools.safe_eval import safe_eval

EGEX_FORMULA_OBJECT = re.compile(r'((?:product\[\')(?P<field>\w+)(?:\'\]))+')

FORMULA_ALLOWED_TOKENS = {
    '(', ')',
    '+', '-', '*', '/', ',', '<', '>', '<=', '>=',
    'and', 'or', 'None',
    'base', 'quantity', 'price_unit',
    'min', 'max',
}


class AccountTax(models.Model):
    _inherit = 'account.tax'

    tipo_impuesto = fields.Selection([('idp', 'IDP'), ('prensa', 'Timbre prensa'),
                                      ('municipal', 'Tasa municipal'), ('inguat', 'Inguat'),
                                      ('retisr', 'Retensión isr'), ('retiva', 'Retensión IVA'), ('iva', 'IVA')],
                                     'Tipo impuesto ')
    impuesto_total = fields.Boolean('Aplica al total ')
    regimen_simplificado = fields.Boolean('Regimen simplificado ')
    renta_imponible_mensual = fields.Float(
        string='Renta imponible mensual ',
    )
    importe_fijo = fields.Float(
        string='Importe fijo ',
    )
    
     # -------------------------------------------------------------------------
    # GENERIC REPRESENTATION OF BUSINESS OBJECTS & METHODS
    # -------------------------------------------------------------------------

    @api.model
    def _get_base_line_field_value_from_record(self, record, field, extra_values, fallback, from_base_line=False):
        """ Helper to extract a default value for a record or something looking like a record.

        Suppose field is 'product_id' and fallback is 'self.env['product.product']'

        if record is an account.move.line, the returned product_id will be `record.product_id._origin`.
        if record is a dict, the returned product_id will be `record.get('product_id', fallback)`.

        :param record:          A record or a dict or a falsy value.
        :param field:           The name of the field to extract.
        :param extra_values:    The extra kwargs passed in addition of 'record'.
        :param fallback:        The value to return if not found in record or extra_values.
        :param from_base_line:  Indicate if the value has to be retrieved automatically from the base_line and not the record.
                                False by default.
        :return:                The field value corresponding to 'field'.
        """
        need_origin = isinstance(fallback, models.Model)
        if field in extra_values:
            value = extra_values[field] or fallback
        elif isinstance(record, models.Model) and field in record._fields and not from_base_line:
            value = record[field]
        elif isinstance(record, dict):
            value = record.get(field, fallback)
        else:
            value = fallback
        if need_origin:
            value = value._origin

        if field == 'id' and record:
            if record._description == 'Journal Item':
                rate = record.currency_rate
                record.env.context = dict(self.env.context)
                record.env.context.update({
                   'x_rate': rate,
                   'x_price_unit':record.price_unit,
                   'x_quantity':record.quantity
                })

        return value


    # -------------------------------------------------------------------------
    # GENERIC REPRESENTATION OF BUSINESS OBJECTS & METHODS
    # -------------------------------------------------------------------------

    @api.model
    def _get_base_line_field_value_from_record_OLD(self, record, field, extra_values, fallback):
        """ Helper to extract a default value for a record or something looking like a record.

        Suppose field is 'product_id' and fallback is 'self.env['product.product']'

        if record is an account.move.line, the returned product_id will be `record.product_id._origin`.
        if record is a dict, the returned product_id will be `record.get('product_id', fallback)`.

        :param record:          A record or a dict or a falsy value.
        :param field:           The name of the field to extract.
        :param extra_values:    The extra kwargs passed in addition of 'record'.
        :param fallback:        The value to return if not found in record or extra_values.
        :return:                The field value corresponding to 'field'.
        """
        rate = 0.00
        need_origin = isinstance(fallback, models.Model)
        if field in extra_values:
            value = extra_values[field] or fallback
        elif isinstance(record, models.Model) and field in record._fields:
            value = record[field]
        elif isinstance(record, dict):
            value = record.get(field, fallback)
        else:
            value = fallback
        if need_origin:
            value = value._origin
        if field == 'id' and record:
            if record._description == 'Journal Item':
                rate = record.currency_rate
                record.env.context = dict(self.env.context)
                record.env.context.update({
                   'x_rate': rate,
                   'x_price_unit':record.price_unit,
                   'x_quantity':record.quantity
                })
        return value



    @api.depends('formula')
    def _compute_formula_decoded_info(self):
        for tax in self:
            if tax.amount_type != 'code':
                tax.formula_decoded_info = None
                continue
 
            formula = (tax.formula or '0.0').strip()

            if tax.amount_type == 'code' and tax.regimen_simplificado:
                ctx = dict(tax.env.context)
                if 'x_rate' in ctx:
                    x_rate = tax.env.context.get('x_rate')
                    renta_imponible_mensual = tax.renta_imponible_mensual * x_rate  
                    importe_fijo = tax.importe_fijo * x_rate
                    renta_imponible_mensual = format(renta_imponible_mensual, '.2f')
                    importe_fijo = format(importe_fijo, '.2f')
                    formula = formula.replace("x", renta_imponible_mensual)
                    formula = formula.replace("z", importe_fijo)
                    formula = (formula or '0.0').strip()
 
            formula_decoded_info = {
                'js_formula': formula,
                'py_formula': formula,
            }
            product_fields = set()

            groups = re.findall(r'((?:product\.)(?P<field>\w+))+', formula) or []
            Product = self.env['product.product']
            for group in groups:
                field_name = group[1]
                if field_name in Product and not Product._fields[field_name].relational:
                    product_fields.add(field_name)
                    formula_decoded_info['py_formula'] = formula_decoded_info['py_formula'].replace(f"product.{field_name}", f"product['{field_name}']")

            formula_decoded_info['product_fields'] = list(product_fields)
            tax.formula_decoded_info = formula_decoded_info


    def _check_formula(self):
        """ Check the formula is passing the minimum check to ensure the compatibility between both evaluation
        in python & javascript.
        """
        self.ensure_one()

        def get_number_size(formula, i):
            starting_i = i
            seen_separator = False
            while i < len(formula):
                if formula[i].isnumeric():
                    i += 1
                elif formula[i] == '.' and (i - starting_i) > 0 and not seen_separator:
                    i += 1
                    seen_separator = True
                else:
                    break
            return i - starting_i

        formula_decoded_info = self.formula_decoded_info
        allowed_tokens = FORMULA_ALLOWED_TOKENS.union(f"product['{field_name}']" for field_name in formula_decoded_info['product_fields'])
        formula = formula_decoded_info['py_formula']

        i = 0
        while i < len(formula):

            if formula[i] == ' ':
                i += 1
                continue

            continue_needed = False
            for token in allowed_tokens:
                if formula[i:i + len(token)] == token:
                    i += len(token)
                    continue_needed = True
                    break
            if continue_needed:
                continue

            number_size = get_number_size(formula, i)
            if number_size > 0:
                i += number_size
                continue

            #PARA QUE NO VALIDE EL IMPUESTO ISR LOCALIZACION GUATEMALA
            if self.amount_type == 'code' and self.regimen_simplificado:
                break
            raise ValidationError(_("Malformed formula '%(formula)s' at position %(position)s", formula=formula, position=i))

    @api.model
    def _eval_tax_amount_formula(self, raw_base, evaluation_context):
        """ Evaluate the formula of the tax passed as parameter.

        [!] Mirror of the same method in account_tax.js.
        PLZ KEEP BOTH METHODS CONSISTENT WITH EACH OTHERS.

        :param tax_data:          The values of a tax returned by '_prepare_taxes_computation'.
        :param evaluation_context:  The context created by '_eval_taxes_computation_prepare_context'.
        :return:                    The tax base amount.
        """
        self._check_formula()

        # Safe eval.
        formula_context = {
            'price_unit': evaluation_context['price_unit'],
            'quantity': evaluation_context['quantity'],
            'product': evaluation_context['product'],
            'base': raw_base,
            'min': min,
            'max': max,
        }
        try:
            ctx = dict(self.env.context)
            formula = self.formula_decoded_info['py_formula']            
            if not 'x_rate' in ctx:
                formula = formula.replace("x", '1')
                formula = formula.replace("z", '1')
            
            return safe_eval(
                formula,
                globals_dict=formula_context,
                locals_dict={},
                locals_builtins=False,
                nocopy=True,
            )
        except ZeroDivisionError:
            return 0.0
