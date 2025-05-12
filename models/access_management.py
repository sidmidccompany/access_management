# -*- coding: utf-8 -*-
import ast
import json
import logging
from lxml import etree
from odoo import models, fields, api, tools, _
from odoo.exceptions import ValidationError, UserError
from odoo.tools.safe_eval import safe_eval
from odoo.osv import expression

_logger = logging.getLogger(__name__)


class AccessManagement(models.Model):
    _name = 'access.management'
    _description = 'Access Management'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'sequence, id desc'
    _rec_name = 'name'
    
    # Basic Fields
    name = fields.Char(
        string='Name', 
        required=True, 
        translate=True,
        tracking=True,
        help="Enter a descriptive name for this access rule"
    )
    active = fields.Boolean(
        string='Active', 
        default=True,
        tracking=True,
        help="Deactivate the access rule without deleting it"
    )
    sequence = fields.Integer(
        string='Sequence', 
        default=10,
        help="Determines the order in which access rules are applied"
    )
    
    # Configuration Fields
    apply_by_group = fields.Boolean(
        string='Apply By Group',
        tracking=True,
        help='Apply this access rule based on user groups instead of individual users'
    )
    read_only = fields.Boolean(
        string='Read-Only',
        tracking=True,
        help='Make all specified accesses read-only (no create, write, or delete)'
    )
    apply_without_company = fields.Boolean(
        string='Apply Without Company',
        tracking=True,
        help='Apply this rule regardless of the user\'s current company'
    )
    
    # User Association
    user_ids = fields.Many2many(
        'res.users', 
        'access_management_users_rel',
        'access_id', 
        'user_id', 
        string='Users',
        domain=[('share', '=', False)],
        help="Select specific users for this access rule"
    )
    group_ids = fields.Many2many(
        'res.groups', 
        'access_management_groups_rel',
        'access_id', 
        'group_id', 
        string='Groups',
        help="Select user groups for this access rule"
    )
    
    # Company
    company_id = fields.Many2one(
        'res.company', 
        string='Company',
        default=lambda self: self.env.company,
        help="Restrict this rule to a specific company"
    )
    
    # User Type Filters
    default_internal_user = fields.Boolean(
        string='Default Internal User',
        help="Apply to all internal users by default"
    )
    default_portal_user = fields.Boolean(
        string='Default Portal User',
        help="Apply to all portal users by default"
    )
    disable_developer_mode = fields.Boolean(
        string='Disable Developer Mode',
        help="Prevent users from accessing developer mode"
    )
    
    # Access Types
    menu_access_ids = fields.One2many(
        'access.management.menu', 
        'access_id',
        string='Hide Menu',
        help="Menus to hide from specified users"
    )
    model_access_ids = fields.One2many(
        'access.management.model', 
        'access_id',
        string='Model Access',
        help="Model-level access permissions"
    )
    field_access_ids = fields.One2many(
        'access.management.field', 
        'access_id',
        string='Field Access',
        help="Field-level access permissions"
    )
    field_conditional_access_ids = fields.One2many(
        'access.management.field.conditional',
        'access_id',
        string='Field Conditional Access',
        help="Conditional field access based on record values"
    )
    domain_access_ids = fields.One2many(
        'access.management.domain', 
        'access_id',
        string='Domain Access',
        help="Domain-based record filtering"
    )
    button_tab_access_ids = fields.One2many(
        'access.management.button.tab', 
        'access_id',
        string='Button/Tab Access',
        help="Control visibility of buttons and tabs"
    )
    search_panel_access_ids = fields.One2many(
        'access.management.search.panel', 
        'access_id',
        string='Search Panel Access',
        help="Control search panel fields visibility"
    )
    chatter_access_ids = fields.One2many(
        'access.management.chatter', 
        'access_id',
        string='Chatter',
        help="Control chatter functionality"
    )
    
    # Global Access
    global_access = fields.Text(
        string='Global Access',
        help="Python code for custom access logic"
    )
    
    # Computed fields
    access_rules_count = fields.Integer(
        string='Access Rules', 
        compute='_compute_access_rules_count',
        store=True
    )
    
    # State and metadata fields
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('disabled', 'Disabled')
    ], string='State', default='draft', tracking=True)
    
    created_by = fields.Many2one(
        'res.users', 
        string='Created by',
        default=lambda self: self.env.user,
        readonly=True
    )
    created_on = fields.Datetime(
        string='Created on',
        default=fields.Datetime.now,
        readonly=True
    )
    last_updated_by = fields.Many2one(
        'res.users',
        string='Last Updated by',
        readonly=True
    )
    last_updated_on = fields.Datetime(
        string='Last Updated on',
        readonly=True
    )
    
    @api.depends('model_access_ids', 'field_access_ids', 'domain_access_ids',
                 'button_tab_access_ids', 'menu_access_ids', 'search_panel_access_ids',
                 'chatter_access_ids', 'field_conditional_access_ids')
    def _compute_access_rules_count(self):
        for record in self:
            count = (
                len(record.model_access_ids) +
                len(record.field_access_ids) +
                len(record.domain_access_ids) +
                len(record.button_tab_access_ids) +
                len(record.menu_access_ids) +
                len(record.search_panel_access_ids) +
                len(record.chatter_access_ids) +
                len(record.field_conditional_access_ids)
            )
            record.access_rules_count = count
    
    @api.model
    def create(self, vals):
        vals['created_by'] = self.env.user.id
        vals['created_on'] = fields.Datetime.now()
        return super(AccessManagement, self).create(vals)
    
    def write(self, vals):
        vals['last_updated_by'] = self.env.user.id
        vals['last_updated_on'] = fields.Datetime.now()
        return super(AccessManagement, self).write(vals)
    
    @api.constrains('user_ids', 'group_ids')
    def _check_user_or_group(self):
        for record in self:
            if not record.user_ids and not record.group_ids and not (
                record.default_internal_user or record.default_portal_user
            ):
                raise ValidationError(
                    _("You must specify at least one user, group, or user type filter.")
                )
    
    @api.constrains('global_access')
    def _check_global_access_code(self):
        for record in self:
            if record.global_access:
                try:
                    compile(record.global_access, '<string>', 'exec')
                except SyntaxError as e:
                    raise ValidationError(
                        _("Global access code has syntax error: %s") % str(e)
                    )
    
    def toggle_active(self):
        """Toggle the active state of the access management rule"""
        for record in self:
            record.active = not record.active
            record.state = 'active' if record.active else 'disabled'
    
    def action_activate(self):
        """Activate the access rule"""
        self.write({'active': True, 'state': 'active'})
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': _('Access rule activated successfully.'),
                'type': 'success',
                'sticky': False,
            }
        }
    
    def action_deactivate_rule(self):
        """Deactivate the current rule"""
        self.write({'active': False, 'state': 'disabled'})
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': _('Access rule deactivated successfully.'),
                'type': 'success',
                'sticky': False,
            }
        }
    
    @api.model
    def _get_applicable_rules(self, user=None):
        """Get all applicable rules for a specific user"""
        if not user:
            user = self.env.user
        
        domain = [('active', '=', True)]
        
        # Company check
        if not self.env.context.get('bypass_company_check'):
            domain.append('|')
            domain.append(('company_id', '=', False))
            domain.append(('company_id', '=', user.company_id.id))
        
        rules = self.search(domain, order='sequence')
        applicable_rules = self.env['access.management']
        
        for rule in rules:
            # Check if rule applies to this user
            applies = False
            
            # Check user types
            if rule.default_internal_user and not user.share:
                applies = True
            elif rule.default_portal_user and user.share:
                applies = True
            
            # Check specific users
            if user in rule.user_ids:
                applies = True
            
            # Check groups
            if rule.apply_by_group and any(group in rule.group_ids for group in user.groups_id):
                applies = True
            
            if applies:
                applicable_rules |= rule
        
        return applicable_rules
    
    @api.model
    def check_access(self, model_name, operation, user=None, raise_exception=True):
        """Check if user has access to perform operation on model"""
        if not user:
            user = self.env.user
        
        # Bypass for superuser
        if user._is_superuser():
            return True
        
        rules = self._get_applicable_rules(user)
        
        for rule in rules:
            # Check model access
            for model_access in rule.model_access_ids:
                if model_access.model_id.model == model_name:
                    if operation == 'read' and not model_access.perm_read:
                        if raise_exception:
                            raise UserError(_("Read access denied on %s") % model_name)
                        return False
                    elif operation == 'write' and not model_access.perm_write:
                        if raise_exception:
                            raise UserError(_("Write access denied on %s") % model_name)
                        return False
                    elif operation == 'create' and not model_access.perm_create:
                        if raise_exception:
                            raise UserError(_("Create access denied on %s") % model_name)
                        return False
                    elif operation == 'unlink' and not model_access.perm_unlink:
                        if raise_exception:
                            raise UserError(_("Delete access denied on %s") % model_name)
                        return False
        
        return True
    
    @api.model
    def apply_field_access(self, model_name, fields_dict, user=None):
        """Apply field access rules to fields dictionary"""
        if not user:
            user = self.env.user
        
        rules = self._get_applicable_rules(user)
        
        for rule in rules:
            for field_access in rule.field_access_ids:
                if field_access.model_id.model == model_name:
                    field_name = field_access.field_id.name
                    if field_name in fields_dict:
                        if field_access.invisible:
                            fields_dict[field_name]['invisible'] = True
                        if field_access.readonly:
                            fields_dict[field_name]['readonly'] = True
                        if field_access.required:
                            fields_dict[field_name]['required'] = True
        
        return fields_dict
    
    @api.model
    def apply_view_access(self, model_name, view_arch, view_type, user=None):
        """Apply view access rules to view architecture"""
        if not user:
            user = self.env.user
        
        rules = self._get_applicable_rules(user)
        doc = etree.fromstring(view_arch)
        
        for rule in rules:
            # Apply button/tab access
            for btn_tab in rule.button_tab_access_ids:
                if btn_tab.model_id.model == model_name:
                    elements = doc.xpath("//%s[@name='%s']" % (btn_tab.element_type, btn_tab.element_name))
                    for element in elements:
                        if btn_tab.invisible:
                            element.set('invisible', '1')
                        if btn_tab.readonly:
                            element.set('readonly', '1')
        
        return etree.tostring(doc, encoding='unicode')


