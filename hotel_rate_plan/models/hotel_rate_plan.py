# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class HotelRatePlan(models.Model):
    _name = 'hotel.rate.plan'
    _description = 'Hotel Rate Plan'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string="Rate Plan Name", required=True, tracking=True)
    code = fields.Char(string="Code", required=True, tracking=True)
    valid_from = fields.Date(string="Valid From")
    valid_to = fields.Date(string="Valid To")
    priority = fields.Integer(string="Priority", default=10)
    market_segment = fields.Selection([
        ('direct', 'Direct Walk-In'),
        ('corporate', 'Corporate Contract'),
        ('ota', 'OTA (Booking.com/Agoda)'),
        ('member', 'Loyalty Member'),
        ('group', 'Group Booking')
    ], string="Market Segment", default='direct', tracking=True)

    tax_included = fields.Boolean(string="Tax Included", default=False)
    service_charge_included = fields.Boolean(string="Service Charge Included", default=False)
    rate_line_ids = fields.One2many('hotel.rate.plan.line', 'rate_plan_id', string="Pricing Rules")

    @api.constrains('valid_from', 'valid_to')
    def _check_dates(self):
        for record in self:
            if record.valid_from and record.valid_to and record.valid_from > record.valid_to:
                raise ValidationError(_("Error! 'Valid From' date cannot be after 'Valid To' date."))


class HotelRatePlanLine(models.Model):
    _name = 'hotel.rate.plan.line'
    _description = 'Hotel Rate Plan Pricing Rules'

    rate_plan_id = fields.Many2one('hotel.rate.plan', string="Rate Plan", ondelete='cascade', required=True)
    room_id = fields.Many2one('hotel.room', string="Room Reference", required=True)
    date_from = fields.Date(string="Date From")
    date_to = fields.Date(string="Date To")

    base_rate = fields.Float(string="Base Nightly Rate", required=True, default=0.0)
    weekend_rate = fields.Float(string="Weekend Rate (Fri-Sat)", default=0.0)
    extra_adult_charge = fields.Float(string="Extra Adult Charge", default=0.0)
    extra_child_charge = fields.Float(string="Extra Child Charge", default=0.0)
    extra_bed_charge = fields.Float(string="Extra Bed Charge", default=0.0)


class HotelPackage(models.Model):
    _name = 'hotel.package'
    _description = 'Hotel Bundled Packages'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string="Package Name", required=True, tracking=True)
    code = fields.Char(string="Package Code", required=True, tracking=True)
    valid_from = fields.Date(string="Valid From")
    valid_to = fields.Date(string="Valid To")

    price_mode = fields.Selection([
        ('fixed', 'Fixed Package Price'),
        ('dynamic', 'Dynamic (Room Rate + Add-ons)')
    ], string="Price Mode", default='fixed', required=True)

    fixed_package_price = fields.Float(string="Fixed Package Price", default=0.0)
    inclusion_notes = fields.Text(string="Package Inclusions")


class HotelProperty(models.Model):
    _inherit = 'hotel.property'
    early_checkin_charge_type = fields.Selection([
        ('fixed', 'Fixed Amount'),
        ('percentage', 'Percentage of Room Rate'),
        ('free', 'Complimentary / Free')
    ], string="Early Check-In Policy", default='free')
    early_checkin_fee = fields.Float(string="Early Check-In Fee")

    late_checkout_charge_type = fields.Selection([
        ('fixed', 'Fixed Amount'),
        ('percentage', 'Percentage of Room Rate'),
        ('free', 'Complimentary / Free')
    ], string="Late Check-Out Policy", default='free')
    late_checkout_fee = fields.Float(string="Late Check-Out Fee")