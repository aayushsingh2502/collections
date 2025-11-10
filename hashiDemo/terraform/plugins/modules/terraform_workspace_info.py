#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2025, Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = '''
---
module: terraform_workspace_info
short_description: Get information about Terraform Enterprise/Cloud workspaces
version_added: "1.0.0"
description:
  - Retrieve information about one or more workspaces
  - Get workspace configuration, status, and metadata
  - List all workspaces in an organization

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
  name:
    description:
      - Name of specific workspace to get info for
      - If not provided, returns info for all workspaces
    type: str
  include_variables:
    description:
      - Whether to include workspace variables in the response
    type: bool
    default: false
  include_runs:
    description:
      - Whether to include recent runs information
    type: bool
    default: false
  runs_limit:
    description:
      - Maximum number of recent runs to include
      - Only applicable when include_runs is true
    type: int
    default: 5
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
- name: Get info for a specific workspace
  hashiDemo.terraform.terraform_workspace_info:
    token: "{{ terraform_token }}"
    organization: "my-org"
    name: "production"
  register: workspace_info

- name: Get info for all workspaces
  hashiDemo.terraform.terraform_workspace_info:
    token: "{{ terraform_token }}"
    organization: "my-org"
  register: all_workspaces

- name: Get workspace info with variables and runs
  hashiDemo.terraform.terraform_workspace_info:
    token: "{{ terraform_token }}"
    organization: "my-org"
    name: "production"
    include_variables: true
    include_runs: true
    runs_limit: 10
  register: detailed_info

- name: Display workspace information
  debug:
    msg: |
      Workspace: {{ workspace_info.workspace.name }}
      Status: {{ workspace_info.workspace.locked | ternary('Locked', 'Unlocked') }}
      Terraform Version: {{ workspace_info.workspace.terraform_version }}
      Resource Count: {{ workspace_info.workspace.resource_count }}
'''

RETURN = '''
workspace:
  description: Information about the requested workspace
  returned: when name is specified
  type: dict
  sample:
    id: "ws-123456789"
    name: "production"
    organization: "my-org"
    description: "Production environment"
    terraform_version: "1.5.0"
    working_directory: ""
    auto_apply: true
    file_triggers_enabled: true
    queue_all_runs: false
    speculative_enabled: true
    trigger_prefixes: []
    execution_mode: "remote"
    tag_names: ["production", "critical"]
    created_at: "2025-01-01T00:00:00Z"
    updated_at: "2025-01-01T00:00:00Z"
    locked: false
    resource_count: 25
    latest_change_at: "2025-01-01T12:00:00Z"
    variables:
      - key: "region"
        value: "us-west-2"
        category: "terraform"
        sensitive: false
    runs:
      - id: "run-123"
        status: "applied"
        message: "Deploy infrastructure"
        created_at: "2025-01-01T10:00:00Z"

workspaces:
  description: List of all workspaces in the organization
  returned: when name is not specified
  type: list
  elements: dict
  sample:
    - id: "ws-123456789"
      name: "production"
      description: "Production environment"
      terraform_version: "1.5.0"
      locked: false
      resource_count: 25
    - id: "ws-987654321"
      name: "staging"
      description: "Staging environment"
      terraform_version: "1.5.0"
      locked: false
      resource_count: 10

msg:
  description: Human-readable message describing the action performed
  returned: always
  type: str
  sample: "Retrieved information for workspace 'production'"
