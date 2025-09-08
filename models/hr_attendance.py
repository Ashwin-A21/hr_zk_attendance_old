from odoo import models, api, fields
from markupsafe import Markup
import pytz

class HrAttendance(models.Model):
    _inherit = 'hr.attendance'

    check_in_is_corrected = fields.Boolean(
        string="Check-in Corrected",
        default=False,
        help="Indicates if the check-in time has been manually corrected."
    )
    check_out_is_corrected = fields.Boolean(
        string="Check-out Corrected",
        default=False,
        help="Indicates if the check-out time has been manually corrected."
    )

    def write(self, vals):
        # Set correction flags on manual edits by HR Managers,
        # but NOT during automated updates from the biometric device.
        if not self.env.context.get('automated_update') and \
           self.env.user.has_group('hr_attendance.group_hr_attendance_manager'):
            if 'check_in' in vals:
                vals['check_in_is_corrected'] = True
            if 'check_out' in vals:
                vals['check_out_is_corrected'] = True
        return super(HrAttendance, self).write(vals)