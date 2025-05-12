/** @odoo-module **/

import { Component, onWillStart, useState, onMounted } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useBus, useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

export class AccessManagementComponent extends Component {
    static template = "access_management.AccessManagement";
    
    setup() {
        this.rpc = useService("rpc");
        this.action = useService("action");
        this.user = useService("user");
        this.notification = useService("notification");
        this.accessRules = useState({ rules: [], loading: true });
        
        onWillStart(async () => {
            await this.loadAccessRules();
        });
        
        onMounted(() => {
            this.applyAccessRules();
        });
        
        useBus(this.env.bus, "access_rules_updated", () => {
            this.loadAccessRules();
        });
    }
    
    async loadAccessRules() {
        try {
            const rules = await this.rpc("/access_management/get_rules", {
                user_id: this.user.userId,
            });
            this.accessRules.rules = rules;
            this.accessRules.loading = false;
        } catch (error) {
            console.error("Error loading access rules:", error);
            this.accessRules.loading = false;
        }
    }
    
    applyAccessRules() {
        const rules = this.accessRules.rules;
        
        rules.forEach(rule => {
            // Apply menu hiding
            if (rule.hidden_menus) {
                rule.hidden_menus.forEach(menuId => {
                    const menuElement = document.querySelector(`[data-menu="${menuId}"]`);
                    if (menuElement) {
                        menuElement.style.display = 'none';
                    }
                });
            }
            
            // Apply field modifications
            if (rule.field_modifications) {
                rule.field_modifications.forEach(fieldMod => {
                    const fieldElement = document.querySelector(
                        `[data-field="${fieldMod.field_name}"]`
                    );
                    if (fieldElement) {
                        if (fieldMod.readonly) {
                            fieldElement.setAttribute('readonly', 'readonly');
                        }
                        if (fieldMod.invisible) {
                            fieldElement.style.display = 'none';
                        }
                        if (fieldMod.required) {
                            fieldElement.setAttribute('required', 'required');
                        }
                    }
                });
            }
            
            // Apply button/tab hiding
            if (rule.hidden_elements) {
                rule.hidden_elements.forEach(element => {
                    const el = document.querySelector(
                        `[data-${element.type}="${element.name}"]`
                    );
                    if (el) {
                        el.style.display = 'none';
                    }
                });
            }
        });
    }
    
    /**
     * Check if user has access to perform action
     */
    async checkAccess(modelName, operation) {
        try {
            const hasAccess = await this.rpc("/access_management/check_access", {
                model: modelName,
                operation: operation,
                user_id: this.user.userId,
            });
            return hasAccess;
        } catch (error) {
            console.error("Error checking access:", error);
            return false;
        }
    }
    
    /**
     * Apply domain to search query
     */
    applyDomain(modelName, currentDomain) {
        const rules = this.accessRules.rules;
        let additionalDomain = [];
        
        rules.forEach(rule => {
            if (rule.domain_access && rule.domain_access[modelName]) {
                additionalDomain = additionalDomain.concat(
                    rule.domain_access[modelName]
                );
            }
        });
        
        if (additionalDomain.length > 0) {
            return ['&', ...currentDomain, ...additionalDomain];
        }
        return currentDomain;
    }
}

// Register the component
registry.category("services").add("access_management", {
    start(env) {
        return new AccessManagementComponent(env);
    },
});

// Access Management Service
export const accessManagementService = {
    dependencies: ["rpc", "user"],
    async start(env, { rpc, user }) {
        let accessRules = null;
        
        const service = {
            async getAccessRules(forceReload = false) {
                if (!accessRules || forceReload) {
                    accessRules = await rpc("/access_management/get_rules", {
                        user_id: user.userId,
                    });
                }
                return accessRules;
            },
            
            async checkAccess(modelName, operation) {
                return rpc("/access_management/check_access", {
                    model: modelName,
                    operation: operation,
                    user_id: user.userId,
                });
            },
            
            applyDomainFilter(modelName, domain) {
                const rules = accessRules;
                if (!rules) return domain;
                
                let additionalDomain = [];
                rules.forEach(rule => {
                    if (rule.domain_access && rule.domain_access[modelName]) {
                        additionalDomain = additionalDomain.concat(
                            rule.domain_access[modelName]
                        );
                    }
                });
                
                if (additionalDomain.length > 0) {
                    return ['&', ...domain, ...additionalDomain];
                }
                return domain;
            },
            
            isFieldReadonly(modelName, fieldName) {
                const rules = accessRules;
                if (!rules) return false;
                
                for (const rule of rules) {
                    if (rule.field_access && rule.field_access[modelName]) {
                        const fieldAccess = rule.field_access[modelName][fieldName];
                        if (fieldAccess && fieldAccess.readonly) {
                            return true;
                        }
                    }
                }
                return false;
            },
            
            isFieldInvisible(modelName, fieldName) {
                const rules = accessRules;
                if (!rules) return false;
                
                for (const rule of rules) {
                    if (rule.field_access && rule.field_access[modelName]) {
                        const fieldAccess = rule.field_access[modelName][fieldName];
                        if (fieldAccess && fieldAccess.invisible) {
                            return true;
                        }
                    }
                }
                return false;
            },
            
            isMenuHidden(menuId) {
                const rules = accessRules;
                if (!rules) return false;
                
                for (const rule of rules) {
                    if (rule.hidden_menus && rule.hidden_menus.includes(menuId)) {
                        return true;
                    }
                }
                return false;
            },
        };
        
        // Load initial rules
        await service.getAccessRules();
        
        return service;
    },
};

registry.category("services").add("access_management_service", accessManagementService);

// Extend FormView to apply access rules
import { FormController } from "@web/views/form/form_controller";
import { patch } from "@web/core/utils/patch";

patch(FormController.prototype, "access_management", {
    async onWillStart() {
        const result = await this._super(...arguments);
        const accessService = this.env.services.access_management_service;
        
        if (accessService) {
            // Apply field access rules
            const modelName = this.props.resModel;
            const fields = this.props.fields;
            
            for (const fieldName in fields) {
                if (accessService.isFieldReadonly(modelName, fieldName)) {
                    fields[fieldName].readonly = true;
                }
                if (accessService.isFieldInvisible(modelName, fieldName)) {
                    fields[fieldName].invisible = true;
                }
            }
        }
        
        return result;
    },
});

// Extend ListView to apply domain filters
import { ListController } from "@web/views/list/list_controller";

patch(ListController.prototype, "access_management", {
    async onWillStart() {
        const result = await this._super(...arguments);
        const accessService = this.env.services.access_management_service;
        
        if (accessService) {
            // Apply domain filters
            const modelName = this.props.resModel;
            const currentDomain = this.props.domain || [];
            this.props.domain = accessService.applyDomainFilter(modelName, currentDomain);
        }
        
        return result;
    },
});