class AccessManagementMenu(models.Model):
    _name = 'access.management.menu'
    _description = 'Access Management Menu'
    _order = 'sequence, id'
    
    access_id = fields.Many2one(
        'access.management', 
        string='Access Management',
        ondelete='cascade', 
        required=True,
        index=True
    )
    menu_id = fields.Many2one(
        'ir.ui.menu', 
        string='Menu', 
        required=True,
        help="Select the menu to hide"
    )
    hidden = fields.Boolean(
        string='Hidden', 
        default=True,
        help="Hide this menu from users"
    )
    sequence = fields.Integer(
        string='Sequence',
        default=10
    )
    
    @api.constrains('access_id', 'menu_id')
    def _check_unique_menu(self):
        for record in self:
            duplicate = self.search([
                ('id', '!=', record.id),
                ('access_id', '=', record.access_id.id),
                ('menu_id', '=', record.menu_id.id)
            ])
            if duplicate:
                raise ValidationError(
                    _("Menu '%s' is already configured in this access rule.") % record.menu_id.name
                )


class AccessManagementModel(models.Model):
    _name = 'access.management.model'
    _description = 'Access Management Model'
    _order = 'model_id'
    
    access_id = fields.Many2one(
        'access.management', 
        string='Access Management',
        ondelete='cascade', 
        required=True,
        index=True
    )
    model_id = fields.Many2one(
        'ir.model', 
        string='Model', 
        required=True,
        help="Select the model to configure access"
    )
    model_name = fields.Char(
        related='model_id.model',
        string='Model Name',
        readonly=True,
        store=True
    )
    perm_read = fields.Boolean(
        string='Read',
        default=True,
        help="Allow read access"
    )
    perm_write = fields.Boolean(
        string='Write',
        help="Allow write access"
    )
    perm_create = fields.Boolean(
        string='Create',
        help="Allow create access"
    )
    perm_unlink = fields.Boolean(
        string='Delete',
        help="Allow delete access"
    )
    
    @api.constrains('access_id', 'model_id')
    def _check_unique_model(self):
        for record in self:
            duplicate = self.search([
                ('id', '!=', record.id),
                ('access_id', '=', record.access_id.id),
                ('model_id', '=', record.model_id.id)
            ])
            if duplicate:
                raise ValidationError(
                    _("Model '%s' is already configured in this access rule.") % record.model_id.name
                )
    
    @api.onchange('access_id')
    def _onchange_access_id(self):
        if self.access_id and self.access_id.read_only:
            self.perm_write = False
            self.perm_create = False
            self.perm_unlink = False


