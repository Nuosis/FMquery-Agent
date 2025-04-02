import os
import sys
import unittest
import json

# Add parent directory to path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from prompts.prompts import get_filemaker_agent_prompt, construct_prompt, serve_prompt
from cache.cache import load_all_caches, db_info_cache, tools_cache


class TestPrompts(unittest.TestCase):
    """Test cases for the prompts module."""

    def setUp(self):
        """Set up test environment."""
        # Load all caches from disk
        load_all_caches()
        
        # Ensure the caches are loaded
        self.assertTrue(db_info_cache.is_valid(), "Database info cache should be valid after loading")
        self.assertTrue(tools_cache.is_valid(), "Tools cache should be valid after loading")
        
        # Create output directory if it doesn't exist
        self.output_dir = os.path.dirname(os.path.abspath(__file__))
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Path for the output file
        self.output_file = os.path.join(self.output_dir, "test_output.md")

    def test_prompt_merging(self):
        """Test that prompt merging works correctly."""
        # Prepare cache data for the prompt
        cache_data = {}
        
        # Add database info from cache
        if db_info_cache.db_info:
            cache_data['databases'] = db_info_cache.db_info.get('databases', [])
            cache_data['db_paths'] = db_info_cache.get_paths()
            cache_data['db_names'] = db_info_cache.get_names()
        
        # Add tools info from cache
        if tools_cache.tools_info:
            cache_data['tools'] = tools_cache.tools_info.get('tools', [])
            # Add tool dependencies for the dependency graph
            if 'tool_dependencies' in tools_cache.tools_info:
                cache_data['tool_dependencies'] = tools_cache.tools_info.get('tool_dependencies', {})
        
        # Generate the prompt
        prompt = get_filemaker_agent_prompt(cache_data)
        
        # Verify the prompt is not empty
        self.assertTrue(prompt, "Generated prompt should not be empty")
        
        # Verify placeholders are replaced
        self.assertNotIn("<<", prompt, "Prompt should not contain any placeholders")
        
        # Verify database information is included if available
        if 'db_names' in cache_data and cache_data['db_names']:
            for db_name in cache_data['db_names']:
                self.assertIn(db_name, prompt, f"Prompt should include database name: {db_name}")
        
        # Verify tool information is included if available
        if 'tools' in cache_data and cache_data['tools']:
            for tool in cache_data['tools']:
                tool_name = tool.get('name', '')
                if tool_name:
                    self.assertIn(tool_name, prompt, f"Prompt should include tool name: {tool_name}")
        
        # Save the prompt to the output file
        with open(self.output_file, 'w') as f:
            f.write(prompt)
        
        print(f"Prompt saved to {self.output_file}")

    def test_construct_prompt(self):
        """Test the construct_prompt function."""
        # Test template with placeholders
        template = """
        This is a test template with placeholders:
        <<insert test_value here>>
        <<test_value2>>
        """
        
        # Test data
        data = {
            'test_value': 'Hello, World!',
            'test_value2': 'Another value'
        }
        
        # Construct the prompt
        result = construct_prompt(template, data)
        
        # Verify placeholders are replaced
        self.assertIn('Hello, World!', result)
        self.assertIn('Another value', result)
        self.assertNotIn('<<insert test_value here>>', result)
        self.assertNotIn('<<test_value2>>', result)

    def test_serve_prompt(self):
        """Test the serve_prompt function."""
        # Test prompt with placeholders
        prompt = """
        This is a test prompt with placeholders:
        <<insert missing_value here>>
        <<another_missing_value>>
        """
        
        # Serve the prompt
        result = serve_prompt(prompt)
        
        # Verify placeholders are removed
        self.assertNotIn('<<insert missing_value here>>', result)
        self.assertNotIn('<<another_missing_value>>', result)


if __name__ == '__main__':
    unittest.main()