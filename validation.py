import json
from typing import Tuple, Dict, List, Any, Optional, Union
from agents.mcp import MCPServerStdio
from agents import Agent, Runner

from models import TOOL_ARG_MODELS
from cache import db_info_cache
from orchestration.cache_hierarchy import schema_cache, table_cache, script_cache
from database import get_database_info
from logging_utils import extract_tool_calls_from_result, all_tool_calls
from validation_decorator import validate_tool_parameters, ToolParameterValidationError

# Validator functions for database paths
def validate_db_paths(value: Any) -> None:
    """
    Validate that the db_paths parameter contains valid database paths.
    
    Args:
        value: The value to validate (can be a string or a list of strings)
        
    Raises:
        ValueError: If the value is not a valid database path
    """
    #print(f"\n--- DEBUG: validate_db_paths called with value: {value} ---")
    
    # Get the valid database paths from the cache
    valid_paths = db_info_cache.get_paths()
    
    #print(f"--- DEBUG: Valid paths in cache: {valid_paths} ---")
    
    # If the cache is empty, we can't validate
    if not valid_paths:
        print("Warning: Database path cache is empty, skipping validation")
        return
    
    # Convert value to a list if it's a string
    paths_to_check = [value] if isinstance(value, str) else value
    
    # If it's a list, validate each item
    if isinstance(paths_to_check, list):
        for path in paths_to_check:
            # Check if the path is a valid path (should not accept just names)
            if path in valid_paths:
                continue
                
            # Check for placeholder paths
            if '/path/to/' in path:
                error_message = f"Placeholder database path detected: {path}\n\nPlease use a valid database path from the list below:\n"
                for valid_path in valid_paths:
                    error_message += f"  - {valid_path}\n"
                raise ValueError(error_message)
            
            # If we get here, the path is not valid
            error_message = f"Invalid database path: {path}\n\nPlease use a valid database path from the list below:\n"
            for valid_path in valid_paths:
                error_message += f"  - {valid_path}\n"
            raise ValueError(error_message)
        
        # All paths are valid
        return
    
    # If it's not a string or a list, it's invalid
    error_message = f"Invalid database path type: {type(value)}\n\nPlease use a valid database path from the list below:\n"
    for path in valid_paths:
        error_message += f"  - {path}\n"
    raise ValueError(error_message)
    
    # If we get here, the path is not valid
    error_message = f"Invalid database path: {value}\n\nPlease use a valid database path from the list below:\n"
    for path in valid_paths:
        error_message += f"  - {path}\n"
    raise ValueError(error_message)

def validate_db_names(value: Any) -> None:
    """
    Validate that the db_names parameter contains valid database names.
    
    Args:
        value: The value to validate (can be a string or a list of strings)
        
    Raises:
        ValueError: If the value is not a valid database name
    """
    # Get the valid database names from the cache
    valid_names = db_info_cache.get_names()
    
    # If the cache is empty, we can't validate
    if not valid_names:
        print("Warning: Database name cache is empty, skipping validation")
        return
    
    # Convert value to a list if it's a string
    names_to_check = [value] if isinstance(value, str) else value
    
    # If it's a list, validate each item
    if isinstance(names_to_check, list):
        for name in names_to_check:
            # Check if the name is a valid name
            if name in valid_names:
                continue
            
            # If we get here, the name is not valid
            error_message = f"Invalid database name: {name}\n\nPlease use a valid database name from the list below:\n"
            for valid_name in valid_names:
                error_message += f"  - {valid_name}\n"
            raise ValueError(error_message)
        
        # All names are valid
        return
    
    # If it's not a string or a list, it's invalid
    error_message = f"Invalid database name type: {type(value)}\n\nPlease use a valid database name from the list below:\n"
    for name in valid_names:
        error_message += f"  - {name}\n"
    raise ValueError(error_message)

    """
    Validate that the db_path parameter contains a valid database path.
    
    Args:
        value: The value to validate (must be a string)
        
    Raises:
        ValueError: If the value is not a valid database path
    """
    # Get the valid database paths from the cache
    valid_paths = db_info_cache.get_paths()
    
    # If the cache is empty, we can't validate
    if not valid_paths:
        print("Warning: Database path cache is empty, skipping validation")
        return
    
    # Check if the value is a string
    if not isinstance(value, str):
        error_message = f"Invalid database path type: {type(value)}\n\nPlease use a valid database path as a string.\n"
        raise ValueError(error_message)
    
    # Check if the value is a valid path (should not accept just names)
    if value in valid_paths:
        return
    
    # Check for placeholder paths
    if '/path/to/' in value:
        error_message = f"Placeholder database path detected: {value}\n\nPlease use a valid database path from the list below:\n"
        for path in valid_paths:
            error_message += f"  - {path}\n"
        raise ValueError(error_message)
    
    # If we get here, the path is not valid
    error_message = f"Invalid database path: {value}\n\nPlease use a valid database path from the list below:\n"
    for path in valid_paths:
        error_message += f"  - {path}\n"
    raise ValueError(error_message)

