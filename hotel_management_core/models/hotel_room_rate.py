# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError

class HotelRoomRate(models.Model):
    _name = 'hotel.room.rate'
    _description = 'Hotel Room Rate Configuration'
    _rec_name = 'property_id'

    property_id = fields.Many2one('hotel.property', string='Resort/Hotel', required=True)
    room_type_id = fields.Many2one('hotel.room.type', string='Room Category', required=True)
    fixed_rate = fields.Float(string='Rate per Night', digits=(16, 2), required=True)
    max_discount = fields.Float(string="Maximum Discount", digits=(16, 2), default=0.0)
    extra_bed_rate = fields.Float(string='Extra Bed Rate per Night', default=0.0)

    _sql_constraints = [
        ('unique_property_room_type', 'unique(property_id, room_type_id)',
         'This Room Category rate is already configured for this Resort!')
    ]


    @api.constrains('property_id', 'room_type_id')
    def _check_unique_property_room_type(self):
        for record in self:
            if record.property_id and record.room_type_id:
                duplicate = self.env['hotel.room.rate'].search([
                    ('property_id', '=', record.property_id.id),
                    ('room_type_id', '=', record.room_type_id.id),
                    ('id', '!=', record.id)
                ])
                if duplicate:
                    raise ValidationError(
                        "🛑 Conflict! Room Category '%s' rate is already configured for '%s'. Duplicate entries are blocked!"
                        % (record.room_type_id.name, record.property_id.name)
                    )