#!/usr/bin/env python3
"""
Simple test script to validate the Terraform collection modules.
This is a basic smoke test to ensure modules can be imported and initialized.
"""

import sys
import os
import tempfile
import unittest
from unittest.mock import Mock, patch, MagicMock

# Add the plugins directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'plugins', 'module_utils'))

class TestTerraformModules(unittest.TestCase):
    """Test cases for Terraform modules"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_module = Mock()
        self.mock_module.params = {
            'token': 'test-token',
            'url': 'https://app.terraform.io',
            'organization': 'test-org',
            'name': 'test-workspace',
            'validate_certs': True
        }
        self.mock_module.fail_json = Mock()
        self.mock_module.exit_json = Mock()
    
    @patch('terraform_base.TFEClient')
    @patch('terraform_base.HAS_PYTFE', True)
    def test_terraform_base_import(self, mock_tfe_client):
        """Test that terraform_base can be imported and initialized"""
        try:
            from terraform_base import TerraformBase
            
            # Mock the client and authentication
            mock_client_instance = Mock()
            mock_client_instance.account.show.return_value = {'id': 'test-account'}
            mock_tfe_client.return_value = mock_client_instance
            
            # Test initialization
            base = TerraformBase(self.mock_module)
            self.assertIsNotNone(base)
            self.assertEqual(base.changed, False)
            
        except ImportError:
            self.skipTest("terraform_base module not available")
    
    def test_argument_specs(self):
        """Test that argument specifications are properly defined"""
        try:
            from terraform_base import terraform_argument_spec, workspace_argument_spec
            
            # Test terraform argument spec
            tf_spec = terraform_argument_spec()
            self.assertIn('token', tf_spec)
            self.assertIn('organization', tf_spec)
            self.assertIn('url', tf_spec)
            self.assertIn('validate_certs', tf_spec)
            
            # Test workspace argument spec
            ws_spec = workspace_argument_spec()
            self.assertIn('name', ws_spec)
            self.assertIn('description', ws_spec)
            self.assertIn('terraform_version', ws_spec)
            
        except ImportError:
            self.skipTest("terraform_base module not available")
    
    def test_validation_functions(self):
        """Test validation functions"""
        try:
            from terraform_base import TerraformBase
            
            # Create a mock base instance
            with patch('terraform_base.TFEClient'):
                with patch.object(TerraformBase, '_validate_authentication'):
                    base = TerraformBase(self.mock_module)
                    
                    # Test workspace name validation
                    base._validate_workspace_name('valid-workspace')
                    base._validate_workspace_name('valid_workspace')
                    base._validate_workspace_name('validworkspace123')
                    
                    # Test invalid workspace names
                    with self.assertRaises(Exception):
                        base._validate_workspace_name('')
                    
                    with self.assertRaises(Exception):
                        base._validate_workspace_name('invalid workspace')
                    
                    # Test Terraform version validation
                    base._validate_terraform_version('1.5.0')
                    base._validate_terraform_version('0.15.5')
                    
                    with self.assertRaises(Exception):
                        base._validate_terraform_version('invalid-version')
                        
        except ImportError:
            self.skipTest("terraform_base module not available")


class TestModuleStructure(unittest.TestCase):
    """Test the overall module structure"""
    
    def test_module_files_exist(self):
        """Test that all expected module files exist"""
        base_dir = os.path.join(os.path.dirname(__file__), '..')
        
        # Check module_utils
        module_utils_dir = os.path.join(base_dir, 'plugins', 'module_utils')
        self.assertTrue(os.path.exists(module_utils_dir))
        self.assertTrue(os.path.exists(os.path.join(module_utils_dir, 'terraform_base.py')))
        
        # Check modules
        modules_dir = os.path.join(base_dir, 'plugins', 'modules')
        self.assertTrue(os.path.exists(modules_dir))
        
        expected_modules = [
            'terraform_workspace.py',
            'terraform_workspace_variables.py',
            'terraform_workspace_run.py',
            'terraform_workspace_info.py',
            'terraform_organization_info.py'
        ]
        
        for module_file in expected_modules:
            module_path = os.path.join(modules_dir, module_file)
            self.assertTrue(os.path.exists(module_path), f"Module {module_file} not found")
    
    def test_documentation_exists(self):
        """Test that documentation files exist"""
        base_dir = os.path.join(os.path.dirname(__file__), '..')
        
        # Check README
        readme_path = os.path.join(base_dir, 'README.md')
        self.assertTrue(os.path.exists(readme_path))
        
        # Check galaxy.yml
        galaxy_path = os.path.join(base_dir, 'galaxy.yml')
        self.assertTrue(os.path.exists(galaxy_path))
        
        # Check requirements
        requirements_path = os.path.join(base_dir, 'requirements.txt')
        self.assertTrue(os.path.exists(requirements_path))
        
        # Check examples
        examples_dir = os.path.join(base_dir, 'examples')
        self.assertTrue(os.path.exists(examples_dir))


def run_tests():
    """Run all tests"""
    # Set up test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test cases
    suite.addTests(loader.loadTestsFromTestCase(TestTerraformModules))
    suite.addTests(loader.loadTestsFromTestCase(TestModuleStructure))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == '__main__':
    print("Running Terraform Collection Tests...")
    print("=" * 50)
    
    success = run_tests()
    
    print("=" * 50)
    if success:
        print("✅ All tests passed!")
        sys.exit(0)
    else:
        print("❌ Some tests failed!")
        sys.exit(1)