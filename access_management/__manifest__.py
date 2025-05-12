# -*- coding: utf-8 -*-
{
    'name': 'Access Management',
    'version': '16.0.1.0.0',
    'category': 'Technical',
    'summary': 'Advanced Access Control Management System',
    'description': """
Access Management Module
=======================

This module provides comprehensive access control features for Odoo:

Key Features:
------------
* User and group-based access rules
* Menu visibility control
* Model-level CRUD permissions
* Field-level access control (readonly, invisible, required)
* Conditional field access based on record values
* Domain-based record filtering
* Button and tab visibility control
* Search panel customization
* Chatter and social features restrictions
* Multi-company support
* Developer mode control
* Import/Export functionality
* Rule testing and validation

Technical Features:
------------------
* Real-time access rule application
* JavaScript frontend integration
* Performance optimized with caching
* Comprehensive logging
* Security groups and record rules
* API endpoints for external integration

Usage:
------
1. Install the module
2. Navigate to Access Studio > Access Management
3. Create new access rules
4. Define users/groups
5. Configure access restrictions
6. Activate the rule

The module integrates seamlessly with Odoo's existing security framework
while providing additional granular control over user access.
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'mail',
        'web',
    ],
    'data': [
        # Security
        'security/access_management_security.xml',
        'security/ir.model.access.csv',
        
        # Data
        'data/access_management_data.xml',
        
        # Wizards
        'wizard/access_management_wizard_views.xml',
        
        # Views
        'views/access_management_views.xml',
        'views/access_management_menus.xml',
        
        # Reports
        'report/access_management_reports.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'access_management/static/src/css/access_management.css',
            'access_management/static/src/js/access_management_component.js',
            'access_management/static/src/js/access_management_service.js',
            'access_management/static/src/xml/access_management_templates.xml',
        ],
        'web.assets_frontend': [
            'access_management/static/src/css/portal_access.css',
        ],
    },
    'demo': [
        'demo/access_management_demo.xml',
    ],
    'images': [
        'static/description/banner.png',
        'static/description/icon.png',
        'static/description/screenshot1.png',
        'static/description/screenshot2.png',
    ],
    'external_dependencies': {
        'python': ['lxml'],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
    'post_init_hook': 'post_init_hook',
    'uninstall_hook': 'uninstall_hook',
}
