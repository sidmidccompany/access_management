# -*- coding: utf-8 -*-
# migrations/16.0.1.0.0/pre-migration.py

from odoo import api, SUPERUSER_ID
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """Pre-migration script"""
    if not version:
        return
    
    env = api.Environment(cr, SUPERUSER_ID, {})
    _logger.info("Starting Access Management pre-migration...")
    
    # Backup existing access rules if any
    cr.execute("""
        CREATE TABLE IF NOT EXISTS access_management_backup AS 
        SELECT * FROM access_management WHERE id > 0;
    """)
    
    # Clean up orphaned records
    cr.execute("""
        DELETE FROM access_management_menu 
        WHERE access_id NOT IN (SELECT id FROM access_management);
    """)
    
    cr.execute("""
        DELETE FROM access_management_model 
        WHERE access_id NOT IN (SELECT id FROM access_management);
    """)
    
    cr.execute("""
        DELETE FROM access_management_field 
        WHERE access_id NOT IN (SELECT id FROM access_management);
    """)
    
    _logger.info("Access Management pre-migration completed")
