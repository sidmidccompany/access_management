# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import json
from datetime import datetime


class AccessManagementReport(models.Model):
    _name = 'access.management.report'
    _description = 'Access Management Report'
    _auto = False
    _order = 'access_rule_name'
    
    # Report fields
    access_rule_id = fields.Many2one('access.management', string='Access Rule')
    access_rule_name = fields.Char(string='Rule Name')
    active = fields.Boolean(string='Active')
    user_count = fields.Integer(string='User Count')
    group_count = fields.Integer(string='Group Count')
    menu_restrictions = fields.Integer(string='Menu Restrictions')
    model_restrictions = fields.Integer(string='Model Restrictions')
    field_restrictions = fields.Integer(string='Field Restrictions')
    total_restrictions = fields.Integer(string='Total Restrictions')
    company_id = fields.Many2one('res.company', string='Company')
    created_by = fields.Many2one('res.users', string='Created By')
    created_date = fields.Date(string='Created Date')
    
    def init(self):
        """Initialize the SQL view for the report"""
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                SELECT
                    row_number() OVER () AS id,
                    am.id AS access_rule_id,
                    am.name AS access_rule_name,
                    am.active,
                    (SELECT COUNT(*) FROM access_management_users_rel WHERE access_id = am.id) AS user_count,
                    (SELECT COUNT(*) FROM access_management_groups_rel WHERE access_id = am.id) AS group_count,
                    (SELECT COUNT(*) FROM access_management_menu WHERE access_id = am.id) AS menu_restrictions,
                    (SELECT COUNT(*) FROM access_management_model WHERE access_id = am.id) AS model_restrictions,
                    (SELECT COUNT(*) FROM access_management_field WHERE access_id = am.id) AS field_restrictions,
                    (
                        (SELECT COUNT(*) FROM access_management_menu WHERE access_id = am.id) +
                        (SELECT COUNT(*) FROM access_management_model WHERE access_id = am.id) +
                        (SELECT COUNT(*) FROM access_management_field WHERE access_id = am.id) +
                        (SELECT COUNT(*) FROM access_management_domain WHERE access_id = am.id) +
                        (SELECT COUNT(*) FROM access_management_button_tab WHERE access_id = am.id)
                    ) AS total_restrictions,
                    am.company_id,
                    am.create_uid AS created_by,
                    am.create_date::date AS created_date
                FROM
                    access_management am
            )
        """ % self._table)


class AccessManagementReportWizard(models.TransientModel):
    _name = 'access.management.report.wizard'
    _description = 'Access Management Report Wizard'
    
    date_from = fields.Date(string='From Date')
    date_to = fields.Date(string='To Date', default=fields.Date.today)
    user_ids = fields.Many2many('res.users', string='Users')
    group_ids = fields.Many2many('res.groups', string='Groups')
    company_ids = fields.Many2many('res.company', string='Companies')
    active_filter = fields.Selection([
        ('all', 'All'),
        ('active', 'Active Only'),
        ('inactive', 'Inactive Only')
    ], string='Status Filter', default='all')
    report_type = fields.Selection([
        ('summary', 'Summary Report'),
        ('detailed', 'Detailed Report'),
        ('user_access', 'User Access Report'),
        ('audit', 'Audit Report')
    ], string='Report Type', default='summary', required=True)
    
    def generate_report(self):
        """Generate the selected report"""
        self.ensure_one()
        
        if self.report_type == 'summary':
            return self._generate_summary_report()
        elif self.report_type == 'detailed':
            return self._generate_detailed_report()
        elif self.report_type == 'user_access':
            return self._generate_user_access_report()
        elif self.report_type == 'audit':
            return self._generate_audit_report()
    
    def _generate_summary_report(self):
        """Generate summary report"""
        domain = self._get_domain()
        
        return {
            'type': 'ir.actions.report',
            'report_name': 'access_management.report_summary',
            'report_type': 'qweb-pdf',
            'data': {
                'domain': domain,
                'date_from': self.date_from,
                'date_to': self.date_to,
            },
            'context': self.env.context,
        }
    
    def _generate_detailed_report(self):
        """Generate detailed report"""
        domain = self._get_domain()
        rules = self.env['access.management'].search(domain)
        
        # Create detailed report data
        report_data = []
        for rule in rules:
            rule_data = {
                'rule': rule,
                'users': rule.user_ids,
                'groups': rule.group_ids,
                'menu_access': rule.menu_access_ids,
                'model_access': rule.model_access_ids,
                'field_access': rule.field_access_ids,
                'domain_access': rule.domain_access_ids,
                'button_tab_access': rule.button_tab_access_ids,
                'chatter_access': rule.chatter_access_ids,
            }
            report_data.append(rule_data)
        
        return {
            'type': 'ir.actions.report',
            'report_name': 'access_management.report_detailed',
            'report_type': 'qweb-pdf',
            'data': {
                'report_data': report_data,
                'date_from': self.date_from,
                'date_to': self.date_to,
            },
            'context': self.env.context,
        }
    
    def _generate_user_access_report(self):
        """Generate user access report"""
        users = self.user_ids or self.env['res.users'].search([])
        
        user_access_data = []
        for user in users:
            rules = self.env['access.management']._get_applicable_rules(user)
            
            user_data = {
                'user': user,
                'rules': rules,
                'total_rules': len(rules),
                'menu_restrictions': sum(len(r.menu_access_ids) for r in rules),
                'model_restrictions': sum(len(r.model_access_ids) for r in rules),
                'field_restrictions': sum(len(r.field_access_ids) for r in rules),
            }
            user_access_data.append(user_data)
        
        return {
            'type': 'ir.actions.report',
            'report_name': 'access_management.report_user_access',
            'report_type': 'qweb-pdf',
            'data': {
                'user_access_data': user_access_data,
                'date': fields.Date.today(),
            },
            'context': self.env.context,
        }
    
    def _generate_audit_report(self):
        """Generate audit report"""
        # This would include tracking changes, modifications, etc.
        domain = self._get_domain()
        
        return {
            'type': 'ir.actions.report',
            'report_name': 'access_management.report_audit',
            'report_type': 'qweb-pdf',
            'data': {
                'domain': domain,
                'date_from': self.date_from,
                'date_to': self.date_to,
                'include_changes': True,
            },
            'context': self.env.context,
        }
    
    def _get_domain(self):
        """Get domain based on wizard filters"""
        domain = []
        
        if self.date_from:
            domain.append(('create_date', '>=', self.date_from))
        if self.date_to:
            domain.append(('create_date', '<=', self.date_to))
        
        if self.active_filter == 'active':
            domain.append(('active', '=', True))
        elif self.active_filter == 'inactive':
            domain.append(('active', '=', False))
        
        if self.company_ids:
            domain.append(('company_id', 'in', self.company_ids.ids))
        
        return domain
