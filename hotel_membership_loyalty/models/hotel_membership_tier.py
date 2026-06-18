# -*- coding: utf-8 -*-
from odoo import models, fields

class HotelMembershipTier(models.Model):
    _name = 'hotel.membership.tier'
    _description = 'Hotel VIP Membership Tier'
    _order = 'sequence'

    name = fields.Char(string='Tier Name', required=True, translate=True)
    code = fields.Char(string='Tier Code', required=True)
    sequence = fields.Integer(default=10)
    min_points = fields.Integer(string='Minimum Points Required', default=0)
    discount_room = fields.Float(string='Room Discount (%)', default=0.0)
    discount_fnb = fields.Float(string='F&B Bill Discount (%)', default=0.0)
    free_night_points = fields.Integer(string='Points Per Free Night', default=1000)
    benefit_ids = fields.Many2many('hotel.membership.benefit', string='Tier Benefits')

class HotelMembershipBenefit(models.Model):
    _name = 'hotel.membership.benefit'
    _description = 'Membership Benefits'

    name = fields.Char(string='Benefit Name', required=True)
    description = fields.Text(string='Description')