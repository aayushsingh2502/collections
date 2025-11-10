#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2025, Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

import json
import traceback
from typing import Dict, Any, Optional, List, Union

try:
    from pytfe import TFEClient, TFEConfig
    HAS_PYTFE = True
except ImportError:
    HAS_PYTFE = False
    TFEClient = None
    TFEConfig = None

from ansible.module_utils.basic import AnsibleModule, missing_required_lib


class TerraformBaseError(Exception):
    """Base exception for Terraform operations"""
    pass


class TerraformAuthError(TerraformBaseError):
    """Authentication related errors"""
    pass


class TerraformValidationError(TerraformBaseError):
    """Validation related errors"""
    pass


class TerraformOperationError(TerraformBaseError):
    """Operation related errors"""
    pass


class TerraformBase:
    """Base class for Terraform Enterprise/Cloud operations"""
    
    def __init__(self, module: AnsibleModule):
        self.module = module
        self.changed = False
        self.client = None
        
        # Check if python-tfe is available
        if not HAS_PYTFE:
            self.module.fail_json(
                msg=missing_required_lib("pytfe"),
                exception=traceback.format_exc()
            )
        
        # Initialize client
        self._init_client()
    
    def _init_client(self):
        """Initialize TFE client with authentication"""
        token = self.module.params.get('token')
        url = self.module.params.get('url', 'https://app.terraform.io')
        
        if not token:
            self.module.fail_json(msg="Terraform API token is required")
        
        try:
            # Create TFEConfig with token and address
            config = TFEConfig(token=token, address=url)
            self.client = TFEClient(config=config)
            # Test authentication by getting account details
            self._validate_authentication()
        except Exception as e:
            self.module.fail_json(
                msg=f"Failed to initialize Terraform client: {str(e)}",
                exception=traceback.format_exc()
            )
    
    def _validate_authentication(self):
        """Validate that the provided token is valid"""
        try:
            # Try to list organizations to validate token
            # This is a simple API call that will fail if token is invalid
            orgs = self.client.organizations.list()
            if orgs is None:
                raise TerraformAuthError("Invalid token or unable to authenticate")
        except Exception as e:
            error_msg = str(e).lower()
            if '401' in error_msg or 'unauthorized' in error_msg:
                raise TerraformAuthError("Invalid or expired API token")
            elif '403' in error_msg or 'forbidden' in error_msg:
                raise TerraformAuthError("Insufficient permissions for API token")
            else:
                raise TerraformAuthError(f"Authentication failed: {str(e)}")
    
    def _validate_organization(self, organization: str) -> Dict[str, Any]:
        """Validate that the organization exists and user has access"""
        try:
            org = self.client.organizations.read(name=organization)
            if not org:
                raise TerraformValidationError(f"Organization '{organization}' not found")
            return org
        except TerraformValidationError:
            raise
        except Exception as e:
            error_msg = str(e).lower()
            if '404' in error_msg or 'not found' in error_msg:
                raise TerraformValidationError(f"Organization '{organization}' not found")
            elif '403' in error_msg or 'forbidden' in error_msg:
                raise TerraformValidationError(f"Access denied to organization '{organization}'")
            else:
                raise TerraformValidationError(f"Failed to validate organization: {str(e)}")
    
    def _get_workspace(self, organization: str, workspace_name: str) -> Optional[Dict[str, Any]]:
        """Get workspace if it exists"""
        try:
            workspace = self.client.workspaces.read(
                organization=organization,
                workspace=workspace_name
            )
            return workspace
        except Exception as e:
            error_msg = str(e).lower()
            if '404' in error_msg or 'not found' in error_msg:
                return None
            else:
                raise TerraformOperationError(f"Failed to get workspace: {str(e)}")
    
    def _workspace_exists(self, organization: str, workspace_name: str) -> bool:
        """Check if workspace exists"""
        return self._get_workspace(organization, workspace_name) is not None
    
    def _validate_workspace_name(self, name: str):
        """Validate workspace name format"""
        if not name:
            raise TerraformValidationError("Workspace name cannot be empty")
        
        # Terraform workspace names must be valid
        import re
        if not re.match(r'^[a-zA-Z0-9_-]+$', name):
            raise TerraformValidationError(
                "Workspace name can only contain letters, numbers, hyphens, and underscores"
            )
        
        if len(name) > 90:
            raise TerraformValidationError("Workspace name must be 90 characters or less")
    
    def _validate_terraform_version(self, version: str):
        """Validate Terraform version format"""
        if not version:
            return
        
        import re
        if not re.match(r'^\d+\.\d+\.\d+$', version):
            raise TerraformValidationError(
                "Terraform version must be in format X.Y.Z (e.g., 1.0.0)"
            )
    
    def _handle_tfe_exception(self, e: Exception, operation: str):
        """Handle TFE exceptions and convert to appropriate error messages"""
        error_msg = str(e).lower()
        
        # Check for HTTP error codes in the error message
        if '401' in error_msg or 'unauthorized' in error_msg:
            self.module.fail_json(msg=f"Authentication failed during {operation}")
        elif '403' in error_msg or 'forbidden' in error_msg:
            self.module.fail_json(msg=f"Insufficient permissions for {operation}")
        elif '404' in error_msg or 'not found' in error_msg:
            self.module.fail_json(msg=f"Resource not found during {operation}")
        elif '409' in error_msg or 'conflict' in error_msg:
            self.module.fail_json(msg=f"Conflict during {operation}: Resource already exists or is locked")
        elif '422' in error_msg or 'validation' in error_msg:
            self.module.fail_json(msg=f"Validation error during {operation}: {str(e)}")
        elif isinstance(e, (TerraformAuthError, TerraformValidationError, TerraformOperationError)):
            self.module.fail_json(msg=f"Error during {operation}: {str(e)}")
        else:
            self.module.fail_json(
                msg=f"Unexpected error during {operation}: {str(e)}",
                exception=traceback.format_exc()
            )
    
    def _normalize_workspace_data(self, workspace: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize workspace data for consistent output"""
        # Handle both pytfe flat format and old nested format
        if 'attributes' in workspace:
            # Old nested format
            attributes = workspace.get('attributes', {})
            relationships = workspace.get('relationships', {})
            
            # Extract organization name from relationships
            org_data = relationships.get('organization', {}).get('data', {})
            organization = org_data.get('id', '')
            
            # Extract project name if available
            project_data = relationships.get('project', {}).get('data', {})
            project = project_data.get('id', '')
            
            normalized = {
                'id': workspace.get('id'),
                'name': attributes.get('name'),
                'organization': organization,
                'project': project,
                'description': attributes.get('description', ''),
                'terraform_version': attributes.get('terraform-version'),
                'working_directory': attributes.get('working-directory', ''),
                'auto_apply': attributes.get('auto-apply', False),
                'file_triggers_enabled': attributes.get('file-triggers-enabled', True),
                'queue_all_runs': attributes.get('queue-all-runs', False),
                'speculative_enabled': attributes.get('speculative-enabled', True),
                'trigger_prefixes': attributes.get('trigger-prefixes', []),
                'source_name': attributes.get('source-name', ''),
                'source_url': attributes.get('source-url', ''),
                'created_at': attributes.get('created-at'),
                'updated_at': attributes.get('updated-at'),
                'resource_count': attributes.get('resource-count', 0),
                'latest_change_at': attributes.get('latest-change-at'),
                'locked': attributes.get('locked', False),
                'execution_mode': attributes.get('execution-mode', 'remote'),
                'vcs_repo': self._extract_vcs_repo(attributes.get('vcs-repo')),
                'tag_names': attributes.get('tag-names', [])
            }
        else:
            # pytfe flat format (keys use underscores, not hyphens)
            normalized = {
                'id': workspace.get('id'),
                'name': workspace.get('name'),
                'organization': workspace.get('organization'),
                'project': workspace.get('project'),
                'description': workspace.get('description', ''),
                'terraform_version': workspace.get('terraform_version'),
                'working_directory': workspace.get('working_directory', ''),
                'auto_apply': workspace.get('auto_apply', False),
                'file_triggers_enabled': workspace.get('file_triggers_enabled', True),
                'queue_all_runs': workspace.get('queue_all_runs', False),
                'speculative_enabled': workspace.get('speculative_enabled', True),
                'trigger_prefixes': workspace.get('trigger_prefixes', []),
                'source_name': workspace.get('source_name', ''),
                'source_url': workspace.get('source_url', ''),
                'created_at': workspace.get('created_at'),
                'updated_at': workspace.get('updated_at'),
                'resource_count': workspace.get('resource_count', 0),
                'latest_change_at': workspace.get('latest_change_at'),
                'locked': workspace.get('locked', False),
                'execution_mode': workspace.get('execution_mode', 'remote'),
                'vcs_repo': workspace.get('vcs_repo'),
                'tag_names': workspace.get('tag_names', []),
                'permissions': workspace.get('permissions')
            }
        
        return {k: v for k, v in normalized.items() if v is not None}
    
    def _extract_vcs_repo(self, vcs_repo: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Extract and normalize VCS repository information"""
        if not vcs_repo:
            return None
        
        return {
            'identifier': vcs_repo.get('identifier'),
            'branch': vcs_repo.get('branch'),
            'oauth_token_id': vcs_repo.get('oauth-token-id'),
            'ingress_submodules': vcs_repo.get('ingress-submodules', False)
        }
    
    def _compare_workspace_attributes(self, current: Dict[str, Any], desired: Dict[str, Any]) -> Dict[str, Any]:
        """Compare current workspace attributes with desired state and return differences"""
        changes = {}
        
        # List of attributes that can be updated
        updatable_attrs = [
            'description', 'terraform_version', 'working_directory', 'auto_apply',
            'file_triggers_enabled', 'queue_all_runs', 'speculative_enabled',
            'trigger_prefixes', 'execution_mode', 'tag_names'
        ]
        
        for attr in updatable_attrs:
            if attr in desired and desired[attr] != current.get(attr):
                changes[attr] = desired[attr]
        
        return changes
    
    def exit_json(self, **kwargs):
        """Exit with JSON response"""
        kwargs['changed'] = self.changed
        self.module.exit_json(**kwargs)
    
    def fail_json(self, **kwargs):
        """Exit with failure"""
        self.module.fail_json(**kwargs)


def terraform_argument_spec():
    """Common argument specifications for Terraform modules"""
    return dict(
        token=dict(type='str', required=True, no_log=True),
        url=dict(type='str', default='https://app.terraform.io'),
        organization=dict(type='str', required=True),
        validate_certs=dict(type='bool', default=True)
    )


def workspace_argument_spec():
    """Argument specifications specific to workspace operations"""
    spec = terraform_argument_spec()
    spec.update(dict(
        name=dict(type='str', required=True),
        description=dict(type='str', default=''),
        terraform_version=dict(type='str'),
        working_directory=dict(type='str', default=''),
        auto_apply=dict(type='bool', default=False),
        file_triggers_enabled=dict(type='bool', default=True),
        queue_all_runs=dict(type='bool', default=False),
        speculative_enabled=dict(type='bool', default=True),
        trigger_prefixes=dict(type='list', elements='str', default=[]),
        execution_mode=dict(
            type='str', 
            choices=['remote', 'local', 'agent'], 
            default='remote'
        ),
        tag_names=dict(type='list', elements='str', default=[]),
        project=dict(type='str'),
        vcs_repo=dict(
            type='dict',
            options=dict(
                identifier=dict(type='str', required=True),
                branch=dict(type='str', default=''),
                oauth_token_id=dict(type='str', required=True),
                ingress_submodules=dict(type='bool', default=False)
            )
        )
    ))
    return spec