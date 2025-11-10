#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2025, Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = '''
---
module: terraform_workspace
short_description: Manage Terraform Enterprise/Cloud workspaces
version_added: "1.0.0"
description:
  - Create, update, or delete Terraform Enterprise/Cloud workspaces
  - Manage workspace configuration including VCS integration, execution mode, and variables
  - Supports both Terraform Enterprise and Terraform Cloud

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
      - Name of the workspace
    type: str
    required: true
  state:
    description:
      - Whether the workspace should exist or not
    type: str
    choices: ['present', 'absent']
    default: present
  description:
    description:
      - Description of the workspace
    type: str
    default: ''
  terraform_version:
    description:
      - Terraform version to use for this workspace
      - If not specified, uses the organization default
    type: str
  working_directory:
    description:
      - Working directory for Terraform operations
    type: str
    default: ''
  auto_apply:
    description:
      - Whether to automatically apply changes
    type: bool
    default: false
  file_triggers_enabled:
    description:
      - Whether file triggers are enabled
    type: bool
    default: true
  queue_all_runs:
    description:
      - Whether to queue all runs
    type: bool
    default: false
  speculative_enabled:
    description:
      - Whether speculative runs are enabled
    type: bool
    default: true
  trigger_prefixes:
    description:
      - List of repository-root-relative paths to trigger runs
    type: list
    elements: str
    default: []
  execution_mode:
    description:
      - Execution mode for the workspace
    type: str
    choices: ['remote', 'local', 'agent']
    default: remote
  tag_names:
    description:
      - List of tag names to apply to the workspace
    type: list
    elements: str
    default: []
  project:
    description:
      - Project to assign the workspace to
    type: str
  vcs_repo:
    description:
      - VCS repository configuration
    type: dict
    suboptions:
      identifier:
        description:
          - Repository identifier (e.g., 'organization/repository')
        type: str
        required: true
      branch:
        description:
          - Repository branch to use
        type: str
        default: ''
      oauth_token_id:
        description:
          - OAuth token ID for VCS integration
        type: str
        required: true
      ingress_submodules:
        description:
          - Whether to include submodules
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

notes:
  - Requires a valid Terraform Enterprise/Cloud API token
  - The token should have appropriate permissions for workspace management
  - Organization must exist before creating workspaces
'''

EXAMPLES = '''
- name: Create a basic workspace
  hashiDemo.terraform.terraform_workspace:
    token: "{{ terraform_token }}"
    organization: "my-org"
    name: "my-workspace"
    description: "Development environment workspace"
    state: present

- name: Create workspace with VCS integration
  hashiDemo.terraform.terraform_workspace:
    token: "{{ terraform_token }}"
    organization: "my-org"
    name: "production-workspace"
    description: "Production environment"
    terraform_version: "1.5.0"
    auto_apply: true
    vcs_repo:
      identifier: "myorg/infrastructure"
      branch: "main"
      oauth_token_id: "ot-123456789"
      ingress_submodules: false
    state: present

- name: Create workspace with advanced configuration
  hashiDemo.terraform.terraform_workspace:
    token: "{{ terraform_token }}"
    organization: "my-org"
    name: "staging-workspace"
    description: "Staging environment"
    terraform_version: "1.5.0"
    working_directory: "environments/staging"
    auto_apply: false
    file_triggers_enabled: true
    queue_all_runs: false
    speculative_enabled: true
    trigger_prefixes:
      - "modules/"
      - "environments/staging/"
    execution_mode: "remote"
    tag_names:
      - "staging"
      - "automated"
    state: present

- name: Update existing workspace
  hashiDemo.terraform.terraform_workspace:
    token: "{{ terraform_token }}"
    organization: "my-org"
    name: "existing-workspace"
    description: "Updated description"
    auto_apply: true
    terraform_version: "1.6.0"
    state: present

- name: Delete workspace
  hashiDemo.terraform.terraform_workspace:
    token: "{{ terraform_token }}"
    organization: "my-org"
    name: "old-workspace"
    state: absent
'''

RETURN = '''
workspace:
  description: Information about the workspace
  returned: always
  type: dict
  sample:
    id: "ws-123456789"
    name: "my-workspace"
    organization: "my-org"
    description: "Development environment workspace"
    terraform_version: "1.5.0"
    working_directory: ""
    auto_apply: false
    file_triggers_enabled: true
    queue_all_runs: false
    speculative_enabled: true
    trigger_prefixes: []
    execution_mode: "remote"
    tag_names: ["development"]
    created_at: "2025-01-01T00:00:00Z"
    updated_at: "2025-01-01T00:00:00Z"
    locked: false
    resource_count: 5

