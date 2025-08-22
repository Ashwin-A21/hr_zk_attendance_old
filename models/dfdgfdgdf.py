import datetime
import logging
import pytz
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from datetime import timedelta
from datetime import datetime
from . import sample_punches

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
        """ Process punches of one employee for one day """
        punches = sorted(punches, key=lambda x: x['timestamp'])
        check_in = punches[0]['timestamp'] if punches else None
        check_out = punches[-1]['timestamp'] if len(punches) > 1 else None

        results = {
            "employee_id": employee.id,
            "date": punches[0]['timestamp'].date() if punches else None,
            "check_in": check_in,
            "check_out": check_out,
            "status": [],
            "worked_hours": 0,
            "extra_hours": 0,
        }

        if check_in and check_out:
            worked_hours = (check_out - check_in).total_seconds() / 3600
            results["worked_hours"] = worked_hours

            # Early / Late logic
            if check_in < shift_start:
                results["status"].append("early_checkin")
            elif check_in > shift_start:
                results["status"].append("late_checkin")

            if check_out < shift_end:
                results["status"].append("early_checkout")
            elif check_out > shift_end:
                results["status"].append("late_checkout")

            planned_hours = (shift_end - shift_start).total_seconds() / 3600
            if worked_hours > planned_hours:
                results["status"].append("extra_hours")
                results["extra_hours"] = worked_hours - planned_hours
            elif worked_hours < planned_hours:
                results["status"].append("less_hours")

        elif check_in and not check_out:
            results["status"].append("missing_checkout")
            # Auto checkout at shift end
            results["check_out"] = shift_end
            results["worked_hours"] = (shift_end - check_in).total_seconds() / 3600

        elif check_out and not check_in:
            results["status"].append("missing_checkin")
            # Auto checkin at shift start
            results["check_in"] = shift_start
            results["worked_hours"] = (check_out - shift_start).total_seconds() / 3600

        else:
            results["status"].append("absent")

        return results


    def action_download_attendance(self):
        zk_attendance = self.env['zk.machine.attendance']
        hr_attendance = self.env['hr.attendance']
        incomplete_attendances = []   # 👈 track incomplete ones

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

                use_sample = True  
                if use_sample:
                    attendance = sample_punches.data   # 👈 use your test data

                if attendance:
                    # Group punches by employee+day
                    punches_by_emp_day = {}
                    for each in attendance:
                        atten_time = each['timestamp']
                        local_tz = pytz.timezone(self.env.user.partner_id.tz or 'GMT')
                        local_dt = local_tz.localize(atten_time, is_dst=None)
                        utc_dt = local_dt.astimezone(pytz.utc)
                        atten_time = fields.Datetime.to_string(utc_dt)

                        # Save punch in zk.machine.attendance (raw log)
                        employee = self.env['hr.employee'].search(
                            [('device_id_num', '=', each['user_id'])], limit=1)
                        if not employee:
                            continue

                        duplicate = zk_attendance.search([
                            ('device_id_num', '=', each['user_id']),
                            ('punching_time', '=', atten_time)
                        ])
                        if not duplicate:
                            zk_attendance.create({
                                'employee_id': employee.id,
                                'device_id_num': each['user_id'],
                                'attendance_type': str(each['status']),
                                'punch_type': str(each['punch']),
                                'punching_time': atten_time,
                                'address_id': info.address_id.id
                            })

                        day = fields.Datetime.from_string(atten_time).date()
                        punches_by_emp_day.setdefault((employee.id, day), []).append({
                            "user_id": each['user_id'],
                            "timestamp": fields.Datetime.from_string(atten_time),
                            "status": each['status'],
                            "punch": each['punch'],
                        })

                    # Process grouped punches
                    for (emp_id, day), punches in punches_by_emp_day.items():
                        employee = self.env['hr.employee'].browse(emp_id)

                        # Get shift timings (example: 9 AM - 4:30 PM)
                        shift_start = datetime.combine(day, datetime.min.time()) + timedelta(hours=9)
                        shift_end = datetime.combine(day, datetime.min.time()) + timedelta(hours=16, minutes=30)

                        result = self.process_attendance(punches, employee, shift_start, shift_end)

                        # Track incomplete
                        if "missing_checkin" in result["status"] or "missing_checkout" in result["status"] or "absent" in result["status"]:
                            incomplete_attendances.append(result)

                        # Create or update hr.attendance
                        if result["check_in"] and result["check_out"]:
                            existing = hr_attendance.search([
                                ('employee_id', '=', employee.id),
                                ('check_in', '=', result["check_in"])
                            ], limit=1)

                            vals = {
                                'employee_id': employee.id,
                                'check_in': result["check_in"],
                                'check_out': result["check_out"],
                                'worked_hours': result["worked_hours"],
                                'status': ", ".join(result["status"]),
                                'overtime_hours': result["extra_hours"],
                            }

                            if not existing:
                                hr_attendance.create(vals)
                            else:
                                existing.write(vals)

                conn.enable_device()
                conn.disconnect()
                return True
            else:
                raise UserError(_('Unable to connect, please check the parameters and network connections.'))


    def action_restart_device(self):
        """For restarting the device"""
        zk = ZK(self.device_ip, port=self.port_number, timeout=500000,
                password=0,
                force_udp=False, ommit_ping=False)
        self.device_connect(zk).restart()
