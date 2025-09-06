# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class ResourceCalendar(models.Model):
    _inherit = 'resource.calendar'

    worksheet_ids = fields.One2many('hr.employee.worksheet', 'resource_calendar_id',
                                    string='Worksheet', copy=True)

    @api.model_create_multi
    def create(self, vals_list):
        calendars = super().create(vals_list)
        for calendar in calendars:
            if not calendar.worksheet_ids:
                calendar._create_missing_worksheet_lines()
        return calendars

    def write(self, vals):
        res = super().write(vals)
        # If attendance_ids are changed directly, resync the worksheet
        if 'attendance_ids' in vals:
            for calendar in self:
                calendar._compute_worksheet_times_from_attendances()
        return res

    def _compute_worksheet_times(self):
        """
        Compute method to get times from the worksheet data to display on the form.
        """
        for calendar in self:
            for day_str in ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']:
                worksheet = calendar.worksheet_ids.filtered(lambda w: w.day_of_week == day_str)
                if worksheet:
                    calendar[f'{day_str}_from'] = worksheet.work_from
                    calendar[f'{day_str}_to'] = worksheet.work_to
                    calendar[f'{day_str}_break_from'] = worksheet.break_from
                    calendar[f'{day_str}_break_to'] = worksheet.break_to
                else:
                    # If no worksheet line exists, create one with default values
                    calendar._create_missing_worksheet_lines()
                    worksheet = calendar.worksheet_ids.filtered(lambda w: w.day_of_week == day_str)
                    calendar[f'{day_str}_from'] = worksheet.work_from
                    calendar[f'{day_str}_to'] = worksheet.work_to
                    calendar[f'{day_str}_break_from'] = worksheet.break_from
                    calendar[f'{day_str}_break_to'] = worksheet.break_to

    def _compute_worksheet_times_from_attendances(self):
        """
        Specialized method to populate the worksheet based on standard attendance lines.
        This is typically called after a direct modification of 'Working Hours'.
        """
        day_map = {'monday': '0', 'tuesday': '1', 'wednesday': '2', 'thursday': '3',
                   'friday': '4', 'saturday': '5', 'sunday': '6'}
        for calendar in self:
            calendar.worksheet_ids.unlink()
            calendar._create_missing_worksheet_lines()
            
            for day_str, day_int in day_map.items():
                worksheet = calendar.worksheet_ids.filtered(lambda w: w.day_of_week == day_str)
                if not worksheet: continue

                day_attendances = calendar.attendance_ids.filtered(lambda att: att.dayofweek == day_int).sorted('hour_from')
                
                next_day_int = str((int(day_int) + 1) % 7)
                next_day_attendances = calendar.attendance_ids.filtered(lambda att: att.dayofweek == next_day_int).sorted('hour_from')
                
                night_shift_part1 = day_attendances.filtered(lambda att: att.hour_to == 24.0)
                night_shift_part2 = next_day_attendances.filtered(lambda att: att.hour_from == 0.0)

                if night_shift_part1 and night_shift_part2:
                    worksheet.work_from = night_shift_part1[-1].hour_from
                    worksheet.work_to = night_shift_part2[0].hour_to
                    lunch = day_attendances.filtered(lambda att: att.day_period == 'lunch')
                    if lunch:
                         worksheet.break_from = lunch[0].hour_from
                         worksheet.break_to = lunch[0].hour_to
                elif day_attendances and not any(att.name.endswith("Night Shift Part 2") for att in day_attendances):
                    worksheet.work_from = min(day_attendances.mapped('hour_from'))
                    worksheet.work_to = max(day_attendances.mapped('hour_to'))
                    lunch = day_attendances.filtered(lambda att: att.day_period == 'lunch')
                    if lunch:
                        worksheet.break_from = lunch[0].hour_from
                        worksheet.break_to = lunch[0].hour_to

    def _create_missing_worksheet_lines(self):
        self.ensure_one()
        all_days = {'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday'}
        existing_days = set(self.worksheet_ids.mapped('day_of_week'))
        missing_days = all_days - existing_days
        if missing_days:
            weekdays = {'monday', 'tuesday', 'wednesday', 'thursday', 'friday'}
            vals_list = []
            for day in missing_days:
                is_weekday = day in weekdays
                vals_list.append({
                    'resource_calendar_id': self.id,
                    'day_of_week': day,
                    'work_from': 9.0 if is_weekday else 0.0, 'work_to': 17.5 if is_weekday else 0.0,
                    'break_from': 13.0 if is_weekday else 0.0, 'break_to': 14.0 if is_weekday else 0.0,
                })
            self.env['hr.employee.worksheet'].create(vals_list)

    def _set_day_value(self, day, from_time=None, to_time=None, break_from=None, break_to=None):
        day_map = {'monday': '0', 'tuesday': '1', 'wednesday': '2', 'thursday': '3',
                   'friday': '4', 'saturday': '5', 'sunday': '6'}
        day_of_week_int = day_map[day]

        for calendar in self:
            worksheet_line = calendar.worksheet_ids.filtered(lambda w: w.day_of_week == day)
            final_from = from_time if from_time is not None else worksheet_line.work_from
            final_to = to_time if to_time is not None else worksheet_line.work_to
            final_break_from = break_from if break_from is not None else worksheet_line.break_from
            final_break_to = break_to if break_to is not None else worksheet_line.break_to

            worksheet_line.write({'work_from': final_from, 'work_to': final_to,
                                  'break_from': final_break_from, 'break_to': final_break_to})

            calendar.attendance_ids.filtered(lambda att: att.dayofweek == day_of_week_int).unlink()
            next_day_int = str((int(day_of_week_int) + 1) % 7)
            calendar.attendance_ids.filtered(
                lambda att: att.dayofweek == next_day_int and day in att.name.lower()
            ).unlink()

            if final_from == 0.0 and final_to == 0.0:
                continue

            is_night_shift = final_to < final_from
            if is_night_shift:
                has_break = final_break_from < final_break_to and final_from <= final_break_from and final_break_to < 24.0

                if has_break:
                    self.env['resource.calendar.attendance'].create({'name': f'{day.capitalize()} Night Shift', 'dayofweek': day_of_week_int, 'hour_from': final_from, 'hour_to': final_break_from, 'calendar_id': calendar.id, 'day_period': 'afternoon'})
                    self.env['resource.calendar.attendance'].create({'name': f'{day.capitalize()} Break', 'dayofweek': day_of_week_int, 'hour_from': final_break_from, 'hour_to': final_break_to, 'calendar_id': calendar.id, 'day_period': 'lunch'})
                    self.env['resource.calendar.attendance'].create({'name': f'{day.capitalize()} Night Shift', 'dayofweek': day_of_week_int, 'hour_from': final_break_to, 'hour_to': 24.0, 'calendar_id': calendar.id, 'day_period': 'afternoon'})
                else:
                    self.env['resource.calendar.attendance'].create({'name': f'{day.capitalize()} Night Shift', 'dayofweek': day_of_week_int, 'hour_from': final_from, 'hour_to': 24.0, 'calendar_id': calendar.id, 'day_period': 'afternoon'})

                self.env['resource.calendar.attendance'].create({'name': f'{day.capitalize()} Night Shift Part 2', 'dayofweek': next_day_int, 'hour_from': 0.0, 'hour_to': final_to, 'calendar_id': calendar.id, 'day_period': 'morning'})

            else:  # Day Shift
                has_break = final_break_from < final_break_to and final_from <= final_break_from and final_break_to <= final_to
                if has_break:
                    self.env['resource.calendar.attendance'].create({'name': f'{day.capitalize()} Morning', 'dayofweek': day_of_week_int, 'hour_from': final_from, 'hour_to': final_break_from, 'calendar_id': calendar.id, 'day_period': 'morning'})
                    self.env['resource.calendar.attendance'].create({'name': f'{day.capitalize()} Break', 'dayofweek': day_of_week_int, 'hour_from': final_break_from, 'hour_to': final_break_to, 'calendar_id': calendar.id, 'day_period': 'lunch'})
                    self.env['resource.calendar.attendance'].create({'name': f'{day.capitalize()} Afternoon', 'dayofweek': day_of_week_int, 'hour_from': final_break_to, 'hour_to': final_to, 'calendar_id': calendar.id, 'day_period': 'afternoon'})
                else:
                    self.env['resource.calendar.attendance'].create({'name': f'{day.capitalize()}', 'dayofweek': day_of_week_int, 'hour_from': final_from, 'hour_to': final_to, 'calendar_id': calendar.id, 'day_period': 'morning'})

    # --- Fields for the Biometric Worksheet tab ---
    monday_from = fields.Float(string="Monday From", compute='_compute_worksheet_times',
                               inverse=lambda self: self._set_day_value('monday', from_time=self[0].monday_from), store=False)
    monday_to = fields.Float(string="Monday To", compute='_compute_worksheet_times',
                             inverse=lambda self: self._set_day_value('monday', to_time=self[0].monday_to), store=False)
    monday_break_from = fields.Float(string="Mon Break From", compute='_compute_worksheet_times',
                                     inverse=lambda self: self._set_day_value('monday', break_from=self[0].monday_break_from), store=False)
    monday_break_to = fields.Float(string="Mon Break To", compute='_compute_worksheet_times',
                                   inverse=lambda self: self._set_day_value('monday', break_to=self[0].monday_break_to), store=False)
    tuesday_from = fields.Float(string="Tuesday From", compute='_compute_worksheet_times',
                                inverse=lambda self: self._set_day_value('tuesday', from_time=self[0].tuesday_from), store=False)
    tuesday_to = fields.Float(string="Tuesday To", compute='_compute_worksheet_times',
                              inverse=lambda self: self._set_day_value('tuesday', to_time=self[0].tuesday_to), store=False)
    tuesday_break_from = fields.Float(string="Tue Break From", compute='_compute_worksheet_times',
                                      inverse=lambda self: self._set_day_value('tuesday', break_from=self[0].tuesday_break_from), store=False)
    tuesday_break_to = fields.Float(string="Tue Break To", compute='_compute_worksheet_times',
                                    inverse=lambda self: self._set_day_value('tuesday', break_to=self[0].tuesday_break_to), store=False)
    wednesday_from = fields.Float(string="Wednesday From", compute='_compute_worksheet_times',
                                  inverse=lambda self: self._set_day_value('wednesday', from_time=self[0].wednesday_from), store=False)
    wednesday_to = fields.Float(string="Wednesday To", compute='_compute_worksheet_times',
                                inverse=lambda self: self._set_day_value('wednesday', to_time=self[0].wednesday_to), store=False)
    wednesday_break_from = fields.Float(string="Wed Break From", compute='_compute_worksheet_times',
                                        inverse=lambda self: self._set_day_value('wednesday', break_from=self[0].wednesday_break_from), store=False)
    wednesday_break_to = fields.Float(string="Wed Break To", compute='_compute_worksheet_times',
                                      inverse=lambda self: self._set_day_value('wednesday', break_to=self[0].wednesday_break_to), store=False)
    thursday_from = fields.Float(string="Thursday From", compute='_compute_worksheet_times',
                                 inverse=lambda self: self._set_day_value('thursday', from_time=self[0].thursday_from), store=False)
    thursday_to = fields.Float(string="Thursday To", compute='_compute_worksheet_times',
                               inverse=lambda self: self._set_day_value('thursday', to_time=self[0].thursday_to), store=False)
    thursday_break_from = fields.Float(string="Thu Break From", compute='_compute_worksheet_times',
                                       inverse=lambda self: self._set_day_value('thursday', break_from=self[0].thursday_break_from), store=False)
    thursday_break_to = fields.Float(string="Thu Break To", compute='_compute_worksheet_times',
                                     inverse=lambda self: self._set_day_value('thursday', break_to=self[0].thursday_break_to), store=False)
    friday_from = fields.Float(string="Friday From", compute='_compute_worksheet_times',
                               inverse=lambda self: self._set_day_value('friday', from_time=self[0].friday_from), store=False)
    friday_to = fields.Float(string="Friday To", compute='_compute_worksheet_times',
                             inverse=lambda self: self._set_day_value('friday', to_time=self[0].friday_to), store=False)
    friday_break_from = fields.Float(string="Fri Break From", compute='_compute_worksheet_times',
                                     inverse=lambda self: self._set_day_value('friday', break_from=self[0].friday_break_from), store=False)
    friday_break_to = fields.Float(string="Fri Break To", compute='_compute_worksheet_times',
                                   inverse=lambda self: self._set_day_value('friday', break_to=self[0].friday_break_to), store=False)
    saturday_from = fields.Float(string="Saturday From", compute='_compute_worksheet_times',
                                 inverse=lambda self: self._set_day_value('saturday', from_time=self[0].saturday_from), store=False)
    saturday_to = fields.Float(string="Saturday To", compute='_compute_worksheet_times',
                               inverse=lambda self: self._set_day_value('saturday', to_time=self[0].saturday_to), store=False)
    saturday_break_from = fields.Float(string="Sat Break From", compute='_compute_worksheet_times',
                                       inverse=lambda self: self._set_day_value('saturday', break_from=self[0].saturday_break_from), store=False)
    saturday_break_to = fields.Float(string="Sat Break To", compute='_compute_worksheet_times',
                                     inverse=lambda self: self._set_day_value('saturday', break_to=self[0].saturday_break_to), store=False)
    sunday_from = fields.Float(string="Sunday From", compute='_compute_worksheet_times',
                               inverse=lambda self: self._set_day_value('sunday', from_time=self[0].sunday_from), store=False)
    sunday_to = fields.Float(string="Sunday To", compute='_compute_worksheet_times',
                             inverse=lambda self: self._set_day_value('sunday', to_time=self[0].sunday_to), store=False)
    sunday_break_from = fields.Float(string="Sun Break From", compute='_compute_worksheet_times',
                                     inverse=lambda self: self._set_day_value('sunday', break_from=self[0].sunday_break_from), store=False)
    sunday_break_to = fields.Float(string="Sun Break To", compute='_compute_worksheet_times',
                                   inverse=lambda self: self._set_day_value('sunday', break_to=self[0].sunday_break_to), store=False)