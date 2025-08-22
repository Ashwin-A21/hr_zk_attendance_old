# hr_zk_attendance/models/hr_attendance.py
from odoo import models, api, fields
from markupsafe import Markup
import pytz

class HrAttendance(models.Model):
    _inherit = 'hr.attendance'

    is_corrected = fields.Boolean(string="Is Corrected", default=False,
                                  help="Indicates if this attendance record has been manually corrected.")

    def write(self, vals):
        # **FIX**: Set 'is_corrected' to True on manual edits by HR Managers
        if self.env.user.has_group('hr_attendance.group_hr_attendance_manager') and \
           any(field in ['check_in', 'check_out'] for field in vals):
            vals['is_corrected'] = True
        return super(HrAttendance, self).write(vals)