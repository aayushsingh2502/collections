#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2025, Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = '''
---
module: terraform_organization_info
short_description: Get information about Terraform Enterprise/Cloud organizations
version_added: "1.0.0"
description:
  - Retrieve information about Terraform organizations
  - Validate organization access and permissions
  - Get organization metadata and settings

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
      - If not provided, returns current user's organizations
    type: str
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
- name: Get current user's organizations
  hashiDemo.terraform.terraform_organization_info:
    token: "{{ terraform_token }}"
  register: user_orgs

- name: Validate specific organization access
  hashiDemo.terraform.terraform_organization_info:
    token: "{{ terraform_token }}"
    organization: "my-org"
  register: org_info

- name: Check organization permissions
  debug:
    msg: |
      Organization: {{ org_info.organization.name }}
      Permissions: {{ org_info.organization.permissions }}
'''

RETURN = '''
organization:
  description: Information about the requested organization
  returned: when organization is specified
  type: dict
  sample:
    id: "org-123456789"
    name: "my-org"
    email: "admin@myorg.com"
    created_at: "2025-01-01T00:00:00Z"
    permissions:
      can_update: true
      can_destroy: false
      can_create_workspace: true

organizations:
  description: List of organizations accessible to the user
  returned: when organization is not specified
  type: list
  elements: dict
  sample:
    - id: "org-123456789"
      name: "my-org"
      email: "admin@myorg.com"
    - id: "org-987654321"
      name: "other-org"
      email: "admin@otherorg.com"

msg:
  description: Human-readable message describing the action performed
  returned: always
  type: str
  sample: "Retrieved information for organization 'my-org'"
'''

import traceback
from typing import Dict, Any, List

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


class TerraformOrganizationInfo(TerraformBase):
    """Terraform organization information retrieval"""
    
    def __init__(self, module: AnsibleModule):
        super().__init__(module)
    
    def run(self):
        """Main execution method"""
        try:
            organization_name = self.module.params.get('organization')
            
            if organization_name:
                result = self._get_organization_info(organization_name)
            else:
                result = self._get_all_organizations()
            
            self.exit_json(**result)
            
        except Exception as e:
            self._handle_tfe_exception(e, "organization info retrieval")
    
    def _get_organization_info(self, organization_name: str) -> Dict[str, Any]:
        """Get information for a specific organization"""
        try:
            organization = self._validate_organization(organization_name)
            org_data = self._normalize_organization_data(organization)
            
            return {
                'organization': org_data,
                'msg': f"Retrieved information for organization '{organization_name}'"
            }
            
        except Exception as e:
            raise TerraformOperationError(f"Failed to get organization info: {str(e)}")
    
    def _get_all_organizations(self) -> Dict[str, Any]:
        """Get all organizations accessible to the user"""
        try:
            organizations = self.client.organizations.list()
            
            orgs_data = []
            for org in organizations:
                org_data = self._normalize_organization_data(org)
                orgs_data.append(org_data)
            
            return {
                'organizations': orgs_data,
                'msg': f"Retrieved {len(orgs_data)} organizations"
            }
            
        except Exception as e:
            raise TerraformOperationError(f"Failed to list organizations: {str(e)}")
    
    def _normalize_organization_data(self, organization) -> Dict[str, Any]:
        """Normalize organization data for output"""
        # Convert Pydantic model to dictionary if needed
        if hasattr(organization, 'model_dump'):
            org_dict = organization.model_dump()
        elif isinstance(organization, dict):
            org_dict = organization
        else:
            org_dict = dict(organization)
        
        # pytfe returns data in a different structure
        return {
            'id': org_dict.get('id'),
            'name': org_dict.get('name'),
            'email': org_dict.get('email'),
            'created_at': org_dict.get('created_at'),
            'permissions': org_dict.get('permissions', {}),
            'plan': org_dict.get('plan'),
            'cost_estimation_enabled': org_dict.get('cost_estimation_enabled', False),
            'send_passing_statuses_for_untriggered_speculative_plans': org_dict.get(
                'send_passing_statuses_for_untriggered_speculative_plans', False
            )
        }


def main():
    """Main function"""
    # Define argument specification
    argument_spec = terraform_argument_spec()
    argument_spec.update(dict(
        organization=dict(type='str')
    ))
    
    # Remove the organization requirement from base spec
    argument_spec['organization']['required'] = False
    
    # Create module
    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True
    )
    
    # Create and run organization info manager
    info_manager = TerraformOrganizationInfo(module)
    info_manager.run()


if __name__ == '__main__':
    main()