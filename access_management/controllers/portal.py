# -*- coding: utf-8 -*-
from collections import OrderedDict
from odoo import http, _
from odoo.exceptions import AccessError, MissingError
from odoo.http import request
from odoo.tools import groupby as groupbyelem
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager
from odoo.osv.expression import OR


class AccessManagementPortal(CustomerPortal):
    
    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        if 'access_rules_count' in counters:
            user = request.env.user
            # Count access rules that apply to the current user
            rules = request.env['access.management']._get_applicable_rules(user)
            values['access_rules_count'] = len(rules)
        return values
    
    @http.route(['/my/access-rules', '/my/access-rules/page/<int:page>'], 
                type='http', auth="user", website=True)
    def portal_my_access_rules(self, page=1, date_begin=None, date_end=None, 
                              sortby=None, filterby=None, **kw):
        values = self._prepare_portal_layout_values()
        AccessRule = request.env['access.management']
        
        # Get applicable rules for current user
        user = request.env.user
        domain = self._get_access_rules_domain(user)
        
        searchbar_sortings = {
            'date': {'label': _('Date'), 'order': 'create_date desc'},
            'name': {'label': _('Name'), 'order': 'name'},
            'sequence': {'label': _('Sequence'), 'order': 'sequence'},
        }
        
        # Default sort by
        if not sortby:
            sortby = 'date'
        sort_order = searchbar_sortings[sortby]['order']
        
        # Archive filter
        searchbar_filters = {
            'all': {'label': _('All'), 'domain': []},
            'active': {'label': _('Active'), 'domain': [('active', '=', True)]},
            'inactive': {'label': _('Inactive'), 'domain': [('active', '=', False)]},
        }
        
        # Default filter by
        if not filterby:
            filterby = 'active'
        domain += searchbar_filters[filterby]['domain']
        
        # Count
        access_rules_count = AccessRule.search_count(domain)
        
        # Pager
        pager = portal_pager(
            url="/my/access-rules",
            url_args={'date_begin': date_begin, 'date_end': date_end, 
                     'sortby': sortby, 'filterby': filterby},
            total=access_rules_count,
            page=page,
            step=self._items_per_page
        )
        
        # Content according to pager
        rules = AccessRule.search(
            domain, order=sort_order, limit=self._items_per_page, 
            offset=pager['offset']
        )
        
        values.update({
            'date': date_begin,
            'rules': rules,
            'page_name': 'access_rules',
            'pager': pager,
            'default_url': '/my/access-rules',
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby,
            'searchbar_filters': OrderedDict(sorted(searchbar_filters.items())),
            'filterby': filterby,
        })
        
        return request.render("access_management.portal_my_access_rules", values)
    
    @http.route(['/my/access-rules/<int:rule_id>'], type='http', auth="user", website=True)
    def portal_my_access_rule_detail(self, rule_id, **kw):
        try:
            rule = self._get_access_rule(rule_id)
        except (AccessError, MissingError):
            return request.redirect('/my')
        
        values = self._prepare_access_rule_values(rule)
        return request.render("access_management.portal_access_rule_detail", values)
    
    def _get_access_rules_domain(self, user):
        """Get domain for access rules applicable to user"""
        domain = [
            '|', '|',
            ('user_ids', 'in', user.id),
            ('group_ids', 'in', user.groups_id.ids),
            '&', ('default_internal_user', '=', True), ('user_ids', '=', False)
        ]
        return domain
    
    def _get_access_rule(self, rule_id):
        """Get specific access rule if user has access"""
        rule = request.env['access.management'].browse(rule_id)
        user = request.env.user
        
        # Check if rule applies to current user
        applicable_rules = request.env['access.management']._get_applicable_rules(user)
        if rule not in applicable_rules:
            raise AccessError(_("You don't have access to this rule."))
        
        return rule
    
    def _prepare_access_rule_values(self, rule):
        """Prepare values for access rule detail page"""
        values = {
            'rule': rule,
            'page_name': 'access_rule_detail',
            'user': request.env.user,
        }
        
        # Add restriction counts
        values.update({
            'menu_count': len(rule.menu_access_ids),
            'model_count': len(rule.model_access_ids),
            'field_count': len(rule.field_access_ids),
            'domain_count': len(rule.domain_access_ids),
            'button_count': len(rule.button_tab_access_ids),
            'chatter_count': len(rule.chatter_access_ids),
        })
        
        return values
    
    @http.route(['/my/access-test'], type='http', auth="user", website=True)
    def portal_access_test(self, **kw):
        """Access test page for users to check their permissions"""
        values = self._prepare_portal_layout_values()
        user = request.env.user
        
        # Get all models user might have access to
        models = request.env['ir.model'].search([
            ('transient', '=', False),
            ('model', 'not like', 'ir.%'),
            ('model', 'not like', 'base.%'),
        ])
        
        # Get applicable rules
        rules = request.env['access.management']._get_applicable_rules(user)
        
        values.update({
            'page_name': 'access_test',
            'models': models,
            'rules': rules,
            'user': user,
        })
        
        return request.render("access_management.portal_access_test", values)
    
    @http.route(['/my/access-test/check'], type='json', auth="user")
    def portal_access_test_check(self, model_name, operation, **kw):
        """AJAX endpoint to check access permissions"""
        try:
            result = request.env['access.management'].check_access(
                model_name, operation, user=request.env.user, raise_exception=False
            )
            
            # Get detailed information about restrictions
            details = self._get_access_details(model_name, request.env.user)
            
            return {
                'success': True,
                'access': result,
                'details': details,
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
            }
    
    def _get_access_details(self, model_name, user):
        """Get detailed access information for a model"""
        rules = request.env['access.management']._get_applicable_rules(user)
        details = {
            'model_access': [],
            'field_access': [],
            'domain_access': [],
            'button_access': [],
        }
        
        for rule in rules:
            # Model access
            for model_access in rule.model_access_ids:
                if model_access.model_id.model == model_name:
                    details['model_access'].append({
                        'rule': rule.name,
                        'read': model_access.perm_read,
                        'write': model_access.perm_write,
                        'create': model_access.perm_create,
                        'unlink': model_access.perm_unlink,
                    })
            
            # Field access
            for field_access in rule.field_access_ids:
                if field_access.model_id.model == model_name:
                    details['field_access'].append({
                        'rule': rule.name,
                        'field': field_access.field_id.field_description,
                        'readonly': field_access.readonly,
                        'invisible': field_access.invisible,
                        'required': field_access.required,
                    })
            
            # Domain access
            for domain_access in rule.domain_access_ids:
                if domain_access.model_id.model == model_name:
                    details['domain_access'].append({
                        'rule': rule.name,
                        'description': domain_access.name,
                        'domain': domain_access.domain,
                    })
            
            # Button/Tab access
            for button_access in rule.button_tab_access_ids:
                if button_access.model_id.model == model_name:
                    details['button_access'].append({
                        'rule': rule.name,
                        'type': button_access.element_type,
                        'name': button_access.element_name,
                        'invisible': button_access.invisible,
                        'readonly': button_access.readonly,
                    })
        
        return details


class AccessManagementPublic(http.Controller):
    
    @http.route(['/access-info'], type='http', auth="public", website=True)
    def access_info_page(self, **kw):
        """Public page with information about access management"""
        values = {
            'page_name': 'access_info',
        }
        return request.render("access_management.public_access_info", values)
    
    @http.route(['/access-request'], type='http', auth="public", website=True)
    def access_request_form(self, **kw):
        """Form for requesting access changes"""
        values = {
            'page_name': 'access_request',
            'models': request.env['ir.model'].sudo().search([
                ('transient', '=', False),
                ('model', 'not like', 'ir.%'),
            ]),
        }
        return request.render("access_management.public_access_request", values)
    
    @http.route(['/access-request/submit'], type='http', auth="public", 
                website=True, methods=['POST'])
    def access_request_submit(self, **kw):
        """Handle access request submission"""
        # Create access request (would need a model for this)
        values = {
            'page_name': 'access_request_success',
            'request_data': kw,
        }
        
        # Send notification email to administrators
        self._notify_access_request(kw)
        
        return request.render("access_management.public_access_request_success", values)
    
    def _notify_access_request(self, request_data):
        """Send notification about new access request"""
        # Implementation would send email to access managers
        pass
