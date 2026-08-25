from odoo import models, fields

class HotelHousekeepingChecklist(models.Model):
    _name = 'hotel.housekeeping.checklist'
    _description = 'Housekeeping Master Checklist'

    name = fields.Char(string='Checklist Name', required=True)
    room_type_ids = fields.Many2many('hotel.room.type', string='Room Types')
    task_type = fields.Selection([
        ('checkout', 'Checkout Clean'),
        ('stayover', 'Stayover'),
        ('deep_clean', 'Deep Clean'),
        ('turndown', 'Turndown'),
        ('inspection', 'Inspection'),
    ], string='Task Type', required=True, default='checkout')
    requires_photo = fields.Boolean(string='Requires Photo Proof', default=False)
    line_ids = fields.One2many('hotel.housekeeping.checklist.line', 'checklist_id', string='Checklist Items')

class HotelHousekeepingChecklistLine(models.Model):
    _name = 'hotel.housekeeping.checklist.line'
    _description = 'Checklist Item Line'

    checklist_id = fields.Many2one('hotel.housekeeping.checklist', ondelete='cascade')
    name = fields.Char(string='Task Description', required=True)
    is_mandatory = fields.Boolean(string='Mandatory?', default=True)