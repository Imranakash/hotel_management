# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError


class HotelBooking(models.Model):
    _name = 'hotel.booking'
    _description = 'Hotel & Resort Reservation'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    name = fields.Char(
        string='Reservation Ref',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New'),
        tracking=True
    )
    property_id = fields.Many2one(
        'hotel.property',
        string='Property/Hotel',
        required=True,
        tracking=True,
        default=lambda self: self.env['hotel.property'].search([('company_id', '=', self.env.company.id)], limit=1)
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
        store=True
    )
    guest_id = fields.Many2one(
        'res.partner',
        string='Primary Guest',
        required=True,
        tracking=True,
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]"
    )

    booking_date = fields.Date(
        string='Booking Date',
        default=fields.Date.context_today,
        required=True,
        readonly=True,
        tracking=True,
    )
    checkin_date = fields.Datetime(
        string='Arrival Date & Time',
        required=True,
        tracking=True,
        help="Expected or actual check-in time."
    )
    checkout_date = fields.Datetime(
        string='Departure Date & Time',
        required=True,
        tracking=True,
        help="Expected or actual check-out time."
    )
    duration_days = fields.Integer(
        string='Duration (Nights)',
        compute='_compute_duration_days',
        store=True
    )

    room_line_ids = fields.One2many(
        'hotel.booking.room.line',
        'booking_id',
        string='Room Allocations',
        copy=True
    )
    folio_ids = fields.One2many(
        'hotel.folio',
        'booking_id',
        string='Connected Folios',
        readonly=True
    )
    room_move_ids = fields.One2many('hotel.room.move.history', 'booking_id', string="Room Move History", readonly=True)

    booking_source = fields.Selection([
        ('direct_walkin', 'Direct Walk-In'),
        ('phone_email', 'Phone/Email Inquiry'),
        ('website', 'Hotel Website'),
        ('ota', 'Online Travel Agency (OTA)'),
        ('corporate', 'Corporate Contract B2B')
    ], string='Booking Source', default='direct_walkin', required=True, tracking=True)

    state = fields.Selection([
        ('draft', 'Inquiry / Draft'),
        ('quotation', 'Quotation Sent'),
        ('tentative', 'Tentative Hold'),
        ('waiting_approval', 'Waiting Manager Approval'),
        ('confirmed', 'Confirmed'),
        ('checked_in', 'Checked In / In House'),
        ('checked_out', 'Checked Out'),
        ('cancelled', 'Cancelled'),
        ('no_show', 'No Show')
    ], string='Status', default='draft', tracking=True, required=True, copy=False)

    deposit_amount = fields.Float(
        string='Deposit Amount',
        default=0.0,
        tracking=10,

    )
    payment_state = fields.Selection([
        ('unpaid', 'Unpaid'),
        ('partially_paid', 'Partially Paid'),
        ('paid', 'Paid')
    ], string='Payment Status',compute='_compute_payment_state', default='unpaid', readonly=True, tracking=True)

    approval_state = fields.Selection([
        ('no_needed', 'No Approval Needed'),
        ('not_required', 'Not Required'),
        ('waiting', 'Waiting Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected')
    ], string='Approval Status', default='no_needed', tracking=True)


    room_subtotal = fields.Float(
        string='Room Subtotal',
        compute='_compute_room_subtotal',
        store=True,
        tracking=True
    )

    discount_amount = fields.Float(string='Discount Amount', default=0.0, tracking=11)
    cancellation_date = fields.Datetime(string='Cancellation Date', readonly=True, copy=False)
    is_credit_exceeded = fields.Boolean(string='Credit Limit Exceeded', readonly=True, copy=False, default=False)
    approval_reason = fields.Text(string='Approval/Rejection Reason', tracking=True)
    refund_amount = fields.Float(string='Refund Amount', readonly=True, copy=False,
                                 help="Amount to be returned to guest")
    forfeiture_amount = fields.Float(string='Cancellation Fee (Forfeiture)', readonly=True, copy=False,
                                     help="Amount withheld as penalty")
    is_approved = fields.Boolean(string='Is Discount Approved', default=False, copy=False)

    is_credit_approved = fields.Boolean(string='Is Credit Approved', default=False, copy=False)

    agent_commission = fields.Float(string='Agent Commission Amount', default=0.0, tracking=True)
    commission_status = fields.Selection([
        ('na', 'Not Applicable'),
        ('active', 'Active'),
        ('reversed', 'Reversed / Cancelled')
    ], string='Commission Status', default='na', tracking=True, copy=False)

    booking_count = fields.Integer(string="Booking Count", compute="_compute_booking_count")


    @api.depends('room_line_ids.price_unit', 'room_line_ids.extra_bed_count', 'duration_days')
    def _compute_room_subtotal(self):
        for record in self:
            num_of_days = record.duration_days if record.duration_days > 0 else 1
            record.room_subtotal = sum(
                (line.price_unit * num_of_days) + (line.extra_bed_count * 500.0)
                for line in record.room_line_ids
            )

    @api.depends('folio_ids', 'folio_ids.invoice_ids', 'folio_ids.invoice_ids.payment_state', 'deposit_amount', 'state')
    def _compute_payment_state(self):
        """ফোলিও এবং ইনভয়েসের পেমেন্ট স্ট্যাটাস ডাইনামিকালি ক্যালকুলেট করার লজিক"""
        for record in self:
            all_invoices = record.folio_ids.mapped('invoice_ids')

            if not all_invoices and record.name:
                all_invoices = self.env['account.move'].search([('invoice_origin', '=', record.name)])

            if not all_invoices:
                if record.deposit_amount > 0.0 and record.state in ['confirmed', 'checked_in']:
                    record.payment_state = 'partially_paid'
                else:
                    record.payment_state = 'unpaid'
                continue

            invoice_states = all_invoices.mapped('payment_state')

            if all(state == 'paid' for state in invoice_states):
                record.payment_state = 'paid'
            elif any(state in ['paid', 'partial'] for state in invoice_states):
                record.payment_state = 'partially_paid'
            else:
                record.payment_state = 'unpaid'

    @api.depends('name', 'guest_id.name')
    def _compute_display_name(self):
        for record in self:
            if record.name and record.guest_id:
                record.display_name = f"{record.name} - {record.guest_id.name}"
            else:
                record.display_name = record.name or ''

    @api.model
    def _name_search(self, name, domain=None, operator='ilike', limit=100, order=None):
        domain = domain or []
        if name:
            domain = ['|', ('name', operator, name), ('guest_id.name', operator, name)] + domain
        return self._search(domain, limit=limit, order=order)

    @api.constrains('checkin_date', 'checkout_date')
    def _check_booking_dates(self):
        for record in self:
            if record.checkin_date and record.checkout_date:
                if record.checkout_date <= record.checkin_date:
                    raise ValidationError(
                        _("Error! Departure (Check-Out) date must be strictly after the Arrival (Check-In) date."))
                if record.checkin_date.date() < fields.Date.today():
                    if record.state == 'draft':
                        continue
                    raise ValidationError(_("Warning: Cannot confirm a booking with an arrival date in the past."))

    @api.depends('checkin_date', 'checkout_date')
    def _compute_duration_days(self):
        for record in self:
            if record.checkin_date and record.checkout_date:
                delta = record.checkout_date - record.checkin_date
                record.duration_days = max(1, delta.days)
            else:
                record.duration_days = 0

    def action_set_to_draft(self):
        for record in self:
            record.write({
                'state': 'draft',
                'is_approved': False,
                'is_credit_approved': False,
                'is_credit_exceeded': False
            })
            record.message_post(
                body=_("<b>Booking Reset:</b> Status reverted to Draft by %s for editing.") % self.env.user.name)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') in [_('New'), 'New']:
                seq_obj = self.env['ir.sequence'].sudo().search([('code', '=', 'hotel.booking')], limit=1)
                if not seq_obj:
                    seq_obj = self.env['ir.sequence'].sudo().create({
                        'name': 'Hotel Booking Sequence',
                        'code': 'hotel.booking',
                        'prefix': 'BK-%(year)s-',
                        'padding': 5,
                        'number_next': 1,
                        'number_increment': 1,
                        'company_id': False,
                    })
                vals['name'] = seq_obj.next_by_id()
        return super(HotelBooking, self).create(vals_list)

    def action_send_quotation(self):
        self.write({'state': 'quotation'})

    def action_set_tentative(self):
        self.write({'state': 'tentative'})

    def action_confirm(self):
        for record in self:
            if not record.room_line_ids:
                raise UserError(_("Cannot confirm reservation. Please allocate at least one room category/line."))

            if record.booking_source == 'corporate' and record.guest_id:
                credit_limit = 5000.0
                current_receivable = 0.0

                total_booking_cost = record.room_subtotal

                if (current_receivable + total_booking_cost) > credit_limit and not record.is_credit_approved:
                    record.write({
                        'state': 'waiting_approval',
                        'is_credit_exceeded': True
                    })
                    record.message_post(body=_(
                        "🛑 <b>Corporate Credit Limit Exceeded!</b><br/>"
                        "Client Credit Limit: %s<br/>"
                        "New Booking Cost: %s<br/>"
                        "Booking locked. Shifting to 'Waiting Manager Approval' state."
                    ) % (credit_limit, total_booking_cost))

                    return {
                        'type': 'ir.actions.client',
                        'tag': 'display_notification',
                        'params': {
                            'title': _('Credit Limit Exceeded'),
                            'message': _('Corporate credit limit exceeded! Sent to Manager for approval.'),
                            'sticky': False,
                            'type': 'danger',
                        }
                    }

            if record.discount_amount and not record.is_approved:
                allowed_max_discount = 0.0

                for line in record.room_line_ids:
                    if line.room_type_id and record.property_id:
                        rate_setup = self.env['hotel.room.rate'].search([
                            ('property_id', '=', record.property_id.id),
                            ('room_type_id', '=', line.room_type_id.id)
                        ], limit=1)

                        if rate_setup:
                            allowed_max_discount = rate_setup.max_discount
                            break

                if record.discount_amount > allowed_max_discount:
                    record.write({'state': 'waiting_approval'})
                    record.message_post(body=_(
                        "<b>Approval Requested:</b> Discount amount (%s) exceeds the allowed limit (%s) for this room. Booking is locked until manager approves."
                    ) % (record.discount_amount, allowed_max_discount))

                    return {
                        'type': 'ir.actions.client',
                        'tag': 'display_notification',
                        'params': {
                            'title': _('Approval Required'),
                            'message': _(
                                'Discount exceeds your allowed limit! Booking has been sent to the Manager for approval.'),
                            'sticky': False,
                            'type': 'warning',
                        }
                }

            for line in record.room_line_ids:
                if line.room_id:
                    overlapping_bookings = self.env['hotel.booking.room.line'].search([
                        ('room_id', '=', line.room_id.id),
                        ('booking_id', '!=', record.id),
                        ('booking_id.state', 'in', ['confirmed', 'checked_in']),
                        ('booking_id.checkin_date', '<', record.checkout_date),
                        ('booking_id.checkout_date', '>', record.checkin_date)
                    ])
                    if overlapping_bookings:
                        raise UserError(
                            _("Room %s is already reserved or occupied for the selected dates!") % line.room_id.name)

            record.write({'state': 'confirmed'})

            for line in record.room_line_ids:
                if line.room_id:
                    line.room_id.write({'status': 'reserved'})

        return True

    def action_approve_discount(self):
        for record in self:
            sudo_record = record.sudo()

            vals = {
                'approval_state': 'approved',
                'state': 'confirmed',
            }

            if record.is_credit_exceeded:
                vals.update({'is_credit_approved': True, 'is_approved': True})
                record.message_post(body=_(
                    "<b>Credit Limit Approved:</b> Manager %s approved the exceeded credit limit.") % self.env.user.name)
            else:
                vals.update({'is_approved': True, 'is_credit_approved': True})
                record.message_post(
                    body=_("<b>Discount Approved:</b> Manager %s approved the discount amount.") % self.env.user.name)

            sudo_record.write(vals)


            for line in record.room_line_ids:
                if line.room_id:
                    line.room_id.sudo().write({'status': 'reserved'})

        return True

    def action_reject_discount(self):
        for record in self:
            record.sudo().write({
                'state': 'draft',
                'discount_amount': 0.0,
                'is_approved': False,
                'is_credit_approved': False,
                'is_credit_exceeded': False,
                'approval_state': 'rejected'
            })
            record.message_post(body=_("<b>Approval Rejected:</b> Resetting booking parameters to Draft."))
        return True

    def action_check_in(self):
        self.flush_recordset()

        for record in self:
            if record.state != 'confirmed':
                continue

            existing_folio = self.env['hotel.folio'].search([('booking_id', '=', record.id)], limit=1)

            if existing_folio:
                folio = existing_folio
            else:
                folio_vals = {
                    'booking_id': record.id,
                    'guest_id': record.guest_id.id,
                    'state': 'open',
                    'property_id': record.property_id.id,
                }
                folio = self.env['hotel.folio'].create(folio_vals)

            folio_lines_vals = []

            product = self.env['product.product'].search([
                ('type', '=', 'service'),
                ('name', 'ilike', 'Room')
            ], limit=1)

            if not product:
                product = self.env['product.product'].search([('type', '=', 'service')], limit=1)

            for line in record.room_line_ids:
                folio_lines_vals.append({
                    'folio_id': folio.id,
                    'product_id': product.id if product else False,
                    'name': _("Room Charge: %s (Room %s) for %s Nights") % (
                        line.room_type_id.name, line.room_id.name, record.duration_days),
                    'quantity': record.duration_days,
                    'price_unit': line.price_unit,
                })

            if folio_lines_vals:
                self.env['hotel.folio.line'].create(folio_lines_vals)

            record.write({'state': 'checked_in'})

        return True

    def action_check_out(self):
        for record in self:
            if record.state != 'checked_in':
                raise UserError(_("Only Checked-In bookings can be checked out."))

            if record.checkout_date and fields.Datetime.now() > record.checkout_date:
                raise UserError(_(
                    "🛑 System Blocked: Expected Departure Time (%s) has already passed!\n\n"
                    "This guest has overstayed. You cannot perform a standard check-out.\n"
                    "Please modify the booking to extend the departure date (so additional room rent is charged) "
                    "or apply manual penalty charges before completing checkout."
                ) % record.checkout_date)

            folio = self.env['hotel.folio'].search([
                ('booking_id', '=', record.id),
                ('state', 'in', ['open', 'billed', 'paid'])
            ], limit=1)

            if not folio:
                raise UserError(_("No active open Folio found for this booking. Cannot proceed with checkout."))


            if folio.state != 'paid':
                raise UserError(_(
                    "🛑 Checkout Blocked: Folio is not cleared yet!\n\n"
                    "The guest still has unpaid balances or the folio is not marked as Paid.\n"
                    "Please process the final payment and mark the folio as PAID before completing checkout."
                ))


            for line in record.room_line_ids:
                if line.room_id:
                    line.room_id.write({'status': 'dirty'})

                    if 'hotel.housekeeping.task' in self.env:
                        self.env['hotel.housekeeping.task'].sudo().create({
                            'room_id': line.room_id.id,
                            'task_type': 'checkout',
                            'priority': '2',
                            'state': 'draft',
                            'note': _(
                                "Auto-generated checkout cleaning task for Room %s. Guest: %s. Booking Ref: %s") % (
                                        line.room_id.name,
                                        record.guest_id.name if record.guest_id else 'Unknown',
                                        record.name
                                    )
                        })
                    else:
                        self.env['mail.activity'].create({
                            'res_id': line.room_id.id,
                            'res_model_id': self.env['ir.model']._get_id('hotel.room'),
                            'activity_type_id': self.env.ref('mail.mail_activity_data_todo').id,
                            'summary': _("Housekeeping Alert: Room %s is Dirty") % line.room_id.name,
                            'note': _("Guest checked out. Please clean the room immediately."),
                            'user_id': self.env.user.id,
                        })

            record.write({'state': 'checked_out'})

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': _('Guest Checked Out Successfully! Room Status Updated to Dirty.'),
                'type': 'success',
                'sticky': False,
                'next': {
                    'type': 'ir.actions.client',
                    'tag': 'reload',
                }
            }
        }

    def action_cancel(self):
        for record in self:
            if record.state in ['checked_in', 'checked_out']:
                raise UserError(_("Security Rule: Active or completed stays cannot be cancelled."))

            record.cancellation_date = fields.Datetime.now()
            if record.checkin_date:
                hours_before_checkin = (record.checkin_date - record.cancellation_date).total_seconds() / 3600.0

                if hours_before_checkin >= 24:
                    record.refund_amount = record.deposit_amount
                    record.forfeiture_amount = 0.0
                    record.message_post(body=_(
                        "<b>Cancellation Policy:</b> Cancelled within Free Cancellation period. 100% Refund calculated."))
                else:
                    record.forfeiture_amount = record.deposit_amount * 0.50
                    record.refund_amount = record.deposit_amount - record.forfeiture_amount
                    record.message_post(body=_(
                        "<b>Cancellation Policy:</b> Late Cancellation! 50%% Cancellation Fee (Forfeiture) applied as penalty."))
            else:
                record.refund_amount = record.deposit_amount
                record.forfeiture_amount = 0.0
            if record.booking_source in ['ota', 'corporate'] and record.agent_commission > 0:
                record.commission_status = 'reversed'
                record.message_post(body=_(
                    "<b>Commission Reversed:</b> Third-party commission of %s has been marked as REVERSED due to booking cancellation.") % record.agent_commission)
            elif record.booking_source in ['ota', 'corporate']:
                record.commission_status = 'na'

            record.write({'state': 'cancelled'})
            for line in record.room_line_ids:
                if line.room_id:
                    line.room_id.write({'status': 'available'})

            if record.folio_ids:
                open_folios = record.folio_ids.filtered(lambda f: f.state == 'open')
                if open_folios:
                    open_folios.write({'state': 'cancelled'})
                    record.message_post(body=_("Connected open folios have been cancelled automatically."))
        return True

    def action_set_no_show(self):
        for record in self:
            if record.state != 'confirmed':
                raise UserError(_("Only confirmed bookings can be marked as No-Show."))
            record.write({'state': 'no_show'})
            for line in record.room_line_ids:
                if line.room_id:
                    line.room_id.write({'status': 'available'})

    def write(self, vals):
        if not vals:
            return super(HotelBooking, self).write(vals)

        for record in self:
            is_manager = self.env.user.has_group('hotel_management_core.group_hotel_manager')
            if record.state in ['confirmed', 'checked_in', 'checked_out'] and not is_manager:
                if 'state' in vals and vals['state'] in ['draft', 'cancelled']:
                    continue

                bypass_fields = ['state', 'payment_state', 'message_follower_ids', 'activity_ids', 'message_ids']
                real_fields_changed = [field for field in vals.keys() if field not in bypass_fields]

                if real_fields_changed:
                    raise UserError(
                        _("Security Block: This booking is Confirmed/Active. You cannot edit any fields unless you are a Hotel Manager!"))

        return super(HotelBooking, self).write(vals)

    def unlink(self):
        for record in self:
            if record.state in ['confirmed', 'checked_in', 'checked_out', 'waiting_approval']:
                raise UserError(
                    _("Security Block: You cannot delete a booking that is confirmed, active, or waiting for approval! Please cancel it first."))
        return super(HotelBooking, self).unlink()

    def action_move_room(self, new_room_id, reason="AC / Maintenance Issue"):
        self.ensure_one()

        if self.state != 'checked_in':
            raise UserError(_("Guest must be 'Checked In' to move rooms!"))
        room_line = self.room_line_ids and self.room_line_ids[0]
        if not room_line:
            raise UserError(_("No room is currently allocated to this booking!"))
        old_room = room_line.room_id
        new_room = self.env['hotel.room'].browse(new_room_id)

        if not new_room or new_room.status != 'available':
            raise UserError(_("The selected new room is not available!"))
        room_line.write({'room_id': new_room.id})
        new_room.write({'status': 'occupied'})
        old_room.write({'status': 'maintenance'})
        self.env['hotel.room.maintenance'].create({
            'room_id': old_room.id,
            'booking_id': self.id,
            'reason': reason,
            'ticket_date': fields.Datetime.now(),
            'state': 'draft'
        })

        self.env['hotel.room.move.history'].create({
            'booking_id': self.id,
            'guest_id': self.guest_id.id if hasattr(self, 'guest_id') else False,
            'old_room_id': old_room.id,
            'new_room_id': new_room.id,
            'move_reason': reason,
            'moved_by_id': self.env.user.id,
            'move_datetime': fields.Datetime.now(),
        })

        self.message_post(body=f"🔄 Room Moved: {old_room.name} ➡️ {new_room.name}. Reason: {reason}")
        return True

    def button_trigger_room_move_test(self):
        self.ensure_one()
        return {
            'name': '🔄 Move Guest Room',
            'type': 'ir.actions.act_window',
            'res_model': 'hotel.room.move.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': self.env.context,
        }

    folio_count = fields.Integer(string="Folio Count", compute="_compute_folio_count")

    @api.depends('folio_ids')
    def _compute_folio_count(self):
        for record in self:
            record.folio_count = len(record.folio_ids)

    def action_view_connected_folios(self):
        self.ensure_one()
        action = {
            'name': 'Connected Folios',
            'type': 'ir.actions.act_window',
            'res_model': 'hotel.folio',
            'view_mode': 'list,form',
            'views': [(False, 'list'), (False, 'form')],
            'domain': [('booking_id', '=', self.id)],
            'context': {'default_booking_id': self.id},
        }
        if len(self.folio_ids) == 1:
            action.update({
                'view_mode': 'form',
                'views': [(False, 'form')],
                'res_id': self.folio_ids[:1].id,
            })
        return action

    def action_view_connected_invoices(self):
        self.ensure_one()
        action = {
            'name': 'Connected Invoices',
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'views': [(False, 'list'), (False, 'form')],
            'domain': [('invoice_origin', '=', self.name)],
            'context': {'default_invoice_origin': self.name},
        }

        invoices = self.env['account.move'].search([('invoice_origin', '=', self.name)])
        if len(invoices) == 1:
            action.update({
                'view_mode': 'form',
                'views': [(False, 'form')],
                'res_id': invoices.id,
            })
        return action

    @api.depends('guest_id')
    def _compute_booking_count(self):
        for record in self:
            if record.guest_id:
                count = self.search_count([('guest_id', '=', record.guest_id.id)])
                record.booking_count = count
            else:
                record.booking_count = 0

    def action_open_approval_wizard(self):
        self.ensure_one()
        return {
            'name': '🛡️ Manager Approval Desk',
            'type': 'ir.actions.act_window',
            'res_model': 'hotel.booking.approval.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_booking_id': self.id,
                'default_approval_state': self.approval_state,
                'default_approval_reason': self.approval_reason,
                'default_is_credit_exceeded': self.is_credit_exceeded,
            }
        }