class AccessManagementField(models.Model):
    _name = 'access.management.field'
    _description = 'Access Management Field'
    _order = 'model_id, field_id'
    
    access_id = fields.Many2one(
        'access.management', 
        string='Access Management',
        ondelete='cascade', 
        required=True,
        index=True
    )
    model_id = fields.Many2one(
        'ir.model', 
        string='Model', 
        required=True,
        help="Select the model containing the field"
    )
    model_name = fields.Char(
        related='model_id.model',
        string='Model Name',
        readonly=True,
        store=True
    )
    field_id = fields.Many2one(
        'ir.model.fields', 
        string='Field', 
        required=True,
        domain="[('model_id', '=', model_id), ('ttype', 'not in', ['one2many', 'many2many'])]",
        help="Select the field to configure access"
    )
    field_name = fields.Char(
        related='field_id.name',
        string='Field Name',
        readonly=True,
        store=True
    )
    field_type = fields.Selection(
        related='field_id.ttype',
        string='Field Type',
        readonly=True
    )
    readonly = fields.Boolean(
        string='Read Only',
        help="Make this field read-only"
    )
    invisible = fields.Boolean(
        string='Invisible',
        help="Hide this field from view"
    )
    required = fields.Boolean(
        string='Required',
        help="Make this field mandatory"
    )
    
    @api.constrains('access_id', 'field_id')
    def _check_unique_field(self):
        for record in self:
            duplicate = self.search([
                ('id', '!=', record.id),
                ('access_id', '=', record.access_id.id),
                ('field_id', '=', record.field_id.id)
            ])
            if duplicate:
                raise ValidationError(
                    _("Field '%s' is already configured in this access rule.") % record.field_id.name
                )
    
    @api.onchange('model_id')
    def _onchange_model_id(self):
        self.field_id = False
    
    @api.onchange('field_id')
    def _onchange_field_id(self):
        if self.field_id:
            # Set sensible defaults based on field type
            if self.field_id.ttype in ['many2one', 'many2many', 'one2many']:
                self.required = False
            if self.field_id.readonly:
                self.readonly = True


