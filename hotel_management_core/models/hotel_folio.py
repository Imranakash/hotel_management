# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class HotelFolio(models.Model):
    _name = 'hotel.folio'
    _description = 'Hotel Folio'
    _order = 'id desc'

    _rec_name = 'folio_no'
    folio_no = fields.Char(string='Folio Number', required=True, readonly=True, default=lambda self: _('New'))

    booking_id = fields.Many2one(
        'hotel.booking',
        string='Guest / Booking Ref',
        required=True,
        domain="[('state', '=', 'checked_in')]"
    )

    guest_id = fields.Many2one('res.partner', string='Guest', compute='_compute_stay_details', store=True)
    room_id = fields.Many2one('hotel.room', string='Room', compute='_compute_stay_details', store=True)

    amount_net_total = fields.Float(string='Net Total', compute='_compute_total_amount', store=True)
    state = fields.Selection([('open', 'Open'), ('billed', 'Billed'), ('paid', 'Paid')], default='open', tracking=True)
    folio_line_ids = fields.One2many('hotel.folio.line', 'folio_id', string='Folio Lines')
    booking_count = fields.Integer(compute='_compute_booking_count', string='Booking Count')
    invoice_count = fields.Integer(compute='_compute_invoice_count', string='Invoice Count')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('folio_no', _('New')) == _('New'):
                vals['folio_no'] = self.env['ir.sequence'].next_by_code('hotel.folio') or _('New')
        return super().create(vals_list)

    @api.depends('folio_line_ids.price_subtotal')
    def _compute_total_amount(self):
        for record in self:
            record.amount_net_total = sum(line.price_subtotal for line in record.folio_line_ids)

    @api.depends('booking_id')
    def _compute_stay_details(self):
        for record in self:
            if record.booking_id:
                record.guest_id = record.booking_id.guest_id.id

                if record.booking_id.room_line_ids:
                    record.room_id = record.booking_id.room_line_ids[0].room_id.id
                else:
                    record.room_id = False
            else:
                record.guest_id = False
                record.room_id = False

    def action_post_restaurant_order(self, order_ref, total_amount):
        self.ensure_one()
        existing_order = self.folio_line_ids.filtered(lambda l: l.source_reference == order_ref)
        if existing_order:
            raise UserError(_("Duplicate Blocked: Restaurant order %s has already been posted!") % order_ref)

        product = self.env['product.product'].search([('name', 'ilike', 'Restaurant')], limit=1)
        if not product:
            product = self.env['product.product'].search([], limit=1)

        self.env['hotel.folio.line'].create({
            'folio_id': self.id,
            'product_id': product.id,
            'name': _("F&B Restaurant Charge (Ref: %s)") % order_ref,
            'quantity': 1.0,
            'price_unit': total_amount,
            'source_reference': order_ref,
        })
        return True

    def action_test_restaurant_posting(self):
        self.ensure_one()
        self.action_post_restaurant_order(order_ref="POS-999", total_amount=3500.0)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': _('Restaurant Order POS-999 posted successfully!'),
                'sticky': False,
                'type': 'success',
            }
        }

    @api.depends('booking_id')
    def _compute_booking_count(self):
        for record in self:
            record.booking_count = 1 if record.booking_id else 0

    def _compute_invoice_count(self):
        for record in self:
            invoices = self.env['account.move'].search([
                ('move_type', '=', 'out_invoice'),
                ('invoice_origin', '=', record.folio_no)
            ])
            record.invoice_count = len(invoices)

    def action_view_booking(self):
        self.ensure_one()
        if self.booking_id:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Related Booking',
                'res_model': 'hotel.booking',
                'view_mode': 'form',
                'res_id': self.booking_id.id,
                'target': 'current',
            }

    def action_view_invoices(self):
        self.ensure_one()

        invoices = self.env['account.move'].search([
            ('move_type', '=', 'out_invoice'),
            ('invoice_origin', '=', self.folio_no)
        ])

        action = {
            'name': 'Invoices',
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'target': 'current',
        }

        if len(invoices) == 1:
            action.update({
                'view_mode': 'form',
                'res_id': invoices[0].id,
            })
        else:
            action.update({
                'view_mode': 'list,form',
                'views': [(False, 'list'), (False, 'form')],
                'domain': [('id', 'in', invoices.ids)],
            })
        return action

    def action_create_invoice(self):
        self.ensure_one()
        existing_invoice = self.env['account.move'].search([
            ('move_type', '=', 'out_invoice'),
            ('invoice_origin', '=', self.folio_no)
        ], limit=1)

        if existing_invoice:
            raise UserError("An invoice already exists for this folio!")
        invoice_lines = []
        for line in self.folio_line_ids:
            invoice_lines.append((0, 0, {
                'name': line.name or line.product_id.name,
                'quantity': line.quantity,
                'price_unit': line.price_unit,
                'product_id': line.product_id.id,
            }))

        if not invoice_lines:
            raise UserError("No bill lines found to create an invoice!")

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'invoice_origin': self.folio_no,
            'partner_id': self.guest_id.id,
            'invoice_line_ids': invoice_lines,
        })

        return {
            'name': 'Customer Invoice',
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'form',
            'res_id': invoice.id,
            'target': 'current',
        }

    def action_print_invoice(self):
        self.ensure_one()
        invoice = self.env['account.move'].search([
            ('move_type', '=', 'out_invoice'),
            ('invoice_origin', '=', self.folio_no)
        ], limit=1)

        if not invoice:
            raise UserError("No invoice found to print! Please create an invoice first.")

        return self.env.ref('account.account_invoices').report_action(invoice)


class HotelFolioLine(models.Model):
    _name = 'hotel.folio.line'
    _description = 'Hotel Folio Line'

    folio_id = fields.Many2one('hotel.folio', string='Folio Ref', ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product / Service', required=True)
    name = fields.Char(string='Description', required=True)
    quantity = fields.Float(string='Quantity', default=1.0)
    price_unit = fields.Float(string='Unit Price', default=0.0)
    price_subtotal = fields.Float(string='Subtotal', compute='_compute_subtotal', store=True)
    source_reference = fields.Char(string='Source Reference', readonly=True)

    @api.onchange('product_id')
    def _onchange_product_id_fetch_details(self):
        if self.product_id:
            self.name = self.product_id.display_name
            self.price_unit = self.product_id.lst_price
        else:
            self.name = False
            self.price_unit = 0.0

    @api.depends('quantity', 'price_unit')
    def _compute_subtotal(self):
        for line in self:
            line.price_subtotal = line.quantity * line.price_unit