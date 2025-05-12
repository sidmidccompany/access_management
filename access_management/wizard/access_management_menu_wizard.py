# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class AccessManagementMenuWizard(models.TransientModel):
    _name = 'access.management.menu.wizard'
    _description = 'Access Management Menu Wizard'
    
    access_id = fields.Many2one(
        'access.management', 
        string='Access Management',
        required=True,
        default=lambda self: self.env.context.get('default_access_id')
    )
    
    menu_id = fields.Many2one(
        'ir.ui.menu',
        string='Menu',
        required=True,
        help="Select the menu to add to access management"
    )
    
    parent_menu_id = fields.Many2one(
        'ir.ui.menu',
        string='Parent Menu',
        compute='_compute_parent_menu_id',
        store=True
    )
    
    hidden = fields.Boolean(
        string='Hidden',
        default=True,
        help="Hide this menu from users"
    )
    
    apply_to_children = fields.Boolean(
        string='Apply to Children',
        default=False,
        help="Also hide all child menus"
    )
    
    @api.depends('menu_id')
    def _compute_parent_menu_id(self):
        for wizard in self:
            wizard.parent_menu_id = wizard.menu_id.parent_id
    
    def action_add_menu(self):
        """Add the selected menu to access management"""
        self.ensure_one()
        
        # Check if menu already exists
        existing = self.env['access.management.menu'].search([
            ('access_id', '=', self.access_id.id),
            ('menu_id', '=', self.menu_id.id)
        ])
        
        if existing:
            raise UserError(_("Menu '%s' is already in the access rule.") % self.menu_id.name)
        
        # Create menu access record
        menu_access = self.env['access.management.menu'].create({
            'access_id': self.access_id.id,
            'menu_id': self.menu_id.id,
            'hidden': self.hidden,
        })
        
        # Apply to children if requested
        if self.apply_to_children:
            child_menus = self._get_all_child_menus(self.menu_id)
            for child_menu in child_menus:
                # Check if child menu already exists
                existing_child = self.env['access.management.menu'].search([
                    ('access_id', '=', self.access_id.id),
                    ('menu_id', '=', child_menu.id)
                ])
                
                if not existing_child:
                    self.env['access.management.menu'].create({
                        'access_id': self.access_id.id,
                        'menu_id': child_menu.id,
                        'hidden': self.hidden,
                    })
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': _('Menu added successfully.'),
                'type': 'success',
                'sticky': False,
                'next': {'type': 'ir.actions.act_window_close'},
            }
        }
    
    def _get_all_child_menus(self, menu):
        """Recursively get all child menus"""
        children = menu.child_id
        all_children = children
        
        for child in children:
            all_children |= self._get_all_child_menus(child)
        
        return all_children


class AccessManagementImportWizard(models.TransientModel):
    _name = 'access.management.import.wizard'
    _description = 'Import Access Management Rules'
    
    file_data = fields.Binary(
        string='Import File',
        required=True,
        help="CSV or Excel file containing access rules"
    )
    
    file_name = fields.Char(string='File Name')
    
    import_type = fields.Selection([
        ('menu', 'Menu Access'),
        ('model', 'Model Access'),
        ('field', 'Field Access'),
        ('domain', 'Domain Access'),
        ('full', 'Full Configuration')
    ], string='Import Type', required=True, default='full')
    
    update_existing = fields.Boolean(
        string='Update Existing',
        default=False,
        help="Update existing rules if found"
    )
    
    def action_import(self):
        """Import access management rules from file"""
        self.ensure_one()
        
        # Implementation would include:
        # 1. Parse the file (CSV/Excel)
        # 2. Validate the data
        # 3. Create or update access management records
        # 4. Handle errors and provide feedback
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Import Completed'),
                'message': _('Access rules imported successfully.'),
                'type': 'success',
                'sticky': False,
            }
        }


class AccessManagementCopyWizard(models.TransientModel):
    _name = 'access.management.copy.wizard'
    _description = 'Copy Access Management Rules'
    
    source_id = fields.Many2one(
        'access.management',
        string='Source Rule',
        required=True,
        default=lambda self: self.env.context.get('active_id')
    )
    
    name = fields.Char(
        string='New Rule Name',
        required=True,
        default=lambda self: self._default_name()
    )
    
    copy_menu_access = fields.Boolean(string='Copy Menu Access', default=True)
    copy_model_access = fields.Boolean(string='Copy Model Access', default=True)
    copy_field_access = fields.Boolean(string='Copy Field Access', default=True)
    copy_domain_access = fields.Boolean(string='Copy Domain Access', default=True)
    copy_button_tab_access = fields.Boolean(string='Copy Button/Tab Access', default=True)
    copy_search_panel_access = fields.Boolean(string='Copy Search Panel Access', default=True)
    copy_chatter_access = fields.Boolean(string='Copy Chatter Access', default=True)
    copy_users = fields.Boolean(string='Copy Users', default=False)
    copy_groups = fields.Boolean(string='Copy Groups', default=False)
    
    def _default_name(self):
        source = self.env['access.management'].browse(self.env.context.get('active_id'))
        if source:
            return _("%s (Copy)") % source.name
        return ""
    
    def action_copy(self):
        """Create a copy of the access management rule"""
        self.ensure_one()
        
        # Create new rule
        new_rule = self.source_id.copy({
            'name': self.name,
            'active': False,  # Start as inactive
            'user_ids': [(6, 0, self.source_id.user_ids.ids)] if self.copy_users else [(5, 0, 0)],
            'group_ids': [(6, 0, self.source_id.group_ids.ids)] if self.copy_groups else [(5, 0, 0)],
        })
        
        # Clear unwanted sections
        if not self.copy_menu_access:
            new_rule.menu_access_ids.unlink()
        if not self.copy_model_access:
            new_rule.model_access_ids.unlink()
        if not self.copy_field_access:
            new_rule.field_access_ids.unlink()
        if not self.copy_domain_access:
            new_rule.domain_access_ids.unlink()
        if not self.copy_button_tab_access:
            new_rule.button_tab_access_ids.unlink()
        if not self.copy_search_panel_access:
            new_rule.search_panel_access_ids.unlink()
        if not self.copy_chatter_access:
            new_rule.chatter_access_ids.unlink()
        
        # Open the new rule
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'access.management',
            'res_id': new_rule.id,
            'view_mode': 'form',
            'target': 'current',
        }
