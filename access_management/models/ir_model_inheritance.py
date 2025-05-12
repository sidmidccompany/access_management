# -*- coding: utf-8 -*-
from odoo import models, fields, api, tools, SUPERUSER_ID
from odoo.exceptions import AccessError
from lxml import etree
import logging

_logger = logging.getLogger(__name__)


class IrModel(models.Model):
    _inherit = 'ir.model'
    
    @api.model
    def check_access_rights(self, operation, raise_exception=True):
        """Override to add custom access management checks"""
        # First check standard access rights
        res = super(IrModel, self).check_access_rights(
            operation, raise_exception=False
        )
        
        if not res and not raise_exception:
            return False
        
        # Then check custom access management
        if self.env.uid != SUPERUSER_ID:
            model_name = self.model
            access_mgmt = self.env['access.management']
            
            if not access_mgmt.check_access(
                model_name, operation, raise_exception=raise_exception
            ):
                return False
        
        if not res and raise_exception:
            raise AccessError(
                _("You don't have the access rights to perform this operation.")
            )
        
        return True


class IrUiView(models.Model):
    _inherit = 'ir.ui.view'
    
    @api.model
    def postprocess_and_fields(self, node, model=None, **options):
        """Override to apply access management rules to views"""
        arch, fields = super(IrUiView, self).postprocess_and_fields(
            node, model=model, **options
        )
        
        if model and self.env.uid != SUPERUSER_ID:
            # Apply access management rules
            access_mgmt = self.env['access.management']
            arch = access_mgmt.apply_view_access(
                model, arch, self.type, user=self.env.user
            )
            
            # Apply field access rules
            if fields:
                fields = access_mgmt.apply_field_access(
                    model, fields, user=self.env.user
                )
        
        return arch, fields


class IrUiMenu(models.Model):
    _inherit = 'ir.ui.menu'
    
    @api.model
    def _visible_menu_ids(self, debug=False):
        """Override to hide menus based on access management"""
        menus = super(IrUiMenu, self)._visible_menu_ids(debug=debug)
        
        if self.env.uid != SUPERUSER_ID:
            # Get applicable access rules
            access_mgmt = self.env['access.management']
            rules = access_mgmt._get_applicable_rules(self.env.user)
            
            hidden_menu_ids = set()
            for rule in rules:
                for menu_access in rule.menu_access_ids:
                    if menu_access.hidden:
                        hidden_menu_ids.add(menu_access.menu_id.id)
            
            menus = menus - hidden_menu_ids
        
        return menus


class BaseModel(models.AbstractModel):
    _inherit = 'base'
    
    @api.model
    def _search(self, args, offset=0, limit=None, order=None,
                count=False, access_rights_uid=None):
        """Override to apply domain access rules"""
        if self.env.uid != SUPERUSER_ID:
            # Apply domain restrictions from access management
            access_mgmt = self.env['access.management']
            rules = access_mgmt._get_applicable_rules(self.env.user)
            
            for rule in rules:
                for domain_access in rule.domain_access_ids:
                    if domain_access.model_id.model == self._name:
                        domain = domain_access.get_domain()
                        if domain:
                            args = ['&'] + args + domain
        
        return super(BaseModel, self)._search(
            args, offset=offset, limit=limit, order=order,
            count=count, access_rights_uid=access_rights_uid
        )
    
    @api.model
    def fields_get(self, allfields=None, attributes=None):
        """Override to apply field access rules"""
        res = super(BaseModel, self).fields_get(
            allfields=allfields, attributes=attributes
        )
        
        if self.env.uid != SUPERUSER_ID:
            # Apply field access rules
            access_mgmt = self.env['access.management']
            res = access_mgmt.apply_field_access(
                self._name, res, user=self.env.user
            )
        
        return res
    
    def write(self, vals):
        """Override to check field-level write access"""
        if self.env.uid != SUPERUSER_ID:
            # Check field-level access
            access_mgmt = self.env['access.management']
            rules = access_mgmt._get_applicable_rules(self.env.user)
            
            for rule in rules:
                for field_access in rule.field_access_ids:
                    if field_access.model_id.model == self._name:
                        field_name = field_access.field_id.name
                        if field_name in vals and field_access.readonly:
                            raise AccessError(
                                _("You don't have write access to field '%s'") % field_name
                            )
                
                # Check conditional field access
                for cond_access in rule.field_conditional_access_ids:
                    if cond_access.model_id.model == self._name:
                        field_name = cond_access.field_id.name
                        if field_name in vals:
                            for record in self:
                                if cond_access.evaluate_condition(record):
                                    if cond_access.readonly:
                                        raise AccessError(
                                            _("You don't have write access to field '%s' for this record") % field_name
                                        )
        
        return super(BaseModel, self).write(vals)


class ResUsers(models.Model):
    _inherit = 'res.users'
    
    @api.model
    def has_group(self, group_ext_id):
        """Override to consider access management rules"""
        has_group = super(ResUsers, self).has_group(group_ext_id)
        
        # Check if developer mode is disabled
        if group_ext_id in ['base.group_system', 'base.group_no_one']:
            if self.env.uid != SUPERUSER_ID:
                access_mgmt = self.env['access.management']
                rules = access_mgmt._get_applicable_rules(self)
                
                for rule in rules:
                    if rule.disable_developer_mode:
                        return False
        
        return has_group


class MailThread(models.AbstractModel):
    _inherit = 'mail.thread'
    
    @api.model
    def _get_mail_thread_data(self, res_id, request_list):
        """Override to apply chatter access rules"""
        thread_data = super(MailThread, self)._get_mail_thread_data(
            res_id, request_list
        )
        
        if self.env.uid != SUPERUSER_ID:
            # Check chatter access rules
            access_mgmt = self.env['access.management']
            rules = access_mgmt._get_applicable_rules(self.env.user)
            
            for rule in rules:
                for chatter_access in rule.chatter_access_ids:
                    if chatter_access.model_id.model == self._name:
                        if chatter_access.disable_chatter:
                            # Return empty data if chatter is disabled
                            return {}
                        
                        # Modify thread data based on restrictions
                        if chatter_access.disable_followers:
                            thread_data.pop('followers', None)
                        if chatter_access.disable_activities:
                            thread_data.pop('activities', None)
                        if chatter_access.restrict_message_post:
                            thread_data['can_post'] = False
        
        return thread_data
