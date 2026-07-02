# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class HotelBookingApprovalWizard(models.TransientModel):
    _name = 'hotel.booking.approval.wizard'
    _description = 'Hotel Booking Approval Wizard'

    booking_id = fields.Many2one('hotel.booking', string="Booking", required=True)
    approval_state = fields.Selection([
        ('no_needed', 'No Approval Needed'),
        ('not_required', 'Not Required'),
        ('waiting', 'Waiting Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected')
    ], string='Approval Status', readonly=True)

    is_credit_exceeded = fields.Boolean(string='Credit Limit Exceeded', readonly=True)
    approval_reason = fields.Text(string='Approval/Rejection Reason', required=True)

    def button_approve(self):
        self.ensure_one()
        if self.booking_id:
            self.booking_id.write({
                'approval_reason': self.approval_reason,
            })

            self.booking_id.action_approve_discount()

            return {
                'type': 'ir.actions.act_window',
                'name': 'Reservation / Booking',
                'res_model': 'hotel.booking',
                'res_id': self.booking_id.id,
                'view_mode': 'form',
                'target': 'main',
            }
        return {'type': 'ir.actions.act_window_close'}

    def button_reject(self):
        self.ensure_one()
        if self.booking_id:
            self.booking_id.write({
                'approval_reason': self.approval_reason,
            })

            self.booking_id.action_reject_discount()

            return {
                'type': 'ir.actions.act_window',
                'name': 'Reservation / Booking',
                'res_model': 'hotel.booking',
                'res_id': self.booking_id.id,
                'view_mode': 'form',
                'target': 'main',
            }
        return {'type': 'ir.actions.act_window_close'}