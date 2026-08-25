# -*- coding: utf-8 -*-
{
    'name': 'Hotel Rate Plan & Pricing',
    'version': '19.0.1.0.0',
    'summary': 'Rate Plans, Seasonal Pricing, Packages, and Early/Late Charges',
    'category': 'Hospitality',
    'author': 'Akash',
    'depends': ['base', 'hotel_management_core','mail'],
    'data': [
        'security/ir.model.access.csv',
        'views/hotel_rate_plan_views.xml',
    ],
    'installable': True,
    'application': True,
}