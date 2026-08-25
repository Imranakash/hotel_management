# -*- coding: utf-8 -*-
{
    'name': 'Hotel Discount & Promotion Management',
    'version': '19.0.1.0.0',
    'summary': 'Manage Discounts, Coupons, Promo Campaigns, and Approvals for Hotel Bookings',
    'category': 'Hospitality',
    'author': 'Your Name',
    'depends': ['base', 'mail', 'hotel_management_core'],
    'data': [
        'security/ir.model.access.csv',
        'views/hotel_discount_campaign_views.xml',
        'views/hotel_reservation_inherit_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}