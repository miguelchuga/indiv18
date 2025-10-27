# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from . import util



#class POSConfig(models.Model):
#    _inherit = "pos.config"

#    x_analytic_id = fields.Many2one('account.analytic.account', string='Cuenta analítica ', index=True)


class mpfel_AccountMoveReversal(models.TransientModel):
    _inherit = 'account.move.reversal'


    def reverse_moves_16(self):
        self.ensure_one()
        moves = self.move_ids

        # Create default values.
        default_values_list = []
        for move in moves:
            default_values_list.append(self._prepare_default_reversal(move))

        batches = [
            [self.env['account.move'], [], True],   # Moves to be cancelled by the reverses.
            [self.env['account.move'], [], False],  # Others.
        ]
        for move, default_vals in zip(moves, default_values_list):
            is_auto_post = default_vals.get('auto_post') != 'no'
            is_cancel_needed = not is_auto_post and self.refund_method in ('cancel', 'modify')
            batch_index = 0 if is_cancel_needed else 1
            batches[batch_index][0] |= move
            batches[batch_index][1].append(default_vals)

        # Handle reverse method.
        moves_to_redirect = self.env['account.move']
        for moves, default_values_list, is_cancel_needed in batches:
            new_moves = moves._reverse_moves(default_values_list, cancel=is_cancel_needed)

            if self.refund_method == 'modify':
                moves_vals_list = []
                for move in moves.with_context(include_business_fields=True):
                    moves_vals_list.append(move.copy_data({'date': self.date if self.date_mode == 'custom' else move.date})[0])
                new_moves = self.env['account.move'].create(moves_vals_list)

            moves_to_redirect |= new_moves

        self.new_move_ids = moves_to_redirect

        if moves_to_redirect and self.move_ids:
            if len(moves_to_redirect) == 1 and len(self.move_ids) == 1:
                moves_to_redirect.write({
                    'mpfel_sat_uuid_ncre': self.move_ids.id,
                    'journal_id': self.journal_id.id,
                })

        # Create action.
        action = {
            'name': _('Reverse Moves'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
        }
        if len(moves_to_redirect) == 1:
            action.update({
                'view_mode': 'form',
                'res_id': moves_to_redirect.id,
                'context': {'default_move_type':  moves_to_redirect.move_type},
            })
        else:
            action.update({
                'view_mode': 'tree,form',
                'domain': [('id', 'in', moves_to_redirect.ids)],
            })
            if len(set(moves_to_redirect.mapped('move_type'))) == 1:
                action['context'] = {'default_move_type':  moves_to_redirect.mapped('move_type').pop()}
        return action


class mpfel_account_invoice(models.Model):
    _name = "account.move"
    _inherit = "account.move"


    mpfel_manual = fields.Boolean(string='Check para FEL manual FEL', default=False,
                              help='Al tener esto marcado se realiza el proceso manual de FEL', copy=False)

    serie_gt = fields.Char('Serie de la factura', size=40, copy=False)
    mpfel_file_name = fields.Char('Nombre del archivo',readonly=True, copy=False)
    mpfel_pdf = fields.Binary(string='PDF Factura',readonly=True, copy=False)

    mpfel_serial = fields.Char('Serial Document', copy=False)
    mpfel_number = fields.Char('FEL Number', copy=False)
    date_sign = fields.Char('Fecha y hora emisión', copy=False)

    gface_dte_serial = fields.Char('Serie DTE', copy=False)
    gface_dte_number = fields.Char('Número DTE', copy=False)

    mpfel_uuid = fields.Char('Document UUID', copy=False)
    mpfel_sat_uuid = fields.Char('SAT UUID', copy=False,tracking=True)  

    mpfel_source_xml = fields.Text('Source XML', copy=False)
    mpfel_signed_xml = fields.Text('Signed XML', copy=False)
    mpfel_result_xml = fields.Text('Result XML', copy=False)
    mpfel_void_uuid = fields.Char('Void document UUID', copy=False,tracking=True)
    mpfel_void_sat_uuid = fields.Char('Void SAT UUID', copy=False)
    mpfel_void_source_xml = fields.Text('Void source XML', copy=False)
    mpfel_void_signed_xml = fields.Text('Void signed XML', copy=False)
    mpfel_void_result_xml = fields.Text('Void result XML', copy=False)
    mpfel_sign_date = fields.Char('Sign date', copy=False)
    x_orden  = fields.Char('No. OrdeN', copy=False)
    x_notas  = fields.Char('Notas', copy=False)

    # EXPORTACION
    x_incoterms_id = fields.Many2one('account.incoterms', 'Incoterms')
    x_nombreconsignatario = fields.Char('Congnatario', copy=False)
    x_direccionconsignatario = fields.Char('Dirección Congnatario', copy=False)
    x_codigoconsignatario = fields.Char('Código congnatario', copy=False)
    x_nombrecomprador = fields.Char('Nombre comprador', copy=False)
    x_direccioncomprador = fields.Char('Dirección comprador', copy=False)
    x_codigocomprador = fields.Char('Código comprador', copy=False)
    x_otrareferencia = fields.Char('Otra referencia', copy=False)
    x_nombreexportador = fields.Char('Nombre del exportador', copy=False)
    x_codigoexportador = fields.Char('Código del exportador', copy=False,compute='_calcular_exportador',inverse='_inverse_calcular_exportador', store=True)

    x_nit_generico = fields.Char(string='Nit genérico	 ?')
    x_nombre_generico = fields.Char(string='Nombre genérico	 ?')
    numeros_a_letras_fel = fields.Char('Total letras FEL')

    x_exento_total = fields.Float(string='Exento total', copy=False)
    x_gravado_total = fields.Float(string='Gravado total', copy=False)
    

 

    def _constrains_date_sequence(self):
        # Make it possible to bypass the constraint to allow edition of already messed up documents.
        # /!\ Do not use this to completely disable the constraint as it will make this mixin unreliable.
        constraint_date = fields.Date.to_date(self.env['ir.config_parameter'].sudo().get_param(
            'sequence.mixin.constraint_start_date',
            '1970-01-01'
        ))
        for record in self:
            date = fields.Date.to_date(record[record._sequence_date_field])
            sequence = record[record._sequence_field]
            if sequence and date and date > constraint_date and not self.journal_id.mpfel_type:
                format_values = record._get_sequence_format_param(sequence)[1]
#                if (
#                    format_values['year'] and format_values['year'] != date.year % 10**len(str(format_values['year']))
#                    or format_values['month'] and format_values['month'] != date.month
#                ):
#                    raise ValidationError(_(
#                        "The %(date_field)s (%(date)s) doesn't match the %(sequence_field)s (%(sequence)s).\n"
#                        "You might want to clear the field %(sequence_field)s before proceeding with the change of the date.",
#                        date=format_date(self.env, date),
#                        sequence=sequence,
#                        date_field=record._fields[record._sequence_date_field]._description_string(self.env),
#                        sequence_field=record._fields[record._sequence_field]._description_string(self.env),
#                    ))

    @api.depends('partner_id','company_id','journal_id')
    def _inverse_calcular_exportador(self):
        for record in self:
            if record.journal_id.mpfel_exportacion :
                record.x_nombreexportador = record.company_id.name
                record.x_codigoexportador = record.company_id.vat
                record.x_nombreconsignatario = record.partner_id.name
                record.x_direccionconsignatario = record.partner_id.street
                record.x_codigoconsignatario = record.partner_id.x_id_extrangero
                record.x_nombrecomprador = record.partner_id.name
                record.x_direccioncomprador = record.partner_id.street
                record.x_codigocomprador = record.partner_id.x_id_extrangero

    @api.depends('partner_id','company_id','journal_id')
    def _calcular_exportador(self):
        for record in self:
            if record.journal_id.mpfel_exportacion :
                record.x_nombreexportador = record.company_id.name
                record.x_codigoexportador = record.company_id.vat
                record.x_nombreconsignatario = record.partner_id.name
                record.x_direccionconsignatario = record.partner_id.street
                record.x_codigoconsignatario = record.partner_id.x_id_extrangero
                record.x_nombrecomprador = record.partner_id.name
                record.x_direccioncomprador = record.partner_id.street
                record.x_codigocomprador = record.partner_id.x_id_extrangero


    def action_post(self):

        used_fields = ('state', 'mpfel_uuid', 'mpfel_signed_xml', 'mpfel_source_xml')
        self.env["account.move"].flush_model(used_fields)
        #self.env['account.move'].flush(['state', 'mpfel_uuid', 'mpfel_signed_xml', 'mpfel_source_xml'])
        for record in self:
            if record.move_type == 'out_invoice' or record.move_type == 'out_refund' or record.move_type == 'in_invoice' and record.journal_id.mpfel_type:
                settings = record.env['mpfel.settings'].search([('company_id', '=', record.company_id.id)])
                if settings:
                    if not record.mpfel_result_xml:
                        record.x_exento_total = 0
                        record.x_gravado_total = 0
                        if record.move_type == 'out_invoice' or record.move_type == 'out_refund' or record.move_type == 'in_invoice' and record.journal_id.mpfel_type:
                            lines_gravado_ids = record.invoice_line_ids.filtered(lambda m: m.tax_ids )
                            lines_exento_ids = record.invoice_line_ids.filtered(lambda m: not m.tax_ids )
                            record.x_gravado_total   = sum(lines_gravado_ids.mapped('price_total'))
                            record.x_exento_total  = sum(lines_exento_ids.mapped('price_total'))

                        settings.sign_document(record)
                else:
                    raise UserError(_('Megaprint FEL settings not found'))
            super(mpfel_account_invoice, self).action_post()
            if not record.mpfel_manual and not record.mpfel_result_xml and record.state =='posted':
                record.mpfel_firmar_documento()
                record.mpfel_registrar_documento()
        return


    def mpfel_firmar_documento(self):
#        self.env['account.move'].flush(['state', 'mpfel_uuid', 'mpfel_signed_xml'])
        for record in self:
            if record.move_type == 'out_invoice' or record.move_type == 'out_refund' or record.move_type == 'in_invoice':
                settings = record.env['mpfel.settings'].search([('company_id','=',record.company_id.id)])
                if settings and record.journal_id.mpfel_type:
                    if record.mpfel_uuid or record.mpfel_source_xml:
                        settings.firmar_documento(record)
                    else:
                        raise UserError(_('Documento no tiene source xml...'))
                return True


    def mpfel_registrar_documento(self):
#16        self.env['account.move'].flush(['state', 'mpfel_uuid', 'mpfel_signed_xml'])
        for record in self:
            if record.move_type == 'out_invoice' or record.move_type == 'out_refund' or record.move_type == 'in_invoice':
                settings = record.env['mpfel.settings'].search([('company_id','=',record.company_id.id)])
                if settings and record.journal_id.mpfel_type:
                    if record.mpfel_uuid and record.mpfel_signed_xml:
                        if not record.mpfel_sat_uuid and not record.mpfel_result_xml:
                            settings.registrar_documento(record)
                    else:
                        raise UserError(_('Documento no esta firmado...'))
                return True

    def mpfel_invoice_void(self):
        for inv in self:
            settings = inv.env['mpfel.settings'].search([('company_id', '=', inv.company_id.id)])
            if inv.mpfel_sat_uuid:
                settings.void_document(inv)
        return True


    def invoice_pdf(self):
        for inv in self:
            settings = inv.env['mpfel.settings'].search([('company_id', '=', inv.company_id.id)])
            if inv.mpfel_sat_uuid and settings:
                settings.pdf_document(inv)
        return True
    

    def _reverse_move_vals_old(self, default_values, cancel=True):
        ''' Reverse values passed as parameter being the copied values of the original journal entry.
        For example, debit / credit must be switched. The tax lines must be edited in case of refunds.

        :param default_values:  A copy_date of the original journal entry.
        :param cancel:          A flag indicating the reverse is made to cancel the original journal entry.
        :return:                The updated default_values.
        '''
        self.ensure_one()

        def compute_tax_repartition_lines_mapping(move_vals):
            ''' Computes and returns a mapping between the current repartition lines to the new expected one.
            :param move_vals:   The newly created invoice as a python dictionary to be passed to the 'create' method.
            :return:            A map invoice_repartition_line => refund_repartition_line.
            '''
            # invoice_repartition_line => refund_repartition_line
            mapping = {}

            # Do nothing if the move is not a credit note.
            if move_vals['move_type'] not in ('out_refund', 'in_refund'):
                return mapping

            for line_command in move_vals.get('line_ids', []):
                line_vals = line_command[2]  # (0, 0, {...})

                if line_vals.get('tax_line_id'):
                    # Tax line.
                    tax_ids = [line_vals['tax_line_id']]
                elif line_vals.get('tax_ids') and line_vals['tax_ids'][0][2]:
                    # Base line.
                    tax_ids = line_vals['tax_ids'][0][2]
                else:
                    continue

                for tax in self.env['account.tax'].browse(tax_ids).flatten_taxes_hierarchy():
                    for inv_rep_line, ref_rep_line in zip(tax.invoice_repartition_line_ids, tax.refund_repartition_line_ids):
                        mapping[inv_rep_line] = ref_rep_line
            return mapping

        move_vals = self.with_context(include_business_fields=True).copy_data(default=default_values)[0]
        if move_vals['move_type'] == 'out_refund':
            move_vals.update({
                'mpfel_sat_uuid_ncre': self.id,
            })
        tax_repartition_lines_mapping = compute_tax_repartition_lines_mapping(move_vals)

        for line_command in move_vals.get('line_ids', []):
            line_vals = line_command[2]  # (0, 0, {...})

            # ==== Inverse debit / credit / amount_currency ====
            amount_currency = -line_vals.get('amount_currency', 0.0)
            balance = line_vals['credit'] - line_vals['debit']

            line_vals.update({
                'amount_currency': amount_currency,
                'debit': balance > 0.0 and balance or 0.0,
                'credit': balance < 0.0 and -balance or 0.0,
            })

            if move_vals['move_type'] not in ('out_refund', 'in_refund'):
                continue

            # ==== Map tax repartition lines ====
            if line_vals.get('tax_repartition_line_id'):
                # Tax line.
                invoice_repartition_line = self.env['account.tax.repartition.line'].browse(line_vals['tax_repartition_line_id'])
                if invoice_repartition_line not in tax_repartition_lines_mapping:
                    raise UserError(_("It seems that the taxes have been modified since the creation of the journal entry. You should create the credit note manually instead."))
                refund_repartition_line = tax_repartition_lines_mapping[invoice_repartition_line]

                # Find the right account.
                account_id = self.env['account.move.line']._get_default_tax_account(refund_repartition_line).id
                if not account_id:
                    if not invoice_repartition_line.account_id:
                        # Keep the current account as the current one comes from the base line.
                        account_id = line_vals['account_id']
                    else:
                        tax = invoice_repartition_line.invoice_tax_id
                        base_line = self.line_ids.filtered(lambda line: tax in line.tax_ids.flatten_taxes_hierarchy())[0]
                        account_id = base_line.account_id.id

                line_vals.update({
                    'tax_repartition_line_id': refund_repartition_line.id,
                    'account_id': account_id,
                    'tax_tag_ids': [(6, 0, refund_repartition_line.tag_ids.ids)],
                })
            elif line_vals.get('tax_ids') and line_vals['tax_ids'][0][2]:
                # Base line.
                taxes = self.env['account.tax'].browse(line_vals['tax_ids'][0][2]).flatten_taxes_hierarchy()
                invoice_repartition_lines = taxes\
                    .mapped('invoice_repartition_line_ids')\
                    .filtered(lambda line: line.repartition_type == 'base')
                refund_repartition_lines = invoice_repartition_lines\
                    .mapped(lambda line: tax_repartition_lines_mapping[line])

                line_vals['tax_tag_ids'] = [(6, 0, refund_repartition_lines.mapped('tag_ids').ids)]
        return move_vals

class account_invoice_line(models.Model):
    _name = 'account.move.line'
    _inherit = 'account.move.line'

    @api.model_create_multi
    def create(self,values):
        res = super(account_invoice_line,self).create(values)

        return res

    @api.depends('price_unit', 'discount', 'tax_ids', 'quantity',
        'product_id', 'move_id.partner_id', 'move_id.currency_id', 'move_id.company_id',
        'move_id.invoice_date')
    def _compute_price(self):
        for line in self:

            currency = line.move_id and line.move_id.currency_id or None
            price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
            discount = (line.quantity * line.price_unit) * line.discount / 100


            taxes = False
            if line.tax_ids:
                taxes = line.tax_ids.compute_all(price, currency, line.quantity, product=line.product_id, partner=line.move_id.partner_id)
            line.price_subtotal = price_subtotal_signed = taxes['total_excluded'] if taxes else line.quantity * price
            line.price_total = taxes['total_included'] if taxes else line.price_subtotal
            line.price_discount = discount
            if line.price_subtotal and line.tax_ids :
                line.tax_par_line = taxes['total_included']-line.price_subtotal
            else:
                line.tax_par_line = 0.0
            sign = line.move_id.move_type in ['in_refund', 'out_refund'] and -1 or 1

#16    tax_par_line =  fields.Float(compute='_compute_price', digits='Account', string='Tax Amount', help='Count tax par line',store="True")
    tax_par_line =  fields.Float( digits='Account', string='Tax Amount', help='Count tax par line',)

#16    price_subtotal = fields.Monetary(string='Subtotal',
#16        store=True, readonly=True, compute='_compute_price', help="Total amount without taxes")
    price_subtotal = fields.Monetary(string='Subtotal', help="Total amount without taxes")

#16    price_discount = fields.Monetary(string='Descuento',
#16       store=True, readonly=True, compute='_compute_price',
#16           help="Total discount amount ")
    price_discount = fields.Monetary(string='Descuento', help="Total discount amount ")


#    price_total = fields.Monetary(string='Total',
#        store=True, readonly=True, compute='_compute_price', help="Total amount with taxes")
    price_total = fields.Monetary(string='Total',help="Total amount with taxes")
