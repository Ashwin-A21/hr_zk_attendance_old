# -*- coding: utf-8 -*-
from odoo import fields, models

class HrEmployeeWorksheet(models.Model):
    _name = 'hr.employee.worksheet'
    _description = 'Employee Worksheet'

    resource_calendar_id = fields.Many2one('resource.calendar', string='Working Hours',
                                           ondelete='cascade', index=True, required=True)
    day_of_week = fields.Selection([
        ('monday', 'Monday'),
        ('tuesday', 'Tuesday'),
        ('wednesday', 'Wednesday'),
        ('thursday', 'Thursday'),
        ('friday', 'Friday'),
        ('saturday', 'Saturday'),
        ('sunday', 'Sunday')
    ], string='Day of the Week', required=True)
    work_from = fields.Float(string='Work From')
    work_to = fields.Float(string='Work To')
    break_from = fields.Float(string='Break From')
    break_to = fields.Float(string='Break To' )