'''

import traceback
from typing import Dict, Any, List, Optional

from ansible.module_utils.basic import AnsibleModule

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


class TerraformWorkspaceInfo(TerraformBase):
    """Terraform workspace information retrieval"""
    
    def __init__(self, module: AnsibleModule):
        super().__init__(module)
    
    def run(self):
        """Main execution method"""
        try:
            workspace_name = self.module.params.get('name')
            
            if workspace_name:
                result = self._get_single_workspace_info(workspace_name)
            else:
                result = self._get_all_workspaces_info()
            
            self.exit_json(**result)
            
        except Exception as e:
            self._handle_tfe_exception(e, "workspace info retrieval")
    
    def _get_single_workspace_info(self, workspace_name: str) -> Dict[str, Any]:
        """Get information for a single workspace"""
        organization = self.module.params['organization']
        include_variables = self.module.params.get('include_variables', False)
        include_runs = self.module.params.get('include_runs', False)
        
        # Validate organization
        self._validate_organization(organization)
        
        # Get workspace
        workspace = self._get_workspace(organization, workspace_name)
        if workspace is None:
            self.module.fail_json(msg=f"Workspace '{workspace_name}' not found")
        
        # Convert Pydantic model to dict if needed
        if hasattr(workspace, 'model_dump'):
            workspace_dict = workspace.model_dump()
        elif isinstance(workspace, dict):
            workspace_dict = workspace
        else:
            workspace_dict = dict(workspace)
        
        workspace_data = self._normalize_workspace_data(workspace_dict)
        
        # Add variables if requested
        if include_variables:
            variables = self._get_workspace_variables_info(workspace_dict['id'])
            workspace_data['variables'] = variables
        
        # Add runs if requested
        if include_runs:
            runs = self._get_workspace_runs_info(workspace_dict['id'])
            workspace_data['runs'] = runs
        
        return {
            'workspace': workspace_data,
            'msg': f"Retrieved information for workspace '{workspace_name}'"
        }
    
    def _get_all_workspaces_info(self) -> Dict[str, Any]:
        """Get information for all workspaces in the organization"""
        organization = self.module.params['organization']
        include_variables = self.module.params.get('include_variables', False)
        include_runs = self.module.params.get('include_runs', False)
        
        # Validate organization
        self._validate_organization(organization)
        
        try:
            # List all workspaces
            workspaces = self.client.workspaces.list(organization=organization)
            
            workspaces_data = []
            for workspace in workspaces:
                # Convert Pydantic model to dict if needed
                if hasattr(workspace, 'model_dump'):
                    workspace_dict = workspace.model_dump()
                elif isinstance(workspace, dict):
                    workspace_dict = workspace
                else:
                    workspace_dict = dict(workspace)
                
                workspace_data = self._normalize_workspace_data(workspace_dict)
                
                # Add variables if requested
                if include_variables:
                    variables = self._get_workspace_variables_info(workspace_dict['id'])
                    workspace_data['variables'] = variables
                
                # Add runs if requested
                if include_runs:
                    runs = self._get_workspace_runs_info(workspace_dict['id'])
                    workspace_data['runs'] = runs
                
                workspaces_data.append(workspace_data)
            
            return {
                'workspaces': workspaces_data,
                'msg': f"Retrieved information for {len(workspaces_data)} workspaces"
            }
            
        except Exception as e:
            raise TerraformOperationError(f"Failed to list workspaces: {str(e)}")
    
    def _get_workspace_variables_info(self, workspace_id: str) -> List[Dict[str, Any]]:
        """Get variables information for a workspace"""
        try:
            variables = self.client.variables.list(workspace_id=workspace_id)
            
            variables_data = []
            for var in variables:
                # Convert Pydantic model to dict if needed
                if hasattr(var, 'model_dump'):
                    var_dict = var.model_dump()
                elif isinstance(var, dict):
                    var_dict = var
                else:
                    var_dict = dict(var)
                
                var_data = self._normalize_variable_info(var_dict)
                variables_data.append(var_data)
            
            return variables_data
            
        except Exception as e:
            # Don't fail the entire operation if variables can't be retrieved
            return []
    
    def _get_workspace_runs_info(self, workspace_id: str) -> List[Dict[str, Any]]:
        """Get recent runs information for a workspace"""
        try:
            runs_limit = self.module.params.get('runs_limit', 5)
            runs = self.client.runs.list(
                workspace_id=workspace_id,
                page_size=runs_limit
            )
            
            runs_data = []
            for run in runs:
                run_data = self._normalize_run_info(run)
                runs_data.append(run_data)
            
            return runs_data
            
        except Exception as e:
            # Don't fail the entire operation if runs can't be retrieved
            return []
    
    def _normalize_variable_info(self, variable: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize variable information for output"""
        # pytfe returns flat structure, not nested attributes
        # Handle both formats for compatibility
        if 'attributes' in variable:
            # Old format with nested attributes
            attributes = variable.get('attributes', {})
            var_id = variable.get('id')
            key = attributes.get('key')
            value = attributes.get('value', '')
            category = attributes.get('category')
            sensitive = attributes.get('sensitive', False)
            hcl = attributes.get('hcl', False)
            description = attributes.get('description', '')
        else:
            # pytfe flat format
            var_id = variable.get('id')
            key = variable.get('key')
            value = variable.get('value', '')
            category = variable.get('category')
            sensitive = variable.get('sensitive', False)
            hcl = variable.get('hcl', False)
            description = variable.get('description', '')
        
        # Mask sensitive values
        if sensitive:
            value = '***SENSITIVE***'
        
        return {
            'id': var_id,
            'key': key,
            'value': value,
            'category': category,
            'sensitive': sensitive,
            'hcl': hcl,
            'description': description
        }
    
    def _normalize_run_info(self, run: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize run information for output"""
        attributes = run.get('attributes', {})
        
        return {
            'id': run.get('id'),
            'status': attributes.get('status'),
            'message': attributes.get('message'),
            'created_at': attributes.get('created-at'),
            'plan_only': attributes.get('plan-only', False),
            'auto_apply': attributes.get('auto-apply'),
            'has_changes': attributes.get('has-changes'),
            'target_addrs': attributes.get('target-addrs', []),
            'replace_addrs': attributes.get('replace-addrs', [])
        }


def main():
    """Main function"""
    # Define argument specification
    argument_spec = terraform_argument_spec()
    argument_spec.update(dict(
        name=dict(type='str'),
        include_variables=dict(type='bool', default=False),
        include_runs=dict(type='bool', default=False),
        runs_limit=dict(type='int', default=5)
    ))
    
    # Create module
    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True
    )
    
    # Create and run workspace info manager
    info_manager = TerraformWorkspaceInfo(module)
    info_manager.run()


if __name__ == '__main__':
    main()