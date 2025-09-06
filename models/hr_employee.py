# hr_zk_attendance/models/hr_employee.py
from odoo import fields, models, api
from datetime import timedelta, datetime, time, date
import pytz


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    device_id_num = fields.Char(string='Biometric Device ID',
                                help="Give the biometric device id")

    def _get_employee_shift_for_day(self, target_day, operating_tz):
        """
        Helper method to get shift details.
        It first checks for a specific night shift schedule for the given day.
        If found, it builds the shift dynamically.
        If not found, it falls back to the employee's default resource calendar.
        """
        self.ensure_one()
        employee = self

        # Check for a specific overriding shift schedule for the target day
        night_shift_schedule = self.env['hr.night.shift.schedule'].search([
            ('employee_ids', 'in', employee.id),
            ('date_from', '<=', target_day),
            ('date_to', '>=', target_day),
        ], limit=1, order='create_date desc')

        if night_shift_schedule:
            # Dynamically build shift from the schedule record
            work_from_hr = night_shift_schedule.time_from
            work_to_hr = night_shift_schedule.time_to
            break_from_hr = night_shift_schedule.break_from
            break_to_hr = night_shift_schedule.break_to

            is_night_shift = work_to_hr < work_from_hr
            break_duration = max(0, break_to_hr - break_from_hr)
            
            if is_night_shift:
                planned_work_hours = (24.0 - work_from_hr) + work_to_hr - break_duration
            else:
                planned_work_hours = work_to_hr - work_from_hr - break_duration
            
            start_dt_naive = datetime.combine(target_day, time.min) + timedelta(hours=work_from_hr)
            break_from_naive = datetime.combine(target_day, time.min) + timedelta(hours=break_from_hr)
            break_to_naive = datetime.combine(target_day, time.min) + timedelta(hours=break_to_hr)

            end_day = target_day
            if is_night_shift:
                end_day += timedelta(days=1)

            end_dt_naive = datetime.combine(end_day, time.min) + timedelta(hours=work_to_hr)
            
            return {
                'start_local': operating_tz.localize(start_dt_naive),
                'end_local': operating_tz.localize(end_dt_naive),
                'break_from_local': operating_tz.localize(break_from_naive),
                'break_to_local': operating_tz.localize(break_to_naive),
                'is_night_shift': is_night_shift,
                'planned_work_hours': max(0, planned_work_hours),
                'break_duration': break_duration,
                'is_holiday': False,
                'calendar_id': None,  # No specific calendar is used
            }

        # Fallback to default resource calendar
        resource_calendar = employee.resource_calendar_id
        if not resource_calendar:
            return {'planned_work_hours': 0.0, 'is_holiday': True}

        day_of_week_str = target_day.strftime('%A').lower()
        worksheet = resource_calendar.worksheet_ids.filtered(
            lambda w: w.day_of_week == day_of_week_str
        )

        if not worksheet or (worksheet.work_from == 0 and worksheet.work_to == 0):
            return {'planned_work_hours': 0.0, 'is_holiday': True, 'calendar_id': resource_calendar.id}

        work_from_hr = worksheet.work_from
        work_to_hr = worksheet.work_to
        break_from_hr = worksheet.break_from
        break_to_hr = worksheet.break_to

        is_night_shift = work_to_hr < work_from_hr
        break_duration = max(0, break_to_hr - break_from_hr)

        if is_night_shift:
             planned_work_hours = (24.0 - work_from_hr) + work_to_hr - break_duration
        else:
             planned_work_hours = work_to_hr - work_from_hr - break_duration


        start_dt_naive = datetime.combine(target_day, time.min) + timedelta(hours=work_from_hr)
        break_from_naive = datetime.combine(target_day, time.min) + timedelta(hours=break_from_hr)
        break_to_naive = datetime.combine(target_day, time.min) + timedelta(hours=break_to_hr)

        end_day = target_day
        if is_night_shift:
            end_day += timedelta(days=1)

        end_dt_naive = datetime.combine(end_day, time.min) + timedelta(hours=work_to_hr)

        return {
            'start_local': operating_tz.localize(start_dt_naive),
            'end_local': operating_tz.localize(end_dt_naive),
            'break_from_local': operating_tz.localize(break_from_naive),
            'break_to_local': operating_tz.localize(break_to_naive),
            'is_night_shift': is_night_shift,
            'planned_work_hours': max(0, planned_work_hours),
            'break_duration': break_duration,
            'is_holiday': False,
            'calendar_id': resource_calendar.id,
        }

    # ... The rest of the file (_compute_attendance_report_data, HrAttendance class, etc.) remains unchanged ...
    # ... (x_working_days and other report fields remain the same) ...
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
        user_tz = pytz.timezone(self.env.user.tz or 'UTC')
        today = fields.Date.context_today(self, timestamp=datetime.now(user_tz))

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
            employee_create_date = fields.Datetime.context_timestamp(
                employee, employee.create_date).date()
            calculation_start_date = max(date_from, employee_create_date)

            def reset_fields():
                employee.x_working_days = "0/0"
                employee.x_week_offs = 0
                employee.x_absent_days = 0
                employee.x_early_in = 0
                employee.x_late_in = 0
                employee.x_early_out = 0
                employee.x_late_out = 0
                employee.x_worked_hours = 0.0
                employee.x_extra_work_hours = 0.0
                employee.x_on_time_check_in = 0
                employee.x_on_time_check_out = 0

            if calculation_start_date > date_to or (not employee.resource_calendar_id and not self.env['hr.night.shift.schedule'].search_count([('employee_ids', 'in', employee.id)])):
                reset_fields()
                continue

            emp_tz = pytz.timezone(employee.tz or self.env.user.tz or 'UTC')
            start_dt_utc = emp_tz.localize(
                datetime.combine(calculation_start_date, time.min)
            ).astimezone(pytz.utc)
            end_dt_utc = emp_tz.localize(
                datetime.combine(date_to, time.max)
            ).astimezone(pytz.utc)

            attendances = Attendance.search([
                ('employee_id', '=', employee.id),
                ('check_in', '>=', start_dt_utc.replace(tzinfo=None)),
                ('check_in', '<=', end_dt_utc.replace(tzinfo=None)),
            ])
            attendances_by_date = {}
            for att in attendances:
                att_date = att.check_in.astimezone(emp_tz).date()
                attendances_by_date[att_date] = att

            working_days, present_days, week_offs, absent_days = 0, 0, 0, 0
            current_date = calculation_start_date
            while current_date <= date_to:
                if current_date > today:
                    current_date += timedelta(days=1)
                    continue
                
                shift = employee._get_employee_shift_for_day(current_date, emp_tz)
                is_scheduled_off = not shift or shift.get('is_holiday')
                has_attendance = current_date in attendances_by_date

                if not is_scheduled_off:
                    working_days += 1
                    if has_attendance:
                        present_days += 1
                    else:
                        absent_days += 1
                else:
                    if has_attendance:
                        working_days += 1
                        present_days += 1
                    else:
                        week_offs += 1
                current_date += timedelta(days=1)

            employee.x_working_days = f"{present_days}/{working_days}"
            employee.x_week_offs = week_offs
            employee.x_absent_days = absent_days

            if attendances:
                status_tags = attendances.mapped('status_ids.name')
                employee.x_early_in = status_tags.count('early_checkin')
                employee.x_late_in = status_tags.count('late_checkin')
                employee.x_early_out = status_tags.count('early_checkout')
                employee.x_late_out = status_tags.count('late_checkout')
                employee.x_worked_hours = sum(attendances.mapped('worked_hours'))
                employee.x_extra_work_hours = sum(
                    attendances.mapped('overtime_hours'))
                on_time_in = present_days - (
                        employee.x_late_in + employee.x_early_in)
                employee.x_on_time_check_in = max(0, on_time_in)

                checked_out_days = len(attendances.filtered(lambda a: a.check_out))
                on_time_out = checked_out_days - (
                        employee.x_early_out + employee.x_late_out)
                employee.x_on_time_check_out = max(0, on_time_out)
            else:
                reset_fields()
                employee.x_working_days = f"0/{working_days}"
                employee.x_week_offs = week_offs
                employee.x_absent_days = absent_days