class AccessManagementFieldConditional(models.Model):
    _name = 'access.management.field.conditional'
    _description = 'Access Management Field Conditional'
    _order = 'model_id, field_id'
    
    access_id = fields.Many2one(
        'access.management', 
        string='Access Management',
        ondelete='cascade', 
        required=True,
        index=True
    )
    model_id = fields.Many2one(
        'ir.model', 
        string='Model', 
        required=True,
        help="Select the model containing the field"
    )
    model_name = fields.Char(
        related='model_id.model',
        string='Model Name',
        readonly=True,
        store=True
    )
    field_id = fields.Many2one(
        'ir.model.fields', 
        string='Field', 
        required=True,
        domain="[('model_id', '=', model_id)]",
        help="Select the field to configure conditional access"
    )
    field_name = fields.Char(
        related='field_id.name',
        string='Field Name',
        readonly=True,
        store=True
    )
    condition = fields.Text(
        string='Condition', 
        required=True,
        help='Python expression that returns True/False. Available variables: record, user, today'
    )
    readonly = fields.Boolean(
        string='Read Only',
        help="Make field read-only when condition is met"
    )
    invisible = fields.Boolean(
        string='Invisible',
        help="Hide field when condition is met"
    )
    required = fields.Boolean(
        string='Required',
        help="Make field required when condition is met"
    )
    
    @api.constrains('condition')
    def _check_condition_syntax(self):
        for record in self:
            try:
                compile(record.condition, '<string>', 'eval')
            except SyntaxError as e:
                raise ValidationError(
                    _("Condition has syntax error: %s") % str(e)
                )
    
    @api.onchange('model_id')
    def _onchange_model_id(self):
        self.field_id = False
    
    def evaluate_condition(self, record):
        """Evaluate the condition for a given record"""
        try:
            context = {
                'record': record,
                'user': self.env.user,
                'today': fields.Date.today(),
                'now': fields.Datetime.now(),
                'uid': self.env.uid,
                'context': self.env.context,
            }
            return safe_eval(self.condition, context)
        except Exception as e:
            _logger.warning("Error evaluating condition: %s", str(e))
            return False


