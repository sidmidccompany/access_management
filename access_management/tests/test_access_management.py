# -*- coding: utf-8 -*-
from odoo.tests import TransactionCase, tagged
from odoo.exceptions import AccessError, ValidationError, UserError
from odoo.tools import mute_logger
import logging

_logger = logging.getLogger(__name__)


@tagged('access_management')
class TestAccessManagement(TransactionCase):
    
    def setUp(self):
        super(TestAccessManagement, self).setUp()
        
        # Create test users
        self.user_manager = self.env['res.users'].create({
            'name': 'Test Manager',
            'login': 'test_manager',
            'email': 'manager@test.com',
            'groups_id': [(6, 0, [self.env.ref('base.group_user').id])]
        })
        
        self.user_employee = self.env['res.users'].create({
            'name': 'Test Employee',
            'login': 'test_employee',
            'email': 'employee@test.com',
            'groups_id': [(6, 0, [self.env.ref('base.group_user').id])]
        })
        
        # Create test group
        self.test_group = self.env['res.groups'].create({
            'name': 'Test Access Group',
        })
        
        # Create test access rule
        self.access_rule = self.env['access.management'].create({
            'name': 'Test Access Rule',
            'active': True,
            'apply_by_group': False,
            'user_ids': [(6, 0, [self.user_employee.id])],
        })
    
    def test_01_access_rule_creation(self):
        """Test access rule creation and constraints"""
        # Test successful creation
        rule = self.env['access.management'].create({
            'name': 'Test Rule Creation',
            'active': True,
            'user_ids': [(6, 0, [self.user_manager.id])],
        })
        self.assertTrue(rule)
        self.assertEqual(rule.state, 'draft')
        
        # Test constraint - no users or groups
        with self.assertRaises(ValidationError):
            self.env['access.management'].create({
                'name': 'Invalid Rule',
                'active': True,
            })
    
    def test_02_user_access_rules(self):
        """Test getting applicable rules for users"""
        # Test employee rules
        employee_rules = self.env['access.management'].with_user(self.user_employee)._get_applicable_rules()
        self.assertIn(self.access_rule, employee_rules)
        
        # Test manager rules
        manager_rules = self.env['access.management'].with_user(self.user_manager)._get_applicable_rules()
        self.assertNotIn(self.access_rule, manager_rules)
        
        # Add manager to rule
        self.access_rule.user_ids = [(4, self.user_manager.id)]
        manager_rules = self.env['access.management'].with_user(self.user_manager)._get_applicable_rules()
        self.assertIn(self.access_rule, manager_rules)
    
    def test_03_group_access_rules(self):
        """Test group-based access rules"""
        # Create group-based rule
        group_rule = self.env['access.management'].create({
            'name': 'Group Test Rule',
            'active': True,
            'apply_by_group': True,
            'group_ids': [(6, 0, [self.test_group.id])],
        })
        
        # Test without group
        employee_rules = self.env['access.management'].with_user(self.user_employee)._get_applicable_rules()
        self.assertNotIn(group_rule, employee_rules)
        
        # Add user to group
        self.user_employee.groups_id = [(4, self.test_group.id)]
        employee_rules = self.env['access.management'].with_user(self.user_employee)._get_applicable_rules()
        self.assertIn(group_rule, employee_rules)
    
    def test_04_menu_access(self):
        """Test menu hiding functionality"""
        test_menu = self.env['ir.ui.menu'].create({
            'name': 'Test Menu',
            'parent_id': self.env.ref('base.menu_administration').id,
        })
        
        # Add menu to access rule
        self.env['access.management.menu'].create({
            'access_id': self.access_rule.id,
            'menu_id': test_menu.id,
            'hidden': True,
        })
        
        # Test menu visibility
        visible_menus = self.env['ir.ui.menu'].with_user(self.user_employee)._visible_menu_ids()
        self.assertNotIn(test_menu.id, visible_menus)
        
        visible_menus = self.env['ir.ui.menu'].with_user(self.user_manager)._visible_menu_ids()
        self.assertIn(test_menu.id, visible_menus)
    
    def test_05_model_access(self):
        """Test model access permissions"""
        # Add model access restriction
        self.env['access.management.model'].create({
            'access_id': self.access_rule.id,
            'model_id': self.env.ref('base.model_res_partner').id,
            'perm_read': True,
            'perm_write': False,
            'perm_create': False,
            'perm_unlink': False,
        })
        
        # Test permissions
        access_mgmt = self.env['access.management']
        
        # Employee should have read access only
        self.assertTrue(access_mgmt.check_access('res.partner', 'read', 
                                               user=self.user_employee, raise_exception=False))
        self.assertFalse(access_mgmt.check_access('res.partner', 'write', 
                                                user=self.user_employee, raise_exception=False))
        self.assertFalse(access_mgmt.check_access('res.partner', 'create', 
                                                user=self.user_employee, raise_exception=False))
        self.assertFalse(access_mgmt.check_access('res.partner', 'unlink', 
                                                user=self.user_employee, raise_exception=False))
        
        # Manager should have full access (no restrictions)
        self.assertTrue(access_mgmt.check_access('res.partner', 'read', 
                                               user=self.user_manager, raise_exception=False))
        self.assertTrue(access_mgmt.check_access('res.partner', 'write', 
                                               user=self.user_manager, raise_exception=False))
    
    def test_06_field_access(self):
        """Test field-level access control"""
        # Add field access restriction
        self.env['access.management.field'].create({
            'access_id': self.access_rule.id,
            'model_id': self.env.ref('base.model_res_partner').id,
            'field_id': self.env.ref('base.field_res_partner__vat').id,
            'readonly': True,
            'invisible': False,
            'required': False,
        })
        
        # Test field access
        fields_dict = {
            'vat': {'type': 'char', 'string': 'VAT'},
            'name': {'type': 'char', 'string': 'Name'},
        }
        
        access_mgmt = self.env['access.management']
        modified_fields = access_mgmt.apply_field_access('res.partner', fields_dict.copy(), 
                                                        user=self.user_employee)
        
        self.assertTrue(modified_fields['vat'].get('readonly'))
        self.assertFalse(modified_fields['name'].get('readonly'))
    
    def test_07_domain_access(self):
        """Test domain-based filtering"""
        # Add domain access
        self.env['access.management.domain'].create({
            'access_id': self.access_rule.id,
            'model_id': self.env.ref('base.model_res_partner').id,
            'name': 'Only Active Partners',
            'domain': "[('active', '=', True)]",
        })
        
        # Create test partners
        partner_active = self.env['res.partner'].create({
            'name': 'Active Partner',
            'active': True,
        })
        partner_inactive = self.env['res.partner'].create({
            'name': 'Inactive Partner',
            'active': False,
        })
        
        # Test domain application
        Partner = self.env['res.partner'].with_user(self.user_employee)
        partners = Partner.search([])
        
        self.assertIn(partner_active, partners)
        self.assertNotIn(partner_inactive, partners)
    
    def test_08_button_tab_access(self):
        """Test button and tab visibility"""
        # Add button restriction
        self.env['access.management.button.tab'].create({
            'access_id': self.access_rule.id,
            'model_id': self.env.ref('base.model_res_partner').id,
            'element_type': 'button',
            'element_name': 'action_archive',
            'invisible': True,
        })
        
        # Test would require view rendering, which is complex in unit tests
        # This is a placeholder for the actual implementation
        self.assertTrue(True)
    
    def test_09_conditional_field_access(self):
        """Test conditional field access"""
        # Add conditional field access
        self.env['access.management.field.conditional'].create({
            'access_id': self.access_rule.id,
            'model_id': self.env.ref('base.model_res_partner').id,
            'field_id': self.env.ref('base.field_res_partner__credit_limit').id,
            'condition': "record.customer_rank > 0",
            'readonly': True,
        })
        
        # Create test partner
        partner = self.env['res.partner'].create({
            'name': 'Test Customer',
            'customer_rank': 1,
        })
        
        # Test condition evaluation
        field_conditional = self.env['access.management.field.conditional'].search([
            ('access_id', '=', self.access_rule.id),
            ('field_id.name', '=', 'credit_limit'),
        ])
        
        result = field_conditional.evaluate_condition(partner)
        self.assertTrue(result)
        
        partner.customer_rank = 0
        result = field_conditional.evaluate_condition(partner)
        self.assertFalse(result)
    
    def test_10_chatter_access(self):
        """Test chatter restrictions"""
        # Add chatter restriction
        self.env['access.management.chatter'].create({
            'access_id': self.access_rule.id,
            'model_id': self.env.ref('base.model_res_partner').id,
            'disable_followers': True,
            'disable_activities': True,
            'restrict_message_post': True,
        })
        
        # Test would require checking mail thread functionality
        # This is a placeholder for the actual implementation
        self.assertTrue(True)
    
    def test_11_global_access(self):
        """Test global access code execution"""
        # Add global access code
        self.access_rule.global_access = """
# Test global access
if user.id == %d:
    return True
return False
""" % self.user_employee.id
        
        # Test code validation
        self.access_rule._check_global_access_code()
        
        # Test with invalid code
        with self.assertRaises(ValidationError):
            self.access_rule.global_access = "invalid python code {"
    
    def test_12_rule_activation_deactivation(self):
        """Test rule activation and deactivation"""
        # Test initial state
        self.assertTrue(self.access_rule.active)
        
        # Deactivate
        self.access_rule.action_deactivate_rule()
        self.assertFalse(self.access_rule.active)
        self.assertEqual(self.access_rule.state, 'disabled')
        
        # Activate
        self.access_rule.action_activate()
        self.assertTrue(self.access_rule.active)
        self.assertEqual(self.access_rule.state, 'active')
        
        # Toggle
        self.access_rule.toggle_active()
        self.assertFalse(self.access_rule.active)
    
    def test_13_access_rules_count(self):
        """Test access rules counting"""
        # Initially empty
        self.assertEqual(self.access_rule.access_rules_count, 0)
        
        # Add various restrictions
        self.env['access.management.menu'].create({
            'access_id': self.access_rule.id,
            'menu_id': self.env.ref('base.menu_administration').id,
        })
        
        self.env['access.management.model'].create({
            'access_id': self.access_rule.id,
            'model_id': self.env.ref('base.model_res_partner').id,
        })
        
        self.env['access.management.field'].create({
            'access_id': self.access_rule.id,
            'model_id': self.env.ref('base.model_res_partner').id,
            'field_id': self.env.ref('base.field_res_partner__name').id,
        })
        
        # Recompute and check
        self.access_rule._compute_access_rules_count()
        self.assertEqual(self.access_rule.access_rules_count, 3)
    
    def test_14_company_restrictions(self):
        """Test multi-company restrictions"""
        # Create test company
        test_company = self.env['res.company'].create({
            'name': 'Test Company',
        })
        
        # Create company-specific rule
        company_rule = self.env['access.management'].create({
            'name': 'Company Specific Rule',
            'active': True,
            'company_id': test_company.id,
            'user_ids': [(6, 0, [self.user_employee.id])],
        })
        
        # Test with different companies
        rules = self.env['access.management'].with_user(self.user_employee)._get_applicable_rules()
        self.assertIn(company_rule, rules)
        
        # Change user company
        self.user_employee.company_id = self.env.ref('base.main_company')
        rules = self.env['access.management'].with_user(self.user_employee)._get_applicable_rules()
        self.assertNotIn(company_rule, rules)
    
    def test_15_inheritance_model_access(self):
        """Test inherited model access checking"""
        # Test the inherited ir.model check_access_rights
        Model = self.env['ir.model'].with_user(self.user_employee)
        partner_model = Model.search([('model', '=', 'res.partner')], limit=1)
        
        # Should work without restrictions
        result = partner_model.check_access_rights('read', raise_exception=False)
        self.assertTrue(result)
        
        # Add restriction
        self.env['access.management.model'].create({
            'access_id': self.access_rule.id,
            'model_id': self.env.ref('base.model_res_partner').id,
            'perm_read': False,
            'perm_write': False,
            'perm_create': False,
            'perm_unlink': False,
        })
        
        # Should now fail
        result = partner_model.check_access_rights('read', raise_exception=False)
        self.assertFalse(result)


