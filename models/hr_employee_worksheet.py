# -*- coding: utf-8 -*-
from odoo import fields, models

class HrEmployeeWorksheet(models.Model):
    _name = 'hr.employee.worksheet'
    _description = 'Employee Worksheet'

    employee_id = fields.Many2one('hr.employee', string='Employee')
    day_of_week = fields.Selection([
        ('monday', 'Monday'),
        ('tuesday', 'Tuesday'),
        ('wednesday', 'Wednesday'),
        ('thursday', 'Thursday'),
        ('friday', 'Friday'),
        ('saturday', 'Saturday'),
        ('sunday', 'Sunday')
    ], string='Day of the Week', required=True)
    work_from = fields.Float(string='Work From', default=8.5)
    work_to = fields.Float(string='Work To', default=18.0)