class AttendanceStatusTag(models.Model):
    _name = 'hr.attendance.status.tag'
    _description = 'Attendance Status Tag'
    name = fields.Char(string='Status', required=True)
    color = fields.Integer(string='Color Index')


class HrAttendance(models.Model):
    _inherit = 'hr.attendance'
    was_missing_checkin = fields.Boolean(string="Was Missing Check-In", readonly=True, copy=False)
    was_missing_checkout = fields.Boolean(string="Was Missing Check-Out", readonly=True, copy=False)
    worked_hours = fields.Float(string='Worked Hours', compute='_compute_worked_hours', store=True, readonly=True)

    @api.depends('check_in', 'check_out', 'employee_id.resource_calendar_id')
    def _compute_worked_hours(self):
        """
        # FIXED LOGIC
        Calculates worked hours, accurately subtracting ONLY the overlapping
        portion of the scheduled break time.
        """
        for att in self:
            if not att.check_out or not att.check_in or not att.employee_id:
                att.worked_hours = 0.0
                continue

            # Get timezone and localize check-in/out times
            user_tz = pytz.timezone(att.employee_id.tz or self.env.user.tz or 'UTC')
            check_in_local = att.check_in.astimezone(user_tz)
            check_out_local = att.check_out.astimezone(user_tz)

            # Get the correct shift for the day
            shift = att.employee_id._get_employee_shift_for_day(check_in_local.date(), user_tz)

            if not shift or shift.get('is_holiday'):
                total_duration_seconds = (att.check_out - att.check_in).total_seconds()
                att.worked_hours = max(0, total_duration_seconds / 3600.0)
                continue

            # Get shift break times (they are already localized from the helper)
            break_from_local = shift.get('break_from_local') if shift else None
            break_to_local = shift.get('break_to_local') if shift else None

            # Calculate the actual duration of the break that overlaps with the work period
            break_overlap_seconds = 0
            if break_from_local and break_to_local:
                # Find the intersection between the work period and the break period
                overlap_start = max(check_in_local, break_from_local)
                overlap_end = min(check_out_local, break_to_local)

                if overlap_end > overlap_start:
                    break_overlap_seconds = (overlap_end - overlap_start).total_seconds()

            # Calculate total duration and subtract the break overlap
            total_duration_seconds = (att.check_out - att.check_in).total_seconds()
            worked_seconds = total_duration_seconds - break_overlap_seconds
            att.worked_hours = max(0, worked_seconds / 3600.0)

    status_ids = fields.Many2many('hr.attendance.status.tag', string='Status', compute='_compute_status_ids', store=True)
    overtime_hours = fields.Float(string="Over Time", compute='_compute_overtime_hours', store=True)
    notification_sent = fields.Boolean(string="Notification Sent", default=False)

    @api.depends('check_in', 'check_out', 'employee_id.resource_calendar_id.worksheet_ids',
                 'is_corrected', 'was_missing_checkin', 'was_missing_checkout')
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
                status_flags.add("Missed checkin")
            if att.was_missing_checkout and not att.is_corrected:
                status_flags.add("Missed checkout")

            user_tz = pytz.timezone(
                att.employee_id.tz or self.env.user.tz or 'UTC')
            check_in_local = att.check_in.astimezone(user_tz)
            shift = att.employee_id._get_employee_shift_for_day(
                check_in_local.date(), user_tz)

            if not shift or shift.get('is_holiday'):
                status_flags.add("Holiday Work")
                if att.worked_hours > 0:
                    status_flags.add("extra_hours")
                if att.was_missing_checkout:
                     status_flags.add("Missed checkout")
                att.status_ids = [(6, 0, [get_tag(flag).id for flag in status_flags])]
                continue

            shift_start_local = shift['start_local']
            shift_end_local = shift['end_local']

            if check_in_local < shift_start_local:
                status_flags.add("early_checkin")
            if check_in_local > (shift_start_local + timedelta(minutes=10)):
                status_flags.add("late_checkin")

            if att.check_out:
                check_out_local = att.check_out.astimezone(user_tz)
                if check_out_local < shift_end_local:
                    status_flags.add("early_checkout")
                if check_out_local > shift_end_local:
                    status_flags.add("late_checkout")
                if shift['is_night_shift']:
                    status_flags.add('night_shift')

                worked_seconds = att.worked_hours * 3600
                planned_seconds = (shift['planned_work_hours'] * 3600)

                if worked_seconds > planned_seconds + 60:
                    status_flags.add("extra_hours")
                elif worked_seconds < planned_seconds - 60:
                    status_flags.add("less_hours")
            else:
                if att.check_in.date() < datetime.now(
                        user_tz).date() and not att.was_missing_checkout:
                    status_flags.add("Missed checkout")

            status_tags = [get_tag(flag) for flag in status_flags]
            att.status_ids = [(6, 0, [tag.id for tag in status_tags])]

    @api.depends('worked_hours', 'employee_id.resource_calendar_id')
    def _compute_overtime_hours(self):
        """Calculates overtime based on the new accurate worked_hours."""
        for att in self:
            if not att.check_in or not att.employee_id:
                att.overtime_hours = 0.0
                continue

            user_tz = pytz.timezone(
                att.employee_id.tz or self.env.user.tz or 'UTC')
            check_in_local = att.check_in.astimezone(user_tz)
            shift = att.employee_id._get_employee_shift_for_day(
                check_in_local.date(), user_tz)

            if not shift or shift.get('is_holiday'):
                att.overtime_hours = att.worked_hours
                continue
            
            if not shift.get('planned_work_hours'):
                att.overtime_hours = 0.0
                continue

            att.overtime_hours = att.worked_hours - shift['planned_work_hours']

    @api.constrains('check_in', 'check_out', 'employee_id')
    def _check_validity(self):
        return True