def validate_table_name(value: Any, schema_name: str, db_name: str) -> None:
    """
    Validate that the table_name parameter contains a valid table name for the given schema.
    
    Args:
        value: The value to validate (can be a string or a list of strings)
        schema_name: The name of the schema to validate against
        db_name: The name of the database containing the schema
        
    Raises:
        ValueError: If the value is not a valid table name
    """
    # Get the valid table names from the schema cache
    valid_tables = schema_cache.get_tables(db_name, schema_name)
    
    # If the cache is empty, we can't validate
    if not valid_tables:
        print(f"Warning: Table cache for schema {schema_name} is empty, skipping validation")
        return
    
    # Convert value to a list if it's a string
    tables_to_check = [value] if isinstance(value, str) else value
    
    # If it's a list, validate each item
    if isinstance(tables_to_check, list):
        for table in tables_to_check:
            # Check if the table is a valid table name
            if table in valid_tables:
                continue
            
            # If we get here, the table is not valid
            error_message = f"Invalid table name: {table} for schema {schema_name}\n\nPlease use a valid table name from the list below:\n"
            for valid_table in valid_tables:
                error_message += f"  - {valid_table}\n"
            raise ValueError(error_message)
        
        # All tables are valid
        return
    
    # If it's not a string or a list, it's invalid
    error_message = f"Invalid table name type: {type(value)}\n\nPlease use a valid table name from the list below:\n"
    for table in valid_tables:
        error_message += f"  - {table}\n"
    raise ValueError(error_message)

def validate_field_names(value: Any, table_name: str, schema_name: str, db_name: str) -> None:
    """
    Validate that the field_names parameter contains valid field names for the given table.
    
    Args:
        value: The value to validate (can be a string or a list of strings)
        table_name: The name of the table to validate against
        schema_name: The name of the schema containing the table
        db_name: The name of the database containing the schema
        
    Raises:
        ValueError: If the value is not a valid field name
    """
    # Get the valid field names from the table cache
    valid_fields = table_cache.get_fields(db_name, schema_name, table_name)
    
    # If the cache is empty, we can't validate
    if not valid_fields:
        print(f"Warning: Field cache for table {table_name} is empty, skipping validation")
        return
    
    # Convert value to a list if it's a string
    fields_to_check = [value] if isinstance(value, str) else value
    
    # If it's a list, validate each item
    if isinstance(fields_to_check, list):
        for field in fields_to_check:
            # Check if the field is a valid field name
            if field in valid_fields:
                continue
            
            # If we get here, the field is not valid
            error_message = f"Invalid field name: {field} for table {table_name}\n\nPlease use a valid field name from the list below:\n"
            for valid_field in valid_fields:
                error_message += f"  - {valid_field}\n"
            raise ValueError(error_message)
        
        # All fields are valid
        return
    
    # If it's not a string or a list, it's invalid
    error_message = f"Invalid field name type: {type(value)}\n\nPlease use a valid field name from the list below:\n"
    for field in valid_fields:
        error_message += f"  - {field}\n"
    raise ValueError(error_message)

