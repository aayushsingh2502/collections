#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2025, Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = '''
---
module: terraform_workspace_run
short_description: Manage Terraform Enterprise/Cloud workspace runs
version_added: "1.0.0"
description:
  - Trigger, monitor, and manage Terraform runs in workspaces
  - Support for plan-only runs and full apply runs
  - Monitor run status and retrieve logs

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
  action:
    description:
      - Action to perform on the workspace run
    type: str
    choices: ['trigger', 'apply', 'discard', 'cancel', 'status']
    required: true
  run_id:
    description:
      - ID of the run to act upon (required for apply, discard, cancel, status)
    type: str
  message:
    description:
      - Message to attach to the run
    type: str
    default: 'Triggered by Ansible'
  plan_only:
    description:
      - Whether to create a plan-only run (no apply)
      - Only applicable when action is 'trigger'
    type: bool
    default: false
  target_addrs:
    description:
      - List of resource addresses to target
      - Only applicable when action is 'trigger'
    type: list
    elements: str
    default: []
  replace_addrs:
    description:
      - List of resource addresses to replace
      - Only applicable when action is 'trigger'
    type: list
    elements: str
    default: []
  auto_apply:
    description:
      - Override workspace auto-apply setting for this run
      - Only applicable when action is 'trigger'
    type: bool
  wait:
    description:
      - Whether to wait for the run to complete
      - Only applicable when action is 'trigger'
    type: bool
    default: false
  wait_timeout:
    description:
      - Maximum time to wait for run completion (in seconds)
      - Only applicable when wait is true
    type: int
    default: 1800
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
- name: Trigger a plan-only run
  hashiDemo.terraform.terraform_workspace_run:
    token: "{{ terraform_token }}"
    organization: "my-org"
    workspace: "production"
    action: "trigger"
    message: "Plan from Ansible automation"
    plan_only: true

- name: Trigger a run and wait for completion
  hashiDemo.terraform.terraform_workspace_run:
    token: "{{ terraform_token }}"
    organization: "my-org"
    workspace: "production"
    action: "trigger"
    message: "Deploy from Ansible"
    wait: true
    wait_timeout: 3600

- name: Trigger a targeted run
  hashiDemo.terraform.terraform_workspace_run:
    token: "{{ terraform_token }}"
    organization: "my-org"
    workspace: "production"
    action: "trigger"
    message: "Update specific resources"
    target_addrs:
      - "aws_instance.web"
      - "aws_security_group.web"

- name: Apply a planned run
  hashiDemo.terraform.terraform_workspace_run:
    token: "{{ terraform_token }}"
    organization: "my-org"
    workspace: "production"
    action: "apply"
    run_id: "run-123456789"
    message: "Apply approved changes"

- name: Discard a planned run
  hashiDemo.terraform.terraform_workspace_run:
    token: "{{ terraform_token }}"
    organization: "my-org"
    workspace: "production"
    action: "discard"
    run_id: "run-123456789"

- name: Cancel a running run
  hashiDemo.terraform.terraform_workspace_run:
    token: "{{ terraform_token }}"
    organization: "my-org"
    workspace: "production"
    action: "cancel"
    run_id: "run-123456789"

- name: Check run status
  hashiDemo.terraform.terraform_workspace_run:
    token: "{{ terraform_token }}"
    organization: "my-org"
    workspace: "production"
    action: "status"
    run_id: "run-123456789"
  register: run_status
'''

RETURN = '''
run:
  description: Information about the run
  returned: always
  type: dict
  sample:
    id: "run-123456789"
    status: "applied"
    message: "Deploy from Ansible"
    created_at: "2025-01-01T00:00:00Z"
    plan_only: false
    auto_apply: true
    target_addrs: []
    replace_addrs: []
    has_changes: true
    permissions:
      can_apply: true
      can_cancel: false
      can_discard: false

changed:
  description: Whether the run state was changed
  returned: always
  type: bool
  sample: true

operation:
  description: The operation that was performed
  returned: always
  type: str
  sample: "triggered"

