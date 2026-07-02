# -*- coding: utf-8 -*-
{
    'name': 'Hotel Housekeeping & Lost/Found Management',
    'version': '19.0.1.0.0',
    'summary': 'Manage hotel room cleaning tasks, dynamic checklists, and lost & found tracking.',
    'category': 'Hotel Management',
    'author': 'MindSynth',
    'depends': ['base', 'mail', 'hotel_management_core'],
    'data': [
        'security/housekeeping_security.xml',
        'security/ir.model.access.csv',
        'data/housekeeping_sequence.xml',
        'views/housekeeping_checklist_views.xml',
        'views/housekeeping_task_views.xml',
        'views/lost_found_views.xml',
        'views/housekeeping_menu.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}