from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class HotelHousekeepingTask(models.Model):
    _name = 'hotel.housekeeping.task'
    _description = 'Housekeeping Cleaning Task'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    task_no = fields.Char(string='Task Number', required=True, readonly=True, default=lambda self: _('New'))
    room_id = fields.Many2one('hotel.room', string='Room/Property', required=True, tracking=True)  # কোরের সাথে ম্যাচিং
    task_type = fields.Selection([
        ('checkout', 'Checkout Clean'),
        ('stayover', 'Stayover'),
        ('deep_clean', 'Deep Clean'),
        ('turndown', 'Turndown'),
        ('inspection', 'Inspection'),
    ], string='Task Type', default='checkout', tracking=True)

    priority = fields.Selection([
        ('0', 'Low'),
        ('1', 'Normal'),
        ('2', 'High'),
        ('3', 'Urgent')
    ], string='Priority', default='1')

    assigned_to = fields.Many2one('res.users', string='Assigned Staff', tracking=True)
    planned_start = fields.Datetime(string='Planned Start')
    planned_end = fields.Datetime(string='Planned End')
    actual_start = fields.Datetime(string='Actual Start', readonly=True)
    actual_end = fields.Datetime(string='Actual End', readonly=True)

    checklist_id = fields.Many2one('hotel.housekeeping.checklist', string='Checklist Template')
    task_line_ids = fields.One2many('hotel.housekeeping.task.line', 'task_id', string='Execution Checklist')

    photo_proof = fields.Binary(string='Photo Proof (Done/Inspection)')
    note = fields.Text(string='Internal Notes')

    state = fields.Selection([
        ('draft', 'Draft'),
        ('assigned', 'Assigned'),
        ('in_progress', 'In Progress'),
        ('done', 'Done'),
        ('inspection', 'Inspection Pending'),
        ('approved', 'Approved'),
        ('rework', 'Rework'),
        ('cancel', 'Cancelled'),
    ], string='Status', default='draft', tracking=True)


    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('task_no', _('New')) == _('New'):
                vals['task_no'] = self.env['ir.sequence'].next_by_code('hotel.housekeeping.task') or _('New')

            if vals.get('checklist_id'):
                checklist = self.env['hotel.housekeeping.checklist'].browse(vals['checklist_id'])
                vals['task_line_ids'] = [
                    (0, 0, {'name': line.name, 'is_mandatory': line.is_mandatory})
                    for line in checklist.line_ids if line.name
                ]
        return super(HotelHousekeepingTask, self).create(vals_list)

    @api.onchange('checklist_id')
    def _onchange_checklist_id(self):

        if self.checklist_id:
            lines = []
            for line in self.checklist_id.line_ids:
                lines.append((0, 0, {
                    'name': line.name,
                    'is_mandatory': line.is_mandatory,
                }))
            self.task_line_ids = [(5, 0, 0)] + lines

    def action_start_task(self):
        self.write({
            'state': 'in_progress',
            'actual_start': fields.Datetime.now()
        })

    def action_complete_task(self):

        for line in self.task_line_ids:
            if line.is_mandatory and not line.is_completed:
                raise ValidationError(_("You must complete all mandatory checklist items before finishing the task!"))

        if self.checklist_id.requires_photo and not self.photo_proof:
            raise ValidationError(_("Photo proof is mandatory for this checklist!"))

        self.write({
            'state': 'done',
            'actual_end': fields.Datetime.now()
        })

        if self.room_id:
            self.room_id.write({'housekeeping_state': 'clean'})

    def action_approve_task(self):

        if not self.env.user.has_group('hotel_housekeeping.group_housekeeping_manager'):
            raise ValidationError(_("Only Housekeeping Managers can approve inspections!"))

        self.write({'state': 'approved'})
        if self.room_id:
            self.room_id.write({'housekeeping_state': 'inspected'})

    def action_rework_task(self):
        self.write({'state': 'rework'})
        if self.room_id:
            self.room_id.write({'housekeeping_state': 'dirty'})


class HotelHousekeepingTaskLine(models.Model):
    _name = 'hotel.housekeeping.task.line'
    _description = 'Task Execution Checklist Line'

    name = fields.Char(string='Item')
    task_id = fields.Many2one('hotel.housekeeping.task', ondelete='cascade')
    is_mandatory = fields.Boolean(string='Mandatory')
    is_completed = fields.Boolean(string='Done', default=False)