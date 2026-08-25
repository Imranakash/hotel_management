# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class HotelLoyaltyHistory(models.Model):
    _name = 'hotel.loyalty.history'
    _description = 'Loyalty Points & Redemption History'
    _order = 'date desc'

    partner_id = fields.Many2one('res.partner', string='Customer', required=True, ondelete='cascade')
    date = fields.Date(string='Date', default=fields.Date.context_today)
    transaction_type = fields.Selection([
        ('earn', 'Points Earned'),
        ('redeem', 'Points Redeemed')
    ], string='Type', required=True, default='earn')
    points = fields.Integer(string='Points', required=True)
    source_document = fields.Char(string='Source Document/Reference')
    redemption_type = fields.Selection([
        ('free_night', 'Free Night Stay'),
        ('fnb_voucher', 'F&B Voucher'),
        ('spa_voucher', 'Spa Voucher'),
        ('none', 'N/A')
    ], string='Redemption Type', default='none')
    free_nights_count = fields.Integer(string='Free Nights Redeemed', default=0)
    description = fields.Char(string='Description / Reason', required=True)

    @api.constrains('points', 'transaction_type', 'partner_id')
    def _check_points_balance(self):
        for record in self:
            if record.transaction_type == 'redeem':
                other_history = self.env['hotel.loyalty.history'].search([
                    ('partner_id', '=', record.partner_id.id),
                    ('id', '!=', record.id or 0)
                ])
                current_balance = sum(h.points if h.transaction_type == 'earn' else -h.points for h in other_history)
                if current_balance < record.points:
                    raise ValidationError(_("Insufficient Points! Customer '%s' only has %s points. Cannot redeem %s points.") % (record.partner_id.name, current_balance, record.points))

    @api.onchange('free_nights_count', 'partner_id', 'redemption_type')
    def _onchange_free_nights(self):
        if self.transaction_type == 'redeem' and self.redemption_type == 'free_night' and self.partner_id.membership_tier_id:
            tier = self.partner_id.membership_tier_id
            self.points = self.free_nights_count * tier.free_night_points