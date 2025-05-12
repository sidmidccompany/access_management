# Access Management Configuration Guide

This guide provides detailed instructions for configuring the Access Management module in Odoo.

## Table of Contents

1. [Initial Setup](#initial-setup)
2. [User Groups Configuration](#user-groups-configuration)
3. [Creating Access Rules](#creating-access-rules)
4. [Advanced Configuration](#advanced-configuration)
5. [Performance Tuning](#performance-tuning)
6. [Security Best Practices](#security-best-practices)
7. [Troubleshooting](#troubleshooting)

## Initial Setup

### 1. Module Installation

After installing the module, perform these initial configuration steps:

1. **Assign Administrator Role**
   ```
   Settings > Users & Companies > Users
   - Select your admin user
   - Add "Access Management / Administrator" group
   ```

2. **Configure System Parameters**
   ```
   Settings > Technical > Parameters > System Parameters
   ```
   
   Create or update these parameters:
   - `access_management.cache_timeout`: 3600 (1 hour)
   - `access_management.audit_retention_days`: 90
   - `access_management.enable_notifications`: True

3. **Set Up Email Templates**
   ```
   Settings > Technical > Email > Templates
   ```
   
   Verify these templates exist:
   - Access Management - Access Request
   - Access Management - Access Granted
   - Access Management - Access Denied

### 2. Enable Scheduled Actions

Navigate to **Settings > Technical > Automation > Scheduled Actions** and enable:

- **Access Management: Review Expired Rules**
  - Interval: Daily
  - Next Execution: Set to tomorrow at 2 AM

- **Access Management: Generate Audit Report**
  - Interval: Weekly
  - Next Execution: Next Monday at 3 AM

## User Groups Configuration

### Creating Custom Access Groups

1. **Create a New Group**
   ```
   Settings > Users & Companies > Groups > Create
   ```
   
   Example: "Sales Limited Access"
   - Name: Sales Limited Access
   - Application: Sales
   - Inherited: Sales / User

2. **Link to Access Management**
   ```
   Access Studio > Access Management > Create
   ```
   
   - Name: Sales Limited Access Rule
   - Apply by Group: ✓
   - Groups: Sales Limited Access

### Group Hierarchy

Recommended group structure:
```
Company
├── Department Managers
│   ├── Sales Manager
│   ├── HR Manager
│   └── Finance Manager
├── Department Users
│   ├── Sales Team
│   ├── HR Team
│   └── Finance Team
└── External Users
    ├── Portal Users
    └── Vendors
```

## Creating Access Rules

### Basic Rule Creation

1. **Navigate to Access Management**
   ```
   Access Studio > Access Management > Create
   ```

2. **Basic Configuration**
   - **Name**: Descriptive name (e.g., "Sales Team - Customer Access Only")
   - **Sequence**: Lower numbers apply first (default: 10)
   - **Active**: Check to enable immediately
   - **Apply by Group**: Check for group-based rules

3. **Target Selection**
   - **Users**: Select individual users
   - **Groups**: Select user groups
   - **User Types**: 
     - Default Internal User
     - Default Portal User

### Menu Access Configuration

1. **Hide Menu Tab**
   - Click "Add a line"
   - Select menu to hide
   - Check "Hidden" box

   Example: Hide Settings menu
   ```
   Menu: Settings/General Settings
   Hidden: ✓
   ```

### Model Access Configuration

1. **Model Access Tab**
   - Add models to restrict
   - Set CRUD permissions

   Example: Read-only access to contacts
   ```
   Model: Contact
   Read: ✓
   Write: ✗
   Create: ✗
   Delete: ✗
   ```

### Field Access Configuration

1. **Field Access Tab**
   - Select model
   - Choose field
   - Set restrictions

   Example: Hide credit limit field
   ```
   Model: Contact
   Field: Credit Limit
   Read Only: ✗
   Invisible: ✓
   Required: ✗
   ```

### Domain Access Configuration

1. **Domain Access Tab**
   - Select model
   - Add filter domain

   Example: Show only customers
   ```
   Model: Contact
   Description: Customers Only
   Domain: [('customer_rank', '>', 0)]
   ```

### Conditional Field Access

1. **Field Conditional Access Tab**
   - Set field restrictions based on conditions

   Example: Make field readonly for draft records
   ```
   Model: Sale Order
   Field: Total Amount
   Condition: record.state == 'draft'
   Read Only: ✓
   ```

## Advanced Configuration

### Global Access Rules

Use Python code for complex access logic:

```python
# Example: Restrict based on department
if user.department_id.name == 'Sales':
    if record.customer_rank > 0:
        return True
return False
```

### Multi-Company Setup

1. **Company-Specific Rules**
   - Set Company field on access rule
   - Rule applies only to that company

2. **Global Rules**
   - Leave Company field empty
   - Rule applies to all companies

### Scheduled Reviews

Configure automatic rule reviews:

1. **Expiration Dates**
   ```python
   rule.expiration_date = fields.Date.today() + timedelta(days=90)
   ```

2. **Review Notifications**
   - Set up email alerts for expiring rules
   - Configure review workflows

## Performance Tuning

### Cache Configuration

1. **Adjust Cache Timeout**
   ```
   System Parameters:
   access_management.cache_timeout = 7200  # 2 hours
   ```

2. **Cache Warming**
   ```python
   # Scheduled action to warm cache
   users = env['res.users'].search([])
   for user in users:
       env['access.management']._get_applicable_rules(user)
   ```

### Database Optimization

1. **Add Indexes**
   ```sql
   CREATE INDEX idx_access_mgmt_active ON access_management(active);
   CREATE INDEX idx_access_mgmt_user ON access_management_users_rel(user_id);
   CREATE INDEX idx_access_mgmt_group ON access_management_groups_rel(group_id);
   ```

2. **Query Optimization**
   - Use select fields when possible
   - Limit search results
   - Batch process large operations

## Security Best Practices

### Rule Design

1. **Principle of Least Privilege**
   - Grant minimum required permissions
   - Start restrictive, add permissions as needed

2. **Regular Audits**
   - Review active rules monthly
   - Check for unused rules
   - Verify user assignments

3. **Testing Protocol**
   - Test rules in staging first
   - Use test users for validation
   - Document expected behavior

### Access Monitoring

1. **Enable Audit Logging**
   ```python
   env['ir.config_parameter'].set_param(
       'access_management.enable_audit_log', 'True'
   )
   ```

2. **Monitor Violations**
   - Set up alerts for access violations
   - Review denial patterns
   - Adjust rules based on legitimate needs

### Backup and Recovery

1. **Regular Backups**
   ```bash
   # Backup access rules
   pg_dump -t access_management* > access_backup.sql
   ```

2. **Export Rules**
   ```python
   # Export to JSON
   rules = env['access.management'].search([])
   data = rules.export_rules(format='json')
   ```

## Troubleshooting

### Common Issues

1. **Rules Not Applied**
   - Clear browser cache
   - Check rule is active
   - Verify user group membership
   - Review rule sequence

2. **Performance Issues**
   ```python
   # Check cache stats
   from odoo.addons.access_management.utils import access_cache
   print(access_cache.get_stats())
   ```

3. **Conflicting Rules**
   - Check rule sequence order
   - Most restrictive rule wins
   - Use debug mode to trace

### Debug Mode

1. **Enable Debug Logging**
   ```python
   import logging
   _logger = logging.getLogger('access_management')
   _logger.setLevel(logging.DEBUG)
   ```

2. **Test Specific User**
   ```python
   user = env['res.users'].browse(user_id)
   rules = env['access.management']._get_applicable_rules(user)
   for rule in rules:
       print(f"Rule: {rule.name}, Sequence: {rule.sequence}")
   ```

### Emergency Recovery

1. **Disable All Rules**
   ```sql
   UPDATE access_management SET active = false;
   ```

2. **Reset Permissions**
   ```python
   # Run as admin
   env['access.management'].search([]).write({'active': False})
   env.cr.commit()
   ```

## Examples

### Example 1: Sales Team Configuration

```python
# Create rule for sales team
rule = env['access.management'].create({
    'name': 'Sales Team - Limited Access',
    'active': True,
    'apply_by_group': True,
    'group_ids': [(6, 0, [env.ref('sales_team.group_sale_salesman').id])],
})

# Hide settings menu
env['access.management.menu'].create({
    'access_id': rule.id,
    'menu_id': env.ref('base.menu_administration').id,
    'hidden': True,
})

# Restrict partner access
env['access.management.model'].create({
    'access_id': rule.id,
    'model_id': env.ref('base.model_res_partner').id,
    'perm_read': True,
    'perm_write': True,
    'perm_create': False,
    'perm_unlink': False,
})

# Show only customers
env['access.management.domain'].create({
    'access_id': rule.id,
    'model_id': env.ref('base.model_res_partner').id,
    'name': 'Customers Only',
    'domain': "[('customer_rank', '>', 0)]",
})
```

### Example 2: Read-Only Viewer Role

```python
# Create read-only rule
rule = env['access.management'].create({
    'name': 'Read-Only Viewer',
    'active': True,
    'read_only': True,
    'apply_by_group': True,
    'group_ids': [(6, 0, [readonly_group.id])],
})

# Apply to all models
models = env['ir.model'].search([('transient', '=', False)])
for model in models:
    env['access.management.model'].create({
        'access_id': rule.id,
        'model_id': model.id,
        'perm_read': True,
        'perm_write': False,
        'perm_create': False,
        'perm_unlink': False,
    })
```

## Maintenance Schedule

### Daily Tasks
- Review access violation logs
- Check for expired temporary rules
- Monitor system performance

### Weekly Tasks
- Audit rule changes
- Review user access reports
- Update documentation

### Monthly Tasks
- Full access audit
- Performance optimization
- Rule cleanup and consolidation

### Quarterly Tasks
- Security assessment
- User training updates
- Policy review and updates
