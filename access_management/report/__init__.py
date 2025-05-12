# -*- coding: utf-8 -*-
# __init__.py (root)

from . import models
from . import wizard
from . import controllers
from . import report

from odoo import api, SUPERUSER_ID
import logging

_logger = logging.getLogger(__name__)


def post_init_hook(cr, registry):
    """Post installation hook"""
    env = api.Environment(cr, SUPERUSER_ID, {})
    
    # Create default access rules
    _logger.info("Creating default access management rules...")
    
    # Create a default rule for demonstration
    default_rule = env['access.management'].create({
        'name': 'Default Access Rule (Inactive)',
        'active': False,
        'apply_by_group': True,
        'sequence': 100,
    })
    
    _logger.info("Access Management module installed successfully")


def uninstall_hook(cr, registry):
    """Uninstall hook"""
    env = api.Environment(cr, SUPERUSER_ID, {})
    
    _logger.info("Cleaning up Access Management data...")
    
    # Clean up any custom data if needed
    # This is optional but can be useful for cleanup
    
    _logger.info("Access Management module uninstalled")


# models/__init__.py
from . import access_management
from . import access_management_menu
from . import access_management_model
from . import access_management_field
from . import access_management_domain
from . import access_management_button_tab
from . import access_management_chatter
from . import access_management_inheritance


# wizard/__init__.py
from . import access_management_menu_wizard
from . import access_management_import_wizard
from . import access_management_copy_wizard


# controllers/__init__.py
from . import main
from . import portal


# report/__init__.py
from . import access_management_report
