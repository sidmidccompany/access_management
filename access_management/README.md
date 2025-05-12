# Access Management Module for Odoo

A comprehensive access control system for Odoo that provides fine-grained permissions management at multiple levels.

## Overview

The Access Management module extends Odoo's built-in security features to provide more granular control over user access. It allows administrators to create detailed access rules that can be applied to users or groups, controlling everything from menu visibility to field-level permissions.

## Features

### Core Features
- **Menu Access Control**: Hide specific menus from users or groups
- **Model-Level Permissions**: Control CRUD operations on any model
- **Field-Level Security**: Make fields read-only, invisible, or required
- **Domain-Based Filtering**: Restrict which records users can see
- **UI Element Control**: Hide or disable buttons, tabs, and other UI elements
- **Conditional Field Access**: Apply field restrictions based on record values
- **Chatter Restrictions**: Control social features and communication
- **Multi-Company Support**: Apply rules per company or globally

### Administrative Features
- **Access Rule Templates**: Create reusable rule templates
- **Bulk Import/Export**: Import and export rules via CSV/Excel
- **Access Testing**: Test user permissions before applying
- **Audit Trail**: Track all access changes and violations
- **Performance Optimization**: Caching system for fast permission checks
- **Scheduled Reviews**: Automatic review of expired rules

### User Features
- **Portal Access**: Users can view their own permissions
- **Access Requests**: Request access through a formal process
- **Permission Testing**: Test what actions are allowed
- **Access Summary**: View comprehensive permission summary

## Installation

1. **Download the Module**
   ```bash
   git clone https://github.com/yourcompany/access_management.git
   ```

2. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Add to Odoo Addons Path**
   - Copy the module to your Odoo addons directory
   - Or add the path to your Odoo configuration

4. **Update Module List**
   - Go to Apps menu in Odoo
   - Click "Update Apps List"
   - Search for "Access Management"

5. **Install the Module**
   - Click Install button
   - Wait for installation to complete

## Configuration

### Initial Setup

1. **Access Groups**
   - The module creates three default groups:
     - Access Management User (view own rules)
     - Access Management Manager (create/edit rules)
     - Access Management Administrator (full access)

2. **System Parameters**
   - `access_management.cache_timeout`: Cache timeout in seconds (default: 3600)
   - `access_management.audit_retention_days`: Days to retain audit logs (default: 90)
   - `access_management.enable_notifications`: Enable email notifications (default: True)

### Creating Access Rules

1. Navigate to **Access Studio > Access Management**
2. Click **Create** to make a new rule
3. Configure the rule:
   - **Name**: Descriptive name for the rule
   - **Apply by Group**: Apply to groups instead of individual users
   - **Read Only**: Make all permissions read-only
   - **Users/Groups**: Select target users or groups

4. Add restrictions in the tabs:
   - **Hide Menu**: Select menus to hide
   - **Model Access**: Set CRUD permissions
   - **Field Access**: Configure field restrictions
   - **Domain Access**: Add record filters
   - **Button/Tab Access**: Hide UI elements

5. **Save** and **Activate** the rule

## Usage

### For Administrators

#### Creating a Basic Rule
```python
rule = env['access.management'].create({
    'name': 'Sales Team Restrictions',
    'active': True,
    'apply_by_group': True,
    'group_ids': [(6, 0, [sales_group.id])],
})

# Add menu restriction
env['access.management.menu'].create({
    'access_id': rule.id,
    'menu_id': settings_menu.id,
    'hidden': True,
})

# Add model restriction
env['access.management.model'].create({
    'access_id': rule.id,
    'model_id': env.ref('base.model_res_partner').id,
    'perm_read': True,
    'perm_write': True,
    'perm_create': False,
    'perm_unlink': False,
})
```

#### Bulk Import Rules
```python
# Import from CSV
with open('access_rules.csv', 'r') as file:
    wizard = env['access.management.import.wizard'].create({
        'file_data': base64.b64encode(file.read()),
        'import_type': 'full',
    })
    wizard.action_import()
```

### For Users

#### Checking Your Access
1. Go to **My Account > Access Rules**
2. View all rules that apply to you
3. Click on a rule to see details

#### Testing Permissions
1. Navigate to **My Account > Access Test**
2. Select a model and operation
3. Click **Test Access** to check permissions

#### Requesting Access
1. Visit **/access-request** on the portal
2. Fill out the access request form
3. Submit for approval

## Best Practices

### Rule Design
- Keep rules focused and specific
- Use groups instead of individual users when possible
- Document the purpose of each rule
- Regularly review and update rules

### Performance
- Enable caching for better performance
- Avoid overly complex domains
- Limit conditional field access rules
- Use scheduled actions for cleanup

### Security
- Follow the principle of least privilege
- Regularly audit access permissions
- Test rules before activation
- Monitor access violations

## Troubleshooting

### Common Issues

1. **Rules Not Applied**
   - Check if the rule is active
   - Verify user/group assignment
   - Clear browser cache
   - Check rule sequence

2. **Performance Issues**
   - Increase cache timeout
   - Reduce complex domains
   - Check for circular dependencies
   - Monitor rule count

3. **Access Denied Errors**
   - Check model permissions
   - Review field restrictions
   - Verify domain filters
   - Test with admin account

### Debug Mode

Enable debug logging:
```python
import logging
logging.getLogger('access_management').setLevel(logging.DEBUG)
```

## API Reference

### Models

#### access.management
Main model for access rules

**Fields:**
- `name`: Rule name
- `active`: Active state
- `apply_by_group`: Group-based application
- `user_ids`: Target users
- `group_ids`: Target groups

**Methods:**
- `_get_applicable_rules(user)`: Get rules for user
- `check_access(model, operation, user)`: Check permissions
- `apply_field_access(model, fields, user)`: Apply field rules

### Utilities

#### access_cache
Cache management for performance

**Methods:**
- `get(key)`: Get cached value
- `set(key, value)`: Set cached value
- `clear(pattern)`: Clear cache entries

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## Support

- Documentation: https://docs.yourcompany.com/access-management
- Issues: https://github.com/yourcompany/access_management/issues
- Email: support@yourcompany.com

## License

This module is licensed under LGPL-3. See LICENSE file for details.

## Changelog

### Version 16.0.1.0.0
- Initial release
- Core access management features
- Portal integration
- Performance optimizations

### Roadmap
- Mobile app support
- AI-powered rule suggestions
- Integration with external auth systems
- Advanced reporting dashboards
