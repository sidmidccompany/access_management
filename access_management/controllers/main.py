# -*- coding: utf-8 -*-
from odoo import http, _
from odoo.http import request
import json
import logging

_logger = logging.getLogger(__name__)


class AccessManagementController(http.Controller):
    
    @http.route('/access_management/get_rules', type='json', auth='user')
    def get_access_rules(self, user_id=None):
        """Get all applicable access rules for the current user"""
        if not user_id:
            user_id = request.env.user.id
            
        user = request.env['res.users'].browse(user_id)
        rules = request.env['access.management']._get_applicable_rules(user)
        
        # Format rules for frontend
        formatted_rules = []
        for rule in rules:
            rule_data = {
                'id': rule.id,
                'name': rule.name,
                'hidden_menus': [],
                'field_modifications': {},
                'domain_access': {},
                'hidden_elements': [],
            }
            
            # Hidden menus
            for menu_access in rule.menu_access_ids:
                if menu_access.hidden:
                    rule_data['hidden_menus'].append(menu_access.menu_id.id)
            
            # Field modifications
            for field_access in rule.field_access_ids:
                model_name = field_access.model_id.model
                if model_name not in rule_data['field_modifications']:
                    rule_data['field_modifications'][model_name] = {}
                
                rule_data['field_modifications'][model_name][field_access.field_id.name] = {
                    'readonly': field_access.readonly,
                    'invisible': field_access.invisible,
                    'required': field_access.required,
                }
            
            # Domain access
            for domain_access in rule.domain_access_ids:
                model_name = domain_access.model_id.model
                if model_name not in rule_data['domain_access']:
                    rule_data['domain_access'][model_name] = []
                
                rule_data['domain_access'][model_name].append(
                    domain_access.get_domain()
                )
            
            # Hidden elements (buttons/tabs)
            for button_tab in rule.button_tab_access_ids:
                if button_tab.invisible:
                    rule_data['hidden_elements'].append({
                        'type': button_tab.element_type,
                        'name': button_tab.element_name,
                        'model': button_tab.model_id.model,
                    })
            
            formatted_rules.append(rule_data)
        
        return formatted_rules
    
    @http.route('/access_management/check_access', type='json', auth='user')
    def check_access(self, model, operation, user_id=None):
        """Check if user has access to perform operation on model"""
        if not user_id:
            user_id = request.env.user.id
        
        user = request.env['res.users'].browse(user_id)
        
        try:
            return request.env['access.management'].check_access(
                model, operation, user=user, raise_exception=False
            )
        except Exception as e:
            _logger.warning("Access check failed: %s", str(e))
            return False
    
    @http.route('/access_management/apply_rules', type='json', auth='user')
    def apply_rules(self, view_type, model, arch, user_id=None):
        """Apply access rules to view architecture"""
        if not user_id:
            user_id = request.env.user.id
        
        user = request.env['res.users'].browse(user_id)
        
        try:
            return request.env['access.management'].apply_view_access(
                model, arch, view_type, user=user
            )
        except Exception as e:
            _logger.error("Error applying access rules: %s", str(e))
            return arch
    
    @http.route('/access_management/developer_mode', type='json', auth='user')
    def check_developer_mode(self, user_id=None):
        """Check if developer mode is disabled for user"""
        if not user_id:
            user_id = request.env.user.id
        
        user = request.env['res.users'].browse(user_id)
        rules = request.env['access.management']._get_applicable_rules(user)
        
        for rule in rules:
            if rule.disable_developer_mode:
                return False
        
        return True
    
    @http.route('/access_management/export_rules', type='http', auth='user')
    def export_rules(self, rule_ids=None):
        """Export access rules to CSV/Excel"""
        if rule_ids:
            rule_ids = json.loads(rule_ids)
            rules = request.env['access.management'].browse(rule_ids)
        else:
            rules = request.env['access.management'].search([])
        
        # Create CSV content
        import csv
        import io
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Headers
        writer.writerow([
            'Name', 'Active', 'Apply by Group', 'Read Only',
            'Users', 'Groups', 'Company', 'Rules Count'
        ])
        
        # Data
        for rule in rules:
            writer.writerow([
                rule.name,
                rule.active,
                rule.apply_by_group,
                rule.read_only,
                ', '.join(rule.user_ids.mapped('name')),
                ', '.join(rule.group_ids.mapped('name')),
                rule.company_id.name if rule.company_id else '',
                rule.access_rules_count
            ])
        
        # Return as download
        content = output.getvalue()
        headers = [
            ('Content-Type', 'text/csv'),
            ('Content-Disposition', 'attachment; filename="access_rules.csv"'),
        ]
        
        return request.make_response(content, headers)
    
    @http.route('/access_management/test_rule', type='json', auth='user')
    def test_rule(self, rule_id, test_user_id=None):
        """Test an access rule with a specific user"""
        rule = request.env['access.management'].browse(rule_id)
        
        if not test_user_id:
            test_user_id = request.env.user.id
        
        test_user = request.env['res.users'].browse(test_user_id)
        
        # Check if rule applies to test user
        rules = request.env['access.management']._get_applicable_rules(test_user)
        
        if rule in rules:
            # Simulate rule application
            results = {
                'applies': True,
                'hidden_menus': len(rule.menu_access_ids),
                'model_restrictions': len(rule.model_access_ids),
                'field_restrictions': len(rule.field_access_ids),
                'domain_restrictions': len(rule.domain_access_ids),
                'button_restrictions': len(rule.button_tab_access_ids),
            }
        else:
            results = {
                'applies': False,
                'reason': 'Rule does not apply to this user'
            }
        
        return results
