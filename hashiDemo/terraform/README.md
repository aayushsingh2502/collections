# Terraform Enterprise/Cloud Ansible Collection

This collection provides Ansible modules for managing Terraform Enterprise and Terraform Cloud workspaces and resources.

## Installation

```bash
# Install the collection
ansible-galaxy collection install hashidemo.terraform

# Install Python dependencies
pip install -r requirements.txt
```

## Requirements

- Python >= 3.6
- pytfe >= 0.1.0
- Ansible >= 2.12.0

## Modules

### terraform_organization_info

Get information about Terraform Enterprise/Cloud organizations.

**Key Features:**
- Retrieve organization details
- Validate organization access
- Get organization permissions

### terraform_workspace

Manage Terraform Enterprise/Cloud workspaces.

**Key Features:**
- Create, update, and delete workspaces
- Configure VCS integration
- Set execution mode and auto-apply
- Manage workspace tags and settings

### terraform_workspace_variables

Manage workspace variables.

**Key Features:**
- Create, update, and delete variables
- Support for Terraform and environment variables
- Sensitive variable handling
- HCL variable support
- Bulk variable management with purge option

### terraform_workspace_run

Manage workspace runs.

**Key Features:**
- Trigger plan and apply runs
- Apply, discard, or cancel runs
- Wait for run completion
- Run status monitoring
- Targeted and replace operations

### terraform_workspace_info

Get information about workspaces.

**Key Features:**
- Retrieve single or all workspace information
- Include variables and runs data
- Comprehensive workspace metadata

## Authentication

All modules require a Terraform Enterprise/Cloud API token. You can provide it in several ways:

1. **Module parameter:**
   ```yaml
   - name: Create workspace
     hashiDemo.terraform.terraform_workspace:
       token: "your-api-token"
       # ... other parameters
   ```

2. **Environment variable:**
   ```bash
   export TF_TOKEN="your-api-token"
   ```

3. **Ansible Vault (recommended):**
   ```yaml
   - name: Create workspace
     hashiDemo.terraform.terraform_workspace:
       token: "{{ vault_terraform_token }}"
       # ... other parameters
   ```

## Quick Start

### 1. Create a Basic Workspace

```yaml
- name: Create development workspace
  hashiDemo.terraform.terraform_workspace:
    token: "{{ terraform_token }}"
    organization: "my-org"
    name: "development"
    description: "Development environment"
    terraform_version: "1.6.0"
    auto_apply: false
    state: present
```

### 2. Set Workspace Variables

```yaml
- name: Configure workspace variables
  hashiDemo.terraform.terraform_workspace_variables:
    token: "{{ terraform_token }}"
    organization: "my-org"
    workspace: "development"
    variables:
      environment:
        value: "dev"
        category: "terraform"
        description: "Environment name"
      AWS_ACCESS_KEY_ID:
        value: "{{ aws_access_key }}"
        category: "env"
        sensitive: true
    state: present
```

### 3. Trigger a Run

```yaml
- name: Plan infrastructure changes
  hashiDemo.terraform.terraform_workspace_run:
    token: "{{ terraform_token }}"
    organization: "my-org"
    workspace: "development"
    action: "trigger"
    message: "Plan from Ansible"
    plan_only: true
    wait: true
```

## Error Handling and Validation

The collection includes comprehensive validation and error handling:

- **Authentication validation:** Verifies API token validity
- **Organization validation:** Confirms organization exists and is accessible
- **Workspace validation:** Checks workspace existence and permissions
- **Input validation:** Validates parameter formats and values
- **API error handling:** Provides meaningful error messages for API failures

## Examples

See the `examples/` directory for comprehensive playbook examples:

- `workspace_management.yml` - Complete workspace lifecycle management

## Best Practices

### Security
- Store API tokens in Ansible Vault
- Use sensitive variable flag for credentials
- Implement proper RBAC in Terraform Enterprise/Cloud

### Organization
- Use consistent naming conventions
- Tag workspaces appropriately
- Implement workspace templates via Ansible

### Automation
- Use check mode for validation
- Implement proper error handling
- Use wait parameters for run completion

## Troubleshooting

### Common Issues

1. **Authentication failures:**
   - Verify API token is correct and not expired
   - Check token permissions in Terraform Enterprise/Cloud
   - Ensure organization access

2. **Workspace not found:**
   - Verify organization name spelling
   - Check workspace name case sensitivity
   - Confirm workspace exists

3. **Variable update failures:**
   - Check variable name conflicts
   - Verify HCL syntax for HCL variables
   - Ensure sensitive variables are properly flagged

### Debug Mode

Enable debug output for troubleshooting:

```yaml
- name: Create workspace with debug
  hashiDemo.terraform.terraform_workspace:
    token: "{{ terraform_token }}"
    organization: "my-org"
    name: "debug-workspace"
    state: present
  register: result
  
- debug:
    var: result
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## License

GNU General Public License v3.0 or later

## Support

For issues and questions:
1. Check the documentation
2. Review existing issues
3. Create a new issue with details

## Changelog

### v1.0.0
- Initial release
- Basic workspace management
- Variable management
- Run management
- Info retrieval functionality
