# -*- encoding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from . import util
from odoo.tools.sql import column_exists, create_column
from odoo.tools import (
    create_index,
    date_utils,
    float_compare,
    float_is_zero,
    float_repr,
    format_amount,
    format_date,
    formatLang,
    frozendict,
    get_lang,
    groupby,
    index_exists,
    OrderedSet,
    SQL,
)


class account_move(models.Model):
    _name = 'account.move'
    _inherit = 'account.move'

    @api.depends('company_id', 'invoice_filter_type_domain')
    def _compute_suitable_journal_ids(self):
        for m in self:
            journal_type = m.invoice_filter_type_domain or 'general'
            company = m.company_id or self.env.company
            #SE AGREGA ESTO PARA QUE SE PUEDAN SELECCIONAR TODOS LOS DIARIOS EN LOS ASIENTOS CONTABLES
            if journal_type == 'general':
                m.suitable_journal_ids = self.env['account.journal'].search([
                    *self.env['account.journal']._check_company_domain(company)
                ])
            else:
                m.suitable_journal_ids = self.env['account.journal'].search([
                    *self.env['account.journal']._check_company_domain(company),
                    ('type', '=', journal_type),
                ])


    @api.onchange('state')
    def _onchange_line_ids_letras(self):
        self.numeros_a_letras_moneda = util.num_a_letras_factura(self.amount_total, self.currency_id.name)

    @api.depends('amount_total')
    def _calcular_dos_decinales(self):
        for rec in self:
            rec.x_price_total_2decimal = rec.currency_id.symbol+' '+format(rec.amount_total, ',.2f')

    #este total pone el valor en monedas en positivo.
    @api.depends('amount_residual','state')
    def _calcular_amount_total_signed(self):
        for rec in self:
            _total = 0
            for line in rec.line_ids:
                _total += abs(line.debit)
            rec.x_amount_total_signed = _total

    serie_gt = fields.Char('Serie de la factura', size=40)
    documento_gt = fields.Char('Numero de Documento', size=60)
    numeros_a_letras_moneda = fields.Char('Letras con moneda',)
    x_price_total_2decimal = fields.Char('Total 2decimales', compute=_calcular_dos_decinales, copy=False, store=True)
    reversed_entry_id = fields.Many2one(comodel_name='account.move', string="Rectificativa", copy=False)
    x_amount_total_signed = fields.Monetary('Total signed ABS', compute=_calcular_amount_total_signed, copy=False, store=True,currency_field='company_currency_id')

    #esto hace que se pueda poner en borrador un asiento por diferencial cambiaro
    #pero el problema es que despues no se puede adjuntar este asiento a la factura y queda en cxc
    def _check_draftable_odoo18(self):
        exchange_move_ids = set()
        if self:
            self.env['account.full.reconcile'].flush_model(['exchange_move_id'])
            self.env['account.partial.reconcile'].flush_model(['exchange_move_id'])
            sql = SQL(
                """
                    SELECT DISTINCT sub.exchange_move_id
                    FROM (
                        SELECT exchange_move_id
                        FROM account_full_reconcile
                        WHERE exchange_move_id IN %s

                        UNION ALL

                        SELECT exchange_move_id
                        FROM account_partial_reconcile
                        WHERE exchange_move_id IN %s
                    ) AS sub
                """,
                tuple(self.ids), tuple(self.ids),
            )
            exchange_move_ids = {id_ for id_, in self.env.execute_query(sql)}

        for move in self:
#            if move.id in exchange_move_ids:
#                raise UserError(_('You cannot reset to draft an exchange difference journal entry.'))
            if move.tax_cash_basis_rec_id or move.tax_cash_basis_origin_move_id:
                # If the reconciliation was undone, move.tax_cash_basis_rec_id will be empty;
                # but we still don't want to allow setting the caba entry to draft
                # (it'll have been reversed automatically, so no manual intervention is required),
                # so we also check tax_cash_basis_origin_move_id, which stays unchanged
                # (we need both, as tax_cash_basis_origin_move_id did not exist in older versions).
                raise UserError(_('You cannot reset to draft a tax cash basis journal entry.'))
            if move.inalterable_hash:
                raise UserError(_('You cannot reset to draft a locked journal entry.'))

class account_invoice_line(models.Model):
    _name = 'account.move.line'
    _inherit = 'account.move.line'



    @api.depends('quantity', 'price_unit')
    def _n_total_linea(self):
        for line in self:
            line.n_total_linea = line.quantity * line.price_unit

    @api.depends('discount', 'price_unit')
    def _unitario_descuento(self):
        for line in self:
            line.x_unitario_con_descuento  =line.price_unit-(line.price_unit*line.discount/100)


    @api.depends('price_total')
    def _calcular_dos_decinales(self):
        for rec in self:
            rec.x_price_total_2decimal = rec.currency_id.symbol+' '+format(rec.price_total, ',.2f')


    analitica_id = fields.Char('lista analitica',compute='_compute_analitica', store=True, readonly=True,)
    n_total_linea = fields.Float('Total linea', )
    x_unitario_con_descuento = fields.Float('Unit/Descuento', )
    x_price_total_2decimal = fields.Char('Total 2decimales', )
 

    @api.depends('analytic_distribution')
    def _compute_analitica(self):
        for line in self:
            if line.analytic_distribution:
                idx= next(iter(line.analytic_distribution.keys()))
                if idx:
                    analitic_id = self.env["account.analytic.account"].search([('id','=',idx )])
                    line.analitica_id = analitic_id.name
                else:
                    line.analitica_id = ''                
            else:
                line.analitica_id = ''
            print(line)
 

    def _trae_lista(self,):
        _list = ''
        if self.analytic_distribution:
            _list = list(self.analytic_distribution.keys())
        return _list

  