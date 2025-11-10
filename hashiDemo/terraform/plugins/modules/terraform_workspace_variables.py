#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2025, Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = '''
---
module: terraform_workspace_variables
short_description: Manage Terraform Enterprise/Cloud workspace variables
version_added: "1.0.0"
description:
  - Create, update, or delete workspace variables in Terraform Enterprise/Cloud
  - Manage both Terraform variables and environment variables
  - Support for sensitive variables with secure handling

options:
  token:
    description:
      - Terraform Enterprise/Cloud API token
      - Can also be set via TF_TOKEN environment variable
    type: str
    required: true
  url:
    description:
      - URL of the Terraform Enterprise instance
      - Defaults to Terraform Cloud (app.terraform.io)
    type: str
    default: https://app.terraform.io
  organization:
    description:
      - Name of the Terraform organization
    type: str
    required: true
  workspace:
    description:
      - Name of the workspace
    type: str
    required: true
  variables:
    description:
      - Dictionary of variables to manage
      - Key is the variable name, value is the variable configuration
    type: dict
    required: true
    suboptions:
      value:
        description:
          - Value of the variable
        type: str
        required: true
      category:
        description:
          - Category of the variable
        type: str
        choices: ['terraform', 'env']
        default: terraform
      sensitive:
        description:
          - Whether the variable is sensitive
        type: bool
        default: false
      description:
        description:
          - Description of the variable
        type: str
        default: ''
      hcl:
        description:
          - Whether the variable is HCL (only for terraform variables)
        type: bool
        default: false
  state:
    description:
      - Whether the variables should exist or not
    type: str
    choices: ['present', 'absent']
    default: present
  purge:
    description:
      - Whether to remove variables not specified in the variables parameter
      - Only applies when state is 'present'
    type: bool
    default: false
  validate_certs:
    description:
      - Whether to validate SSL certificates
    type: bool
    default: true

requirements:
  - python >= 3.6
  - pytfe

author:
  - Ansible Terraform Collection (@ansible-collections)
'''

EXAMPLES = '''
- name: Set Terraform and environment variables
  hashiDemo.terraform.terraform_workspace_variables:
    token: "{{ terraform_token }}"
    organization: "my-org"
    workspace: "my-workspace"
    variables:
      region:
        value: "us-west-2"
        category: "terraform"
        description: "AWS region"
      instance_type:
        value: "t3.micro"
        category: "terraform"
        description: "EC2 instance type"
      AWS_ACCESS_KEY_ID:
        value: "{{ aws_access_key }}"
        category: "env"
        sensitive: true
        description: "AWS access key"
      AWS_SECRET_ACCESS_KEY:
        value: "{{ aws_secret_key }}"
        category: "env"
        sensitive: true
        description: "AWS secret key"
    state: present

- name: Set HCL variable
  hashiDemo.terraform.terraform_workspace_variables:
    token: "{{ terraform_token }}"
    organization: "my-org"
    workspace: "my-workspace"
    variables:
      vpc_config:
        value: |
          {
            cidr = "10.0.0.0/16"
            enable_dns = true
          }
        category: "terraform"
        hcl: true
        description: "VPC configuration"
    state: present

- name: Remove specific variables
  hashiDemo.terraform.terraform_workspace_variables:
    token: "{{ terraform_token }}"
    organization: "my-org"
    workspace: "my-workspace"
    variables:
      old_variable:
        value: ""  # Value doesn't matter for deletion
    state: absent

- name: Set variables and remove others (purge)
  hashiDemo.terraform.terraform_workspace_variables:
    token: "{{ terraform_token }}"
    organization: "my-org"
    workspace: "my-workspace"
    variables:
      environment:
        value: "production"
        category: "terraform"
      debug:
        value: "false"
        category: "env"
    purge: true
    state: present
'''

RETURN = '''
variables:
  description: Information about the managed variables
  returned: always
  type: dict
  sample:
    region:
      id: "var-123456"
      key: "region"
      value: "us-west-2"
      category: "terraform"
      sensitive: false
      hcl: false
      description: "AWS region"
    AWS_ACCESS_KEY_ID:
      id: "var-789012"
      key: "AWS_ACCESS_KEY_ID"
      value: "***SENSITIVE***"
      category: "env"
      sensitive: true
      hcl: false
      description: "AWS access key"