class AccessManagementDomain(models.Model):
    _name = 'access.management.domain'
    _description = 'Access Management Domain'
    _order = 'model_id, sequence'
    
    access_id = fields.Many2one(
        'access.management', 
        string='Access Management',
        ondelete='cascade', 
        required=True,
        index=True
    )
    model_id = fields.Many2one(
        'ir.model', 
        string='Model', 
        required=True,
        help="Select the model to apply domain"
    )
    model_name = fields.Char(
        related='model_id.model',
        string='Model Name',
        readonly=True,
        store=True
    )
    domain = fields.Text(
        string='Domain', 
        required=True,
        help='Domain to filter records, e.g., [(\'state\', \'=\', \'draft\')]'
    )
    name = fields.Char(
        string='Description',
        help="Short description of what this domain does"
    )
    sequence = fields.Integer(
        string='Sequence',
        default=10,
        help="Order in which domains are applied"
    )
    
    @api.constrains('domain')
    def _check_domain_syntax(self):
        for record in self:
            try:
                domain = safe_eval(record.domain)
                if not isinstance(domain, list):
                    raise ValidationError(_("Domain must be a list"))
                # Test domain format
                expression.normalize_domain(domain)
            except Exception as e:
                raise ValidationError(
                    _("Invalid domain format: %s") % str(e)
                )
    
    def get_domain(self):
        """Get the domain as a Python object"""
        self.ensure_one()
        try:
            return safe_eval(self.domain)
        except Exception:
            return []


