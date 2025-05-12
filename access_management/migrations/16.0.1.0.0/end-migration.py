
# migrations/16.0.1.0.0/end-migration.py

from odoo import api, SUPERUSER_ID
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """End migration script - final cleanup"""
    if not version:
        return
    
    env = api.Environment(cr, SUPERUSER_ID, {})
    _logger.info("Starting Access Management end-migration...")
    
    # Rebuild access rules cache
    AccessManagement = env['access.management']
    rules = AccessManagement.search([('active', '=', True)])
    
    for rule in rules:
        # Recompute access rules count
        rule._compute_access_rules_count()
    
    # Clear any cached data
    env.registry.clear_caches()
    
    # Log migration completion
    env['ir.config_parameter'].sudo().set_param(
        'access_management.migration_16_completed', 
        'True'
    )
    
    _logger.info("Access Management end-migration completed")
    _logger.info(f"Migrated {len(rules)} active access rules")


# Migration utilities

def backup_table(cr, table_name):
    """Backup a table before migration"""
    backup_name = f"{table_name}_backup_{cr.now()}"
    cr.execute(f"CREATE TABLE {backup_name} AS SELECT * FROM {table_name};")
    return backup_name


def restore_table(cr, table_name, backup_name):
    """Restore a table from backup"""
    cr.execute(f"DROP TABLE IF EXISTS {table_name};")
    cr.execute(f"ALTER TABLE {backup_name} RENAME TO {table_name};")


def add_column_if_not_exists(cr, table_name, column_name, column_type, default=None):
    """Add a column if it doesn't exist"""
    cr.execute(f"""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name='{table_name}' AND column_name='{column_name}';
    """)
    if not cr.fetchone():
        default_clause = f"DEFAULT {default}" if default else ""
        cr.execute(f"""
            ALTER TABLE {table_name} 
            ADD COLUMN {column_name} {column_type} {default_clause};
        """)


def rename_column_if_exists(cr, table_name, old_name, new_name):
    """Rename a column if it exists"""
    cr.execute(f"""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name='{table_name}' AND column_name='{old_name}';
    """)
    if cr.fetchone():
        cr.execute(f"""
            ALTER TABLE {table_name} 
            RENAME COLUMN {old_name} TO {new_name};
        """)


def migrate_data(cr, source_table, target_table, mapping):
    """Migrate data from one table to another with field mapping"""
    fields_from = ', '.join(mapping.keys())
    fields_to = ', '.join(mapping.values())
    
    cr.execute(f"""
        INSERT INTO {target_table} ({fields_to})
        SELECT {fields_from}
        FROM {source_table};
    """)
