# -*- coding: utf-8 -*-
import functools
import time
import hashlib
import json
from odoo import api, tools
from odoo.tools import config
import logging

_logger = logging.getLogger(__name__)

# Cache configuration
CACHE_TIMEOUT = int(config.get('access_management_cache_timeout', 3600))  # 1 hour default
_cache = {}


class AccessCache:
    """Cache for access management rules"""
    
    def __init__(self, timeout=CACHE_TIMEOUT):
        self.timeout = timeout
        self.cache = {}
        self.timestamps = {}
    
    def get(self, key):
        """Get value from cache if not expired"""
        if key in self.cache:
            if time.time() - self.timestamps[key] < self.timeout:
                return self.cache[key]
            else:
                # Remove expired entry
                del self.cache[key]
                del self.timestamps[key]
        return None
    
    def set(self, key, value):
        """Set value in cache with timestamp"""
        self.cache[key] = value
        self.timestamps[key] = time.time()
    
    def clear(self, pattern=None):
        """Clear cache entries matching pattern"""
        if pattern:
            keys_to_remove = [k for k in self.cache.keys() if pattern in k]
            for key in keys_to_remove:
                del self.cache[key]
                del self.timestamps[key]
        else:
            self.cache.clear()
            self.timestamps.clear()
    
    def get_stats(self):
        """Get cache statistics"""
        return {
            'size': len(self.cache),
            'memory': sum(len(str(v)) for v in self.cache.values()),
            'oldest': min(self.timestamps.values()) if self.timestamps else None,
            'newest': max(self.timestamps.values()) if self.timestamps else None,
        }


# Global cache instance
access_cache = AccessCache()


def cached_method(key_func=None, timeout=None):
    """Decorator for caching method results"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            # Generate cache key
            if key_func:
                cache_key = key_func(self, *args, **kwargs)
            else:
                cache_key = f"{self._name}.{func.__name__}:{self.env.uid}:{args}:{kwargs}"
            
            # Check cache
            cached_value = access_cache.get(cache_key)
            if cached_value is not None:
                _logger.debug(f"Cache hit for {cache_key}")
                return cached_value
            
            # Execute function
            result = func(self, *args, **kwargs)
            
            # Store in cache
            access_cache.set(cache_key, result)
            _logger.debug(f"Cache miss for {cache_key}, stored result")
            
            return result
        return wrapper
    return decorator


def clear_access_cache(model=None, user_id=None):
    """Clear access cache for specific model/user"""
    if model and user_id:
        pattern = f"{model}.*:{user_id}:"
    elif model:
        pattern = f"{model}."
    elif user_id:
        pattern = f":{user_id}:"
    else:
        pattern = None
    
    access_cache.clear(pattern)
    _logger.info(f"Cleared access cache with pattern: {pattern}")


def get_user_access_hash(user):
    """Generate hash of user's access configuration"""
    # Collect all relevant data
    data = {
        'user_id': user.id,
        'groups': sorted(user.groups_id.ids),
        'company_id': user.company_id.id,
        'share': user.share,
    }
    
    # Generate hash
    data_str = json.dumps(data, sort_keys=True)
    return hashlib.md5(data_str.encode()).hexdigest()