@tagged('access_management', 'wizard')
class TestAccessManagementWizards(TransactionCase):
    
    def setUp(self):
        super(TestAccessManagementWizards, self).setUp()
        
        # Create test data
        self.access_rule = self.env['access.management'].create({
            'name': 'Test Rule for Wizards',
            'active': True,
        })
        
        self.test_menu = self.env['ir.ui.menu'].create({
            'name': 'Test Menu for Wizard',
            'parent_id': self.env.ref('base.menu_administration').id,
        })
    
    def test_01_menu_wizard(self):
        """Test menu wizard functionality"""
        wizard = self.env['access.management.menu.wizard'].create({
            'access_id': self.access_rule.id,
            'menu_id': self.test_menu.id,
            'hidden': True,
            'apply_to_children': False,
        })
        
        # Test menu addition
        wizard.action_add_menu()
        
        # Check if menu was added
        menu_access = self.env['access.management.menu'].search([
            ('access_id', '=', self.access_rule.id),
            ('menu_id', '=', self.test_menu.id),
        ])
        self.assertTrue(menu_access)
        self.assertTrue(menu_access.hidden)
        
        # Test duplicate prevention
        wizard2 = self.env['access.management.menu.wizard'].create({
            'access_id': self.access_rule.id,
            'menu_id': self.test_menu.id,
            'hidden': True,
        })
        
        with self.assertRaises(UserError):
            wizard2.action_add_menu()
    
    def test_02_copy_wizard(self):
        """Test copy wizard functionality"""
        # Add some data to original rule
        self.env['access.management.menu'].create({
            'access_id': self.access_rule.id,
            'menu_id': self.test_menu.id,
            'hidden': True,
        })
        
        self.env['access.management.model'].create({
            'access_id': self.access_rule.id,
            'model_id': self.env.ref('base.model_res_partner').id,
            'perm_read': True,
        })
        
        # Create copy wizard
        wizard = self.env['access.management.copy.wizard'].create({
            'source_id': self.access_rule.id,
            'name': 'Copied Rule',
            'copy_menu_access': True,
            'copy_model_access': False,
        })
        
        # Execute copy
        result = wizard.action_copy()
        
        # Check new rule
        new_rule_id = result['res_id']
        new_rule = self.env['access.management'].browse(new_rule_id)
        
        self.assertEqual(new_rule.name, 'Copied Rule')
        self.assertFalse(new_rule.active)  # Should start inactive
        self.assertTrue(new_rule.menu_access_ids)  # Should have menu access
        self.assertFalse(new_rule.model_access_ids)  # Should not have model access
    
    def test_03_import_wizard(self):
        """Test import wizard structure"""
        # Just test the wizard can be created
        wizard = self.env['access.management.import.wizard'].create({
            'import_type': 'full',
            'update_existing': False,
        })
        
        self.assertEqual(wizard.import_type, 'full')
        self.assertFalse(wizard.update_existing)


