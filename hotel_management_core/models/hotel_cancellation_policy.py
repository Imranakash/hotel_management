from odoo import models, fields

class HotelCancellationPolicy(models.Model):
    _name = 'hotel.cancellation.policy'
    _description = 'Hotel Cancellation Policy'
    _order = 'days_before desc'

    name = fields.Char(string='Policy Name', required=True)
    days_before = fields.Integer(string='Days Before Check-in', required=True)
    refund_percentage = fields.Float(string='Refund (%)', required=True, default=100.0)
    property_id = fields.Many2one(
        'hotel.property',
        string='Property / Hotel',
        help="Leave empty if this policy applies to all hotels"
    )