def profile_access_check(func):
    """Decorator to profile access check performance"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        
        duration = end_time - start_time
        if duration > 0.1:  # Log slow access checks
            _logger.warning(
                f"Slow access check: {func.__name__} took {duration:.3f}s"
            )
        
        return result
    return wrapper


class AccessContext:
    """Context manager for access checking"""
    
    def __init__(self, user, bypass_cache=False):
        self.user = user
        self.bypass_cache = bypass_cache
        self.original_uid = None
    
    def __enter__(self):
        self.original_uid = self.user.env.uid
        if self.bypass_cache:
            clear_access_cache(user_id=self.user.id)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # Restore original uid if changed
        if self.original_uid != self.user.env.uid:
            self.user.env.uid = self.original_uid


def merge_access_rules(rules):
    """Merge multiple access rules into consolidated permissions"""
    merged = {
        'menu_ids': set(),
        'model_access': {},
        'field_access': {},
        'domain_access': {},
        'button_access': {},
    }
    
    for rule in rules:
        # Merge menu restrictions
        merged['menu_ids'].update(
            menu.menu_id.id for menu in rule.menu_access_ids if menu.hidden
        )
        
        # Merge model access
        for model_access in rule.model_access_ids:
            model_name = model_access.model_id.model
            if model_name not in merged['model_access']:
                merged['model_access'][model_name] = {
                    'read': True,
                    'write': True,
                    'create': True,
                    'unlink': True,
                }
            
            # Most restrictive permission wins
            merged['model_access'][model_name]['read'] &= model_access.perm_read
            merged['model_access'][model_name]['write'] &= model_access.perm_write
            merged['model_access'][model_name]['create'] &= model_access.perm_create
            merged['model_access'][model_name]['unlink'] &= model_access.perm_unlink
        
        # Merge field access
        for field_access in rule.field_access_ids:
            model_name = field_access.model_id.model
            field_name = field_access.field_id.name
            
            if model_name not in merged['field_access']:
                merged['field_access'][model_name] = {}
            
            if field_name not in merged['field_access'][model_name]:
                merged['field_access'][model_name][field_name] = {
                    'readonly': False,
                    'invisible': False,
                    'required': False,
                }
            
            # Most restrictive access wins
            merged['field_access'][model_name][field_name]['readonly'] |= field_access.readonly
            merged['field_access'][model_name][field_name]['invisible'] |= field_access.invisible
            merged['field_access'][model_name][field_name]['required'] |= field_access.required
        
        # Merge domains
        for domain_access in rule.domain_access_ids:
            model_name = domain_access.model_id.model
            if model_name not in merged['domain_access']:
                merged['domain_access'][model_name] = []
            
            merged['domain_access'][model_name].append(domain_access.get_domain())
    
    return merged


def export_access_rules(rules, format='json'):
    """Export access rules to specified format"""
    data = []
    
    for rule in rules:
        rule_data = {
            'name': rule.name,
            'active': rule.active,
            'apply_by_group': rule.apply_by_group,
            'read_only': rule.read_only,
            'users': [u.login for u in rule.user_ids],
            'groups': [g.name for g in rule.group_ids],
            'company': rule.company_id.name if rule.company_id else None,
            'menu_access': [],
            'model_access': [],
            'field_access': [],
            'domain_access': [],
        }
        
        # Export menu access
        for menu in rule.menu_access_ids:
            rule_data['menu_access'].append({
                'menu': menu.menu_id.complete_name,
                'hidden': menu.hidden,
            })
        
        # Export model access
        for model in rule.model_access_ids:
            rule_data['model_access'].append({
                'model': model.model_id.model,
                'read': model.perm_read,
                'write': model.perm_write,
                'create': model.perm_create,
                'unlink': model.perm_unlink,
            })
        
        # Export field access
        for field in rule.field_access_ids:
            rule_data['field_access'].append({
                'model': field.model_id.model,
                'field': field.field_id.name,
                'readonly': field.readonly,
                'invisible': field.invisible,
                'required': field.required,
            })
        
        # Export domain access
        for domain in rule.domain_access_ids:
            rule_data['domain_access'].append({
                'model': domain.model_id.model,
                'name': domain.name,
                'domain': domain.domain,
            })
        
        data.append(rule_data)
    
    if format == 'json':
        return json.dumps(data, indent=2)
    elif format == 'csv':
        import csv
        import io
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Headers
        writer.writerow([
            'Name', 'Active', 'Apply by Group', 'Read Only',
            'Users', 'Groups', 'Company'
        ])
        
        # Data
        for rule_data in data:
            writer.writerow([
                rule_data['name'],
                rule_data['active'],
                rule_data['apply_by_group'],
                rule_data['read_only'],
                ', '.join(rule_data['users']),
                ', '.join(rule_data['groups']),
                rule_data['company'],
            ])
        
        return output.getvalue()
    
    return data


def import_access_rules(data, format='json'):
    """Import access rules from data"""
    if format == 'json':
        if isinstance(data, str):
            data = json.loads(data)
    elif format == 'csv':
        import csv
        import io
        
        reader = csv.DictReader(io.StringIO(data))
        data = list(reader)
    
    created_rules = []
    
    for rule_data in data:
        # Create main rule
        rule_vals = {
            'name': rule_data.get('name'),
            'active': rule_data.get('active', True),
            'apply_by_group': rule_data.get('apply_by_group', False),
            'read_only': rule_data.get('read_only', False),
        }
        
        # Add users
        if 'users' in rule_data:
            user_logins = rule_data['users']
            if isinstance(user_logins, str):
                user_logins = [u.strip() for u in user_logins.split(',')]
            
            users = request.env['res.users'].search([('login', 'in', user_logins)])
            rule_vals['user_ids'] = [(6, 0, users.ids)]
        
        # Add groups
        if 'groups' in rule_data:
            group_names = rule_data['groups']
            if isinstance(group_names, str):
                group_names = [g.strip() for g in group_names.split(',')]
            
            groups = request.env['res.groups'].search([('name', 'in', group_names)])
            rule_vals['group_ids'] = [(6, 0, groups.ids)]
        
        # Create rule
        rule = request.env['access.management'].create(rule_vals)
        created_rules.append(rule)
        
        # Import detailed access data if format is JSON
        if format == 'json':
            # Import menu access
            for menu_data in rule_data.get('menu_access', []):
                menu = request.env['ir.ui.menu'].search([
                    ('complete_name', '=', menu_data['menu'])
                ], limit=1)
                if menu:
                    request.env['access.management.menu'].create({
                        'access_id': rule.id,
                        'menu_id': menu.id,
                        'hidden': menu_data.get('hidden', True),
                    })
            
            # Import other access types similarly...
    
    return created_rules


def validate_access_rule(rule):
    """Validate access rule configuration"""
    errors = []
    warnings = []
    
    # Check if rule has targets
    if not rule.user_ids and not rule.group_ids and not (
        rule.default_internal_user or rule.default_portal_user
    ):
        errors.append("Rule must have at least one user, group, or user type")
    
    # Check for conflicting permissions
    for model_access in rule.model_access_ids:
        if model_access.perm_write and not model_access.perm_read:
            warnings.append(
                f"Model {model_access.model_id.name}: Write permission without read"
            )
        if model_access.perm_create and not model_access.perm_write:
            warnings.append(
                f"Model {model_access.model_id.name}: Create permission without write"
            )
    
    # Check for invalid domains
    for domain_access in rule.domain_access_ids:
        try:
            domain = domain_access.get_domain()
            if not isinstance(domain, list):
                errors.append(
                    f"Invalid domain for {domain_access.model_id.name}: Not a list"
                )
        except Exception as e:
            errors.append(
                f"Invalid domain for {domain_access.model_id.name}: {str(e)}"
            )
    
    # Check conditional field syntax
    for field_cond in rule.field_conditional_access_ids:
        try:
            compile(field_cond.condition, '<string>', 'eval')
        except SyntaxError as e:
            errors.append(
                f"Invalid condition for {field_cond.field_id.name}: {str(e)}"
            )
    
    return errors, warnings


def get_access_summary(user):
    """Get summary of user's access permissions"""
    rules = user.env['access.management']._get_applicable_rules(user)
    
    summary = {
        'user': user.name,
        'total_rules': len(rules),
        'hidden_menus': 0,
        'model_restrictions': {},
        'field_restrictions': {},
        'domains': {},
    }
    
    # Aggregate data
    for rule in rules:
        summary['hidden_menus'] += len(rule.menu_access_ids)
        
        for model_access in rule.model_access_ids:
            model_name = model_access.model_id.model
            if model_name not in summary['model_restrictions']:
                summary['model_restrictions'][model_name] = {
                    'read': True,
                    'write': True,
                    'create': True,
                    'unlink': True,
                }
            
            # Most restrictive wins
            perms = summary['model_restrictions'][model_name]
            perms['read'] &= model_access.perm_read
            perms['write'] &= model_access.perm_write
            perms['create'] &= model_access.perm_create
            perms['unlink'] &= model_access.perm_unlink
        
        for field_access in rule.field_access_ids:
            model_name = field_access.model_id.model
            field_name = field_access.field_id.name
            
            if model_name not in summary['field_restrictions']:
                summary['field_restrictions'][model_name] = {}
            
            if field_name not in summary['field_restrictions'][model_name]:
                summary['field_restrictions'][model_name][field_name] = []
            
            restrictions = []
            if field_access.readonly:
                restrictions.append('readonly')
            if field_access.invisible:
                restrictions.append('invisible')
            if field_access.required:
                restrictions.append('required')
            
            summary['field_restrictions'][model_name][field_name].extend(restrictions)
        
        for domain_access in rule.domain_access_ids:
            model_name = domain_access.model_id.model
            if model_name not in summary['domains']:
                summary['domains'][model_name] = []
            
            summary['domains'][model_name].append({
                'name': domain_access.name,
                'domain': domain_access.domain,
            })
    
    return summary