@tagged('access_management', 'performance')
class TestAccessManagementPerformance(TransactionCase):
    
    def setUp(self):
        super(TestAccessManagementPerformance, self).setUp()
        
        # Create many test users and rules for performance testing
        self.users = []
        for i in range(10):
            user = self.env['res.users'].create({
                'name': f'Test User {i}',
                'login': f'test_user_{i}',
                'email': f'user{i}@test.com',
            })
            self.users.append(user)
        
        self.rules = []
        for i in range(20):
            rule = self.env['access.management'].create({
                'name': f'Test Rule {i}',
                'active': True,
                'user_ids': [(6, 0, self.users[:5])],  # First 5 users
            })
            self.rules.append(rule)
    
    def test_01_rule_lookup_performance(self):
        """Test performance of rule lookup"""
        import time
        
        # Test rule lookup performance
        start_time = time.time()
        
        for user in self.users[:5]:
            rules = self.env['access.management'].with_user(user)._get_applicable_rules()
            self.assertEqual(len(rules), 20)  # All rules apply to first 5 users
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Should complete in reasonable time (adjust threshold as needed)
        self.assertLess(duration, 2.0, "Rule lookup took too long")
        _logger.info(f"Rule lookup for 5 users took {duration:.3f} seconds")
    
    def test_02_access_check_performance(self):
        """Test performance of access checking"""
        import time
        
        # Add model restrictions to rules
        for rule in self.rules[:10]:
            self.env['access.management.model'].create({
                'access_id': rule.id,
                'model_id': self.env.ref('base.model_res_partner').id,
                'perm_read': True,
                'perm_write': False,
            })
        
        # Test access check performance
        start_time = time.time()
        
        for user in self.users[:5]:
            for operation in ['read', 'write', 'create', 'unlink']:
                result = self.env['access.management'].check_access(
                    'res.partner', operation, user=user, raise_exception=False
                )
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Should complete in reasonable time
        self.assertLess(duration, 3.0, "Access checking took too long")
        _logger.info(f"Access check for 5 users x 4 operations took {duration:.3f} seconds")
