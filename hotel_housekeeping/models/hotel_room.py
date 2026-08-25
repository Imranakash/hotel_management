from odoo import models, fields


class HotelRoom(models.Model):
    _inherit = 'hotel.room'

    housekeeping_state = fields.Selection([
        ('dirty', 'Dirty'),
        ('clean', 'Clean'),
        ('inspected', 'Inspected'),
    ], string='Housekeeping Status', default='dirty', tracking=True)