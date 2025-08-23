# hr_zk_attendance/models/hr_employee.py
from odoo import fields, models, api
from datetime import timedelta, datetime, time, date
import pytz


class HrEmployee(models.Model):
    """Inherit the model to add worksheet fields"""
    _inherit = 'hr.employee'

    device_id_num = fields.Char(string='Biometric Device ID',
                                help="Give the biometric device id")
    worksheet_ids = fields.One2many('hr.employee.worksheet', 'employee_id',
                                    string='Worksheet')

    @api.model_create_multi
    def create(self, vals_list):
        """
        Override create to automatically generate a default worksheet for
        new employees.
        """
        employees = super().create(vals_list)
        all_days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
        worksheet_vals_list = []
        for employee in employees:
            for day in all_days:
                worksheet_vals_list.append({
                    'employee_id': employee.id,
                    'day_of_week': day,
                    'work_from': 8.5,  # Explicitly set default
                    'work_to': 16.0,   # Explicitly set default
                })
        self.env['hr.employee.worksheet'].create(worksheet_vals_list)
        return employees

    def _compute_worksheet_times(self):
        """Compute method to get times from the worksheet lines."""
        for employee in self:
            all_days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
            worksheet_map = {w.day_of_week: w for w in employee.worksheet_ids}
            for day in all_days:
                day_line = worksheet_map.get(day)
                employee[f'{day}_from'] = day_line.work_from if day_line else 0.0
                employee[f'{day}_to'] = day_line.work_to if day_line else 0.0

    def _set_day_value(self, day, from_time=None, to_time=None):
        """Helper to create/update a single worksheet value."""
        for employee in self:
            day_line = employee.worksheet_ids.filtered(lambda w: w.day_of_week == day)
            vals = {}
            if from_time is not None:
                vals['work_from'] = from_time
            if to_time is not None:
                vals['work_to'] = to_time

            if day_line:
                day_line.write(vals)
            elif any(v is not None for v in vals.values()):
                vals.update({'employee_id': employee.id, 'day_of_week': day})
                self.env['hr.employee.worksheet'].create(vals)

    def _get_employee_shift_for_day(self, target_day, operating_tz):
        """Helper method to get shift details for a specific day."""
        self.ensure_one()
        employee = self
        day_of_week_str = target_day.strftime('%A').lower()
        worksheet = self.env['hr.employee.worksheet'].search([
            ('employee_id', '=', employee.id),
            ('day_of_week', '=', day_of_week_str)
        ], limit=1)

        if not worksheet or (worksheet.work_from == 0 and worksheet.work_to == 0):
            return None

        work_from_hr = worksheet.work_from
        work_to_hr = worksheet.work_to

        start_dt_naive = datetime.combine(target_day, time.min) + timedelta(hours=work_from_hr)

        end_day = target_day
        is_night_shift = work_to_hr < work_from_hr
        if is_night_shift:
            end_day += timedelta(days=1)

        end_dt_naive = datetime.combine(end_day, time.min) + timedelta(hours=work_to_hr)

        return {
            'start_local': operating_tz.localize(start_dt_naive),
            'end_local': operating_tz.localize(end_dt_naive),
            'is_night_shift': is_night_shift
        }

    monday_from = fields.Float(string="Monday From", compute='_compute_worksheet_times',
                               inverse=lambda self: self._set_day_value('monday', from_time=self[0].monday_from), store=False)
    monday_to = fields.Float(string="Monday To", compute='_compute_worksheet_times',
                             inverse=lambda self: self._set_day_value('monday', to_time=self[0].monday_to), store=False)
    tuesday_from = fields.Float(string="Tuesday From", compute='_compute_worksheet_times',
                                inverse=lambda self: self._set_day_value('tuesday', from_time=self[0].tuesday_from), store=False)
    tuesday_to = fields.Float(string="Tuesday To", compute='_compute_worksheet_times',
                              inverse=lambda self: self._set_day_value('tuesday', to_time=self[0].tuesday_to), store=False)
    wednesday_from = fields.Float(string="Wednesday From", compute='_compute_worksheet_times',
                                  inverse=lambda self: self._set_day_value('wednesday', from_time=self[0].wednesday_from), store=False)
    wednesday_to = fields.Float(string="Wednesday To", compute='_compute_worksheet_times',
                                inverse=lambda self: self._set_day_value('wednesday', to_time=self[0].wednesday_to), store=False)
    thursday_from = fields.Float(string="Thursday From", compute='_compute_worksheet_times',
                                 inverse=lambda self: self._set_day_value('thursday', from_time=self[0].thursday_from), store=False)
    thursday_to = fields.Float(string="Thursday To", compute='_compute_worksheet_times',
                               inverse=lambda self: self._set_day_value('thursday', to_time=self[0].thursday_to), store=False)
    friday_from = fields.Float(string="Friday From", compute='_compute_worksheet_times',
                               inverse=lambda self: self._set_day_value('friday', from_time=self[0].friday_from), store=False)
    friday_to = fields.Float(string="Friday To", compute='_compute_worksheet_times',
                             inverse=lambda self: self._set_day_value('friday', to_time=self[0].friday_to), store=False)
    saturday_from = fields.Float(string="Saturday From", compute='_compute_worksheet_times',
                                 inverse=lambda self: self._set_day_value('saturday', from_time=self[0].saturday_from), store=False)
    saturday_to = fields.Float(string="Saturday To", compute='_compute_worksheet_times',
                               inverse=lambda self: self._set_day_value('saturday', to_time=self[0].saturday_to), store=False)
    sunday_from = fields.Float(string="Sunday From", compute='_compute_worksheet_times',
                               inverse=lambda self: self._set_day_value('sunday', from_time=self[0].sunday_from), store=False)
    sunday_to = fields.Float(string="Sunday To", compute='_compute_worksheet_times',
                             inverse=lambda self: self._set_day_value('sunday', to_time=self[0].sunday_to), store=False)

    x_working_days = fields.Char(string="Working Days", compute='_compute_attendance_report_data')
    x_week_offs = fields.Integer(string="Week Offs", compute='_compute_attendance_report_data')
    x_early_in = fields.Integer(string="Early In", compute='_compute_attendance_report_data')
    x_late_in = fields.Integer(string="Late In", compute='_compute_attendance_report_data')
    x_on_time_check_in = fields.Integer(string="On Time Check-In", compute='_compute_attendance_report_data')
    x_on_time_check_out = fields.Integer(string="On Time Check-Out", compute='_compute_attendance_report_data')
    x_early_out = fields.Integer(string="Early Out", compute='_compute_attendance_report_data')
    x_late_out = fields.Integer(string="Late Out", compute='_compute_attendance_report_data')
    x_absent_days = fields.Integer(string="Absent Days", compute='_compute_attendance_report_data')
    x_worked_hours = fields.Float(string="Total Work Time", compute='_compute_attendance_report_data')
    x_extra_work_hours = fields.Float(string="Total Extra Work", compute='_compute_attendance_report_data')

    def _compute_attendance_report_data(self):
        """Computes attendance statistics based on context date filters."""
        today = date.today()
        date_from = today.replace(day=1)
        date_to = today

        date_filter = self.env.context.get('report_date_filter')
        if date_filter == 'today':
            date_from = date_to = today
        elif date_filter == 'yesterday':
            date_from = date_to = today - timedelta(days=1)
        elif date_filter == 'this_month':
            date_from = today.replace(day=1)
            next_month = date_from.replace(day=28) + timedelta(days=4)
            date_to = next_month - timedelta(days=next_month.day)

        Attendance = self.env['hr.attendance']
        for employee in self:
            working_days, absent_days, week_offs = 0, 0, 0
            present_dates = set()

            current_date = date_from
            while current_date <= date_to:
                day_of_week_str = current_date.strftime('%A').lower()
                worksheet_entry = employee.worksheet_ids.filtered(
                    lambda w: w.day_of_week == day_of_week_str
                )[:1]
                
                # *** LOGIC CORRECTION STARTS HERE ***
                if worksheet_entry:
                    is_week_off = worksheet_entry.work_from == 0 and worksheet_entry.work_to == 0
                    if is_week_off:
                        week_offs += 1
                    else:
                        working_days += 1
                # Days without any worksheet entry are neither working days nor week offs.
                # *** LOGIC CORRECTION ENDS HERE ***

                current_date += timedelta(days=1)

            attendances = Attendance.search([
                ('employee_id', '=', employee.id),
                ('check_in', '>=', datetime.combine(date_from, time.min)),
                ('check_in', '<=', datetime.combine(date_to, time.max)),
            ])

            if attendances:
                status_tags = attendances.mapped('status_ids.name')
                present_dates = set(fields.Datetime.context_timestamp(employee, att.check_in).date() for att in attendances)

                employee.x_early_in = status_tags.count('early_checkin')
                employee.x_late_in = status_tags.count('late_checkin')
                employee.x_early_out = status_tags.count('early_checkout')
                employee.x_late_out = status_tags.count('late_checkout')
                employee.x_worked_hours = sum(attendances.mapped('worked_hours'))
                employee.x_extra_work_hours = sum(attendances.mapped('overtime_hours'))
            else:
                employee.x_early_in = 0
                employee.x_late_in = 0
                employee.x_early_out = 0
                employee.x_late_out = 0
                employee.x_worked_hours = 0.0
                employee.x_extra_work_hours = 0.0

            present_days_count = len(present_dates)
            absent_days = working_days - present_days_count

            employee.x_working_days = f"{present_days_count}/{working_days}"
            employee.x_week_offs = week_offs
            employee.x_absent_days = absent_days if absent_days > 0 else 0
            employee.x_on_time_check_in = present_days_count - employee.x_late_in
            employee.x_on_time_check_out = present_days_count - employee.x_early_out