changed:
  description: Whether the workspace was changed
  returned: always
  type: bool
  sample: true

operation:
  description: The operation that was performed
  returned: when state is present
  type: str
  sample: "created"

changes:
  description: Dictionary of fields that were changed
  returned: when workspace is updated
  type: dict
  sample:
    auto_apply: true
    terraform_version: "1.6.0"
    description: "Updated description"

msg:
  description: Human-readable message describing the action performed
  returned: always
  type: str
  sample: "Workspace 'my-workspace' created successfully"
'''

import traceback
from typing import Dict, Any, Optional

from ansible.module_utils.basic import AnsibleModule

try:
    from pytfe.models import WorkspaceCreateOptions, WorkspaceUpdateOptions, VCSRepoOptions
    HAS_PYTFE_MODELS = True
except ImportError:
    HAS_PYTFE_MODELS = False

try:
    from ansible_collections.hashiDemo.terraform.plugins.module_utils.terraform_base import (
        TerraformBase,
        workspace_argument_spec,
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
        workspace_argument_spec,
        TerraformValidationError,
        TerraformOperationError
    )


class TerraformWorkspace(TerraformBase):
    """Terraform workspace management"""
    
    def __init__(self, module: AnsibleModule):
        super().__init__(module)
        
        # Validate inputs
        self._validate_inputs()
    
    def _validate_inputs(self):
        """Validate module parameters"""
        name = self.module.params['name']
        terraform_version = self.module.params.get('terraform_version')
        
        # Validate workspace name
        self._validate_workspace_name(name)
        
        # Validate Terraform version if provided
        if terraform_version:
            self._validate_terraform_version(terraform_version)
        
        # Validate VCS repo configuration if provided
        vcs_repo = self.module.params.get('vcs_repo')
        if vcs_repo:
            self._validate_vcs_repo(vcs_repo)
    
    def _validate_vcs_repo(self, vcs_repo: Dict[str, Any]):
        """Validate VCS repository configuration"""
        required_fields = ['identifier', 'oauth_token_id']
        for field in required_fields:
            if not vcs_repo.get(field):
                raise TerraformValidationError(f"VCS repo field '{field}' is required")
        
        # Validate identifier format (should be org/repo)
        identifier = vcs_repo['identifier']
        if '/' not in identifier:
            raise TerraformValidationError(
                "VCS repo identifier should be in format 'organization/repository'"
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
            self._handle_tfe_exception(e, f"workspace {state}")
    
    def _ensure_present(self) -> Dict[str, Any]:
        """Ensure workspace exists with correct configuration"""
        organization = self.module.params['organization']
        workspace_name = self.module.params['name']
        
        # Validate organization exists
        self._validate_organization(organization)
        
        # Check if workspace exists
        current_workspace = self._get_workspace(organization, workspace_name)
        
        if current_workspace is None:
            # Create new workspace
            return self._create_workspace()
        else:
            # Update existing workspace if needed
            return self._update_workspace(current_workspace)
    
    def _ensure_absent(self) -> Dict[str, Any]:
        """Ensure workspace does not exist"""
        organization = self.module.params['organization']
        workspace_name = self.module.params['name']
        
        # Validate organization exists
        self._validate_organization(organization)
        
        # Check if workspace exists
        current_workspace = self._get_workspace(organization, workspace_name)
        
        if current_workspace is None:
            return {
                'workspace': None,
                'operation': 'none',
                'msg': f"Workspace '{workspace_name}' already absent"
            }
        else:
            return self._delete_workspace(current_workspace)
    
    def _create_workspace(self) -> Dict[str, Any]:
        """Create a new workspace"""
        organization = self.module.params['organization']
        name = self.module.params['name']
        
        # Prepare workspace options
        options_dict = {
            'name': name,
            'type': 'workspaces'
        }
        
        # Add optional parameters if provided
        if self.module.params.get('description'):
            options_dict['description'] = self.module.params['description']
        if self.module.params.get('auto_apply') is not None:
            options_dict['auto_apply'] = self.module.params['auto_apply']
        if self.module.params.get('terraform_version'):
            options_dict['terraform_version'] = self.module.params['terraform_version']
        if self.module.params.get('working_directory'):
            options_dict['working_directory'] = self.module.params['working_directory']
        if self.module.params.get('execution_mode'):
            options_dict['execution_mode'] = self.module.params['execution_mode']
        if self.module.params.get('allow_destroy_plan') is not None:
            options_dict['allow_destroy_plan'] = self.module.params['allow_destroy_plan']
        if self.module.params.get('queue_all_runs') is not None:
            options_dict['queue_all_runs'] = self.module.params['queue_all_runs']
        if self.module.params.get('speculative_enabled') is not None:
            options_dict['speculative_enabled'] = self.module.params['speculative_enabled']
        
        # Handle VCS repo if specified
        vcs_repo = self.module.params.get('vcs_repo')
        if vcs_repo:
            vcs_options_dict = {
                'oauth_token_id': vcs_repo.get('oauth_token_id'),
                'identifier': vcs_repo.get('identifier')
            }
            if vcs_repo.get('branch'):
                vcs_options_dict['branch'] = vcs_repo['branch']
            if vcs_repo.get('ingress_submodules') is not None:
                vcs_options_dict['ingress_submodules'] = vcs_repo['ingress_submodules']
            
            options_dict['vcs_repo'] = VCSRepoOptions(**vcs_options_dict)
        
        try:
            # Create WorkspaceCreateOptions and workspace
            options = WorkspaceCreateOptions(**options_dict)
            workspace = self.client.workspaces.create(
                organization=organization,
                options=options
            )
            
            self.changed = True
            
            return {
                'workspace': self._normalize_workspace_data(workspace),
                'operation': 'created',
                'msg': f"Workspace '{name}' created successfully"
            }
            
        except Exception as e:
            raise TerraformOperationError(f"Failed to create workspace: {str(e)}")
    
    def _update_workspace(self, current_workspace: Dict[str, Any]) -> Dict[str, Any]:
        """Update existing workspace if changes are needed"""
        current_data = self._normalize_workspace_data(current_workspace)
        desired_data = self._prepare_desired_state()
        
        # Compare current and desired state
        changes = self._compare_workspace_attributes(current_data, desired_data)
        
        if not changes:
            return {
                'workspace': current_data,
                'operation': 'none',
                'msg': f"Workspace '{self.module.params['name']}' already in desired state"
            }
        
        # Prepare update options
        options_dict = {
            'name': self.module.params['name']  # name is required
        }
        for key, value in changes.items():
            options_dict[key] = value
        
        # Handle VCS repo updates
        vcs_repo = self.module.params.get('vcs_repo')
        if vcs_repo:
            vcs_options_dict = {
                'oauth_token_id': vcs_repo.get('oauth_token_id'),
                'identifier': vcs_repo.get('identifier')
            }
            if vcs_repo.get('branch'):
                vcs_options_dict['branch'] = vcs_repo['branch']
            if vcs_repo.get('ingress_submodules') is not None:
                vcs_options_dict['ingress_submodules'] = vcs_repo['ingress_submodules']
            
            options_dict['vcs_repo'] = VCSRepoOptions(**vcs_options_dict)
        
        try:
            # Update workspace
            organization = self.module.params['organization']
            workspace_name = self.module.params['name']
            
            options = WorkspaceUpdateOptions(**options_dict)
            updated_workspace = self.client.workspaces.update(
                organization=organization,
                workspace=workspace_name,
                options=options
            )
            
            self.changed = True
            
            return {
                'workspace': self._normalize_workspace_data(updated_workspace),
                'operation': 'updated',
                'msg': f"Workspace '{workspace_name}' updated successfully",
                'changes': changes
            }
            
        except Exception as e:
            raise TerraformOperationError(f"Failed to update workspace: {str(e)}")
    
    def _delete_workspace(self, workspace: Dict[str, Any]) -> Dict[str, Any]:
        """Delete existing workspace"""
        organization = self.module.params['organization']
        workspace_name = self.module.params['name']
        workspace_data = self._normalize_workspace_data(workspace)
        
        try:
            # Delete workspace
            self.client.workspaces.delete(
                organization=organization,
                workspace=workspace_name
            )
            
            self.changed = True
            
            return {
                'workspace': workspace_data,
                'operation': 'deleted',
                'msg': f"Workspace '{workspace_name}' deleted successfully"
            }
            
        except Exception as e:
            raise TerraformOperationError(f"Failed to delete workspace: {str(e)}")
    
    def _normalize_workspace_data(self, workspace) -> Dict[str, Any]:
        """Normalize workspace data for output"""
        # Convert Pydantic model to dictionary if needed
        if hasattr(workspace, 'model_dump'):
            ws_dict = workspace.model_dump()
        elif isinstance(workspace, dict):
            ws_dict = workspace
        else:
            ws_dict = dict(workspace)
        
        # Return normalized data
        return {
            'id': ws_dict.get('id'),
            'name': ws_dict.get('name'),
            'description': ws_dict.get('description'),
            'auto_apply': ws_dict.get('auto_apply'),
            'terraform_version': ws_dict.get('terraform_version'),
            'working_directory': ws_dict.get('working_directory'),
            'execution_mode': ws_dict.get('execution_mode'),
            'locked': ws_dict.get('locked'),
            'created_at': ws_dict.get('created_at'),
            'updated_at': ws_dict.get('updated_at'),
            'resource_count': ws_dict.get('resource_count'),
            'permissions': ws_dict.get('permissions', {}),
        }
    
    def _prepare_workspace_attributes(self) -> Dict[str, Any]:
        """Prepare workspace attributes for API call"""
        attributes = {
            'name': self.module.params['name'],
            'description': self.module.params.get('description', ''),
            'auto-apply': self.module.params.get('auto_apply', False),
            'file-triggers-enabled': self.module.params.get('file_triggers_enabled', True),
            'queue-all-runs': self.module.params.get('queue_all_runs', False),
            'speculative-enabled': self.module.params.get('speculative_enabled', True),
            'execution-mode': self.module.params.get('execution_mode', 'remote'),
        }
        
        # Add optional attributes
        terraform_version = self.module.params.get('terraform_version')
        if terraform_version:
            attributes['terraform-version'] = terraform_version
        
        working_directory = self.module.params.get('working_directory')
        if working_directory:
            attributes['working-directory'] = working_directory
        
        trigger_prefixes = self.module.params.get('trigger_prefixes', [])
        if trigger_prefixes:
            attributes['trigger-prefixes'] = trigger_prefixes
        
        tag_names = self.module.params.get('tag_names', [])
        if tag_names:
            attributes['tag-names'] = tag_names
        
        return attributes
    
    def _prepare_vcs_repo_attributes(self, vcs_repo: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare VCS repository attributes"""
        return {
            'identifier': vcs_repo['identifier'],
            'branch': vcs_repo.get('branch', ''),
            'oauth-token-id': vcs_repo['oauth_token_id'],
            'ingress-submodules': vcs_repo.get('ingress_submodules', False)
        }
    
    def _prepare_relationships(self) -> Optional[Dict[str, Any]]:
        """Prepare workspace relationships (e.g., project)"""
        relationships = {}
        
        project = self.module.params.get('project')
        if project:
            relationships['project'] = {
                'data': {
                    'type': 'projects',
                    'id': project
                }
            }
        
        return relationships if relationships else None
    
    def _prepare_desired_state(self) -> Dict[str, Any]:
        """Prepare desired state for comparison"""
        return {
            'name': self.module.params['name'],
            'description': self.module.params.get('description', ''),
            'terraform_version': self.module.params.get('terraform_version'),
            'working_directory': self.module.params.get('working_directory', ''),
            'auto_apply': self.module.params.get('auto_apply', False),
            'file_triggers_enabled': self.module.params.get('file_triggers_enabled', True),
            'queue_all_runs': self.module.params.get('queue_all_runs', False),
            'speculative_enabled': self.module.params.get('speculative_enabled', True),
            'trigger_prefixes': self.module.params.get('trigger_prefixes', []),
            'execution_mode': self.module.params.get('execution_mode', 'remote'),
            'tag_names': self.module.params.get('tag_names', [])
        }


def main():
    """Main function"""
    # Define argument specification
    argument_spec = workspace_argument_spec()
    argument_spec.update(dict(
        state=dict(type='str', choices=['present', 'absent'], default='present')
    ))
    
    # Create module
    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=False
    )
    
    # Create and run workspace manager
    workspace_manager = TerraformWorkspace(module)
    workspace_manager.run()


if __name__ == '__main__':
    main()