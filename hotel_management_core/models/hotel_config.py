from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class HotelBuilding(models.Model):
    _name = 'hotel.building'
    _description = 'Hotel Building/Tower'
    _order = 'sequence, id'

    name = fields.Char(string='Building Name', required=True)
    code = fields.Char(string='Short Code', help="e.g., T1 for Tower 1")
    property_id = fields.Many2one(
        'hotel.property',
        string='Parent Property',
        required=True,
        ondelete='cascade'
    )
    sequence = fields.Integer(string='Sequence', default=10)
    active = fields.Boolean(string='Active', default=True)

    _sql_constraints = [
        ('unique_building_code_per_property', 'unique(code, property_id)',
         'The building code must be unique per property/hotel!')
    ]


class HotelFloor(models.Model):
    _name = 'hotel.floor'
    _description = 'Hotel Floor'
    _order = 'sequence, id'

    name = fields.Char(string='Floor Name/Number', required=True)
    code = fields.Char(string='Floor Code', help="e.g., FL1, FL2")
    property_id = fields.Many2one(
        'hotel.property',
        string='Parent Property',
        required=True,
        ondelete='cascade'
    )
    building_id = fields.Many2one(
        'hotel.building',
        string='Building',
        domain="[('property_id', '=', property_id)]"
    )
    sequence = fields.Integer(string='Sequence', default=10)
    active = fields.Boolean(string='Active', default=True)


class HotelZone(models.Model):
    _name = 'hotel.zone'
    _description = 'Hotel Zone/Area'
    _order = 'sequence, id'

    name = fields.Char(string='Zone Name', required=True)
    code = fields.Char(string='Zone Code')
    property_id = fields.Many2one(
        'hotel.property',
        string='Parent Property',
        required=True,
        ondelete='cascade'
    )
    sequence = fields.Integer(string='Sequence', default=10)
    active = fields.Boolean(string='Active', default=True)


class HotelRoomType(models.Model):
    _name = 'hotel.room.type'
    _description = 'Room Type / Category'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    name = fields.Char(string='Room Type Name', required=True, tracking=True)
    code = fields.Char(string='Type Code', required=True, tracking=True)

    base_adults = fields.Integer(string='Base Adults Capacity', default=2, required=True, tracking=True)
    base_children = fields.Integer(string='Base Children Capacity', default=0, tracking=True)
    max_capacity = fields.Integer(string='Maximum Capacity', default=4, required=True, tracking=True)

    allow_extra_bed = fields.Boolean(string='Allow Extra Bed', default=True, tracking=True)
    max_extra_beds = fields.Integer(string='Max Extra Beds Allowed', default=1, tracking=True)

    description = fields.Text(string='Description / Features')
    active = fields.Boolean(string='Active', default=True)

    @api.constrains('base_adults', 'base_children', 'max_capacity', 'allow_extra_bed', 'max_extra_beds')
    def _check_capacity_rules(self):

        for record in self:
            if record.base_adults < 1:
                raise ValidationError(_("Configuration Error: Base adults capacity must be at least 1."))

            if record.max_capacity < (record.base_adults + record.base_children):
                raise ValidationError(
                    _("Specification Violation: Max capacity cannot be lower than base adult + base child capacity."))

            if not record.allow_extra_bed and record.max_extra_beds > 0:
                raise ValidationError(
                    _("Validation Error: Extra bed quantity must be zero when extra bed is not allowed for this room type."))

    _sql_constraints = [
        ('unique_type_code', 'unique(code)', 'The room type code must be unique across the system!')
    ]