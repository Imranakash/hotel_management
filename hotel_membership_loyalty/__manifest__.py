# -*- coding: utf-8 -*-
{
    'name': 'Hotel Membership & Loyalty Management',
    'version': '19.0.1.0.0',
    'summary': 'Manage membership plans, VIP tiers, benefits, loyalty points, free nights, and redemption.',
    'category': 'Hotel Management',
    'author': 'MindSynth Technologies',
    'depends': ['base', 'hotel_management_core'],
    'data': [
        'security/membership_security.xml',
        'security/ir.model.access.csv',
        'views/hotel_membership_tier_views.xml',
        'views/hotel_loyalty_rule_views.xml',
        'views/hotel_loyalty_history_views.xml',
        'views/res_partner_views.xml',
        'views/hotel_membership_menus.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}