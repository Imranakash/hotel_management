# -*- coding: utf-8 -*-
from odoo import models, fields

class HotelLoyaltyRule(models.Model):
    _name = 'hotel.loyalty.rule'
    _description = 'Loyalty Points Earning Rules'

    name = fields.Char(string='Rule Name', required=True)
    rule_type = fields.Selection([
        ('room', 'Room Revenue'),
        ('fnb', 'Food & Beverage'),
        ('spa', 'Spa & Wellness')
    ], string='Rule Type', required=True, default='room')
    amount_per_point = fields.Float(string='Spend Amount Per Point', default=100.0, required=True)
    valid_from = fields.Date(string='Valid From')
    valid_to = fields.Date(string='Valid To')
    active = fields.Boolean(default=True)