def validate_script_names(value: Any) -> None:
    """
    Validate that the script_name parameter contains a valid script name/ID.
    
    Args:
        value: The value to validate (can be a string or a list of strings)
        
    Raises:
        ValueError: If the value is not a valid script name
    """
    # Get the valid script names from the script cache
    valid_scripts = script_cache.get_scripts()
    
    # If the cache is empty, we can't validate
    if not valid_scripts:
        print("Warning: Script cache is empty, skipping validation")
        return
    
    # Convert value to a list if it's a string
    scripts_to_check = [value] if isinstance(value, str) else value
    
    # If it's a list, validate each item
    if isinstance(scripts_to_check, list):
        for script in scripts_to_check:
            # Check if the script is a valid script name
            if script in valid_scripts:
                continue
            
            # If we get here, the script is not valid
            error_message = f"Invalid script name: {script}\n\nPlease use a valid script name from the list below:\n"
            for valid_script in valid_scripts:
                error_message += f"  - {valid_script}\n"
            raise ValueError(error_message)
        
        # All scripts are valid
        return
    
    # If it's not a string or a list, it's invalid
    error_message = f"Invalid script name type: {type(value)}\n\nPlease use a valid script name from the list below:\n"
    for script in valid_scripts:
        error_message += f"  - {script}\n"
    raise ValueError(error_message)

# Define tool specifications
tool_specs = {
    # Database Discovery Tool - No parameters required
    "discover_databases": {},
    "discover_databases_tool": {},  # Add the _tool suffix version
    
    # Schema Information Tool - Requires db_paths
    "get_schema_information": {
        "db_paths": {"type": "list", "required": True, "validator": validate_db_paths},
    },
    "get_schema_information_tool": {  # Add the _tool suffix version
        "db_paths": {"type": "list", "required": True, "validator": validate_db_paths},
    },
    
    # Table Information Tool - Requires table_name only
    "get_table_information": {
        "table_name": {"type": "str", "required": True, "validator": validate_table_name},
    },
    "get_table_information_tool": {  # Add the _tool suffix version
        "table_name": {"type": "str", "required": True},  # Remove validator since it requires additional parameters
        "table_path": {"type": "str", "required": True},  # Also requires table_path
    },
    
    # Script Information Tool - Requires db_paths
    "get_script_information": {
        "db_paths": {"type": "list", "required": True, "validator": validate_db_paths},
    },
    "get_script_information_tool": {  # Add the _tool suffix version
        "db_paths": {"type": "list", "required": True, "validator": validate_db_paths},
    },
    
    # Script Details Tool - Requires script_name only
    "get_script_details": {
        "script_name": {"type": "str", "required": True, "validator": validate_script_names},
    },
    "get_script_details_tool": {  # Add the _tool suffix version
        "script_name": {"type": "str", "required": True, "validator": validate_script_names},
        "script_path": {"type": "str", "required": True},  # Also requires script_path
    },
    
    # Custom Functions Tool - Requires db_path
    "get_custom_functions": {
        "db_path": {"type": "str", "required": True, "validator": validate_db_paths},
    },
    "get_custom_functions_tool": {  # Add the _tool suffix version
        "db_path": {"type": "str", "required": True, "validator": validate_db_paths},
    },
    
    # Large Result Handler Tools
    "read_file_content": {
        "file_path": {"type": "str", "required": True},
        "chunk_size": {"type": "int", "required": False},
    },
    "read_file_content_tool": {  # Add the _tool suffix version
        "file_path": {"type": "str", "required": False},
        "file_name": {"type": "str", "required": False},
        "chunk_size": {"type": "int", "required": False},
    },
    
    "read_chunk": {
        "chunk_path": {"type": "str", "required": True},
    },
    "read_chunk_tool": {  # Add the _tool suffix version
        "chunk_path": {"type": "str", "required": False},
        "chunk_name": {"type": "str", "required": False},
    },
    
    "cleanup_old_files": {
        "max_age_seconds": {"type": "int", "required": False},
    },
    "cleanup_old_files_tool": {  # Add the _tool suffix version
        "max_age_seconds": {"type": "int", "required": False},
    },
    
    # Database by Name Tool - Requires db_name
    "get_database_by_name": {
        "db_name": {"type": "str", "required": True, "validator": validate_db_names},
    },
    
    # Databases by Names Tool - Requires db_names
    "get_databases_by_names": {
        "db_names": {"type": "list", "required": True, "validator": validate_db_names},
    }
}

