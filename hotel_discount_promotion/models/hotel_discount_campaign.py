# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class HotelDiscountCampaign(models.Model):
    _name = 'hotel.discount.campaign'
    _description = 'Hotel Promo Campaign & Coupons'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string="Campaign Name", required=True, tracking=True)
    code = fields.Char(string="Coupon/Promo Code", required=True, tracking=True)

    campaign_type = fields.Selection([
        ('coupon', 'Coupon Code (Single/Limited Use)'),
        ('promo', 'Promotional Campaign (Date Based)')
    ], string="Campaign Type", default='coupon', required=True)

    discount_method = fields.Selection([
        ('percentage', 'Percentage (%)'),
        ('fixed', 'Fixed Amount ($/৳)')
    ], string="Discount Method", default='percentage', required=True)

    discount_value = fields.Float(string="Discount Value", required=True, tracking=True)

    valid_from = fields.Date(string="Valid From", required=True)
    valid_to = fields.Date(string="Valid To", required=True)

    max_usage = fields.Integer(string="Max Usage Limit", default=100, help="0 means unlimited")
    current_usage = fields.Integer(string="Current Usage", default=0, readonly=True)
    active = fields.Boolean(string="Active", default=True)

    _sql_constraints = [
        ('unique_promo_code', 'unique(code)', 'The Promo/Coupon Code must be unique!')
    ]

    @api.constrains('valid_from', 'valid_to', 'discount_value', 'discount_method')
    def _check_campaign_constraints(self):
        for record in self:
            if record.valid_from > record.valid_to:
                raise ValidationError(_("Valid From date cannot be after Valid To date."))
            if record.discount_method == 'percentage' and (record.discount_value <= 0 or record.discount_value > 100):
                raise ValidationError(_("Percentage discount must be between 1 and 100%."))
            if record.discount_method == 'fixed' and record.discount_value <= 0:
                raise ValidationError(_("Fixed discount amount must be greater than 0."))