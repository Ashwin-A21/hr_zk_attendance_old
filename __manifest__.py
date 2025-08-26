{
    'name': 'Biometric Device Integration',
    'version': '17.0.1.3.0',
    'category': 'Human Resources',
    'summary': "Integrating Biometric Device (Model: ZKteco uFace 202) With HR Attendance (Face + Thumb)",
    'description': "This module integrates Odoo with the biometric device(Model: ZKteco uFace 202),odoo17,odoo,hr,attendance",
    'depends': ['base_setup', 'hr_attendance', 'resource'],
    'external_dependencies': {
        'python': ['pyzk'],
    },
    'data': [
        'security/ir.model.access.csv',
        'views/biometric_device_details_views.xml',
        'views/hr_employee_views.xml',
        'views/hr_attendance_views.xml',
        'views/daily_attendance_views.xml',
        'views/biometric_device_attendance_menus.xml',
        'views/resource_calendar_views.xml',
        'views/hr_attendance_report_views.xml',
        'data/download_data.xml',
        'data/ir_cron_data.xml'
    ],
    'images': ['static/description/banner.png'],
    'license': 'AGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}