changed:
  description: Whether any variables were changed
  returned: always
  type: bool
  sample: true

operations:
  description: List of operations performed
  returned: when state is present
  type: list
  sample:
    - operation: "created"
      variable: "region"
    - operation: "updated"
      variable: "environment"
    - operation: "deleted"
      variable: "old_variable"

msg:
  description: Human-readable message describing the action performed
  returned: always
  type: str
  sample: "Managed 3 variables for workspace 'my-workspace'"
'''

import traceback
from typing import Dict, Any, List, Optional, Tuple

from ansible.module_utils.basic import AnsibleModule

try:
    from pytfe.models import VariableCreateOptions, VariableUpdateOptions, CategoryType
    HAS_PYTFE_MODELS = True
except ImportError:
    HAS_PYTFE_MODELS = False

try:
    from ansible_collections.hashiDemo.terraform.plugins.module_utils.terraform_base import (
        TerraformBase,
        terraform_argument_spec,
        TerraformValidationError,
        TerraformOperationError
    )
except ImportError:
    # Fallback for development
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'module_utils'))
    from terraform_base import (
        TerraformBase,
        terraform_argument_spec,
        TerraformValidationError,
        TerraformOperationError
    )


class TerraformWorkspaceVariables(TerraformBase):
    """Terraform workspace variables management"""
    
    def __init__(self, module: AnsibleModule):
        super().__init__(module)
        
        # Validate inputs
        self._validate_inputs()
    
    def _validate_inputs(self):
        """Validate module parameters"""
        variables = self.module.params.get('variables', {})
        
        # Validate variables structure
        for var_name, var_config in variables.items():
            self._validate_variable_config(var_name, var_config)
    
    def _validate_variable_config(self, name: str, config: Dict[str, Any]):
        """Validate individual variable configuration"""
        if not isinstance(config, dict):
            raise TerraformValidationError(f"Variable '{name}' must be a dictionary")
        
        # Validate required fields
        if 'value' not in config:
            raise TerraformValidationError(f"Variable '{name}' must have a 'value' field")
        
        # Validate category
        category = config.get('category', 'terraform')
        if category not in ['terraform', 'env']:
            raise TerraformValidationError(
                f"Variable '{name}' category must be 'terraform' or 'env', got '{category}'"
            )
        
        # Validate HCL setting (only for terraform variables)
        if config.get('hcl', False) and category != 'terraform':
            raise TerraformValidationError(
                f"Variable '{name}' can only use HCL format with 'terraform' category"
            )
    
    def run(self):
        """Main execution method"""
        state = self.module.params['state']
        
        try:
            if state == 'present':
                result = self._ensure_present()
            elif state == 'absent':
                result = self._ensure_absent()
            else:
                self.module.fail_json(msg=f"Invalid state: {state}")
            
            self.exit_json(**result)
            
        except Exception as e:
            self._handle_tfe_exception(e, f"workspace variables {state}")
    
    def _ensure_present(self) -> Dict[str, Any]:
        """Ensure variables exist with correct values"""
        organization = self.module.params['organization']
        workspace_name = self.module.params['workspace']
        desired_variables = self.module.params.get('variables', {})
        purge = self.module.params.get('purge', False)
        
        # Validate organization and workspace
        self._validate_organization(organization)
        workspace = self._get_workspace(organization, workspace_name)
        if workspace is None:
            raise TerraformValidationError(f"Workspace '{workspace_name}' not found")
        
        # Convert Pydantic model to dict if needed
        if hasattr(workspace, 'model_dump'):
            workspace_dict = workspace.model_dump()
        elif isinstance(workspace, dict):
            workspace_dict = workspace
        else:
            workspace_dict = dict(workspace)
        
        workspace_id = workspace_dict['id']
        
        # Get current variables
        current_variables = self._get_workspace_variables(workspace_id)
        
        # Plan operations
        operations = self._plan_variable_operations(
            current_variables, desired_variables, purge
        )
        
        # Execute operations
        result_variables = {}
        operation_results = []
        
        for operation in operations:
            op_type = operation['type']
            var_name = operation['name']
            
            if op_type == 'create':
                var_data = self._create_variable(workspace_id, operation)
                result_variables[var_name] = var_data
                operation_results.append({'operation': 'created', 'variable': var_name})
                self.changed = True
                
            elif op_type == 'update':
                var_data = self._update_variable(workspace_id, operation)
                result_variables[var_name] = var_data
                operation_results.append({'operation': 'updated', 'variable': var_name})
                self.changed = True
                
            elif op_type == 'delete':
                self._delete_variable(operation['id'])
                operation_results.append({'operation': 'deleted', 'variable': var_name})
                self.changed = True
                
            elif op_type == 'unchanged':
                var_data = self._normalize_variable_data(current_variables[var_name])
                result_variables[var_name] = var_data
        
        return {
            'variables': result_variables,
            'operations': operation_results,
            'msg': f"Managed {len(operations)} variables for workspace '{workspace_name}'"
        }
    
    def _ensure_absent(self) -> Dict[str, Any]:
        """Ensure specified variables do not exist"""
        organization = self.module.params['organization']
        workspace_name = self.module.params['workspace']
        variables_to_remove = self.module.params.get('variables', {})
        
        # Validate organization and workspace
        self._validate_organization(organization)
        workspace = self._get_workspace(organization, workspace_name)
        if workspace is None:
            raise TerraformValidationError(f"Workspace '{workspace_name}' not found")
        
        # Convert Pydantic model to dict if needed
        if hasattr(workspace, 'model_dump'):
            workspace_dict = workspace.model_dump()
        elif isinstance(workspace, dict):
            workspace_dict = workspace
        else:
            workspace_dict = dict(workspace)
        
        workspace_id = workspace_dict['id']
        
        # Get current variables
        current_variables = self._get_workspace_variables(workspace_id)
        
        # Delete specified variables
        operation_results = []
        
        for var_name in variables_to_remove.keys():
            if var_name in current_variables:
                var_id = current_variables[var_name]['id']
                self._delete_variable(var_id)
                operation_results.append({'operation': 'deleted', 'variable': var_name})
                self.changed = True
            else:
                operation_results.append({'operation': 'not_found', 'variable': var_name})
        
        return {
            'variables': {},
            'operations': operation_results,
            'msg': f"Removed variables from workspace '{workspace_name}'"
        }
    
    def _get_workspace_variables(self, workspace_id: str) -> Dict[str, Dict[str, Any]]:
        """Get all variables for a workspace"""
        try:
            variables = self.client.variables.list(workspace_id=workspace_id)
            
            # Convert to dictionary keyed by variable name
            var_dict = {}
            for var in variables:
                # Convert Pydantic model to dict if needed
                if hasattr(var, 'model_dump'):
                    var_data = var.model_dump()
                else:
                    var_data = var
                var_name = var_data.get('key')
                if var_name:
                    var_dict[var_name] = var_data
            
            return var_dict
            
        except Exception as e:
            raise TerraformOperationError(f"Failed to get workspace variables: {str(e)}")
    
    def _plan_variable_operations(
        self, 
        current: Dict[str, Dict[str, Any]], 
        desired: Dict[str, Dict[str, Any]], 
        purge: bool
    ) -> List[Dict[str, Any]]:
        """Plan what operations need to be performed"""
        operations = []
        
        # Check desired variables
        for var_name, var_config in desired.items():
            if var_name in current:
                # Variable exists, check if update needed
                if self._variable_needs_update(current[var_name], var_config):
                    operations.append({
                        'type': 'update',
                        'name': var_name,
                        'id': current[var_name]['id'],
                        'config': var_config
                    })
                else:
                    operations.append({
                        'type': 'unchanged',
                        'name': var_name,
                        'id': current[var_name]['id']
                    })
            else:
                # Variable doesn't exist, create it
                operations.append({
                    'type': 'create',
                    'name': var_name,
                    'config': var_config
                })
        
        # Check for variables to purge
        if purge:
            for var_name, var_data in current.items():
                if var_name not in desired:
                    operations.append({
                        'type': 'delete',
                        'name': var_name,
                        'id': var_data['id']
                    })
        
        return operations
    
    def _variable_needs_update(
        self, 
        current: Dict[str, Any], 
        desired: Dict[str, Any]
    ) -> bool:
        """Check if variable needs to be updated"""
        current_attrs = current.get('attributes', {})
        
        # Compare all relevant attributes
        checks = [
            ('value', 'value'),
            ('category', 'category'),
            ('sensitive', 'sensitive'),
            ('description', 'description'),
            ('hcl', 'hcl')
        ]
        
        for current_key, desired_key in checks:
            current_val = current_attrs.get(current_key)
            desired_val = desired.get(desired_key)
            
            # Handle defaults
            if desired_key == 'category' and desired_val is None:
                desired_val = 'terraform'
            elif desired_key in ['sensitive', 'hcl'] and desired_val is None:
                desired_val = False
            elif desired_key == 'description' and desired_val is None:
                desired_val = ''
            
            if current_val != desired_val:
                return True
        
        return False
    
    def _create_variable(self, workspace_id: str, operation: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new variable"""
        var_name = operation['name']
        var_config = operation['config']
        
        # Prepare variable options
        options_dict = {
            'key': var_name,
            'value': str(var_config['value']),
            'category': var_config.get('category', 'terraform'),
            'sensitive': var_config.get('sensitive', False),
            'description': var_config.get('description', ''),
        }
        
        # Add HCL for terraform variables
        if options_dict['category'] == 'terraform':
            options_dict['hcl'] = var_config.get('hcl', False)
        
        try:
            options = VariableCreateOptions(**options_dict)
            variable = self.client.variables.create(
                workspace_id=workspace_id,
                options=options
            )
            return self._normalize_variable_data(variable)
            
        except Exception as e:
            raise TerraformOperationError(f"Failed to create variable '{var_name}': {str(e)}")
    
    def _update_variable(self, workspace_id: str, operation: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing variable"""
        var_id = operation['id']
        var_name = operation['name']
        var_config = operation['config']
        
        # Prepare update options
        options_dict = {
            'key': var_name,
            'value': str(var_config['value']),
            'category': var_config.get('category', 'terraform'),
            'sensitive': var_config.get('sensitive', False),
            'description': var_config.get('description', ''),
        }
        
        # Add HCL for terraform variables
        if options_dict['category'] == 'terraform':
            options_dict['hcl'] = var_config.get('hcl', False)
        
        try:
            options = VariableUpdateOptions(**options_dict)
            variable = self.client.variables.update(
                workspace_id=workspace_id,
                variable_id=var_id,
                options=options
            )
            return self._normalize_variable_data(variable)
            
        except Exception as e:
            raise TerraformOperationError(f"Failed to update variable '{var_name}': {str(e)}")
    
    def _delete_variable(self, var_id: str):
        """Delete a variable"""
        try:
            self.client.variables.delete(variable_id=var_id)
        except Exception as e:
            raise TerraformOperationError(f"Failed to delete variable: {str(e)}")
    
    def _normalize_variable_data(self, variable) -> Dict[str, Any]:
        """Normalize variable data for consistent output"""
        # Convert Pydantic model to dictionary if needed
        if hasattr(variable, 'model_dump'):
            var_dict = variable.model_dump()
        elif isinstance(variable, dict):
            var_dict = variable
        else:
            var_dict = dict(variable)
        
        # Mask sensitive values
        value = var_dict.get('value', '')
        if var_dict.get('sensitive', False):
            value = '***SENSITIVE***'
        
        return {
            'id': var_dict.get('id'),
            'key': var_dict.get('key'),
            'value': value,
            'category': var_dict.get('category'),
            'sensitive': var_dict.get('sensitive', False),
            'hcl': var_dict.get('hcl', False),
            'description': var_dict.get('description', '')
        }


def main():
    """Main function"""
    # Define argument specification
    argument_spec = terraform_argument_spec()
    argument_spec.update(dict(
        workspace=dict(type='str', required=True),
        variables=dict(
            type='dict',
            required=True
        ),
        state=dict(type='str', choices=['present', 'absent'], default='present'),
        purge=dict(type='bool', default=False)
    ))
    
    # Create module
    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=False
    )
    
    # Create and run variables manager
    variables_manager = TerraformWorkspaceVariables(module)
    variables_manager.run()


if __name__ == '__main__':
    main()