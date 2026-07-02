from odoo import models, fields, api, _


class HotelLostFound(models.Model):
    _name = 'hotel.lost.found'
    _description = 'Hotel Lost and Found Management'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    _rec_name = 'item_no'

    item_no = fields.Char(string='Item Code', required=True, readonly=True, default=lambda self: _('New'))
    room_id = fields.Many2one('hotel.room', string='Found Location / Room', required=True, tracking=True)
    guest_id = fields.Many2one('res.partner', string='Possible Guest / Owner', tracking=True)
    booking_id = fields.Many2one('hotel.booking', string='Related Booking', tracking=True)

    item_description = fields.Text(string='Item Description', required=True)
    photo = fields.Binary(string='Item Photo')
    found_by = fields.Many2one('res.users', string='Found By Staff', default=lambda self: self.env.user)
    found_date = fields.Date(string='Found Date', default=fields.Date.context_today)
    storage_location = fields.Char(string='Storage Locker/Location', help="e.g., Locker B-12" ,tracking=True)

    state = fields.Selection([
        ('found', 'Found'),
        ('notified', 'Guest Notified'),
        ('claimed', 'Claimed'),
        ('returned', 'Returned to Guest'),
        ('disposed', 'Disposed'),
        ('donated', 'Donated'),
    ], string='Status', default='found', tracking=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('item_no', _('New')) == _('New'):
                vals['item_no'] = self.env['ir.sequence'].next_by_code('hotel.lost.found') or _('New')
        return super(HotelLostFound, self).create(vals_list)

    def action_notify_guest(self):
        self.write({'state': 'notified'})

    def action_return_item(self):
        self.write({'state': 'returned'})

    @api.depends('item_no', 'item_description')
    def _compute_display_name(self):
        for record in self:
            res_name = record.item_no or ''
            if record.item_description:

                desc = record.item_description[:30] + '...' if len(
                    record.item_description) > 30 else record.item_description
                res_name = f"{res_name} - {desc}"
            record.display_name = res_name