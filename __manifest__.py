<<<<<<< HEAD
# hr_zk_attendance/__manifest__.py
{
    'name': 'Biometric Device Integration',
    'version': '17.0.1.3.2', # Incremented version
    'category': 'Human Resources',
    'summary': "Integrating Biometric Device (Model: ZKteco uFace 202) With HR Attendance (Face + Thumb)",
    'description': "This module integrates Odoo with the biometric device(Model: ZKteco uFace 202),odoo17,odoo,hr,attendance",
    'author': 'Concept Solutions ',
    'website': 'https://www.csloman.com',
=======
{
    'name': 'Biometric Device Integration',
    'version': '17.0.1.3.0',
    'category': 'Human Resources',
    'summary': "Integrating Biometric Device (Model: ZKteco uFace 202) With HR Attendance (Face + Thumb)",
    'description': "This module integrates Odoo with the biometric device(Model: ZKteco uFace 202),odoo17,odoo,hr,attendance",
>>>>>>> a58772681a33aa74879ebd15d5baa7319d4cb73b
    'depends': ['base_setup', 'hr_attendance', 'resource'],
    'external_dependencies': {
        'python': ['pyzk'],
    },
    'data': [
        'security/ir.model.access.csv',
        'data/hr_night_shift_schedule_data.xml', 
        'views/biometric_device_details_views.xml',
        'views/hr_employee_views.xml',
        'views/hr_attendance_views.xml',
        'views/daily_attendance_views.xml',
        'views/biometric_device_attendance_menus.xml',
        'views/resource_calendar_views.xml',
        'views/hr_attendance_report_views.xml',
        'views/hr_night_shift_schedule_views.xml',
        'data/download_data.xml',
        'data/ir_cron_data.xml'
    ],
    'images': ['static/description/banner.png'],
    'license': 'AGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}