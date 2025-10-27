# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError





class pos_order_fel(models.Model):
    _name = "pos.order"
    _inherit = "pos.order"

    infilefel_comercial_name = fields.Char(string='Comercial name')
    serie_venta = fields.Char('Serie ventas')
    infilefel_establishment_street = fields.Char('Establishment street')

    nit_certificador = fields.Char('Nit empresa certificadora')
    nombre_certificador = fields.Char('Nombre empresa certificadora ')
    frase_certificador = fields.Char('Frase empresa o cliente')

    nit_empresa = fields.Char('Nit empresa')
    nombre_empresa = fields.Char('Nombre empresa')

    infile_number = fields.Char('Número DTE')
    infilefel_sat_uuid = fields.Char('SAT UUID')
    infilefel_sign_date = fields.Char('Sign date')

    nombre_cliente = fields.Char('Nombre cliente')
    nit = fields.Char('Nit cliente')
    direccion_cliente = fields.Char('Dirección cliente')
    fecha_factura = fields.Char('Fecha factura')

    caja = fields.Char('Caja')
    vendedor = fields.Char('Vendedor')
    forma_pago = fields.Char('Forma pago')


    def _generate_pos_order_invoice(self):
        moves = self.env['account.move']

        for order in self:
            # Force company for all SUPERUSER_ID action
            if order.account_move:
                moves += order.account_move
                continue

            if not order.partner_id:
                raise UserError(_('Please provide a partner for the sale.'))

            move_vals = order._prepare_invoice_vals()
            new_move = order._create_invoice(move_vals)

            order.write({'account_move': new_move.id, 'state': 'invoiced'})

            if new_move.move_type == 'out_invoice' :
                settings = new_move.env['mpfel.settings'].search([])
                if settings:
                    settings.sign_document(new_move)
                    if new_move.mpfel_uuid or new_move.mpfel_source_xml:
                        settings.firmar_documento(new_move)
                        settings.registrar_documento(new_move)
                    else:
                        raise UserError(_('Megaprint FEL No se firmo el documento ni valido'))
                else:
                    raise UserError(_('Megaprint FEL settings not found'))

            new_move.sudo().with_company(order.company_id)._post()
            moves += new_move
            payment_moves = order._apply_invoice_payments()

            if order.session_id.state == 'closed':  # If the session isn't closed this isn't needed.
                # If a client requires the invoice later, we need to revers the amount from the closing entry, by making a new entry for that.
                order._create_misc_reversal_move(payment_moves)

        if not moves:
            return {}

        return {
            'name': _('Customer Invoice'),
            'view_mode': 'form',
            'view_id': self.env.ref('account.view_move_form').id,
            'res_model': 'account.move',
            'context': "{'move_type':'out_invoice'}",
            'type': 'ir.actions.act_window',
            'nodestroy': True,
            'target': 'current',
            'res_id': moves and moves.ids[0] or False,
        }