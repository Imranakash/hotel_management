from datetime import datetime, time
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class HotelProperty(models.Model):
    _name = 'hotel.property'
    _description = 'Hotel Property Config'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    name = fields.Char(
        string='Property Name',
        required=True,
        tracking=True,
        help="e.g., Grand Resort, City Center Hotel"
    )
    code = fields.Char(
        string='Property Code',
        required=True,
        tracking=True,
        help="Unique short code for identification (e.g., GR01)"
    )
    company_id = fields.Many2one(
        'res.company',
        string='Owning Company',
        required=True,
        default=lambda self: self.env.company,
        tracking=True
    )
    property_type = fields.Selection([
        ('hotel', 'Standard Hotel'),
        ('resort', 'Luxury Resort'),
        ('villa_resort', 'Villa Resort'),
        ('guest_house', 'Guest House'),
        ('club', 'Club House'),
        ('serviced_apartment', 'Serviced Apartment'),
        ('eco_resort', 'Eco-Resort')
    ], string='Property Type', required=True, default='hotel', tracking=True)

    property_fixed_rate = fields.Float(string='Fixed Rate per Night', default=0.0, tracking=True)

    street = fields.Char(string='Street Address')
    street2 = fields.Char(string='Street 2')
    city = fields.Char(string='City')
    state_id = fields.Many2one('res.country.state', string='State')
    zip_code = fields.Char(string='ZIP/Postal Code')
    country_id = fields.Many2one('res.country', string='Country')

    phone = fields.Char(string='Phone Number')
    email = fields.Char(string='Email Address')
    website = fields.Char(string='Website')
    vat_number = fields.Char(string='Tax/VAT Registration No')

    default_checkin_time = fields.Float(
        string='Default Check-In Time',
        default=14.0,
        required=True,
        help="Standard arrival hour expressed in float time (e.g., 14.0 = 02:00 PM)"
    )
    default_checkout_time = fields.Float(
        string='Default Check-Out Time',
        default=12.0,
        required=True,
        help="Standard departure hour expressed in float time (e.g., 12.0 = 12:00 PM)"
    )

    currency_id = fields.Many2one(
        'res.currency',
        string='Default Currency',
        required=True,
        default=lambda self: self.env.company.currency_id
    )

    @api.constrains('default_checkin_time', 'default_checkout_time')
    def _check_standard_hours(self):
        for record in self:
            if not (0.0 <= record.default_checkin_time < 24.0) or not (0.0 <= record.default_checkout_time < 24.0):
                raise ValidationError(
                    _("Configuration Error: Standard time hours must be strictly between 00:00 and 23:59."))

    _sql_constraints = [
        ('unique_property_code_per_company', 'unique(code, company_id)',
         'The property code must be unique per company!')
    ]

    def action_open_room_dashboard(self):
        self.ensure_one()
        return {
            'name': _('Room Status Dashboard - %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'hotel.room',
            'view_mode': 'list,form',
            'domain': [('property_id', '=', self.id)],
            'context': {'default_property_id': self.id}
        }

    def action_open_today_arrivals(self):
        self.ensure_one()

        today = fields.Date.context_today(self)
        return {
            'name': _('Today Arrivals - %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'hotel.booking',
            'view_mode': 'list,form',
            'domain': [
                ('property_id', '=', self.id),
                ('checkin_date', '>=', fields.Datetime.to_string(datetime.combine(today, time.min))),
                ('checkin_date', '<=', fields.Datetime.to_string(datetime.combine(today, time.max))),
                ('state', 'in', ['confirmed', 'tentative'])
            ],
        }

    def action_open_today_departures(self):
        self.ensure_one()
        today = fields.Date.context_today(self)
        return {
            'name': _('Today Departures - %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'hotel.booking',
            'view_mode': 'list,form',
            'domain': [
                ('property_id', '=', self.id),

                ('checkout_date', '<=', fields.Datetime.to_string(datetime.combine(today, time.max))),
                ('state', '=', 'checked_in')
            ],
        }