# -*- coding: utf-8 -*-
################################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2024-TODAY Cybrosys Technologies(<https://www.cybrosys.com>).
#    Author: Ammu Raj (odoo@cybrosys.com)
#
#    You can modify it under the terms of the GNU AFFERO
#    GENERAL PUBLIC LICENSE (AGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU AFFERO GENERAL PUBLIC LICENSE (AGPL v3) for more details.
#
#    You should have received a copy of the GNU AFFERO GENERAL PUBLIC LICENSE
#    (AGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
################################################################################
import datetime
import logging
import pytz
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from datetime import timedelta

_logger = logging.getLogger(__name__)
try:
    from zk import ZK, const
except ImportError:
    _logger.error("Please Install pyzk library.")


class BiometricDeviceDetails(models.Model):
    """Model for configuring and connect the biometric device with odoo"""
    _name = 'biometric.device.details'
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

    def action_download_attendance(self): 

        zk_attendance = self.env['zk.machine.attendance']
        hr_attendance = self.env['hr.attendance']
        
        for info in self:
            machine_ip = info.device_ip
            zk_port = info.port_number
            
            try:
                # Connecting with the device with the ip and port provided
                zk = ZK(machine_ip, port=zk_port, timeout=150000, password=0,
                        force_udp=False, ommit_ping=False)
            except NameError:
                raise UserError(_("Pyzk module not Found. Please install it with 'pip3 install pyzk'."))
            
            conn = self.device_connect(zk)
            # self.action_set_timezone()
            
            if conn:
                conn.disable_device()
                user = conn.get_users()
                attendance = conn.get_attendance()
                
                if attendance:
                    for each in sorted(attendance, key=lambda x: x.timestamp):  # ensure sorted punches
                        atten_time = each.timestamp
                        local_tz = pytz.timezone(self.env.user.partner_id.tz or 'GMT')
                        local_dt = local_tz.localize(atten_time, is_dst=None)
                        utc_dt = local_dt.astimezone(pytz.utc)
                        atten_time = fields.Datetime.to_string(utc_dt)

                        for uid in user:
                            if uid.user_id == each.user_id:
                                employee = self.env['hr.employee'].search(
                                    [('device_id_num', '=', each.user_id)], limit=1)

                                if employee:
                                    duplicate_atten_ids = zk_attendance.search([
                                        ('device_id_num', '=', each.user_id),
                                        ('punching_time', '=', atten_time)
                                    ])
                                    if not duplicate_atten_ids:
                                        zk_attendance.create({
                                            'employee_id': employee.id,
                                            'device_id_num': each.user_id,
                                            'attendance_type': str(each.status),
                                            'punch_type': str(each.punch),
                                            'punching_time': atten_time,
                                            'address_id': info.address_id.id
                                        })

                                        last_attendance = hr_attendance.search([
                                            ('employee_id', '=', employee.id)
                                        ], order="check_in desc", limit=1)

                                        punch_dt = fields.Datetime.from_string(atten_time)

                                        if last_attendance and not last_attendance.check_out:
                                            last_checkin = last_attendance.check_in
                                            time_diff = punch_dt - last_checkin
                                            gap_minutes = 10 

                                           
                                            if time_diff.total_seconds() >= gap_minutes * 60:
                                                forced_checkout_time = last_checkin + timedelta(minutes=gap_minutes)
                                                last_attendance.write({'check_out': forced_checkout_time})

                                                # Notify HR Managers
                                                hr_admin = self.env.ref('hr_attendance.group_hr_attendance_manager')
                                                hr_admin_users = self.env['res.users'].search([('groups_id', 'in', hr_admin.ids)])
                                                last_attendance.message_post(
                                                    body=f"Attendance Check-In record {last_attendance.id} for employee {employee.name} was auto-checked out after {gap_minutes} hours.",
                                                    subject="Auto Check-Out Notification",
                                                    message_type='notification',
                                                    subtype_xmlid='mail.mt_note',
                                                    partner_ids=[user.partner_id.id for user in hr_admin_users]
                                                )

                                                hr_attendance.create({
                                                    'employee_id': employee.id,
                                                    'check_in': punch_dt
                                                })
                                            else:
                                                last_attendance.write({'check_out': punch_dt})
                                        else:
                                            hr_attendance.create({
                                                'employee_id': employee.id,
                                                'check_in': punch_dt
                                            })
                                 
                
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
