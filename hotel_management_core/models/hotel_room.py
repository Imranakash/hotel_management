from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class HotelRoom(models.Model):
    _name = 'hotel.room'
    _description = 'Physical Hotel Room Unit'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'room_number'

    active = fields.Boolean(default=True)

    name = fields.Char(
        string='Display Name',
        compute='_compute_display_name_custom',
        store=True,
        tracking=True
    )
    room_number = fields.Char(
        string='Room/Unit Number',
        required=True,
        tracking=True,
        help="e.g., 101, 204, V-01"
    )

    property_id = fields.Many2one(
        'hotel.property',
        string='Parent Property/Hotel',
        required=True,
        tracking=True,
        default=lambda self: self.env['hotel.property'].search([('company_id', '=', self.env.company.id)], limit=1)
    )
    room_type_id = fields.Many2one(
        'hotel.room.type',
        string='Room Category',
        required=True,
        tracking=True
    )

    building_id = fields.Many2one(
        'hotel.building',
        string='Building/Tower',
        domain="[('property_id', '=', property_id)]"
    )
    floor_id = fields.Many2one(
        'hotel.floor',
        string='Floor',
        domain="[('property_id', '=', property_id), ('building_id', '=', building_id)]"
    )
    zone_id = fields.Many2one(
        'hotel.zone',
        string='Operational Zone',
        domain="[('property_id', '=', property_id)]"
    )

    status = fields.Selection([
        ('available', 'Available'),
        ('reserved', 'Reserved'),
        ('occupied', 'Occupied'),
        ('dirty', 'Dirty'),
        ('clean', 'Clean'),
        ('inspected', 'Inspected'),
        ('maintenance', 'Maintenance'),
        ('out_of_order', 'Out of Order'),
        ('blocked', 'Blocked')
    ], string='Current Status', default='available', tracking=True, required=True)

    operational_status = fields.Selection([
        ('active', 'Active / Operational'),
        ('inactive', 'Inactive'),
        ('renovation', 'Under Renovation'),
        ('seasonal_closed', 'Seasonal Closed')
    ], string='Operational State', default='active', tracking=True, required=True)

    amenity_ids = fields.Many2many(
        'hotel.room.amenity',
        string='Room Amenities',
        help="Wi-Fi, Mini Bar, Bathtub, etc."
    )
    hk_instruction = fields.Text(string='Housekeeping Special Instructions')
    internal_notes = fields.Text(string='Internal Management Notes')

    @api.depends('room_number', 'room_type_id')
    def _compute_display_name_custom(self):
        for record in self:
            if record.room_number and record.room_type_id:
                record.name = f"Room {record.room_number} ({record.room_type_id.name})"
            else:
                record.name = record.room_number or _("New Room")

    _sql_constraints = [
        ('unique_room_number_per_property', 'unique(room_number, property_id)',
         'The room or unit number must be unique per property/hotel!')
    ]

    def action_set_room_clean(self):
        for record in self:
            if record.status == 'dirty':
                record.status = 'clean'
                record.message_post(body="🧹 Room has been cleaned by Housekeeping staff.")

    def action_set_room_inspected(self):
        for record in self:
            if record.status == 'clean':
                record.status = 'available'
                record.message_post(body="✅ Room inspected and marked as AVAILABLE for new bookings.")


class HotelRoomAmenity(models.Model):
    _name = 'hotel.room.amenity'
    _description = 'Room Amenities Master Data'

    name = fields.Char(string='Amenity Name', required=True)
    code = fields.Char(string='Amenity Code')
    description = fields.Text(string='Description')

    _sql_constraints = [
        ('unique_amenity_code', 'unique(code)', 'Amenity code must be unique!')
    ]


class HotelRoomMaintenance(models.Model):
    _name = 'hotel.room.maintenance'
    _description = 'Hotel Room Maintenance Ticket'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string="Ticket ID", required=True, copy=False, readonly=True, default=lambda self: _('New'))
    room_id = fields.Many2one('hotel.room', string="Room Under Maintenance", required=True)
    booking_id = fields.Many2one('hotel.booking', string="Triggered From Booking")
    reason = fields.Char(string="Issue / Reason", required=True)
    ticket_date = fields.Datetime(string="Reported Date", default=fields.Datetime.now)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('under_review', 'Under Review'),
        ('resolved', 'Resolved')
    ], string="Status", default='draft', tracking=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('hotel.room.maintenance') or _('New')
        return super(HotelRoomMaintenance, self).create(vals_list)

    def action_resolve_maintenance(self):
        for record in self:
            record.write({'state': 'resolved'})
            if record.room_id.status == 'maintenance':
                record.room_id.write({'status': 'available'})