logs:
  description: Run logs (if available)
  returned: when applicable
  type: dict
  sample:
    plan: "Terraform plan output..."
    apply: "Terraform apply output..."

msg:
  description: Human-readable message describing the action performed
  returned: always
  type: str
  sample: "Run triggered successfully"
'''

import time
import traceback
from typing import Dict, Any, Optional, List

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


class TerraformWorkspaceRun(TerraformBase):
    """Terraform workspace run management"""
    
    def __init__(self, module: AnsibleModule):
        super().__init__(module)
        
        # Validate inputs
        self._validate_inputs()
    
    def _validate_inputs(self):
        """Validate module parameters"""
        action = self.module.params['action']
        run_id = self.module.params.get('run_id')
        
        # Validate run_id requirement
        if action in ['apply', 'discard', 'cancel', 'status'] and not run_id:
            raise TerraformValidationError(f"Action '{action}' requires 'run_id' parameter")
        
        # Validate target and replace addresses format
        target_addrs = self.module.params.get('target_addrs', [])
        replace_addrs = self.module.params.get('replace_addrs', [])
        
        for addr in target_addrs + replace_addrs:
            if not addr or not isinstance(addr, str):
                raise TerraformValidationError("Target and replace addresses must be non-empty strings")
        
        # Validate timeout
        wait_timeout = self.module.params.get('wait_timeout', 1800)
        if wait_timeout <= 0:
            raise TerraformValidationError("Wait timeout must be positive")
    
    def run(self):
        """Main execution method"""
        action = self.module.params['action']
        
        try:
            if action == 'trigger':
                result = self._trigger_run()
            elif action == 'apply':
                result = self._apply_run()
            elif action == 'discard':
                result = self._discard_run()
            elif action == 'cancel':
                result = self._cancel_run()
            elif action == 'status':
                result = self._get_run_status()
            else:
                self.module.fail_json(msg=f"Invalid action: {action}")
            
            self.exit_json(**result)
            
        except Exception as e:
            self._handle_tfe_exception(e, f"run {action}")
    
    def _trigger_run(self) -> Dict[str, Any]:
        """Trigger a new run"""
        organization = self.module.params['organization']
        workspace_name = self.module.params['workspace']
        
        # Validate organization and workspace
        self._validate_organization(organization)
        workspace = self._get_workspace(organization, workspace_name)
        if workspace is None:
            raise TerraformValidationError(f"Workspace '{workspace_name}' not found")
        
        workspace_id = workspace['id']
        
        # Prepare run attributes
        attributes = self._prepare_run_attributes()
        
        # Prepare payload
        payload = {
            'data': {
                'type': 'runs',
                'attributes': attributes,
                'relationships': {
                    'workspace': {
                        'data': {
                            'type': 'workspaces',
                            'id': workspace_id
                        }
                    }
                }
            }
        }
        
        try:
            # Create run
            run = self.client.runs.create(payload=payload)
            self.changed = True
            
            run_data = self._normalize_run_data(run)
            result = {
                'run': run_data,
                'operation': 'triggered',
                'msg': f"Run triggered for workspace '{workspace_name}'"
            }
            
            # Wait for completion if requested
            wait = self.module.params.get('wait', False)
            if wait:
                final_run = self._wait_for_run_completion(run['id'])
                result['run'] = self._normalize_run_data(final_run)
                result['msg'] += f" - Final status: {final_run.get('attributes', {}).get('status')}"
            
            return result
            
        except Exception as e:
            raise TerraformOperationError(f"Failed to trigger run: {str(e)}")
    
    def _apply_run(self) -> Dict[str, Any]:
        """Apply a planned run"""
        run_id = self.module.params['run_id']
        message = self.module.params.get('message', 'Applied by Ansible')
        
        # Get current run status
        run = self._get_run(run_id)
        status = run.get('attributes', {}).get('status')
        
        if status not in ['planned', 'cost_estimated', 'policy_checked']:
            raise TerraformValidationError(f"Run {run_id} cannot be applied (status: {status})")
        
        try:
            # Apply run
            apply_payload = {
                'comment': message
            }
            
            self.client.runs.apply(run_id=run_id, payload=apply_payload)
            self.changed = True
            
            # Get updated run
            updated_run = self._get_run(run_id)
            
            return {
                'run': self._normalize_run_data(updated_run),
                'operation': 'applied',
                'msg': f"Run {run_id} applied successfully"
            }
            
        except Exception as e:
            raise TerraformOperationError(f"Failed to apply run: {str(e)}")
    
    def _discard_run(self) -> Dict[str, Any]:
        """Discard a planned run"""
        run_id = self.module.params['run_id']
        message = self.module.params.get('message', 'Discarded by Ansible')
        
        # Get current run status
        run = self._get_run(run_id)
        status = run.get('attributes', {}).get('status')
        
        if status not in ['planned', 'cost_estimated', 'policy_checked']:
            raise TerraformValidationError(f"Run {run_id} cannot be discarded (status: {status})")
        
        try:
            # Discard run
            discard_payload = {
                'comment': message
            }
            
            self.client.runs.discard(run_id=run_id, payload=discard_payload)
            self.changed = True
            
            # Get updated run
            updated_run = self._get_run(run_id)
            
            return {
                'run': self._normalize_run_data(updated_run),
                'operation': 'discarded',
                'msg': f"Run {run_id} discarded successfully"
            }
            
        except Exception as e:
            raise TerraformOperationError(f"Failed to discard run: {str(e)}")
    
    def _cancel_run(self) -> Dict[str, Any]:
        """Cancel a running run"""
        run_id = self.module.params['run_id']
        message = self.module.params.get('message', 'Cancelled by Ansible')
        
        # Get current run status
        run = self._get_run(run_id)
        status = run.get('attributes', {}).get('status')
        
        cancellable_statuses = [
            'pending', 'planning', 'planned', 'cost_estimating', 'cost_estimated',
            'policy_checking', 'policy_checked', 'applying', 'confirmed'
        ]
        
        if status not in cancellable_statuses:
            raise TerraformValidationError(f"Run {run_id} cannot be cancelled (status: {status})")
        
        try:
            # Cancel run
            cancel_payload = {
                'comment': message
            }
            
            self.client.runs.cancel(run_id=run_id, payload=cancel_payload)
            self.changed = True
            
            # Get updated run
            updated_run = self._get_run(run_id)
            
            return {
                'run': self._normalize_run_data(updated_run),
                'operation': 'cancelled',
                'msg': f"Run {run_id} cancelled successfully"
            }
            
        except Exception as e:
            raise TerraformOperationError(f"Failed to cancel run: {str(e)}")
    
    def _get_run_status(self) -> Dict[str, Any]:
        """Get run status and details"""
        run_id = self.module.params['run_id']
        
        try:
            run = self._get_run(run_id)
            
            result = {
                'run': self._normalize_run_data(run),
                'operation': 'status',
                'msg': f"Retrieved status for run {run_id}"
            }
            
            # Try to get logs if available
            logs = self._get_run_logs(run_id)
            if logs:
                result['logs'] = logs
            
            return result
            
        except Exception as e:
            raise TerraformOperationError(f"Failed to get run status: {str(e)}")
    
    def _get_run(self, run_id: str) -> Dict[str, Any]:
        """Get run details"""
        try:
            return self.client.runs.show(run_id=run_id)
        except Exception as e:
            raise TerraformOperationError(f"Failed to get run {run_id}: {str(e)}")
    
    def _get_run_logs(self, run_id: str) -> Dict[str, str]:
        """Get run logs if available"""
        logs = {}
        try:
            # Try to get plan logs
            plan_log = self.client.plan_logs.show(run_id=run_id)
            if plan_log:
                logs['plan'] = plan_log
        except:
            pass
        
        try:
            # Try to get apply logs
            apply_log = self.client.apply_logs.show(run_id=run_id)
            if apply_log:
                logs['apply'] = apply_log
        except:
            pass
        
        return logs
    
    def _wait_for_run_completion(self, run_id: str) -> Dict[str, Any]:
        """Wait for run to complete"""
        wait_timeout = self.module.params.get('wait_timeout', 1800)
        start_time = time.time()
        
        while True:
            # Check timeout
            if time.time() - start_time > wait_timeout:
                raise TerraformOperationError(f"Timeout waiting for run {run_id} to complete")
            
            # Get current run status
            run = self._get_run(run_id)
            status = run.get('attributes', {}).get('status')
            
            # Check if run is finished
            terminal_statuses = [
                'applied', 'discarded', 'errored', 'canceled', 'force_canceled'
            ]
            
            if status in terminal_statuses:
                return run
            
            # Check for states that require manual intervention
            manual_statuses = ['planned', 'cost_estimated', 'policy_checked']
            if status in manual_statuses:
                # If auto_apply is enabled, the run should progress automatically
                workspace_attrs = run.get('relationships', {}).get('workspace', {}).get('attributes', {})
                if not workspace_attrs.get('auto-apply', False):
                    # Return the run as is - it's waiting for manual approval
                    return run
            
            # Wait before checking again
            time.sleep(10)
    
    def _prepare_run_attributes(self) -> Dict[str, Any]:
        """Prepare run attributes for API call"""
        attributes = {
            'message': self.module.params.get('message', 'Triggered by Ansible'),
            'plan-only': self.module.params.get('plan_only', False)
        }
        
        # Add auto-apply override if specified
        auto_apply = self.module.params.get('auto_apply')
        if auto_apply is not None:
            attributes['auto-apply'] = auto_apply
        
        # Add target addresses
        target_addrs = self.module.params.get('target_addrs', [])
        if target_addrs:
            attributes['target-addrs'] = target_addrs
        
        # Add replace addresses
        replace_addrs = self.module.params.get('replace_addrs', [])
        if replace_addrs:
            attributes['replace-addrs'] = replace_addrs
        
        return attributes
    
    def _normalize_run_data(self, run: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize run data for consistent output"""
        attributes = run.get('attributes', {})
        
        # Extract permissions
        permissions = attributes.get('permissions', {})
        
        # Extract relationships
        relationships = run.get('relationships', {})
        workspace_data = relationships.get('workspace', {}).get('data', {})
        
        return {
            'id': run.get('id'),
            'status': attributes.get('status'),
            'status_timestamps': attributes.get('status-timestamps', {}),
            'message': attributes.get('message'),
            'created_at': attributes.get('created-at'),
            'plan_only': attributes.get('plan-only', False),
            'auto_apply': attributes.get('auto-apply'),
            'target_addrs': attributes.get('target-addrs', []),
            'replace_addrs': attributes.get('replace-addrs', []),
            'has_changes': attributes.get('has-changes'),
            'workspace_id': workspace_data.get('id'),
            'permissions': {
                'can_apply': permissions.get('can-apply', False),
                'can_cancel': permissions.get('can-cancel', False),
                'can_discard': permissions.get('can-discard', False),
                'can_force_execute': permissions.get('can-force-execute', False)
            }
        }


def main():
    """Main function"""
    # Define argument specification
    argument_spec = terraform_argument_spec()
    argument_spec.update(dict(
        workspace=dict(type='str', required=True),
        action=dict(
            type='str',
            choices=['trigger', 'apply', 'discard', 'cancel', 'status'],
            required=True
        ),
        run_id=dict(type='str'),
        message=dict(type='str', default='Triggered by Ansible'),
        plan_only=dict(type='bool', default=False),
        target_addrs=dict(type='list', elements='str', default=[]),
        replace_addrs=dict(type='list', elements='str', default=[]),
        auto_apply=dict(type='bool'),
        wait=dict(type='bool', default=False),
        wait_timeout=dict(type='int', default=1800)
    ))
    
    # Create module
    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=False
    )
    
    # Create and run workspace run manager
    run_manager = TerraformWorkspaceRun(module)
    run_manager.run()


if __name__ == '__main__':
    main()