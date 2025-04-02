"""
This module contains prompts for different agents used in the FMquery-Agent system.
Prompts can be selected and assigned to agent variables for use in the main application.

The module provides functions to:
1. Construct prompts by injecting cache data into placeholders
2. Serve prompts to agents or users
3. Generate specialized prompts for FileMaker agents
"""

from typing import Dict, Any, Optional
import re
import json

# Base FileMaker Agent prompt
filemaker_base_prompt = """
You are a sophisticated FileMaker database systems engineer built with the OpenAI Agents SDK.

## Project Overview
This agentic project,FMquery-Agent, allows users to query FileMaker databases using natural language, with intelligent caching and orchestration to improve performance and user experience.
FMquery-Agent connects to FileMaker databases through a Model Context Protocol (MCP) server, allowing users to:
- Discover available databases
- Query database schemas and table structures
- Retrieve script information
- Analyze relationships between tables
- Ask natural language questions about database content and structure

The agent maintains conversation context across multiple queries and uses a sophisticated caching and orchestration system to improve performance.

## Cache Structure
The project implements a hierarchical caching system to efficiently store and retrieve database information:

### Cache Hierarchy
1. **Database-level cache** (`DBInfoCache` in `cache.py`)
   - Stores basic database information (paths, names)
   - Cache key: Simple in-memory object
2. **Tools-level cache** (`ToolsCache` in `cache.py`)
   - Stores information about available tools from the MCP server
   - Cache key: Simple in-memory object
3. **Schema-level cache** (`SchemaCache` in `orchestration/cache_hierarchy.py`)
   - Stores schema information for each database
   - Cache key format: `db:{db_name}:schema:{schema_name}`
4. **Table-level cache** (`TableCache` in `orchestration/cache_hierarchy.py`)
   - Stores table information for each schema
   - Cache key format: `db:{db_name}:schema:{schema_name}:table:{table_name}`
5. **Script-level cache** (`ScriptCache` in `orchestration/cache_hierarchy.py`)
   - Stores script information
   - Cache key format: `script:{script_id}`

## Tool Descriptions and Examples
<<tool descriptions and examples here>>

### Dependency Graph
Tool dependencies are defined as follows:
<<dependency graph here>>

### HANDLING LARGE RESULTS:
Some tool results may be too large to process directly. In these cases, the tool will store the result in a file
and return a response with "status": "file_stored". When you receive such a response, use the file path provided
in the response to access the stored result.

If the file is very large, it may be chunked into multiple files. In this case, the response will have
"status": "file_chunked" and a list of "chunk_paths". You should retrieve each chunk and combine them.

Example workflow for handling large results:
1. If a tool returns {"status": "file_stored", "file_path": "/path/to/file.json"}, use the file path to access the content.
2. If a tool returns {"status": "file_chunked", "chunk_paths": ["/path/to/chunk1.json", "/path/to/chunk2.json"]},
   retrieve each chunk and combine them.

## Database Cache
<<database cache description here>>

## ADVANCED ANALYSIS TECHNIQUES:
When analyzing FileMaker databases:
1. Look for relationships between tables to understand data flow
2. Identify key scripts that handle core business logic
3. Pay attention to custom functions that may be used across the solution
4. Note any unusual table structures or naming conventions
"""
def construct_prompt(template: str, cache_data: dict) -> str:
    """
    Construct a prompt by replacing placeholders in the template with data from the cache.
    
    Handles two placeholder formats:
    1. <<insert placeholder_name here>> - Traditional format
    2. <<placeholder_name>> - Simplified format
    
    Args:
        template: A string containing the prompt template with placeholders.
        cache_data: A dictionary containing cached data to inject into the template.
        
    Returns:
        A string containing the constructed prompt with placeholders replaced.
    """
    result = template
    
    # Helper function to convert value to string
    def value_to_string(value):
        if not isinstance(value, str):
            if isinstance(value, (list, dict)):
                import json
                return json.dumps(value, indent=2)
            else:
                return str(value)
        return value
    
    # Replace placeholders in the format <<insert placeholder_name here>>
    for key, value in cache_data.items():
        placeholder = f"<<insert {key} here>>"
        if placeholder in result:
            value_str = value_to_string(value)
            result = result.replace(placeholder, value_str)
    
    # Replace placeholders in the format <<placeholder_name>>
    import re
    pattern = r'<<([^>]+)>>'
    matches = re.findall(pattern, result)
    
    for match in matches:
        placeholder = f"<<{match}>>"
        # Check if the key exists in cache_data
        if match in cache_data:
            value_str = value_to_string(cache_data[match])
            result = result.replace(placeholder, value_str)
    
    return result
    return result

