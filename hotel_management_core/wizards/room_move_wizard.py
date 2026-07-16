# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class HotelRoomMoveWizard(models.TransientModel):
    _name = 'hotel.room.move.wizard'
    _description = 'Hotel Room Move Wizard'

    booking_id = fields.Many2one('hotel.booking', string="Booking", required=True,
                                 default=lambda self: self.env.context.get('active_id'))

    property_id = fields.Many2one('hotel.property', string="Property", related='booking_id.property_id')
    current_room_id = fields.Many2one('hotel.room', string="Current Room", readonly=True)

    room_domain = fields.Char(compute="_compute_room_domain", readonly=True)
    filter_same_type = fields.Boolean(string="Filter by Same Room Type", default=True)
    folio_impact_msg = fields.Text(string="Financial Impact Notice", compute="_compute_folio_impact_msg", readonly=True)

    new_room_id = fields.Many2one('hotel.room', string="Select New Room", required=True)
    reason = fields.Char(string="Reason for Move", required=True, default="AC / Maintenance Issue")

    @api.model
    def default_get(self, fields_list):
        res = super(HotelRoomMoveWizard, self).default_get(fields_list)
        booking_id = self.env.context.get('active_id')
        if booking_id:
            booking = self.env['hotel.booking'].browse(booking_id)
            room_line = booking.room_line_ids and booking.room_line_ids[0]
            if room_line:
                res['current_room_id'] = room_line.room_id.id
        return res

    @api.depends('property_id', 'current_room_id', 'filter_same_type')
    def _compute_room_domain(self):
        for record in self:
            domain = [('status', '=', 'available')]

            if record.filter_same_type and record.current_room_id and record.current_room_id.room_type_id:
                domain.append(('room_type_id', '=', record.current_room_id.room_type_id.id))

            if record.property_id:
                domain.append(('property_id', '=', record.property_id.id))
            if record.current_room_id:
                domain.append(('id', '!=', record.current_room_id.id))

            record.room_domain = str(domain)

    @api.depends('new_room_id')
    def _compute_folio_impact_msg(self):
        for record in self:
            if not record.new_room_id or not record.booking_id:
                record.folio_impact_msg = False
                continue

            today = fields.Date.today()
            checkout_date = fields.Date.to_date(record.booking_id.checkout_date)
            remaining_nights = (checkout_date - today).days
            if remaining_nights <= 0:
                remaining_nights = 1

            room_line = record.booking_id.room_line_ids and record.booking_id.room_line_ids[0]
            current_price = room_line.price_unit if room_line else 0.0

            new_rate_record = self.env['hotel.room.rate'].search([
                ('property_id', '=', record.property_id.id),
                ('room_type_id', '=', record.new_room_id.room_type_id.id)
            ], limit=1)
            new_price = new_rate_record.fixed_rate if new_rate_record else 0.0

            price_difference = new_price - current_price
            total_adjustment = price_difference * remaining_nights

            if total_adjustment > 0:
                record.folio_impact_msg = _(
                    "⚠️ Notice: Moving from Room Category '%s' to '%s' will increase the rate by $%s per night.\n"
                    "👉 Total $%s will be AUTOMATICALLY ADDED to the guest's folio for the remaining %s night(s)."
                ) % (record.current_room_id.room_type_id.name, record.new_room_id.room_type_id.name, price_difference,
                     total_adjustment, remaining_nights)
            elif total_adjustment < 0:
                record.folio_impact_msg = _(
                    "📉 Notice: Moving to a lower category room will reduce the rate by $%s per night.\n"
                    "👉 Total $%s will be DEDUCTED/CREDITED to the guest's folio for the remaining %s night(s)."
                ) % (abs(price_difference), abs(total_adjustment), remaining_nights)
            else:
                record.folio_impact_msg = _(
                    "ℹ️ Note: No price difference between these rooms. Folio balance will remain unchanged.")

    def action_confirm_move(self):
        self.ensure_one()
        return self.booking_id.action_move_room(
            new_room_id=self.new_room_id.id,
            reason=self.reason
        )