class AccessManagementButtonTab(models.Model):
    _name = 'access.management.button.tab'
    _description = 'Access Management Button/Tab'
    _order = 'model_id, element_type, element_name'
    
    access_id = fields.Many2one(
        'access.management', 
        string='Access Management',
        ondelete='cascade', 
        required=True,
        index=True
    )
    model_id = fields.Many2one(
        'ir.model', 
        string='Model', 
        required=True,
        help="Select the model containing the element"
    )
    model_name = fields.Char(
        related='model_id.model',
        string='Model Name',
        readonly=True,
        store=True
    )
    element_type = fields.Selection([
        ('button', 'Button'),
        ('tab', 'Tab'),
        ('page', 'Page'),
        ('group', 'Group'),
        ('div', 'Div'),
        ('field', 'Field'),
        ('widget', 'Widget')
    ], string='Type', required=True, default='button')
    element_name = fields.Char(
        string='Element Name', 
        required=True,
        help='Technical name or identifier of the element'
    )
    element_label = fields.Char(
        string='Element Label',
        help='User-friendly label of the element'
    )
    view_type = fields.Selection([
        ('form', 'Form'),
        ('tree', 'Tree'),
        ('kanban', 'Kanban'),
        ('pivot', 'Pivot'),
        ('graph', 'Graph'),
        ('calendar', 'Calendar')
    ], string='View Type', default='form')
    invisible = fields.Boolean(
        string='Invisible',
        help="Hide this element"
    )
    readonly = fields.Boolean(
        string='Read Only',
        help="Make this element read-only"
    )
    attrs = fields.Text(
        string='Attributes',
        help='Additional attributes as JSON, e.g., {"class": "btn-primary"}'
    )
    
    @api.constrains('attrs')
    def _check_attrs_format(self):
        for record in self:
            if record.attrs:
                try:
                    json.loads(record.attrs)
                except json.JSONDecodeError:
                    raise ValidationError(
                        _("Attributes must be valid JSON format")
                    )


class AccessManagementSearchPanel(models.Model):
    _name = 'access.management.search.panel'
    _description = 'Access Management Search Panel'
    _order = 'model_id, field_id'
    
    access_id = fields.Many2one(
        'access.management', 
        string='Access Management',
        ondelete='cascade', 
        required=True,
        index=True
    )
    model_id = fields.Many2one(
        'ir.model', 
        string='Model', 
        required=True,
        help="Select the model for search panel configuration"
    )
    model_name = fields.Char(
        related='model_id.model',
        string='Model Name',
        readonly=True,
        store=True
    )
    field_id = fields.Many2one(
        'ir.model.fields', 
        string='Field', 
        required=True,
        domain="[('model_id', '=', model_id)]",
        help="Select the field to configure in search panel"
    )
    field_name = fields.Char(
        related='field_id.name',
        string='Field Name',
        readonly=True,
        store=True
    )
    invisible = fields.Boolean(
        string='Invisible',
        help="Hide this field from search panel"
    )
    sequence = fields.Integer(
        string='Sequence',
        default=10,
        help="Order of fields in search panel"
    )
    
    @api.onchange('model_id')
    def _onchange_model_id(self):
        self.field_id = False


class AccessManagementChatter(models.Model):
    _name = 'access.management.chatter'
    _description = 'Access Management Chatter'
    _order = 'model_id'
    
    access_id = fields.Many2one(
        'access.management', 
        string='Access Management',
        ondelete='cascade', 
        required=True,
        index=True
    )
    model_id = fields.Many2one(
        'ir.model', 
        string='Model', 
        required=True,
        help="Select the model for chatter configuration"
    )
    model_name = fields.Char(
        related='model_id.model',
        string='Model Name',
        readonly=True,
        store=True
    )
    disable_chatter = fields.Boolean(
        string='Disable Chatter',
        help="Completely disable chatter for this model"
    )
    disable_followers = fields.Boolean(
        string='Disable Followers',
        help="Disable follower functionality"
    )
    disable_activities = fields.Boolean(
        string='Disable Activities',
        help="Disable activity functionality"
    )
    restrict_message_post = fields.Boolean(
        string='Restrict Message Post',
        help="Restrict message posting to specific users/groups"
    )
    disable_log_note = fields.Boolean(
        string='Disable Log Note',
        help="Disable log note functionality"
    )
    disable_attachments = fields.Boolean(
        string='Disable Attachments',
        help="Disable attachment functionality in chatter"
    )
    
    @api.constrains('access_id', 'model_id')
    def _check_unique_model(self):
        for record in self:
            duplicate = self.search([
                ('id', '!=', record.id),
                ('access_id', '=', record.access_id.id),
                ('model_id', '=', record.model_id.id)
            ])
            if duplicate:
                raise ValidationError(
                    _("Model '%s' already has chatter configuration in this access rule.") % record.model_id.name
                )
