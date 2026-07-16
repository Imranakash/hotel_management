from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class HotelCheckinWizard(models.TransientModel):
    _name = 'hotel.checkin.wizard'
    _description = 'Hotel Check-In Room Allocation Wizard'

    booking_id = fields.Many2one('hotel.booking', string="Booking", required=True)
    property_id = fields.Many2one('hotel.property', string="Property")
    line_ids = fields.One2many('hotel.checkin.wizard.line', 'wizard_id', string="Rooms to Allocate")

    def action_assign_rooms_and_confirm_checkin(self):
        self.ensure_one()
        booking = self.booking_id

        for wizard_line in self.line_ids:
            if not wizard_line.room_id:
                raise ValidationError(_("You cannot check in without selecting a room!!"))

            booking_line = booking.room_line_ids.filtered(
                lambda l: l.room_type_id == wizard_line.room_type_id and not l.room_id
            )
            if booking_line:
                booking_line[0].write({'room_id': wizard_line.room_id.id})


            wizard_line.room_id.write({'status': 'occupied'})

        booking.action_actual_check_in()

        return {'type': 'ir.actions.act_window_close'}


class HotelCheckinWizardLine(models.TransientModel):
    _name = 'hotel.checkin.wizard.line'
    _description = 'Check-In Wizard Line'

    wizard_id = fields.Many2one('hotel.checkin.wizard', string="Wizard")
    room_type_id = fields.Many2one('hotel.room.type', string="Room Category", readonly=True)

    room_id = fields.Many2one(
        'hotel.room',
        string="Select Available Room",
        domain="[('property_id', '=', parent.property_id), ('room_type_id', '=', room_type_id), ('status', '=', 'available')]"
    )