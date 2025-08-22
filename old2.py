import datetime
import logging
import pytz
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from datetime import timedelta
from datetime import datetime
from . import sample_punches
from markupsafe import Markup

_logger = logging.getLogger(__name__)
try:
    from zk import ZK, const
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

    def device_connect(self, zk):
        """Function for connecting the device with Odoo"""
        try:
            conn = zk.connect()
            return conn
        except Exception:
            return False

    def action_test_connection(self):
        """Checking the connection status"""
        zk = ZK(self.device_ip, port=self.port_number, timeout=30,
                password=False, ommit_ping=False)
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
            machine_ip = info.device_ip
            zk_port = info.port_number
            try:
                # Connecting with the device with the ip and port provided
                zk = ZK(machine_ip, port=zk_port, timeout=15,
                        password=0,
                        force_udp=False, ommit_ping=False)
            except NameError:
                raise UserError(
                    _("Pyzk module not Found. Please install it"
                      "with 'pip3 install pyzk'."))
            conn = self.device_connect(zk)
            if conn:
                user_tz = self.env.context.get(
                    'tz') or self.env.user.tz or 'UTC'
                user_timezone_time = pytz.utc.localize(fields.Datetime.now())
                user_timezone_time = user_timezone_time.astimezone(
                    pytz.timezone(user_tz))
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
                raise UserError(_(
                    "Please Check the Connection"))

    def action_clear_attendance(self):
        """Methode to clear record from the zk.machine.attendance model and
        from the device"""
        for info in self:
            try:
                machine_ip = info.device_ip
                zk_port = info.port_number
                try:
                    # Connecting with the device
                    zk = ZK(machine_ip, port=zk_port, timeout=30,
                            password=0, force_udp=False, ommit_ping=False)
                except NameError:
                    raise UserError(_(
                        "Please install it with 'pip3 install pyzk'."))
                conn = self.device_connect(zk)
                if conn:
                    conn.enable_device()
                    clear_data = zk.get_attendance()
                    if clear_data:
                        # Clearing data in the device
                        conn.clear_attendance()
                        # Clearing data from attendance log
                        self._cr.execute(
                            """delete from zk_machine_attendance""")
                        conn.disconnect()
                    else:
                        raise UserError(
                            _('Unable to clear Attendance log.Are you sure '
                              'attendance log is not empty.'))
                else:
                    raise UserError(
                        _('Unable to connect to Attendance Device. Please use '
                          'Test Connection button to verify.'))
            except Exception as error:
                raise ValidationError(f'{error}')

    @api.model
    def cron_download(self):
        machines = self.env['biometric.device.details'].search([])
        for machine in machines:
            machine.action_download_attendance()


    # =========================
    # Main downloader
    # ========================= 
 
    def process_attendance(self, punches, employee, shift_start, shift_end):
        """Process punches of one employee for one day"""
        punches = sorted(punches, key=lambda x: x['timestamp'])
        check_in = None
        check_out = None
        status_flags = []

        if punches: 
            check_in = punches[0]['timestamp']
            check_out = punches[-1]['timestamp']

        results = {
            "employee_id": employee.id,
            "date": punches[0]['timestamp'].date() if punches else None,
            "check_in": check_in,
            "check_out": check_out,
            "status": [],
            "worked_hours": 0,
            "extra_hours": 0,
            "has_punches": bool(punches),
        }

        if check_in and check_out:
            # Validate punch order
            if check_out < check_in:
                # Auto adjust invalid punch order
                check_out = shift_end
                status_flags.append("invalid_order_fixed")

            # Calculate worked hours purely based on actual punches
            worked_hours = (check_out - check_in).total_seconds() / 3600.0
            results["worked_hours"] = round(worked_hours, 2)

            # Planned hours based on shift
            planned_hours = (shift_end - shift_start).total_seconds() / 3600.0

            # Extra hours calculation
            extra_hours = max(0, worked_hours - planned_hours)
            results["extra_hours"] = round(extra_hours, 2)

            # Early / Late logic
            if check_in < shift_start:
                status_flags.append("early_checkin")
            elif check_in > shift_start:
                status_flags.append("late_checkin")

            if check_out < shift_end:
                status_flags.append("early_checkout")
            elif check_out > shift_end:
                status_flags.append("late_checkout")

            # Less hours detection
            if worked_hours < planned_hours - 0.1:
                status_flags.append("less_hours")
                diff = round(worked_hours - planned_hours, 2)
                results["extra_hours"] = diff
            if extra_hours > 0.1:
                status_flags.append("extra_hours")

        elif check_in and not check_out:
            status_flags.append("missing_checkout")
            # Auto checkout at shift end
            check_out = shift_end
            check_out = check_in + timedelta(hours=18)
            results["check_out"] = check_out
            worked_hours = (check_out - check_in).total_seconds() / 3600.0
            results["worked_hours"] = round(worked_hours, 2)

            planned_hours = (shift_end - shift_start).total_seconds() / 3600.0
            extra_hours = round(worked_hours - planned_hours, 2)
            results["extra_hours"] = max(0, extra_hours)


        elif check_out and not check_in:
            status_flags.append("missing_checkin")
            status_flags.append("extra_hours")
            # Auto checkin at shift start
            check_in = shift_start
            results["check_in"] = check_in
            worked_hours = (check_out - check_in).total_seconds() / 3600.0
            results["worked_hours"] = round(worked_hours, 2)
            results["extra_hours"] = max(0, round(worked_hours - ((shift_end - shift_start).total_seconds() / 3600.0), 2))

        else:
            status_flags.append("absent")

        results["status"] = status_flags
        return results

    def action_download_attendance(self):
        zk_attendance = self.env['zk.machine.attendance']
        hr_attendance = self.env['hr.attendance']

        for info in self:
            machine_ip = info.device_ip
            zk_port = info.port_number

            try:
                from zk import ZK
                zk = ZK(machine_ip, port=zk_port, timeout=150000, password=0,
                        force_udp=False, ommit_ping=False)
            except NameError:
                raise UserError(_("Pyzk module not Found. Please install it with 'pip3 install pyzk'."))

            conn = self.device_connect(zk)
            if conn:
                conn.disable_device()
                user = conn.get_users()
                attendance = conn.get_attendance()

                # --- Use sample punches for testing ---
                use_sample = True
                if use_sample:
                    from . import sample_punches  # your module file
                    attendance = sample_punches.data

                if attendance:
                    local_tz = pytz.timezone(self.env.user.partner_id.tz or 'UTC')
                    punches_by_emp_day = {}

                    for each in attendance:
                        raw_dt = each['timestamp']
                        if getattr(raw_dt, 'tzinfo', None) is None:
                            local_dt = local_tz.localize(raw_dt, is_dst=None)
                        else:
                            local_dt = raw_dt.astimezone(local_tz)

                        utc_dt = local_dt.astimezone(pytz.utc)
                        utc_str = fields.Datetime.to_string(utc_dt)
                        local_day = local_dt.date()

                        employee = self.env['hr.employee'].search(
                            [('device_id_num', '=', each['user_id'])], limit=1)
                        if not employee:
                            continue

                        # Save in raw log model
                        duplicate = zk_attendance.search([
                            ('device_id_num', '=', each['user_id']),
                            ('punching_time', '=', utc_str)
                        ])
                        if not duplicate:
                            zk_attendance.create({
                                'employee_id': employee.id,
                                'device_id_num': each['user_id'],
                                'attendance_type': str(each['status']),
                                'punch_type': str(each['punch']),
                                'punching_time': utc_str,
                                'address_id': info.address_id.id
                            })

                        punches_by_emp_day.setdefault((employee.id, local_day), []).append({
                            "user_id": each['user_id'],
                            "timestamp": fields.Datetime.from_string(utc_str),
                            "status": each['status'],
                            "punch": each['punch'],
                        })

                    # Collect all days from punches
                    all_days = set(day for (_, day) in punches_by_emp_day.keys())
                    processed_employees = set(emp_id for (emp_id, _) in punches_by_emp_day.keys())

                    # --- Process grouped punches (employees who have punches) ---
                    for (emp_id, local_day), punches in punches_by_emp_day.items():
                        employee = self.env['hr.employee'].browse(emp_id)

                        shift_start_local = datetime.combine(local_day, datetime.min.time()) + timedelta(hours=9)
                        shift_end_local = datetime.combine(local_day, datetime.min.time()) + timedelta(hours=17, minutes=30)

                        local_tz = pytz.timezone(self.env.user.partner_id.tz or 'UTC')
                        shift_start_aware = local_tz.localize(shift_start_local, is_dst=None).astimezone(pytz.utc)
                        shift_end_aware = local_tz.localize(shift_end_local, is_dst=None).astimezone(pytz.utc)

                        shift_start = shift_start_aware.replace(tzinfo=None)
                        shift_end = shift_end_aware.replace(tzinfo=None)

                        result = self.process_attendance(punches, employee, shift_start, shift_end)
                        self._create_or_update_attendance(result, employee, hr_attendance)

                    # --- Handle employees with NO punches (mark absent) ---
                    all_employees = self.env['hr.employee'].search([])  # or filter by company/location if needed
                    for employee in all_employees:
                        for local_day in all_days:
                            if (employee.id, local_day) not in punches_by_emp_day:
                                shift_start_local = datetime.combine(local_day, datetime.min.time()) + timedelta(hours=9)
                                shift_end_local = datetime.combine(local_day, datetime.min.time()) + timedelta(hours=17, minutes=30)

                                shift_start_aware = local_tz.localize(shift_start_local, is_dst=None).astimezone(pytz.utc)
                                shift_end_aware = local_tz.localize(shift_end_local, is_dst=None).astimezone(pytz.utc)

                                shift_start = shift_start_aware.replace(tzinfo=None)
                                shift_end = shift_end_aware.replace(tzinfo=None)

                                result = self.process_attendance([], employee, shift_start, shift_end)
                                self._create_or_update_attendance(result, employee, hr_attendance)

                conn.enable_device()
                conn.disconnect()
                return True
            else:
                raise UserError(_('Unable to connect, please check the parameters and network connections.'))


    def _create_or_update_attendance(self, result, employee, hr_attendance):
        """Helper to insert/update hr.attendance records"""  

        if result["check_in"] and result["check_out"]:
            existing = hr_attendance.search([
                ('employee_id', '=', employee.id),
                ('check_in', '=', result["check_in"])
            ], limit=1)

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
                'overtime_hours': result["extra_hours"]
            }

            if not existing: 
                attendance_rec = self.env['hr.attendance'].create(vals)
            else:
                existing.write(vals)
                attendance_rec = existing


            # Notify HR Managers
            # 🔔 Notify HR Managers ONLY if status includes "missing checkout"
            hr_admin_group = self.env.ref('hr_attendance.group_hr_attendance_manager')
            hr_admin_users = self.env['res.users'].search([('groups_id', 'in', hr_admin_group.ids)])

            user_tz = pytz.timezone(self.env.user.tz or 'UTC')

            ci_local = fields.Datetime.context_timestamp(attendance_rec, attendance_rec.check_in)
            co_local = fields.Datetime.context_timestamp(attendance_rec, attendance_rec.check_out)

            ci_str = ci_local.strftime("%Y-%m-%d %H:%M")
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
                    # message_type="notification",
                    subtype_xmlid="mail.mt_note"
                    # subtype_xmlid="mail.mt_comment"
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
                    # message_type="notification",
                    subtype_xmlid="mail.mt_note"
                    # subtype_xmlid="mail.mt_comment"
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
                    # message_type="notification",
                    subtype_xmlid="mail.mt_note"
                    # subtype_xmlid="mail.mt_comment"
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
                    # message_type="notification",
                    subtype_xmlid="mail.mt_note"
                    # subtype_xmlid="mail.mt_comment"
                )

            if "missing_checkin" in status_list:
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
                    # message_type="notification",
                    subtype_xmlid="mail.mt_note"
                    # subtype_xmlid="mail.mt_comment"
                )

            if "missing_checkout" in status_list:
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
                    # message_type="notification",
                    subtype_xmlid="mail.mt_note"
                    # subtype_xmlid="mail.mt_comment"
                )






    def action_restart_device(self):
        """For restarting the device"""
        zk = ZK(self.device_ip, port=self.port_number, timeout=500000,
                password=0,
                force_udp=False, ommit_ping=False)
        self.device_connect(zk).restart()
