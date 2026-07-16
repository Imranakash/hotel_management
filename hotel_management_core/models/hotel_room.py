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
        domain="[('property_id', '=', property_id)]", tracking=True
    )
    floor_id = fields.Many2one(
        'hotel.floor',
        string='Floor',
        domain="[('property_id', '=', property_id), ('building_id', '=', building_id)]",
        tracking=True
    )

    zone_id = fields.Many2one(
        'hotel.zone',
        string='Operational Zone',
        domain="[('property_id', '=', property_id)]", tracking=True
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

    hk_instruction = fields.Text(string='Housekeeping Special Instructions')
    internal_notes = fields.Text(string='Internal Management Notes')

    @api.onchange('property_id')
    def _onchange_property_id(self):
        self.building_id = False
        self.floor_id = False

    @api.onchange('building_id')
    def _onchange_building_id(self):
        current_floor_building = getattr(self.floor_id, 'building_id', False)
        if current_floor_building and current_floor_building != self.building_id:
            self.floor_id = False

    @api.onchange('floor_id')
    def _onchange_floor_id(self):
        floor_building = getattr(self.floor_id, 'building_id', False)
        if floor_building:
            self.building_id = floor_building

    @api.depends('room_number', 'room_type_id', 'building_id.name', 'floor_id.name')
    def _compute_display_name_custom(self):
        for record in self:
            if record.room_number and record.room_type_id:
                record.name = f"Room {record.room_number} ({record.room_type_id.name})"
            else:
                record.name = record.room_number or _("New Room")

    def _compute_display_name(self):
        for record in self:
            building = record.building_id.name if record.building_id else "No Building"
            floor = record.floor_id.name if record.floor_id else "No Floor"
            record.display_name = f"Room {record.room_number or record.id} ({building} - {floor})"



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

    def action_dashboard_book_room(self):

        self.ensure_one()
        return {
            'name': 'New Reservation',
            'type': 'ir.actions.act_window',
            'res_model': 'hotel.booking',
            'view_mode': 'form',
            'target': 'current',
            'context': {
                'default_property_id': self.property_id.id,
                'default_room_line_ids': [
                    (0, 0, {
                        'room_type_id': self.room_type_id.id,
                        'room_id': self.id,
                    })
                ]
            }
        }

    def action_dashboard_see_details(self):

        self.ensure_one()
        booking_line = self.env['hotel.booking.room.line'].search([
            ('room_id', '=', self.id),
            ('booking_id.state', 'in', ['confirmed', 'checked_in'])
        ], limit=1)

        if not booking_line:
            booking_line = self.env['hotel.booking.room.line'].search([
                ('room_id', '=', self.id)
            ], order='id desc', limit=1)

        if not booking_line or not booking_line.booking_id:
            from odoo.exceptions import ValidationError
            raise ValidationError("No reservation details found found for this room in system!")

        return {
            'name': f"Booking Details - Room {self.room_number}",
            'type': 'ir.actions.act_window',
            'res_model': 'hotel.booking',
            'view_mode': 'form',
            'res_id': booking_line.booking_id.id,

            'view_id': self.env.ref('hotel_management_core.view_hotel_booking_simple_popup').id,
            'target': 'new',
        }

    @api.constrains('room_number', 'property_id')
    def _check_unique_room_per_property(self):
        for record in self:
            if record.room_number and record.property_id:
                duplicate_room = self.search([
                    ('room_number', '=', record.room_number),
                    ('property_id', '=', record.property_id.id),
                    ('id', '!=', record.id)
                ], limit=1)

                if duplicate_room:
                    raise ValidationError(_(
                        "🚨 Business Rule Violation:\n"
                        "The Room/Unit Number '%s' already exists in '%s'!\n"
                        "Duplicate rooms are strictly prohibited."
                    ) % (record.room_number, record.property_id.name))


class HotelRoomAmenity(models.Model):
    _name = 'hotel.room.amenity'
    _description = 'Room Amenities Master Data'

    name = fields.Char(string='Amenity Name', required=True)
    code = fields.Char(string='Amenity Code')
    description = fields.Text(string='Description')
    color = fields.Integer(string='Color Index', default=0)

    _sql_constraints = [
        ('unique_amenity_code', 'unique(code)', 'Amenity code must be unique!')
    ]


class HotelRoomMaintenance(models.Model):
    _name = 'hotel.room.maintenance'
    _description = 'Hotel Room Maintenance Ticket'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string="Ticket ID", required=True, copy=False, readonly=True, default=lambda self: _('New'))
    room_id = fields.Many2one('hotel.room', string="Room Under Maintenance", required=True,tracking=True)
    booking_id = fields.Many2one('hotel.booking', string="Triggered From Booking")
    reason = fields.Char(string="Issue / Reason", required=True,tracking=True)
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






