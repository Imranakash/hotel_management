# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class HotelBookingInherit(models.Model):
    _inherit = 'hotel.booking'

    promo_id = fields.Many2one('hotel.discount.campaign', string="Apply Coupon/Promo", tracking=True)

    manual_discount_type = fields.Selection([
        ('none', 'No Manual Discount'),
        ('percentage', 'Percentage (%)'),
        ('fixed', 'Fixed Amount')
    ], string="Manual Discount Type", default='none', tracking=True)

    manual_discount_value = fields.Float(string="Manual Discount Value", default=0.0, tracking=True)

    is_complimentary = fields.Boolean(string="Is Complimentary (FOC)?", default=False, tracking=True)
    complimentary_reason = fields.Selection([
        ('management', 'Management Guest / VIP'),
        ('owner', 'Owner / Shareholder'),
        ('compensation', 'Service Complaint Compensation'),
        ('staff', 'Staff Special Benefit')
    ], string="FOC Reason", tracking=True)

    approval_state = fields.Selection([
        ('not_required', 'No Approval Needed'),
        ('pending', 'Waiting Manager Approval'),
        ('approved', 'Approved by Manager'),
        ('rejected', 'Discount Rejected')
    ], string="Discount Approval Status", default='not_required', readonly=True, tracking=True)

    @api.onchange('promo_id', 'manual_discount_type', 'manual_discount_value', 'is_complimentary')
    def _onchange_calculate_discounts(self):
        for record in self:

            if record.approval_state in ['approved', 'rejected']:
                continue

            base_price = getattr(record, 'room_subtotal', 0.0)
            calculated_discount = 0.0

            if record.is_complimentary:
                calculated_discount = base_price
                record.approval_state = 'pending'

            elif record.promo_id:
                if record.promo_id.discount_method == 'percentage':
                    calculated_discount = base_price * (record.promo_id.discount_value / 100.0)
                else:
                    calculated_discount = record.promo_id.discount_value
                record.approval_state = 'not_required'

            elif record.manual_discount_type != 'none':
                if record.manual_discount_type == 'percentage':
                    calculated_discount = base_price * (record.manual_discount_value / 100.0)
                    if record.manual_discount_value > 15.0:
                        record.approval_state = 'pending'
                    else:
                        record.approval_state = 'not_required'
                else:
                    calculated_discount = record.manual_discount_value
                    if record.manual_discount_value > 5000:
                        record.approval_state = 'pending'
                    else:
                        record.approval_state = 'not_required'

            record.discount_amount = calculated_discount

    def action_approve_discount(self):

        for record in self:
            sudo_record = record.sudo()
            sudo_record.write({
                'approval_state': 'approved',
                'is_approved': True,
                'state': 'confirmed'
            })

            if record.deposit_amount > 0.0:
                sudo_record.write({'payment_state': 'partially_paid'})
            else:
                sudo_record.write({'payment_state': 'unpaid'})

            for line in record.room_line_ids:
                if line.room_id:
                    line.room_id.sudo().write({'status': 'reserved'})

            record.message_post(body=_(
                "<b>Discount Approved:</b> Manager %s approved the discount. Booking is now CONFIRMED.") % self.env.user.name)
        return True

    def action_reject_discount(self):
        for record in self:
            record.sudo().write({
                'approval_state': 'rejected',
                'state': 'draft',
                'discount_amount': 0.0,
                'manual_discount_value': 0.0,
                'manual_discount_type': 'none',
                'promo_id': False,
                'is_complimentary': False,
                'is_approved': False
            })
            record.message_post(body=_("<b>Discount Rejected:</b> Resetting booking parameters to Draft."))
        return True