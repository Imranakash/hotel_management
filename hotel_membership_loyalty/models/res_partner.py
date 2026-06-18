# -*- coding: utf-8 -*-
from odoo import models, fields, api

class ResPartner(models.Model):
    _inherit = 'res.partner'

    membership_card_no = fields.Char(string='Membership Card No', copy=False, readonly=True)
    membership_tier_id = fields.Many2one('hotel.membership.tier', string='VIP Tier', compute='_compute_membership_tier', store=True)
    loyalty_points_balance = fields.Integer(string='Loyalty Points Balance', compute='_compute_loyalty_points', store=True)
    total_points_earned = fields.Integer(string='Total Points Earned', compute='_compute_loyalty_points', store=True)
    loyalty_history_ids = fields.One2many('hotel.loyalty.history', 'partner_id', string='Loyalty Ledger')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('membership_card_no'):
                vals['membership_card_no'] = self.env['ir.sequence'].next_by_code('hotel.membership.card.seq') or '/'
        return super().create(vals_list)

    @api.depends('loyalty_history_ids.points', 'loyalty_history_ids.transaction_type')
    def _compute_loyalty_points(self):
        for partner in self:
            earned = sum(h.points for h in partner.loyalty_history_ids if h.transaction_type == 'earn')
            redeemed = sum(h.points for h in partner.loyalty_history_ids if h.transaction_type == 'redeem')
            partner.total_points_earned = earned
            partner.loyalty_points_balance = earned - redeemed

    @api.depends('total_points_earned')
    def _compute_membership_tier(self):
        for partner in self:
            if partner.total_points_earned > 0:
                tier = self.env['hotel.membership.tier'].search([
                    ('min_points', '<=', partner.total_points_earned)
                ], order='min_points desc', limit=1)
                partner.membership_tier_id = tier.id if tier else False
            else:
                partner.membership_tier_id = False