class AttendanceStatusTag(models.Model):
    _name = 'hr.attendance.status.tag'
    _description = 'Attendance Status Tag'

    name = fields.Char(string='Status', required=True)
    color = fields.Integer(string='Color Index')


class HrAttendance(models.Model):
    _inherit = 'hr.attendance'

    was_missing_checkin = fields.Boolean(
        string="Was Missing Check-In", readonly=True, copy=False,
        help="Set if the check-in was originally missing and auto-corrected.")
    was_missing_checkout = fields.Boolean(
        string="Was Missing Check-Out", readonly=True, copy=False,
        help="Set if the check-out was originally missing and auto-corrected.")

    worked_hours = fields.Float(
        string='Worked Hours',
        compute='_compute_worked_hours',
        store=True,
        readonly=True
    )

    @api.depends('check_in', 'check_out')
    def _compute_worked_hours(self):
        """
        Overrides Odoo's default computation to ensure accuracy regardless
        of timezone configurations.
        """
        for att in self:
            if att.check_out and att.check_in:
                delta = att.check_out - att.check_in
                att.worked_hours = delta.total_seconds() / 3600.0
            else:
                att.worked_hours = 0.0

    status_ids = fields.Many2many(
        'hr.attendance.status.tag',
        string='Status',
        compute='_compute_status_ids',
        store=True,
        help="Attendance status, automatically computed based on employee's schedule."
    )
    overtime_hours = fields.Float(
        string="Over Time",
        compute='_compute_overtime_hours',
        store=True,
        help="Calculated overtime hours for this attendance record."
    )
    notification_sent = fields.Boolean(string="Notification Sent", default=False)

    @api.depends('check_in', 'check_out', 'employee_id.worksheet_ids', 'is_corrected', 'was_missing_checkin', 'was_missing_checkout')
    def _compute_status_ids(self):
        StatusTag = self.env['hr.attendance.status.tag']
        status_tag_cache = {tag.name: tag for tag in StatusTag.search([])}

        def get_tag(name):
            if name not in status_tag_cache:
                tag = StatusTag.create({'name': name})
                status_tag_cache[name] = tag
            return status_tag_cache[name]

        for att in self:
            status_flags = set()
            if not att.check_in or not att.employee_id:
                att.status_ids = False
                continue

            if att.was_missing_checkin and not att.is_corrected:
                status_flags.add("missing_checkin")
            if att.was_missing_checkout and not att.is_corrected:
                status_flags.add("missing_checkout")

            user_tz = pytz.timezone(att.employee_id.tz or self.env.user.tz or 'UTC')
            check_in_local = att.check_in.astimezone(user_tz)
            shift = att.employee_id._get_employee_shift_for_day(check_in_local.date(), user_tz)

            if not shift:
                status_flags.add("unscheduled")
                if not att.check_out and att.check_in.date() < datetime.now(user_tz).date():
                    status_flags.add("missing_checkout")
                att.status_ids = [(6, 0, [get_tag(flag).id for flag in status_flags])]
                continue

            shift_start_local = shift['start_local']
            shift_end_local = shift['end_local']

            if check_in_local < shift_start_local:
                status_flags.add("early_checkin")
            if check_in_local > (shift_start_local + timedelta(minutes=5)):
                status_flags.add("late_checkin")

            if att.check_out:
                check_out_local = att.check_out.astimezone(user_tz)
                if check_out_local < shift_end_local:
                    status_flags.add("early_checkout")
                if check_out_local > shift_end_local:
                    status_flags.add("late_checkout")
                if shift['is_night_shift']:
                    status_flags.add('night_shift')

                worked_seconds = (att.check_out - att.check_in).total_seconds()
                planned_seconds = (shift_end_local - shift_start_local).total_seconds()

                if worked_seconds > planned_seconds + 60:
                    status_flags.add("extra_hours")
                elif worked_seconds < planned_seconds - 60:
                    status_flags.add("less_hours")
            else:
                if att.check_in.date() < datetime.now(user_tz).date() and not att.was_missing_checkout:
                    status_flags.add("missing_checkout")

            status_tags = [get_tag(flag) for flag in status_flags]
            att.status_ids = [(6, 0, [tag.id for tag in status_tags])]

    @api.depends('check_in', 'check_out', 'employee_id.worksheet_ids')
    def _compute_overtime_hours(self):
        for att in self:
            if not att.check_in or not att.check_out or not att.employee_id:
                att.overtime_hours = 0.0
                continue

            user_tz = pytz.timezone(att.employee_id.tz or self.env.user.tz or 'UTC')
            check_in_local = att.check_in.astimezone(user_tz)
            shift = att.employee_id._get_employee_shift_for_day(check_in_local.date(), user_tz)

            if not shift:
                att.overtime_hours = 0.0
                continue

            shift_start_local = shift['start_local']
            shift_end_local = shift['end_local']
            planned_seconds = (shift_end_local - shift_start_local).total_seconds()
            worked_seconds = (att.check_out - att.check_in).total_seconds()
            overtime_seconds = worked_seconds - planned_seconds

            att.overtime_hours = overtime_seconds / 3600.0

    @api.constrains('check_in', 'check_out', 'employee_id')
    def _check_validity(self):
        """
        Override to allow check_out to be before check_in to allow night shifts.
        """
        return True