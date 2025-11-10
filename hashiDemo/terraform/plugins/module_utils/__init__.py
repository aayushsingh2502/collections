#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2025, Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""
Terraform Enterprise/Cloud Ansible Collection Module Utils

This package provides common utilities for managing Terraform Enterprise
and Terraform Cloud resources via the Ansible modules.
"""

from __future__ import absolute_import, division, print_function
__metaclass__ = type

__version__ = '1.0.0'
__author__ = 'Ansible Terraform Collection'

# Export main classes for easier imports
try:
    from .terraform_base import (
        TerraformBase,
        TerraformBaseError,
        TerraformAuthError,
        TerraformValidationError,
        TerraformOperationError,
        terraform_argument_spec,
        workspace_argument_spec
    )
    
    __all__ = [
        'TerraformBase',
        'TerraformBaseError',
        'TerraformAuthError', 
        'TerraformValidationError',
        'TerraformOperationError',
        'terraform_argument_spec',
        'workspace_argument_spec'
    ]
    
except ImportError:
    # Handle cases where pytfe is not available
    __all__ = []