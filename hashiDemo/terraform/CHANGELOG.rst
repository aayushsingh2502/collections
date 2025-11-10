===============================
Terraform Collection Changelog
===============================

.. contents:: Topics


v1.0.0
======

Release Summary
---------------

Initial release of the Terraform Enterprise/Cloud Ansible Collection.

Major Changes
-------------

- Initial implementation of terraform_workspace module for workspace management
- Initial implementation of terraform_workspace_variables module for variable management
- Initial implementation of terraform_workspace_run module for triggering and managing runs
- Initial implementation of terraform_workspace_info module for retrieving workspace information
- Initial implementation of terraform_organization_info module for retrieving organization information

New Modules
-----------

- hashidemo.terraform.terraform_organization_info - Get information about Terraform Enterprise/Cloud organizations
- hashidemo.terraform.terraform_workspace - Manage Terraform Enterprise/Cloud workspaces
- hashidemo.terraform.terraform_workspace_info - Get information about Terraform Enterprise/Cloud workspaces
- hashidemo.terraform.terraform_workspace_run - Manage Terraform Enterprise/Cloud workspace runs
- hashidemo.terraform.terraform_workspace_variables - Manage Terraform Enterprise/Cloud workspace variables
