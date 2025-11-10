#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2025, Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""
Terraform Enterprise/Cloud Ansible Collection Modules

This package contains Ansible modules for managing Terraform Enterprise
and Terraform Cloud resources including workspaces, variables, runs, and organizations.

Available modules:
- terraform_workspace: Manage workspaces (create, update, delete)
- terraform_workspace_variables: Manage workspace variables
- terraform_workspace_run: Trigger and manage runs
- terraform_workspace_info: Get workspace information
- terraform_organization_info: Get organization information
"""

from __future__ import absolute_import, division, print_function
__metaclass__ = type

__version__ = '1.0.0'
__author__ = 'Ansible Terraform Collection'