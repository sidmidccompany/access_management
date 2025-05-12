# migrations/16.0.1.0.0/post-migration.py

from odoo import api, SUPERUSER_ID
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """Post-migration script"""
    if not version:
        return
    
    env = api.Environment(cr, SUPERUSER_ID, {})
    _logger.info("Starting Access Management post-migration...")
    
    # Update states for existing rules
    cr.execute("""
        UPDATE access_management 
        SET state = CASE 
            WHEN active = true THEN 'active'
            ELSE 'disabled'
        END
        WHERE state IS NULL;
    """)
    
    # Migrate old permission names to new structure
    old_to_new_mapping = {
        'access_management_admin': 'access_management.group_access_management_admin',
        'access_management_manager': 'access_management.group_access_management_manager',
        'access_management_user': 'access_management.group_access_management_user',
    }
    
    for old_name, new_name in old_to_new_mapping.items():
        cr.execute("""
            UPDATE res_groups 
            SET name = %s 
            WHERE name = %s;
        """, (new_name, old_name))
    
    # Set default values for new fields
    cr.execute("""
        UPDATE access_management 
        SET created_by = create_uid,
            created_on = create_date,
            last_updated_by = write_uid,
            last_updated_on = write_date
        WHERE created_by IS NULL;
    """)
    
    # Create default email templates if they don't exist
    template_model = env['mail.template']
    if not template_model.search([('name', '=', 'Access Management - Access Request')]):
        _logger.info("Creating default email templates...")
        # Templates would be created via data files
    
    # Update menu sequences
    cr.execute("""
        UPDATE ir_ui_menu 
        SET sequence = sequence + 100 
        WHERE parent_id IN (
            SELECT id FROM ir_ui_menu 
            WHERE name = 'Access Studio'
        );
    """)
    
    # Clean up backup table
    cr.execute("DROP TABLE IF EXISTS access_management_backup;")
    
    _logger.info("Access Management post-migration completed")

