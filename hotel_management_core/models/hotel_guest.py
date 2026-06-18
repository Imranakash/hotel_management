from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ResPartner(models.Model):
    _inherit = 'res.partner'

    is_hotel_guest = fields.Boolean(
        string='Is a Hotel Guest',
        default=False,
        help="Check this if the contact is a hotel client/guest."
    )

    vip_tier = fields.Selection([
        ('regular', 'Regular Guest'),
        ('silver', 'Silver Member'),
        ('gold', 'Gold VIP'),
        ('platinum', 'Platinum Elite')
    ], string='VIP / Membership Tier', default='regular', tracking=True)

    id_type = fields.Selection([
        ('nid', 'National ID (NID)'),
        ('passport', 'Passport'),
        ('driving_license', 'Driving License'),
        ('birth_certificate', 'Birth Certificate')
    ], string='Identification Type', tracking=True)

    id_number = fields.Char(string='ID / Document Number', tracking=True)
    nationality_id = fields.Many2one('res.country', string='Guest Nationality')

    is_blacklisted_guest = fields.Boolean(
        string='Blacklisted Guest',
        default=False,
        tracking=True,
        help="If checked, this guest will trigger a warning during reservations."
    )
    blacklist_reason = fields.Text(string='Reason for Blacklisting')

    booking_ids = fields.One2many(
        'hotel.booking',
        'guest_id',
        string='Stay/Booking History',
        readonly=True
    )
    total_stays = fields.Integer(
        string='Total Stays Count',
        compute='_compute_guest_stats',
        store=True
    )

    @api.depends('booking_ids.state')
    def _compute_guest_stats(self):
        for record in self:
            completed_bookings = record.booking_ids.filtered(lambda b: b.state in ['checked_out'])
            record.total_stays = len(completed_bookings)

    @api.constrains('is_blacklisted_guest', 'blacklist_reason')
    def _check_blacklist_reason(self):
        for record in self:
            if record.is_blacklisted_guest and not record.blacklist_reason:
                raise ValidationError(
                    _("Security Policy Rule: You must provide a valid reason if you are blacklisting a guest profile."))

    @api.onchange('is_blacklisted_guest')
    def _onchange_blacklist_warning(self):
        if self.is_blacklisted_guest:
            return {
                'warning': {
                    'title': _("Security Warning!"),
                    'message': _(
                        "You are marking this guest profile as Blacklisted. This will restrict future booking operations for this individual."),
                }
            }