# Create a wrapper around MCPServerStdio to validate tool calls
class ValidatingMCPServerStdio(MCPServerStdio):
    """A wrapper around MCPServerStdio that validates tool calls before executing them."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.agent = None
        self.model = None
    
    def set_agent(self, agent):
        """Set the agent for this server."""
        self.agent = agent
        self.model = agent.model
    
    async def call_tool(self, name, arguments):
        """
        Validate tool arguments before calling the tool.
        
        Args:
            name: The name of the tool to call
            arguments: The arguments to pass to the tool
            
        Returns:
            The result of the tool call
        """
        print(f"\n--- DEBUG: ValidatingMCPServerStdio.call_tool called for {name} with arguments: {arguments} ---")
        
        # Apply the validation decorator
        # Store a reference to self for use in the nested function
        outer_self = self
        
        @validate_tool_parameters(tool_specs.get(name, {}))
        async def call_tool_with_validation(name, **kwargs):
            # Use the stored reference to self instead of super()
            return await MCPServerStdio.call_tool(outer_self, name, kwargs)
        
        try:
            # Call the tool with validation
            if isinstance(arguments, str):
                try:
                    arguments = json.loads(arguments)
                except json.JSONDecodeError:
                    # If it's not valid JSON, keep it as is
                    pass
            
            return await call_tool_with_validation(name, **arguments)
        except ToolParameterValidationError as e:
            # LLM Revision Mechanism
            print(f"Tool parameter validation error: {e}")
            error_dict = e.to_dict()
            
            # Send the error message and original parameters to the LLM
            try:
                llm_response = await self.revise_parameters(name, error_dict["original_params"], error_dict["changes"])
                
                # Retry the validation with the revised parameters
                try:
                    revised_params = llm_response["revised_parameters"]
                    return await call_tool_with_validation(name, **revised_params)
                except ToolParameterValidationError as e:
                    print(f"Tool parameter validation failed after revision: {e}")
                    raise  # Re-raise the original exception
            except Exception as e:
                print(f"Error during parameter revision: {e}")
                raise  # Re-raise the original exception
    
    async def revise_parameters(self, tool_name: str, original_params: Dict[str, Any], changes: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        Send the error message and original parameters to the LLM and get a revised response.
        
        Args:
            tool_name: The name of the tool that failed validation.
            original_params: The original parameters passed to the tool.
            changes: A list of dictionaries containing information about the validation errors.
            
        Returns:
            A dictionary containing the revised parameters from the LLM.
        """
        if not self.agent:
            raise ValueError("Agent not set. Call set_agent() before using revise_parameters().")
        
        # Construct the message to send to the LLM
        message = f"Tool '{tool_name}' failed validation with the following errors:\n"
        for change in changes:
            message += f"- Parameter '{change['parameter']}': {change['reason']} (Original value: {change['original_value']})\n"
        message += f"Original parameters: {original_params}\n"
        message += "Please provide revised parameters in the following JSON format:\n"
        message += """
        {
            "revised_parameters": {
                "param1": "new_value",
                "param2": 123
            },
            "changes": [
                {
                    "parameter": "param1",
                    "reason": "The original value was invalid because...",
                    "original_value": "old_value"
                },
                {
                    "parameter": "param2",
                    "reason": "The original value was not an integer.",
                    "original_value": "abc"
                }
            ]
        }
        """
        
        # Create a temporary agent with the same model and instructions
        temp_agent = Agent(
            name="Parameter Revision Agent",
            instructions="You are a helpful assistant that revises tool parameters based on validation errors.",
            model=self.model
        )
        
        # Run the agent with the message
        result = await Runner.run(starting_agent=temp_agent, input=message)
        
        # Parse the JSON response
        try:
            response_text = result.final_output
            # Extract JSON from the response
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                json_str = response_text[json_start:json_end]
                llm_response = json.loads(json_str)
                return llm_response
            else:
                raise ValueError("No JSON found in LLM response")
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON response from LLM: {e}")
