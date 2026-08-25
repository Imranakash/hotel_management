from odoo import models, fields, api, _

class HotelBookingCancelWizard(models.TransientModel):
    _name = 'hotel.booking.cancel.wizard'
    _description = 'Hotel Booking Cancellation Wizard'

    booking_id = fields.Many2one('hotel.booking', string="Booking", required=True)
    advance_amount = fields.Float(string="Advance Paid", readonly=True)
    refund_percentage = fields.Float(string="Refund (%)", readonly=True)
    refund_amount = fields.Float(string="Refund Amount", readonly=True)
    cancellation_fee = fields.Float(string="Cancellation Charge", readonly=True)

    def action_confirm_cancel(self):
        self.ensure_one()

        self.booking_id.write({
            'refund_amount': self.refund_amount,
            'forfeiture_amount': self.cancellation_fee,
            'cancellation_fee': self.cancellation_fee,
            'cancellation_date': fields.Datetime.now(),
            'state': 'cancelled',
        })
        return {'type': 'ir.actions.act_window_close'}