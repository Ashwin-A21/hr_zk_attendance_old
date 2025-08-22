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
    days_to_sync = fields.Integer(string="Days to Sync", default=30,
                                  help="The number of past days to sync attendance for. Set to 0 to sync all records.")

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
                user_tz_str = self.env.context.get('tz') or self.env.user.tz or 'UTC'
                user_timezone = pytz.timezone(user_tz_str)
                device_time = datetime.now(user_timezone)
                conn.set_time(device_time)
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
        use_sample_data = True
        _logger.info("--- Starting attendance download ---")

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
            zk = ZK(self.device_ip, port=self.port_number, timeout=30)
            conn = self.device_connect(zk)
            if conn:
                conn.disable_device()
                attendance_data = conn.get_attendance()
                conn.enable_device()
                conn.disconnect()

        if not attendance_data:
            _logger.warning("No attendance data found to process.")
            return

        zk_attendance = self.env['zk.machine.attendance']
        operating_tz_str = self.env.user.tz or 'UTC'
        operating_tz = pytz.timezone(operating_tz_str)

        punches_by_workday = {}

        for punch in sorted(attendance_data, key=lambda p: p.timestamp):
            employee = self.env['hr.employee'].search([('device_id_num', '=', str(punch.user_id))], limit=1)
            if not employee:
                continue

            punch_time_naive = punch.timestamp
            punch_time_local = operating_tz.localize(punch_time_naive)
            punch_time_utc = punch_time_local.astimezone(pytz.utc).replace(tzinfo=None)

            existing_punch = zk_attendance.search([
                ('employee_id', '=', employee.id),
                ('punching_time', '=', punch_time_utc)
            ], limit=1)

            if not existing_punch:
                zk_attendance.create({
                    'employee_id': employee.id,
                    'device_id_num': str(punch.user_id),
                    'punch_type': str(punch.punch),
                    'attendance_type': str(punch.status),
                    'punching_time': punch_time_utc,
                    'address_id': self.address_id.id,
                })

            workday = self._get_workday_for_punch(employee, punch_time_local, operating_tz)
            if not workday:
                _logger.warning(f"Could not determine workday for punch at {punch_time_local} for employee {employee.name}")
                continue

            punches_by_workday.setdefault((employee.id, workday), []).append(punch_time_local)

        all_workdays = set(day for (_, day) in punches_by_workday.keys())
        all_employees = self.env['hr.employee'].browse(list(set(emp_id for (emp_id, _) in punches_by_workday.keys())))

        for employee in all_employees:
            for workday in all_workdays:
                day_start_utc = operating_tz.localize(datetime.combine(workday, time.min)).astimezone(pytz.utc)
                day_end_utc = operating_tz.localize(datetime.combine(workday, time.max)).astimezone(pytz.utc)

                existing_attendances = self.env['hr.attendance'].search([
                    ('employee_id', '=', employee.id),
                    ('check_in', '>=', day_start_utc),
                    ('check_in', '<=', day_end_utc),
                ])

                for att in existing_attendances:
                    if att.check_in:
                        punches_by_workday.setdefault((employee.id, workday), []).append(att.check_in.astimezone(operating_tz))
                    if att.check_out:
                        punches_by_workday.setdefault((employee.id, workday), []).append(att.check_out.astimezone(operating_tz))

        for (emp_id, workday), punches in punches_by_workday.items():
            employee = self.env['hr.employee'].browse(emp_id)
            shift = self._get_employee_shift_for_day(employee, workday, operating_tz)

            if not shift:
                continue

            result = self.process_attendance(punches, shift['start_local'], shift['end_local'])
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
        punch_date = punch_time_local.date()

        prev_date = punch_date - timedelta(days=1)
        prev_shift = self._get_employee_shift_for_day(employee, prev_date, operating_tz)
        if prev_shift and prev_shift['is_night_shift'] and punch_time_local <= (prev_shift['end_local'] + timedelta(hours=4)):
             return prev_date

        current_shift = self._get_employee_shift_for_day(employee, punch_date, operating_tz)
        if current_shift and punch_time_local >= (current_shift['start_local'] - timedelta(hours=3)):
             return punch_date

        return None

    def _get_employee_shift_for_day(self, employee, target_day, operating_tz):
        day_of_week_str = target_day.strftime('%A').lower()
        worksheet = self.env['hr.employee.worksheet'].search([
            ('employee_id', '=', employee.id),
            ('day_of_week', '=', day_of_week_str)
        ], limit=1)

        if not worksheet or (worksheet.work_from == 0 and worksheet.work_to == 0):
            return None

        work_from_hr = worksheet.work_from
        work_to_hr = worksheet.work_to

        start_dt_naive = datetime.combine(target_day, datetime.min.time()) + timedelta(hours=work_from_hr)

        end_day = target_day
        is_night_shift = work_to_hr < work_from_hr
        if is_night_shift:
            end_day += timedelta(days=1)

        end_dt_naive = datetime.combine(end_day, datetime.min.time()) + timedelta(hours=work_to_hr)

        return {
            'start_local': operating_tz.localize(start_dt_naive),
            'end_local': operating_tz.localize(end_dt_naive),
            'is_night_shift': is_night_shift
        }

    def process_attendance(self, punches, shift_start_local, shift_end_local):
        punches = sorted(list(set(punches)))
        status_flags = []
        check_in_local = None
        check_out_local = None

        if len(punches) == 1:
            single_punch = punches[0]
            time_to_start = abs((single_punch - shift_start_local).total_seconds())
            time_to_end = abs((shift_end_local - single_punch).total_seconds())

            if time_to_start < time_to_end:
                check_in_local = single_punch
            else:
                check_out_local = single_punch

        elif len(punches) >= 2:
            check_in_local = punches[0]
            check_out_local = punches[-1]

        if check_in_local and not check_out_local:
            status_flags.append("missing_checkout")
        if not check_in_local and check_out_local:
            status_flags.append("missing_checkin")

        if check_in_local:
            if check_in_local < shift_start_local:
                status_flags.append("early_checkin")
            if check_in_local > (shift_start_local + timedelta(minutes=5)):
                status_flags.append("late_checkin")
        if check_out_local:
            if check_out_local < shift_end_local:
                status_flags.append("early_checkout")
            if check_out_local > shift_end_local:
                status_flags.append("late_checkout")

        calc_check_in = check_in_local
        calc_check_out = check_out_local
        
        if "missing_checkin" in status_flags:
            calc_check_in = shift_start_local
        
        is_today_open = check_in_local and check_in_local.date() == datetime.now().date() and not check_out_local
        if "missing_checkout" in status_flags and not is_today_open:
            calc_check_out = shift_end_local

        worked_hours = 0
        overtime_hours = 0

        if calc_check_in and calc_check_out:
            if calc_check_out < calc_check_in:
                calc_check_out = calc_check_in

            planned_seconds = (shift_end_local - shift_start_local).total_seconds()
            worked_seconds = (calc_check_out - calc_check_in).total_seconds()

            worked_hours = worked_seconds / 3600.0
            overtime_seconds = worked_seconds - planned_seconds
            overtime_hours = overtime_seconds / 3600.0

            if overtime_seconds > 60:
                if "extra_hours" not in status_flags:
                    status_flags.append("extra_hours")
            elif overtime_seconds < -60:
                if "less_hours" not in status_flags:
                    status_flags.append("less_hours")
        
        display_worked_hours = 0
        if check_in_local and check_out_local:
            display_worked_hours = (check_out_local - check_in_local).total_seconds() / 3600.0
        else:
            display_worked_hours = worked_hours

        return {
            "check_in": check_in_local,
            "check_out": check_out_local,
            "status": list(set(status_flags)),
            "worked_hours": display_worked_hours,
            "overtime_hours": overtime_hours,
        }


    def _create_or_update_attendance(self, result, employee, hr_attendance):
        """Helper to insert/update hr.attendance records"""

        check_in_local = result.get("check_in")
        check_out_local = result.get("check_out")
        status_list = result.get("status", [])
        notification_to_send = None

        if "missing_checkin" in status_list and check_out_local:
            workday = check_out_local.date()
            shift = self._get_employee_shift_for_day(employee, workday, check_out_local.tzinfo)
            if shift and shift.get('start_local'):
                check_in_local = shift['start_local']
                notification_to_send = 'missing_checkin'
            else:
                _logger.warning(f"Could not find worksheet schedule for {employee.name} on {workday} to correct missing check-in.")
                return 

        if check_in_local and not check_out_local:
            if (datetime.now(check_in_local.tzinfo) - check_in_local) > timedelta(hours=18):
                check_out_local = check_in_local + timedelta(hours=18)
                if 'missing_checkout' not in status_list:
                    status_list.append('missing_checkout')
                notification_to_send = 'missing_checkout'

        if not check_in_local:
            return

        if check_out_local and check_in_local.date() < check_out_local.date() and 'night_shift' not in status_list:
            status_list.append('night_shift')

        check_in_for_odoo = check_in_local.astimezone(pytz.utc).replace(tzinfo=None)
        check_out_for_odoo = check_out_local.astimezone(pytz.utc).replace(tzinfo=None) if check_out_local else None

        status_ids = []
        for status_name in set(status_list):
            status_tag = self.env['hr.attendance.status.tag'].search([('name', '=', status_name)], limit=1)
            if not status_tag:
                status_tag = self.env['hr.attendance.status.tag'].create({'name': status_name})
            status_ids.append(status_tag.id)

        vals = {
            'employee_id': employee.id,
            'check_in': check_in_for_odoo,
            'check_out': check_out_for_odoo,
            'status_ids': [(6, 0, status_ids)],
            'worked_hours': result.get("worked_hours", 0),
            'overtime_hours': result.get("overtime_hours", 0),
        }

        day_start_local = datetime.combine(check_in_local.date(), time.min)
        day_end_local = datetime.combine(check_in_local.date(), time.max)
        day_start_utc = day_start_local.astimezone(pytz.utc).replace(tzinfo=None)
        day_end_utc = day_end_local.astimezone(pytz.utc).replace(tzinfo=None)

        existing = hr_attendance.search([
            ('employee_id', '=', employee.id),
            ('check_in', '>=', day_start_utc),
            ('check_in', '<=', day_end_utc),
        ], limit=1)
        
        attendance_rec = existing
        if not existing:
            attendance_rec = hr_attendance.create(vals)
        else:
            if not existing.is_corrected:
                existing_statuses = existing.status_ids.mapped('name')
                final_statuses = set(existing_statuses + status_list)
                
                status_ids = []
                for status_name in final_statuses:
                    status_tag = self.env['hr.attendance.status.tag'].search([('name', '=', status_name)], limit=1)
                    if not status_tag:
                        status_tag = self.env['hr.attendance.status.tag'].create({'name': status_name})
                    status_ids.append(status_tag.id)
                vals['status_ids'] = [(6, 0, status_ids)]
                existing.write(vals)

        if notification_to_send and not attendance_rec.notification_sent:
            hr_admin_group = self.env.ref('hr_attendance.group_hr_attendance_manager')
            hr_admin_users = self.env['res.users'].search([('groups_id', 'in', hr_admin_group.ids)])
            partner_ids = hr_admin_users.mapped('partner_id').ids

            user_tz = pytz.timezone(self.env.user.tz or 'UTC')
            ci_local = fields.Datetime.context_timestamp(attendance_rec, attendance_rec.check_in)
            co_local = fields.Datetime.context_timestamp(attendance_rec, attendance_rec.check_out) if attendance_rec.check_out else None
            ci_str = ci_local.strftime("%Y-%m-%d %H:%M")
            co_str = co_local.strftime("%Y-%m-%d %H:%M") if co_local else ""
            
            if notification_to_send == 'missing_checkout':
                attendance_rec.message_post(
                    body=Markup(f"""
                            <p>
                                Dear HR Team, <b>{employee.name}</b> checked in at
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
                attendance_rec.notification_sent = True
            elif notification_to_send == 'missing_checkin':
                attendance_rec.message_post(
                    body=Markup(f"""
                            <p>
                                Dear HR Team, <b>{employee.name}</b>
                                <span style="color:red;">missed check-in</span>.
                            </p>
                            <p>
                                System considered first log at
                                <b style="color:blue;">{ci_str}</b> based on the worksheet.
                            </p>
                        """),
                    partner_ids=hr_admin_users.mapped('partner_id').ids,
                    subtype_xmlid="mail.mt_note"
                )
                attendance_rec.notification_sent = True