class HotelRoomMoveHistory(models.Model):
    _name = 'hotel.room.move.history'
    _description = 'Hotel Room Move History'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'move_datetime desc'

    booking_id = fields.Many2one('hotel.booking', string="Booking Ref", ondelete='cascade',tracking=True )
    guest_id = fields.Many2one('res.partner', string="Guest", tracking=True)
    old_room_id = fields.Many2one('hotel.room', string="Old Room", readonly=True,tracking=True)
    new_room_id = fields.Many2one('hotel.room', string="New Room", readonly=True,tracking=True)
    move_reason = fields.Char(string="Reason for Move", readonly=True,tracking=True)
    moved_by_id = fields.Many2one('res.users', string="Moved By", default=lambda self: self.env.user, readonly=True,tracking=True)
    move_datetime = fields.Datetime(string="Move Date & Time", default=fields.Datetime.now, readonly=True,tracking=True)


class HotelBookingRoomLine(models.Model):
    _name = 'hotel.booking.room.line'
    _description = 'Booking Room Allocation Line'

    booking_id = fields.Many2one('hotel.booking', string='Booking Ref', ondelete='cascade', required=True)
    property_id = fields.Many2one('hotel.property', related='booking_id.property_id', store=True)
    room_type_id = fields.Many2one('hotel.room.type', string='Room Type/Category', required=True)
    room_id = fields.Many2one('hotel.room', string='Specific Room No')

    price_unit = fields.Float(string='Rate per Night', readonly=True, required=True, default=0.0, store=True)
    extra_bed_count = fields.Integer(string='Extra Beds', default=0)

    @api.onchange('room_type_id', 'booking_id.checkin_date', 'booking_id.checkout_date')
    def _onchange_room_availability_filter(self):
        domain = [('property_id', '=', self.property_id.id), ('room_type_id', '=', self.room_type_id.id)]

        if self.booking_id.checkin_date and self.booking_id.checkout_date:
            confirmed_lines = self.env['hotel.booking.room.line'].search([
                ('booking_id.state', 'in', ['confirmed', 'checked_in']),
                ('booking_id.checkin_date', '<', self.booking_id.checkout_date),
                ('booking_id.checkout_date', '>', self.booking_id.checkin_date),
                ('room_id', '!=', False)
            ])
            booked_room_ids = confirmed_lines.mapped('room_id.id')
            domain.append(('id', 'not in', booked_room_ids))

        return {'domain': {'room_id': domain}}

    @api.onchange('room_id')
    def _onchange_room_id_fetch_combined_price(self):
        if self.room_id and self.booking_id.property_id:
            rate_record = self.env['hotel.room.rate'].search([
                ('property_id', '=', self.booking_id.property_id.id),
                ('room_type_id', '=', self.room_id.room_type_id.id)
            ], limit=1)

            if rate_record:
                self.price_unit = rate_record.fixed_rate
            else:
                self.price_unit = 0.0
        else:
            self.price_unit = 0.0

    @api.onchange('property_id')
    def _onchange_property_id_filter_room_types(self):
        if self.property_id:
            return {'domain': {'room_type_id': [('property_id', '=', self.property_id.id)]}}
        return {'domain': {'room_type_id': []}}


    @api.constrains('room_id')
    def _check_room_property_match(self):
        for line in self:
            if line.room_id and line.room_id.property_id != line.booking_id.property_id:
                raise ValidationError(
                    _("Configuration Error: The assigned room must belong to the selected property/hotel."))

            if line.room_id and line.booking_id.checkin_date and line.booking_id.checkout_date:
                overlapping = self.search([
                    ('room_id', '=', line.room_id.id),
                    ('id', '!=', line.id),
                    ('booking_id.state', 'in', ['confirmed', 'checked_in']),
                    ('booking_id.checkin_date', '<', line.booking_id.checkout_date),
                    ('booking_id.checkout_date', '>', line.booking_id.checkin_date)
                ])
                if overlapping:
                    raise ValidationError(
                        _("Conflict! Room %s is already booked for this date range in another reservation.") % line.room_id.name)