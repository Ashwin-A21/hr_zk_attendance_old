# hr_zk_attendance/models/biometric_device_details.py
import logging
import pytz
from datetime import timedelta, datetime, time
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from . import sample_punches
from markupsafe import Markup

_logger = logging.getLogger(__name__)
try:
    from zk import ZK
except ImportError:
    _logger.error("Please Install pyzk library.")


class BiometricDeviceDetails(models.Model):
    """Model for configuring and connect the biometric device with odoo"""
    _name = 'biometric.device.details'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Biometric Device Details'

    name = fields.Char(string='Name', required=True, help='Record Name')
    device_ip = fields.Char(string='Device IP', required=True,
                            help='The IP address of the Device')
    port_number = fields.Integer(string='Port Number', required=True,
                                 help="The Port Number of the Device")
    address_id = fields.Many2one('res.partner', string='Working Address',
                                 help='Working address of the partner')
    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda
                                     self: self.env.user.company_id.id,
                                 help='Current Company')
    days_to_sync = fields.Integer(string="Days to Sync", default=30, readonly=True,
                                  help="The number of past days to sync attendance for. Set to 0 to sync all records.")
    last_download_time = fields.Datetime(string="Last Download Time",
                                         help="The last time attendance data was downloaded from this device." )

    def device_connect(self, zk):
        """Function for connecting the device with Odoo"""
        try:
            return zk.connect()
        except Exception as e:
            _logger.error(f"Failed to connect to device: {e}")
            return False

    def action_test_connection(self):
        """Checking the connection status"""
        zk = ZK(self.device_ip, port=self.port_number, timeout=30)
        try:
            if zk.connect():
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'message': 'Successfully Connected',
                        'type': 'success',
                        'sticky': False
                    }
                }
        except Exception as error:
            raise ValidationError(f'{error}')

    def action_set_timezone(self):
        """Function to set user's timezone to device"""
        for info in self:
            try:
                zk = ZK(info.device_ip, port=info.port_number, timeout=15)
            except NameError:
                raise UserError(
                    _("Pyzk module not Found. Please install it with 'pip3 install pyzk'."))

            conn = self.device_connect(zk)
            if conn:
                # Get user timezone from context, user preferences, or default to UTC
                user_tz_str = self.env.context.get('tz') or self.env.user.tz or 'UTC'
                user_timezone = pytz.timezone(user_tz_str)

                # Get current UTC time and convert to user's timezone
                utc_now = pytz.utc.localize(fields.Datetime.now())
                user_timezone_time = utc_now.astimezone(user_timezone)

                conn.set_time(user_timezone_time)
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'message': 'Successfully Set the Time',
                        'type': 'success',
                        'sticky': False
                    }
                }
            else:
                raise UserError(_("Please Check the Connection"))

    def action_clear_attendance(self):
        """Clear attendance records from the device and Odoo"""
        for info in self:
            try:
                zk = ZK(info.device_ip, port=info.port_number, timeout=30)
            except NameError:
                raise UserError(
                    _("Please install it with 'pip3 install pyzk'."))

            conn = self.device_connect(zk)
            if conn:
                try:
                    conn.enable_device()
                    conn.clear_attendance()
                    self._cr.execute("""delete from zk_machine_attendance""")
                    conn.disconnect()
                except Exception as e:
                    raise UserError(
                        _('Unable to clear Attendance log: %s') % e)
            else:
                raise UserError(_('Unable to connect to Attendance Device.'))

    def action_restart_device(self):
        """For restarting the device"""
        zk = ZK(self.device_ip, port=self.port_number, timeout=30)
        conn = self.device_connect(zk)
        if conn:
            conn.restart()

    @api.model
    def cron_download(self):
        """Cron job to download attendance data from all configured devices."""
        machines = self.env['biometric.device.details'].search([])
        for machine in machines:
            machine.action_download_attendance()

    def action_download_attendance(self):
        use_sample_data = False
        _logger.info("--- Starting attendance download ---")

        for device in self:
            attendance_data = []
            if use_sample_data:
                _logger.info("Using sample data from 'sample_punches.py'.")
                class SampleAttendance:
                    def __init__(self, att_dict):
                        self.user_id = att_dict.get('user_id')
                        self.timestamp = att_dict.get('timestamp')
                        self.status = att_dict.get('status', 1)
                        self.punch = att_dict.get('punch', 0)
                attendance_data = [SampleAttendance(p) for p in sample_punches.data]
            else:
                zk = ZK(device.device_ip, port=device.port_number, timeout=30)
                conn = device.device_connect(zk)
                if conn:
                    conn.disable_device()
                    attendance_data = conn.get_attendance()
                    conn.enable_device()
                    conn.disconnect()

            if not attendance_data:
                _logger.warning("No new attendance data found to process.")
                continue

            latest_punch_time = max(att.timestamp for att in attendance_data)

            if device.last_download_time:
                attendance_data = [att for att in attendance_data if att.timestamp > device.last_download_time]

            device.last_download_time = latest_punch_time

            if not attendance_data:
                _logger.warning("No new attendance data found after filtering.")
                continue

            zk_attendance = self.env['zk.machine.attendance']
            operating_tz_str = self.env.user.tz or 'UTC'
            operating_tz = pytz.timezone(operating_tz_str)

            punches_by_workday = {}

            for punch in sorted(attendance_data, key=lambda p: p.timestamp):
                employee = self.env['hr.employee'].search([('device_id_num', '=', str(punch.user_id))], limit=1)
                if not employee:
                    continue

                raw_dt = punch.timestamp
                if getattr(raw_dt, 'tzinfo', None) is None:
                    local_dt = operating_tz.localize(raw_dt, is_dst=None)
                else:
                    local_dt = raw_dt.astimezone(operating_tz)

                utc_dt = local_dt.astimezone(pytz.utc)

                atten_time = fields.Datetime.to_string(utc_dt)

                existing_punch = zk_attendance.search([
                    ('employee_id', '=', employee.id),
                    ('punching_time', '=', atten_time)
                ], limit=1)

                if not existing_punch:
                    zk_attendance.create({
                        'employee_id': employee.id,
                        'device_id_num': str(punch.user_id),
                        'punch_type': str(punch.punch),
                        'attendance_type': str(punch.status),
                        'punching_time': atten_time,
                        'address_id': device.address_id.id,
                    })

                workday = self._get_workday_for_punch(employee, local_dt, operating_tz)
                if not workday:
                    _logger.warning(f"Could not determine workday for punch at {local_dt} for employee {employee.name}")
                    continue

                punches_by_workday.setdefault((employee.id, workday), []).append({
                    "timestamp": utc_dt.replace(tzinfo=None),
                    "local_time": local_dt
                })

            all_workdays = set(day for (_, day) in punches_by_workday.keys())
            all_employees = self.env['hr.employee'].browse(list(set(emp_id for (emp_id, _) in punches_by_workday.keys())))

            for employee in all_employees:
                for workday in all_workdays:
                    shift = employee._get_employee_shift_for_day(workday, operating_tz)
                    if not shift:
                        continue
                    
                    start_of_day_utc = operating_tz.localize(datetime.combine(workday, time.min)).astimezone(pytz.utc)
                    end_of_day_utc = operating_tz.localize(datetime.combine(workday, time.max)).astimezone(pytz.utc)
                    
                    existing_punches = zk_attendance.search([
                        ('employee_id', '=', employee.id),
                        ('punching_time', '>=', start_of_day_utc),
                        ('punching_time', '<=', end_of_day_utc),
                    ])
                    
                    punches = [fields.Datetime.from_string(p.punching_time) for p in existing_punches]

                    result = self.process_attendance(punches, employee, shift, operating_tz)
                    self._create_or_update_attendance(result, employee, self.env['hr.attendance'])

            _logger.info("--- Attendance download finished ---")

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': _('Attendance data has been downloaded successfully.'),
                'type': 'success',
                'sticky': False,
                'next': {'type': 'ir.actions.client', 'tag': 'reload'},
            }
        }

    def _get_workday_for_punch(self, employee, punch_time_local, operating_tz):
        """Determine the workday for a punch, handling night shifts"""
        punch_date = punch_time_local.date()

        prev_date = punch_date - timedelta(days=1)
        prev_shift = employee._get_employee_shift_for_day(prev_date, operating_tz)
        if prev_shift and not prev_shift.get('is_holiday') and prev_shift['is_night_shift'] and punch_time_local <= (prev_shift['end_local'] + timedelta(hours=4)):
            return prev_date

        current_shift = employee._get_employee_shift_for_day(punch_date, operating_tz)
        if current_shift and not current_shift.get('is_holiday') and punch_time_local >= (current_shift['start_local'] - timedelta(hours=3)):
            return punch_date

        return punch_date

    def process_attendance(self, punches, employee, shift, tz):
        """Process punches of one employee for one day"""
        punches = sorted(punches)
        check_in = None
        check_out = None
        status_flags = []

        if shift.get('is_holiday'):
            if punches:
                check_in = punches[0]
                if len(punches) > 1:
                    check_out = punches[-1]
                else:
                    check_out = None

                worked_hours = 0.0
                if check_in and check_out:
                    worked_hours = (check_out - check_in).total_seconds() / 3600.0

                results = {
                    "employee_id": employee.id,
                    "date": punches[0].date(),
                    "check_in": check_in,
                    "check_out": check_out,
                    "status": ["Holiday Work", "extra_hours"],
                    "worked_hours": round(worked_hours, 2),
                    "extra_hours": round(worked_hours, 2),
                    "has_punches": True,
                }
                if not check_out:
                    results['status'].append("Missed checkout")
                return results
            else:
                return { "has_punches": False }


        shift_start_utc = shift['start_local'].astimezone(pytz.utc).replace(tzinfo=None)
        shift_end_utc = shift['end_local'].astimezone(pytz.utc).replace(tzinfo=None)
        break_from_utc = shift.get('break_from_local').astimezone(pytz.utc).replace(tzinfo=None) if shift.get('break_from_local') else None
        break_to_utc = shift.get('break_to_local').astimezone(pytz.utc).replace(tzinfo=None) if shift.get('break_to_local') else None

        planned_hours = shift.get('planned_work_hours', 0.0)

        if len(punches) == 1:
            punch_time = punches[0]
            if abs(punch_time - shift_start_utc) <= abs(punch_time - shift_end_utc):
                check_in = punch_time
            else:
                check_out = punch_time
        elif len(punches) > 1:
            check_in = punches[0]
            check_out = punches[-1]

        results = {
            "employee_id": employee.id,
            "date": punches[0].date() if punches else None,
            "check_in": check_in,
            "check_out": check_out,
            "status": [],
            "worked_hours": 0,
            "extra_hours": 0,
            "has_punches": bool(punches),
        }

        if check_in and check_out:
            if check_out < check_in:
                check_out = shift_end_utc
                status_flags.append("invalid_order_fixed")

            break_overlap_seconds = 0
            if break_from_utc and break_to_utc:
                overlap_start = max(check_in, break_from_utc)
                overlap_end = min(check_out, break_to_utc)
                if overlap_end > overlap_start:
                    break_overlap_seconds = (overlap_end - overlap_start).total_seconds()

            total_duration_seconds = (check_out - check_in).total_seconds()
            worked_seconds = total_duration_seconds - break_overlap_seconds
            worked_hours = worked_seconds / 3600.0
            results["worked_hours"] = round(worked_hours, 2)

            extra_hours = worked_hours - planned_hours
            results["extra_hours"] = round(extra_hours, 2)

            if check_in < shift_start_utc:
                status_flags.append("early_checkin")
            elif check_in > shift_start_utc:
                status_flags.append("late_checkin")

            if check_out < shift_end_utc:
                status_flags.append("early_checkout")
            elif check_out > shift_end_utc:
                status_flags.append("late_checkout")

            if extra_hours < -0.1:
                status_flags.append("less_hours")
            elif extra_hours > 0.1:
                status_flags.append("extra_hours")

        elif check_in and not check_out:
            status_flags.append("Missed checkout")
            if datetime.now() >= check_in + timedelta(hours=18):
                check_out = check_in + timedelta(hours=18)
                results["check_out"] = check_out
                worked_hours = 18.0
                results["worked_hours"] = worked_hours
                extra_hours = worked_hours - planned_hours
                results["extra_hours"] = round(extra_hours, 2)

        elif check_out and not check_in:
            status_flags.append("Missed checkin")
            check_in = shift_start_utc
            results["check_in"] = check_in
            worked_hours = (check_out - check_in).total_seconds() / 3600.0
            results["worked_hours"] = round(worked_hours, 2)
            extra_hours = worked_hours - planned_hours
            results["extra_hours"] = round(extra_hours, 2)
            if extra_hours > 0.1:
                 status_flags.append("extra_hours")

        else:
            status_flags.append("absent")

        results["status"] = status_flags
        return results

    def _create_or_update_attendance(self, result, employee, hr_attendance):
        """Helper to insert/update hr.attendance records"""
        if not result["has_punches"]:
            return

        status_list = result["status"]
        status_ids = []

        for status_name in status_list:
            status_tag = self.env['hr.attendance.status.tag'].search([('name', '=', status_name)], limit=1)
            if not status_tag:
                status_tag = self.env['hr.attendance.status.tag'].create({'name': status_name})
            status_ids.append(status_tag.id)

        vals = {
            'employee_id': employee.id,
            'check_in': result["check_in"],
            'check_out': result["check_out"],
            'worked_hours': result["worked_hours"],
            'status_ids': [(6, 0, status_ids)],
            'overtime_hours': result["extra_hours"],
            'was_missing_checkin': "Missed checkin" in status_list,
            'was_missing_checkout': "Missed checkout" in status_list,
        }

        workday_date = result['check_in'].date() if result.get('check_in') else (result.get('check_out').date() if result.get('check_out') else None)
        if not workday_date:
            return

        start_of_day = datetime.combine(workday_date, time.min)
        end_of_day = datetime.combine(workday_date, time.max)

        existing = hr_attendance.search([
            ('employee_id', '=', employee.id),
            ('check_in', '>=', start_of_day),
            ('check_in', '<=', end_of_day),
        ], limit=1)

        if existing and (existing.check_in_is_corrected or existing.check_out_is_corrected):
            _logger.info(f"Skipping auto-update for manually corrected attendance record {existing.id} for {employee.name} on {workday_date}.")
            return

        attendance_rec = None
        if existing:
            existing.with_context(automated_update=True).write(vals)
            attendance_rec = existing
        else:
            attendance_rec = hr_attendance.with_context(automated_update=True).create(vals)


        if not attendance_rec:
            return

        hr_admin_group = self.env.ref('hr_attendance.group_hr_attendance_manager', raise_if_not_found=False)
        if not hr_admin_group:
            return

        hr_admin_users = self.env['res.users'].search([('groups_id', 'in', hr_admin_group.ids)])

        ci_str, co_str = "", ""
        if result["check_in"]:
            ci_local = fields.Datetime.context_timestamp(attendance_rec, attendance_rec.check_in)
            ci_str = ci_local.strftime("%Y-%m-%d %H:%M")

        if result["check_out"]:
            co_local = fields.Datetime.context_timestamp(attendance_rec, attendance_rec.check_out)
            co_str = co_local.strftime("%Y-%m-%d %H:%M")

        if "early_checkin" in status_list:
            attendance_rec.message_post(
                body=Markup(f"""
                    <p>
                        Dear <b>{employee.name}</b>, you checked in
                        <span style="color:green;">early</span>
                        at <span style="color:blue;">{ci_str}</span>.
                    </p>
                """),
                partner_ids=hr_admin_users.mapped('partner_id').ids,
                subtype_xmlid="mail.mt_note"
            )

        if "late_checkin" in status_list:
            attendance_rec.message_post(
                body=Markup(f"""
                    <p>
                        Dear <b>{employee.name}</b>, you checked in
                        <span style="color:red;">late</span>
                        at <span style="color:blue;">{ci_str}</span>.
                    </p>
                """),
                partner_ids=hr_admin_users.mapped('partner_id').ids,
                subtype_xmlid="mail.mt_note"
            )

        if "early_checkout" in status_list:
            attendance_rec.message_post(
                body=Markup(f"""
                    <p>
                        Dear <b>{employee.name}</b>, you checked out
                        <span style="color:red;">early</span>
                        at <span style="color:blue;">{co_str}</span>.
                    </p>
                """),
                partner_ids=hr_admin_users.mapped('partner_id').ids,
                subtype_xmlid="mail.mt_note"
            )

        if "late_checkout" in status_list:
            attendance_rec.message_post(
                body=Markup(f"""
                    <p>
                        Dear <b>{employee.name}</b>, you checked out
                        <span style="color:green;">late</span>
                        at <span style="color:blue;">{co_str}</span>.
                    </p>
                """),
                partner_ids=hr_admin_users.mapped('partner_id').ids,
                subtype_xmlid="mail.mt_note"
            )

        if "Missed checkin" in status_list and result["check_in"]:
            attendance_rec.message_post(
                body=Markup(f"""
                    <p>
                        Dear <b>{employee.name}</b>,
                        you <span style="color:red;">missed check-in</span>.
                    </p>
                    <p>
                        System considered first log at
                        <b style="color:blue;">{ci_str}</b>.
                    </p>
                """),
                partner_ids=hr_admin_users.mapped('partner_id').ids,
                subtype_xmlid="mail.mt_note"
            )

        if "Missed checkout" in status_list and result["check_out"]:
            attendance_rec.message_post(
                body=Markup(f"""
                    <p>
                        Dear <b>{employee.name}</b>, you checked in at
                        <span style="color:blue;">{ci_str}</span>
                        but <span style="color:red;">missed checkout</span>.
                    </p>
                    <p>
                        System auto-checked out at
                        <b style="color:green;">{co_str}</b>.
                    </p>
                """),
                partner_ids=hr_admin_users.mapped('partner_id').ids,
                subtype_xmlid="mail.mt_note"
            )