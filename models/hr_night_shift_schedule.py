# hr_zk_attendance/models/hr_night_shift_schedule.py
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError

class HrNightShiftSchedule(models.Model):
    _name = 'hr.night.shift.schedule'
    _description = 'Night Shift Schedule'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # The name field is now simpler as it's set from the data file.
    name = fields.Char(string='Name', required=True, readonly=True)
    date_from = fields.Date(string='From Date', required=True, tracking=True)
    date_to = fields.Date(string='To Date', required=True, tracking=True)
    employee_ids = fields.Many2many('hr.employee', string='Employees', required=True, tracking=True)

    time_from = fields.Float(string='Time From', required=True, tracking=True, help="Shift start time (e.g., 22.0 for 10 PM)")
    time_to = fields.Float(string='Time To', required=True, tracking=True, help="Shift end time (e.g., 6.0 for 6 AM)")
    break_from = fields.Float(string='Break From', default=0.0, help="Set 0.0 if no break is scheduled.")
    break_to = fields.Float(string='Break To', default=0.0, help="Set 0.0 if no break is scheduled.")

    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)

    # The create method is no longer needed to generate a name,
    # but we can leave it for potential future programmatic creations.
    # @api.model_create_multi
    # def create(self, vals_list):
    #     for vals in vals_list:
    #         if vals.get('name', _('New')) == _('New'):
    #             vals['name'] = self.env['ir.sequence'].next_by_code('hr.night.shift.schedule') or _('New')
    #     return super().create(vals_list)

    @api.constrains('time_from', 'time_to', 'break_from', 'break_to')
    def _check_times(self):
        for rec in self:
            if not (0 <= rec.time_from < 24 and 0 <= rec.time_to < 24):
                raise ValidationError(_("'Time From' and 'Time To' must be between 0 and 24."))
            if not (0 <= rec.break_from < 24 and 0 <= rec.break_to < 24):
                raise ValidationError(_("'Break From' and 'Break To' must be between 0 and 24."))
            if rec.break_to and rec.break_from > rec.break_to:
                raise ValidationError(_("'Break From' cannot be later than 'Break To'."))

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for schedule in self:
            if schedule.date_from > schedule.date_to:
                raise ValidationError(_("The start date cannot be after the end date."))

    @api.constrains('date_from', 'date_to', 'employee_ids')
    def _check_overlapping_schedules(self):
        for schedule in self:
            domain = [
                ('id', '!=', schedule.id),
                ('employee_ids', 'in', schedule.employee_ids.ids),
                ('date_from', '<=', schedule.date_to),
                ('date_to', '>=', schedule.date_from),
            ]
            overlapping_schedules = self.search(domain)
            if overlapping_schedules:
                raise ValidationError(_(
                    "There is an overlapping night shift schedule for one or more selected employees."
                ))