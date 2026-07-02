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

    @api.depends('property_id', 'current_room_id')
    def _compute_room_domain(self):
        for record in self:
            domain = [('status', '=', 'available')]
            if record.property_id:
                domain.append(('property_id', '=', record.property_id.id))
            if record.current_room_id:
                domain.append(('id', '!=', record.current_room_id.id))

            record.room_domain = str(domain)

    def action_confirm_move(self):
        self.ensure_one()
        return self.booking_id.action_move_room(
            new_room_id=self.new_room_id.id,
            reason=self.reason
        )