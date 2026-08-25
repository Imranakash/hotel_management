# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class HotelRoomAvailabilityWizard(models.TransientModel):
    _name = 'hotel.room.availability.wizard'
    _description = 'Room Category Availability Search'

    name = fields.Char(
        string='Name',
        default='Room Availability',
        readonly=True,
    )

    property_id = fields.Many2one(
        'hotel.property',
        string='Property/Hotel',
        required=True,
    )
    room_type_id = fields.Many2one(
        'hotel.room.type',
        string='Room Category',
        required=True,
        domain="[('room_ids.property_id', '=', property_id)]",
    )
    date_from = fields.Date(
        string='Date From',
        required=True,
        default=fields.Date.context_today,
    )
    date_to = fields.Date(
        string='Date To',
        required=True,
    )

    result_html = fields.Html(
        string='Availability Result',
        readonly=True,
        sanitize=False,
    )

    @api.onchange('property_id')
    def _onchange_property_id(self):
        self.room_type_id = False

    @api.onchange('date_from')
    def _onchange_date_from(self):
        if self.date_from and (not self.date_to or self.date_to <= self.date_from):
            self.date_to = self.date_from

    def action_search(self):
        self.ensure_one()

        if self.date_to <= self.date_from:
            raise UserError(_("Date To must be after Date From."))

        total_rooms = self.env['hotel.room'].search_count([
            ('property_id', '=', self.property_id.id),
            ('room_type_id', '=', self.room_type_id.id),
        ])

        overlapping_lines = self.env['hotel.booking.room.line'].search([
            ('room_type_id', '=', self.room_type_id.id),
            ('booking_id.property_id', '=', self.property_id.id),
            ('booking_id.state', 'in', ['confirmed', 'checked_in']),
            ('booking_id.checkin_date', '<', self.date_to),
            ('booking_id.checkout_date', '>', self.date_from),
        ])

        booked_count = len(overlapping_lines)
        available_count = max(0, total_rooms - booked_count)

        badges = []
        for line in overlapping_lines.sorted(lambda l: l.booking_id.checkin_date or fields.Date.today()):
            b = line.booking_id
            if not b.checkin_date or not b.checkout_date:
                continue
            badges.append(
                '<span class="badge rounded-pill me-2 mb-2 px-3 py-2" '
                'style="font-size:12px; background:#dc3545; color:#fff;">'
                '<i class="fa fa-calendar me-1"/> %s - %s'
                '</span>' % (b.checkin_date.strftime('%d %b'), b.checkout_date.strftime('%d %b'))
            )

        badges_html = ''.join(badges) if badges else (
            '<div class="text-muted fst-italic">No confirmed bookings found in this date range.</div>'
        )

        border_color = '28a745' if available_count > 0 else 'dc3545'

        result_html = '''
            <div class="p-0 rounded-3 bg-white overflow-hidden"
                 style="border: 1px solid #e0e0e0; border-left: 6px solid #%(border_color)s;
                        box-shadow: 0 4px 6px rgba(0,0,0,0.05);">
                <div class="p-4">
                    <div class="d-flex justify-content-between align-items-center mb-3">
                        <div>
                            <div class="text-uppercase fw-bold text-dark opacity-75" style="font-size:11px; letter-spacing:0.5px;">
                                <i class="fa fa-building me-1 text-primary"/> %(property)s
                            </div>
                            <h3 class="fw-black mb-0 text-dark mt-1" style="font-size:22px; font-weight:800;">
                                <i class="fa fa-bed text-primary me-2"/> %(room_type)s
                            </h3>
                        </div>
                        <div class="text-muted text-end small">
                            <i class="fa fa-calendar-o me-1"/> %(date_from)s - %(date_to)s
                        </div>
                    </div>

                    <div class="d-flex gap-3 mb-4">
                        <div class="text-center px-4 py-3 rounded-3 flex-fill" style="background:#f1f3f5;">
                            <div class="fw-bold" style="font-size:24px;">%(total)s</div>
                            <div class="text-muted small text-uppercase" style="font-size:10px;">Total Rooms</div>
                        </div>
                        <div class="text-center px-4 py-3 rounded-3 flex-fill" style="background:#d1e7dd;">
                            <div class="fw-bold text-success" style="font-size:24px;">%(available)s</div>
                            <div class="text-muted small text-uppercase" style="font-size:10px;">Available</div>
                        </div>
                        <div class="text-center px-4 py-3 rounded-3 flex-fill" style="background:#f8d7da;">
                            <div class="fw-bold text-danger" style="font-size:24px;">%(booked)s</div>
                            <div class="text-muted small text-uppercase" style="font-size:10px;">Booked</div>
                        </div>
                    </div>

                    <div class="pt-3 border-top" style="border-top-color:#f1f1f1 !important;">
                        <div class="text-muted small text-uppercase fw-bold mb-2" style="font-size:10px; letter-spacing:0.5px;">
                            Confirmed Booking Dates in This Range
                        </div>
                        <div>%(badges)s</div>
                    </div>
                </div>
            </div>
        ''' % {
            'room_type': self.room_type_id.name,
            'property': self.property_id.name,
            'total': total_rooms,
            'available': available_count,
            'booked': booked_count,
            'badges': badges_html,
            'border_color': border_color,
            'date_from': self.date_from.strftime('%d %b %Y'),
            'date_to': self.date_to.strftime('%d %b %Y'),
        }

        self.result_html = result_html

        return {
            'name': _('Room Availability'),
            'type': 'ir.actions.act_window',
            'res_model': 'hotel.room.availability.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'current',
            'context': self.env.context,
        }