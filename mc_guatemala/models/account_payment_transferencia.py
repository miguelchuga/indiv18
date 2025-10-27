# -*- coding: utf-8 -*-
# Copyright 2025 Waleed Mohsen. (<https://wamodoo.com/>)
# License OPL-1

from odoo import models, fields, api, _


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    is_internal_transfer = fields.Boolean(string="Transferencia interna",
                                          tracking=True)

    destination_journal_id = fields.Many2one(
        comodel_name='account.journal',
        string='Diario destino',
        domain="[('type', 'in', ('bank','cash')), ('id', '!=', journal_id)]",
        check_company=True,
    )


    # Override the _get_aml_default_display_name_list method to set the label for the liquidity line
    def _get_aml_default_display_name_list(self):
        self.ensure_one()
        result = super()._get_aml_default_display_name_list()
        if self.is_internal_transfer:
            label = _("Internal Transfer")
            result[0] = ('label', label)
        return result

    def _get_liquidity_aml_display_name_list(self):
        """ Hook allowing custom values when constructing the label to set on the liquidity line.

        :return: A list of terms to concatenate all together. E.g.
            [('reference', "INV/2018/0001")]
        """
        self.ensure_one()
        if self.is_internal_transfer:
            if self.payment_type == 'inbound':
                return [('transfer_to', _('Transfer to %s', self.journal_id.name))]
            else:  # payment.payment_type == 'outbound':
                return [('transfer_from', _('Transfer from %s', self.journal_id.name))]
        elif self.payment_reference:
            return [('reference', self.payment_reference)]
        else:
            return self._get_aml_default_display_name_list()

    # Call the super method to keep the original behavior for non-internal transfers
    @api.depends('partner_id', 'company_id', 'payment_type', 'destination_journal_id', 'is_internal_transfer')
    def _compute_available_partner_bank_ids(self):
        super()._compute_available_partner_bank_ids()
        for pay in self:
            if pay.is_internal_transfer:
                pay.available_partner_bank_ids = pay.destination_journal_id.bank_account_id

    # Call the super method to keep the original behavior for non-internal transfers
    @api.depends('journal_id', 'partner_id', 'partner_type', 'is_internal_transfer', 'destination_journal_id')
    def _compute_destination_account_id(self):
        super()._compute_destination_account_id()
        for pay in self:
            if pay.is_internal_transfer:
                pay.destination_account_id = pay.destination_journal_id.company_id.transfer_account_id

    # Call the super method to keep the original behavior for non-internal transfers
    @api.depends('journal_id', 'is_internal_transfer')
    def _compute_partner_id(self):
        super()._compute_partner_id()
        for pay in self:
            if pay.is_internal_transfer:
                pay.partner_id = pay.journal_id.company_id.partner_id

    # Exists in Odoo 18.0
    def _prepare_move_line_default_vals(self, write_off_line_vals=None, force_balance=None):
        self.ensure_one()
        line_vals_list = super()._prepare_move_line_default_vals()
        # if the payment is an internal transfer, we need to set the liquidity line name and the counterpart line name (Label)
        if self.is_internal_transfer:
            liquidity_line_name = ''.join(x[1] for x in self._get_liquidity_aml_display_name_list())
            counterpart_line_name = ''.join(x[1] for x in self._get_aml_default_display_name_list())
            line_vals_list[0]['name'] = liquidity_line_name
            line_vals_list[1]['name'] = counterpart_line_name
        return line_vals_list

    # This method new in Odoo 18.0 and I extended it to set the journal_id and payment_method_line_id if the payment is not an internal transfer
    def copy_data(self, default=None):
        default = dict(default or {})
        vals_list = super().copy_data(default)
        for payment, vals in zip(self, vals_list):
            if not payment.is_internal_transfer:  # Just added this line
                vals.update({
                    'journal_id': payment.journal_id.id,
                    'payment_method_line_id': payment.payment_method_line_id.id,
                    **(vals or {}),
                })
        return vals_list

    # override the _get_trigger_fields_to_synchronize method to add the is_internal_transfer field
    @api.model
    def _get_trigger_fields_to_synchronize(self):
        res = super()._get_trigger_fields_to_synchronize()
        res += ('is_internal_transfer',)
        return res

    # I override the action_post method to create a paired payment when posting an internal transfer
    def action_post(self):
        super().action_post()

        # Added this code from Odoo 17.0 to create a paired payment for internal transfer
        self.filtered(
            lambda pay: pay.is_internal_transfer and not pay.paired_internal_transfer_payment_id
        )._create_paired_internal_transfer_payment()

    # This method only for internal transfer and not exists anymore in Odoo 18.0
    def _create_paired_internal_transfer_payment(self):
        ''' When an internal transfer is posted, a paired payment is created
        with opposite payment_type and swapped journal_id & destination_journal_id.
        Both payments liquidity transfer lines are then reconciled.
        '''
        for payment in self:
            payment_type = payment.payment_type == 'outbound' and 'inbound' or 'outbound'
            available_payment_method_lines = payment.destination_journal_id._get_available_payment_method_lines(
                payment_type)
            inbound_payment_method = payment.partner_id.property_inbound_payment_method_line_id
            outbound_payment_method = payment.partner_id.property_outbound_payment_method_line_id
            if payment.payment_type == 'outbound' and inbound_payment_method.id in available_payment_method_lines.ids:
                payment_method_line_id = inbound_payment_method
            elif payment.payment_type == 'inbound' and outbound_payment_method.id in available_payment_method_lines.ids:
                payment_method_line_id = outbound_payment_method
            elif payment.payment_method_line_id.id in available_payment_method_lines.ids:
                payment_method_line_id = payment.payment_method_line_id
            elif available_payment_method_lines:
                payment_method_line_id = available_payment_method_lines[0]._origin
            else:
                payment_method_line_id = False

            paired_payment = payment.copy({
                'journal_id': payment.destination_journal_id.id,
                'company_id': payment.company_id.id,
                'destination_journal_id': payment.journal_id.id,
                'payment_method_line_id': payment_method_line_id.id,
                'payment_type': payment_type,
                'move_id': None,
                'memo': payment.memo,
                'paired_internal_transfer_payment_id': payment.id,
                'date': payment.date,
            })
            paired_payment.action_post()
            payment.paired_internal_transfer_payment_id = paired_payment
            body = _("This payment has been created from:") + payment._get_html_link()
            paired_payment.message_post(body=body)
            body = _("A second payment has been created:") + paired_payment._get_html_link()
            payment.message_post(body=body)

            lines = (payment.move_id.line_ids + paired_payment.move_id.line_ids).filtered(
                lambda l: l.account_id == payment.destination_account_id and not l.reconciled)
            lines.reconcile()