def serve_prompt(prompt: str) -> str:
    """
    Serve the prompt to the user or agent.
    
    This function prepares the final prompt for delivery, performing any
    necessary formatting or validation. It removes any remaining placeholders
    and cleans up the formatting.
    
    Args:
        prompt: A string containing the prompt to serve.
        
    Returns:
        A string containing the served prompt, ready for use.
    """
    import re
    
    # Find and remove all placeholder formats
    # Format 1: <<insert placeholder_name here>>
    cleaned_prompt = re.sub(r'<<insert [^>]+ here>>', '', prompt)
    
    # Format 2: <<placeholder_name>>
    cleaned_prompt = re.sub(r'<<[^>]+>>', '', cleaned_prompt)
    
    # Remove any resulting empty lines (multiple newlines)
    cleaned_prompt = re.sub(r'\n{3,}', '\n\n', cleaned_prompt)
    
    return cleaned_prompt.strip()

def get_filemaker_agent_prompt(cache: dict) -> str:
    """
    Generate a prompt for the FileMaker agent using the base prompt and cache data.
    
    This function takes the cache dictionary and injects relevant data into
    the base FileMaker prompt template, replacing all placeholders with actual values.
    
    Args:
        cache: A dictionary containing cached data to inject into the prompt.
        
    Returns:
        A string containing the complete FileMaker agent prompt.
    """
    # Start with the base prompt
    prompt_template = filemaker_base_prompt
    
    # Prepare cache data for insertion
    cache_data = {}
    
    # Extract dependency graph if available
    dependency_info = []
    if 'dependency_graph' in cache:
        # If dependency graph is directly provided in the cache
        dependency_info = cache['dependency_graph']
    elif 'tool_dependencies' in cache:
        # If tool_dependencies is provided in the cache (from tools_cache)
        dependency_info = []
        tool_dependencies = cache['tool_dependencies']
        
        # Process each tool and its dependencies
        for tool_name, tool_info in tool_dependencies.items():
            # Convert MCP tool name to user-facing tool name (remove _tool suffix)
            user_tool_name = tool_name
            if user_tool_name.endswith('_tool'):
                user_tool_name = user_tool_name[:-5]
                
            # Get dependencies
            dependencies = tool_info.get('dependencies', [])
            
            if not dependencies:
                # No dependencies (foundational tool)
                dependency_info.append(f"- `{user_tool_name}`: No dependencies (foundational tool)")
            else:
                # Has dependencies
                # Convert dependency MCP names to user-facing names
                user_dependencies = []
                for dep in dependencies:
                    if dep.endswith('_tool'):
                        user_dependencies.append(f"`{dep[:-5]}`")
                    else:
                        user_dependencies.append(f"`{dep}`")
                
                # Format the dependency string
                if len(user_dependencies) == 1:
                    dependency_info.append(f"- `{user_tool_name}`: Requires output from {user_dependencies[0]}")
                else:
                    last_dep = user_dependencies.pop()
                    deps_str = ", ".join(user_dependencies)
                    dependency_info.append(f"- `{user_tool_name}`: Requires output from {deps_str} and {last_dep}")
    else:
        # Otherwise, construct it from the tools information
        if 'tools' in cache:
            # Create a simplified dependency graph description
            dependency_info = []
            tool_names = [tool.get('name', '') for tool in cache.get('tools', [])]
            
            # Add foundational tools (no dependencies)
            dependency_info.append("- `discover_databases`: No dependencies (foundational tool)")
            dependency_info.append("- `list_tools`: No dependencies (foundational tool)")
            
            # Add tools with dependencies
            if 'discover_databases_tool' in tool_names:
                dependency_info.append("- `get_schema_information`: Requires output from `discover_databases`")
                dependency_info.append("- `get_table_information`: Requires output from `discover_databases` and `get_schema_information`")
                dependency_info.append("- `get_script_information`: Requires output from `discover_databases`")
                dependency_info.append("- `get_custom_functions`: Requires output from `discover_databases`")
            
            if 'get_script_information_tool' in tool_names:
                dependency_info.append("- `get_script_details`: Requires output from `get_script_information`")
    
    # Add dependency graph to cache data
    if dependency_info:
        if isinstance(dependency_info, list):
            cache_data['dependency graph here'] = "\n".join(dependency_info)
        else:
            cache_data['dependency graph here'] = str(dependency_info)
    
    # Extract tool descriptions if available
    if 'tools' in cache:
        tool_descriptions = []
        for tool in cache.get('tools', []):
            name = tool.get('name', '')
            mcp_name = tool.get('mcp_name', '')
            
            # Process description to remove the original Args section
            description = tool.get('description', '')
            # Find the Args section in the description
            args_index = description.find("\nArgs:")
            if args_index != -1:
                # Find the Returns section that follows Args
                returns_index = description.find("\nReturns:", args_index)
                if returns_index != -1:
                    # Remove the Args section but keep the Returns section
                    description = description[:args_index] + description[returns_index:]
            
            return_type = tool.get('return_type', '')
            real_example = tool.get('real_example', '')
            
            # Format parameters
            params_str = ""
            parameters = tool.get('parameters', [])
            if parameters:
                params_str = "Args:"
                for param in parameters:
                    param_name = param.get('name', '')
                    param_required = param.get('required', False)
                    param_type = param.get('type', '')
                    param_default = param.get('default', None)
                    
                    required_str = "required" if param_required else "optional"
                    default_str = f", default={param_default}" if param_default is not None else ""
                    
                    params_str += f"\n- {param_name} ({required_str}, {param_type}{default_str})"
            
            # Format the tool description with minimal whitespace
            tool_desc = f"### {name}\n"
            tool_desc += f"MCP Tool Name: {mcp_name}\n"
            tool_desc += f"{description}"
            
            if params_str:
                tool_desc += f"\n{params_str}"
                
            tool_desc += f"\nReturn Type: {return_type}"
            tool_desc += f"\nExample:\n```\n{real_example}\n```"
            
            tool_descriptions.append(tool_desc)
        
        cache_data['tool descriptions and examples here'] = "\n".join(tool_descriptions)
    
    # Add database paths and names if available
    if 'db_paths' in cache and 'db_names' in cache:
        db_paths_str = ", ".join(cache['db_paths'])
        db_names_str = ", ".join(cache['db_names'])
        
        # Get database names and paths for the NAMES AND THEIR ASSOCIATED PATHS section
        names_and_paths = ""
        if 'databases' in cache:
            names_and_paths = "\n### NAMES AND THEIR ASSOCIATED PATHS:\n"
            for db in cache.get('databases', []):
                db_name = db.get('name', '')
                db_path = db.get('path', '')
                names_and_paths += f"- {db_name}: {db_path}\n"
        
        # Create database info section
        db_info_section = f"""
### AVAILABLE DATABASE PATHS:
[{db_paths_str}]

### AVAILABLE DATABASE NAMES:
[{db_names_str}]
{names_and_paths}
"""
        # Add the database info section to the prompt template
        # Find a good position to insert it - after the Database Cache section
        insert_pos = prompt_template.find("## Database Cache")
        if insert_pos != -1:
            # Find the end of that section (next section or end of file)
            next_section_pos = prompt_template.find("##", insert_pos + 1)
            if next_section_pos != -1:
                # Insert before the next section
                prompt_template = prompt_template[:next_section_pos] + db_info_section + prompt_template[next_section_pos:]
            else:
                # Insert at the end of the file
                prompt_template = prompt_template + db_info_section
        else:
            # If Database Cache section not found, just add to cache_data
            cache_data['database_info'] = db_info_section
    
    # Construct the prompt by replacing placeholders
    constructed_prompt = construct_prompt(prompt_template, cache_data)
    
    # Serve the final prompt
    return serve_prompt(constructed_prompt)

# Dictionary of available prompts
available_prompts = {
    "base": filemaker_base_prompt
}

# Default prompt to use
default_prompt = "base"

# Function to get a prompt by name
def get_prompt(prompt_name=None, cache=None):
    """
    Get a prompt by name and optionally inject cache data.
    
    Args:
        prompt_name: The name of the prompt to get (optional)
        cache: A dictionary containing cached data to inject into the prompt (optional)
        
    Returns:
        The prompt template or the constructed prompt if cache is provided
    """
    if prompt_name is None:
        prompt_name = default_prompt
    
    template = available_prompts.get(prompt_name, available_prompts[default_prompt])
    
    if cache is not None:
        # Construct and serve the prompt with cache data
        constructed = construct_prompt(template, cache)
        return serve_prompt(constructed)
    
    return template