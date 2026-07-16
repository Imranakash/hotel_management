# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class HotelFolio(models.Model):
    _name = 'hotel.folio'
    _description = 'Hotel Folio'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    _rec_name = 'folio_no'
    folio_no = fields.Char(string='Folio Number', required=True, readonly=True, default=lambda self: _('New'), tracking=True)

    booking_id = fields.Many2one(
        'hotel.booking',
        string='Guest / Booking Ref',
        required=True,
        domain="[('state', '=', 'checked_in')]",
        tracking = True
    )

    guest_id = fields.Many2one('res.partner', string='Guest', compute='_compute_stay_details', store=True)
    room_id = fields.Many2one('hotel.room', string='Room', compute='_compute_stay_details', store=True)

    amount_net_total = fields.Float(string='Net Total', compute='_compute_total_amount', store=True,tracking=True)
    state = fields.Selection([('open', 'Open'), ('billed', 'Billed'), ('paid', 'Paid')], default='open', tracking=True)
    folio_line_ids = fields.One2many('hotel.folio.line', 'folio_id', string='Folio Lines')
    booking_count = fields.Integer(compute='_compute_booking_count', string='Booking Count')
    invoice_count = fields.Integer(compute='_compute_invoice_count', string='Invoice Count')
    property_id = fields.Many2one('hotel.property', string='Property/Hotel', required=True)

    # NEW: direct link to invoices, replaces folio_no/partner_id text matching
    invoice_ids = fields.One2many('account.move', 'folio_id', string='Invoices')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            name = vals.get('name', '')
            if name and ('Room Charge' in name or 'Room' in name):
                room_product = self.env['product.product'].sudo().search([('name', 'ilike', 'Room')], limit=1)
                if room_product:
                    vals['product_id'] = room_product.id
        return super().create(vals_list)


    @api.depends('folio_line_ids.price_subtotal')
    def _compute_total_amount(self):
        for record in self:
            record.amount_net_total = sum(line.price_subtotal for line in record.folio_line_ids)

    @api.depends('booking_id', 'booking_id.room_line_ids.room_id', 'booking_id.guest_id')
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

    @api.depends('booking_id')
    def _compute_booking_count(self):
        for record in self:
            record.booking_count = 1 if record.booking_id else 0

    @api.depends('invoice_ids')
    def _compute_invoice_count(self):
        for record in self:
            record.invoice_count = len(record.invoice_ids)

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

        invoices = self.invoice_ids

        action = {
            'name': 'Invoices',
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'target': 'current',
        }

        if len(invoices) == 1:
            action.update({
                'view_mode': 'form',
                'res_id': invoices.id,
            })
        elif len(invoices) > 1:
            action.update({
                'view_mode': 'list,form',
                'views': [(False, 'list'), (False, 'form')],
                'domain': [('id', 'in', invoices.ids)],
            })
        else:
            action.update({
                'name': _('Create Invoice for %s') % self.guest_id.name,
                'view_mode': 'form',
                'views': [(self.env.ref('account.view_move_form').id, 'form')],
                'context': {
                    'default_move_type': 'out_invoice',
                    'default_partner_id': self.guest_id.id,
                    'default_invoice_origin': self.folio_no,
                    'default_folio_id': self.id,
                }
            })
        return action

    def action_create_invoice(self):
        self.ensure_one()
        if self.invoice_ids:
            raise UserError(_("An invoice already exists for this folio!"))

        invoice_lines = []

        room_product = self.env['product.product'].search([('name', 'ilike', 'Room')], limit=1)

        for line in self.folio_line_ids:
            product_id = line.product_id.id if line.product_id else (room_product.id if room_product else False)

            invoice_lines.append((0, 0, {
                'name': line.name or (line.product_id.name if line.product_id else _("Room Charge/Adjustment")),
                'quantity': line.quantity,
                'price_unit': line.price_unit,
                'product_id': product_id,
            }))

        if self.booking_id and self.booking_id.deposit_amount > 0:
            deposit_product = self.env['product.product'].search([('name', 'ilike', 'Deposit')], limit=1)
            invoice_lines.append((0, 0, {
                'name': _("Advance Deposit Adjustment (Deducted)"),
                'quantity': 1.0,
                'price_unit': -self.booking_id.deposit_amount,
                'product_id': deposit_product.id if deposit_product else False,
            }))

        if self.booking_id and hasattr(self.booking_id, 'discount_amount') and self.booking_id.discount_amount > 0:
            discount_product = self.env['product.product'].search([('name', 'ilike', 'Discount')], limit=1)
            invoice_lines.append((0, 0, {
                'name': _("Approved Manager Discount (Deducted)"),
                'quantity': 1.0,
                'price_unit': -self.booking_id.discount_amount,
                'product_id': discount_product.id if discount_product else False,
            }))

        if not invoice_lines:
            raise UserError(_("No bill lines found to create an invoice!"))

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'invoice_origin': self.folio_no,
            'partner_id': self.guest_id.id,
            'folio_id': self.id,
            'invoice_line_ids': invoice_lines,
        })

        self.write({'state': 'billed'})

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
        invoice = self.invoice_ids[:1]

        if not invoice:
            raise UserError(_("No invoice found to print! Please create an invoice first."))

        return self.env.ref('account.account_invoices').report_action(invoice)

    def write(self, vals):
        res = super(HotelFolio, self).write(vals)
        if 'state' not in vals or vals.get('state') != 'paid':
            for record in self:
                if record.state == 'paid':
                    continue
                paid_invoice = record.invoice_ids.filtered(lambda inv: inv.payment_state == 'paid')
                if paid_invoice:
                    super(HotelFolio, record).write({'state': 'paid'})
        return res


class HotelFolioLine(models.Model):
    _name = 'hotel.folio.line'
    _description = 'Hotel Folio Line'

    folio_id = fields.Many2one('hotel.folio', string='Folio Ref', ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product / Service', required=True)
    name = fields.Char(string='Description', required=True)
    quantity = fields.Float(string='Quantity', default=1.0, tracking=True)
    price_unit = fields.Float(string='Unit Price', default=0.0, tracking=True)
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


class AccountMove(models.Model):
    _inherit = 'account.move'

    # NEW: direct link back to the folio that created this invoice
    folio_id = fields.Many2one('hotel.folio', string='Hotel Folio', readonly=True, copy=False)

    def _compute_payment_state(self):
        res = super()._compute_payment_state()
        for move in self:
            if move.move_type == 'out_invoice' and move.payment_state == 'paid' and move.folio_id:
                if move.folio_id.state != 'paid':
                    move.folio_id.write({'state': 'paid'})
        return res