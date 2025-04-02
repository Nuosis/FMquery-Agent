import json
import time
import asyncio
from typing import Dict, List, Any, Optional, Tuple, Callable
from agents.mcp import MCPServer, MCPServerStdio
from agents import Agent, Runner

from orchestration.cache_hierarchy import schema_cache, table_cache, script_cache
from orchestration.dependency_manager import DependencyGraph, DependencyResolver
from cache import db_info_cache
from validation_decorator import ToolParameterValidationError


class CacheChecker:
    """
    A class to check if dependencies are satisfied in the cache.
    """
    def __init__(self):
        """
        Initialize the cache checker.
        """
        pass
    
    async def is_dependency_satisfied(self, tool_name: str, arguments: Dict[str, Any] = None) -> bool:
        """
        Check if a dependency is satisfied in the cache.
        
        Args:
            tool_name: The name of the tool
            arguments: The arguments for the tool (optional)
            
        Returns:
            True if the dependency is satisfied, False otherwise
        """
        # For discover_databases, check if the database info cache is valid
        if tool_name == 'discover_databases':
            return db_info_cache.is_valid()
        
        # For get_schema_information, check if the schema cache is valid for the specified database
        elif tool_name == 'get_schema_information':
            if not arguments or 'db_paths' not in arguments:
                return False
            
            # For each database path, check if we have schema information
            db_paths = arguments['db_paths']
            if isinstance(db_paths, str):
                db_paths = [db_paths]
            
            # Get database names from paths
            db_names = []
            for db_path in db_paths:
                # Find the database with this path
                if not db_info_cache.is_valid():
                    return False
                
                for db in db_info_cache.db_info.get('databases', []):
                    if db.get('path') == db_path:
                        db_names.append(db.get('name'))
                        break
            
            # Check if we have schema information for each database
            for db_name in db_names:
                # We need to check if any schema is cached for this database
                # This is a simplification - in reality, we'd need to check specific schemas
                schema_keys = [key for key in schema_cache.get_keys() if key.startswith(f"db:{db_name}:schema:")]
                if not schema_keys:
                    return False
            
            return True
        
        # For get_table_information, check if the table cache is valid for the specified table
        elif tool_name == 'get_table_information':
            if not arguments or 'table_name' not in arguments:
                return False
            
            # We need the database name and schema name to check the table cache
            # This information should be in the arguments
            if 'db_name' not in arguments or 'schema_name' not in arguments:
                return False
            
            table_name = arguments['table_name']
            db_name = arguments['db_name']
            schema_name = arguments['schema_name']
            
            # Check if the table is in the cache
            return table_cache.get_table(db_name, schema_name, table_name) is not None
        
        # For get_script_information, check if the script cache is valid
        elif tool_name == 'get_script_information':
            if not arguments or 'db_paths' not in arguments:
                return False
            
            # For now, just check if we have any scripts in the cache
            # This is a simplification - in reality, we'd need to check specific scripts
            return len(script_cache.get_scripts()) > 0
        
        # For get_script_details, check if the script details are in the cache
        elif tool_name == 'get_script_details':
            if not arguments or 'script_name' not in arguments:
                return False
            
            script_name = arguments['script_name']
            
            # Check if the script is in the cache
            return script_cache.get_script(script_name) is not None
        
        # For get_custom_functions, check if the database info cache is valid
        elif tool_name == 'get_custom_functions':
            return db_info_cache.is_valid()
        
        # For get_database_by_name and get_databases_by_names, check if the database info cache is valid
        elif tool_name in ['get_database_by_name', 'get_databases_by_names']:
            return db_info_cache.is_valid()
        
        # For file handling tools, always return True (no dependencies)
        elif tool_name in ['read_file_content', 'read_chunk', 'cleanup_old_files']:
            return True
        
        # Default case - unknown tool
        return False


class ToolRunner:
    """
    A class to run tools with proper validation and caching.
    """
    def __init__(self, mcp_server: MCPServer):
        """
        Initialize the tool runner.
        
        Args:
            mcp_server: The MCP server to use for tool calls
        """
        self.mcp_server = mcp_server
    
    async def run_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """
        Run a tool with the specified arguments.
        
        Args:
            tool_name: The name of the tool to run
            arguments: The arguments for the tool
            
        Returns:
            The result of the tool call
        """
        print(f"\n--- DEBUG: {tool_name}  called with arguments: {arguments} ---")
        
        try:
            # Use MCPServerStdio.call_tool directly to bypass the orchestration layer
            result = await MCPServerStdio.call_tool(self.mcp_server, tool_name, arguments)

            
            # Process and cache the result
            await self._process_and_cache_result(tool_name, arguments, result)
            
            return result
        except Exception as e:
            print(f"Error running tool {tool_name}: {e}")
            raise
    
    async def _process_and_cache_result(self, tool_name: str, arguments: Dict[str, Any], result: Any) -> None:
        """
        Process and cache the result of a tool call.
        
        Args:
            tool_name: The name of the tool
            arguments: The arguments for the tool
            result: The result of the tool call
        """
        print(f"\n--- DEBUG: _process_and_cache_result called for {tool_name} with arguments: {arguments}")
        print(f"--- DEBUG: Result type: {type(result)}")
        
        # Extract the text content from the result
        content = None
        if hasattr(result, 'content') and result.content:
            print(f"--- DEBUG: Result has content with {len(result.content)} items")
            for i, content_item in enumerate(result.content):
                print(f"--- DEBUG: Processing content item {i}")
                if hasattr(content_item, 'text') and content_item.text:
                    print(f"--- DEBUG: Content item has text: {content_item.text[:100]}...")  # Print first 100 chars
                    try:
                        content = json.loads(content_item.text)
                        print(f"--- DEBUG: Successfully parsed JSON content")
                        break
                    except json.JSONDecodeError as e:
                        print(f"--- DEBUG: JSON decode error: {e}")
                        # If it's not valid JSON, keep it as is
                        content = content_item.text
        
        if content is None:
            print(f"Warning: Could not extract content from result for tool {tool_name}")
            return
        
        print(f"--- DEBUG: Content type: {type(content)}")
        if isinstance(content, dict):
            print(f"--- DEBUG: Content keys: {content.keys()}")
        # Cache the result based on the tool
        if tool_name == 'discover_databases' or tool_name == 'discover_databases_tool':
            # Ensure content is a dictionary before using get
            if isinstance(content, dict):
                print(f"Updating db_info_cache with content: {content.keys()}")
                db_info_cache.update(content)
                print(f"Updated database info cache with {len(content.get('databases', []))} databases")
                # Verify the cache was updated
                paths = db_info_cache.get_paths()
                print(f"After update, db_info_cache.get_paths() returns: {paths}")
            else:
                print(f"Warning: Content is not a dictionary for tool {tool_name}: {content}")
                # Don't try to access content.get if it's not a dictionary
        
        elif tool_name == 'get_schema_information':
            # Cache schema information
            if isinstance(content, dict) and 'schemas' in content:
                for schema in content['schemas']:
                    db_name = schema.get('database_name', '')
                    schema_name = schema.get('name', '')
                    if db_name and schema_name:
                        schema_cache.update_schema(db_name, schema_name, schema)
                        print(f"Updated schema cache for {db_name}.{schema_name}")
            else:
                print(f"Warning: Content is not a dictionary or missing 'schemas' for tool {tool_name}: {content}")
        
        elif tool_name == 'get_table_information':
            # Cache table information
            if isinstance(content, dict) and 'table' in content:
                table = content['table']
                db_name = table.get('database_name', '')
                schema_name = table.get('schema_name', '')
                table_name = table.get('name', '')
                if db_name and schema_name and table_name:
                    table_cache.update_table(db_name, schema_name, table_name, table)
                    print(f"Updated table cache for {db_name}.{schema_name}.{table_name}")
            else:
                print(f"Warning: Content is not a dictionary or missing 'table' for tool {tool_name}: {content}")
        
        elif tool_name == 'get_script_information':
            # Cache script information
            if isinstance(content, dict) and 'scripts' in content:
                for script in content['scripts']:
                    script_id = script.get('id', '')
                    if script_id:
                        script_cache.update_script(script_id, script)
                        print(f"Updated script cache for script {script_id}")
            else:
                print(f"Warning: Content is not a dictionary or missing 'scripts' for tool {tool_name}: {content}")
        
        elif tool_name == 'get_script_details':
            # Cache script details
            if isinstance(content, dict) and 'script' in content:
                script = content['script']
                script_id = script.get('id', '')
                if script_id:
                    script_cache.update_script(script_id, script)
                    print(f"Updated script details cache for script {script_id}")
            else:
                print(f"Warning: Content is not a dictionary or missing 'script' for tool {tool_name}: {content}")


class Orchestrator:
    """
    The main orchestration engine that coordinates tool calls, checks dependencies, and manages the cache.
    """
    def __init__(self, mcp_server: MCPServer):
        """
        Initialize the orchestrator.
        
        Args:
            mcp_server: The MCP server to use for tool calls
        """
        self.mcp_server = mcp_server
        self.dependency_graph = DependencyGraph()
        self.dependency_resolver = DependencyResolver(self.dependency_graph)
        self.cache_checker = CacheChecker()
        self.tool_runner = ToolRunner(mcp_server)
        self.original_arguments = {}  # Initialize original_arguments
    
    async def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """
        Execute a tool with the specified arguments, ensuring all dependencies are satisfied.
        
        Args:
            tool_name: The name of the tool to execute
            arguments: The arguments for the tool
            
        Returns:
            The result of the tool call
        """
        print(f"\n--- DEBUG: Orchestrator.execute_tool called for {tool_name} with arguments: {arguments} ---")
        
        # Ensure arguments is a dictionary
        if arguments is None:
            arguments = {}
            
        # Store original arguments for later use
        original_arguments = arguments.copy()
        
        # Store the original arguments in the orchestrator for this tool
        if hasattr(self.mcp_server, 'original_arguments') and self.mcp_server.original_arguments:
            self.original_arguments = self.mcp_server.original_arguments
            print(f"--- DEBUG: Stored MCP server original arguments in orchestrator: {self.original_arguments}")
            
        # Check if the tool exists in the dependency graph
        if tool_name not in self.dependency_graph.graph:
            print(f"Warning: Tool {tool_name} not found in dependency graph, executing directly")
            return await self.tool_runner.run_tool(tool_name, arguments)
        
        # Check if all dependencies are satisfied
        dependencies_satisfied, missing_dependencies = await self.dependency_resolver.resolve_dependencies(
            tool_name, self.cache_checker
        )
        
        # If all dependencies are satisfied, execute the tool with the original arguments
        if dependencies_satisfied:
            # First try to use the orchestrator's original_arguments
            if self.original_arguments:
                print(f"All dependencies satisfied for tool {tool_name}, executing with orchestrator original arguments: {self.original_arguments}")
                return await self.tool_runner.run_tool(tool_name, self.original_arguments)
            # Then try to use the MCP server's original_arguments
            elif hasattr(self.mcp_server, 'original_arguments') and self.mcp_server.original_arguments:
                print(f"All dependencies satisfied for tool {tool_name}, executing with MCP server original arguments: {self.mcp_server.original_arguments}")
                return await self.tool_runner.run_tool(tool_name, self.mcp_server.original_arguments)
            # Finally, fall back to the original_arguments passed to this method
            else:
                print(f"All dependencies satisfied for tool {tool_name}, executing with original arguments: {original_arguments}")
                return await self.tool_runner.run_tool(tool_name, original_arguments)
        
        # If there are missing dependencies, execute them first
        print(f"Missing dependencies for tool {tool_name}: {missing_dependencies}")
        
        # Get the execution plan
        execution_plan = self.dependency_resolver.get_execution_plan(tool_name)
        
        # Execute each tool in the plan
        for plan_tool in execution_plan:
            # Skip tools that are not in the missing dependencies
            if plan_tool not in missing_dependencies and plan_tool != tool_name:
                continue
            
            # Get the arguments for the dependency
            dependency_arguments = self._get_dependency_arguments(plan_tool, arguments)
            
            # Execute the dependency
            print(f"Executing dependency {plan_tool} with arguments: {dependency_arguments}")
            await self.tool_runner.run_tool(plan_tool, dependency_arguments)
        
        # Now execute the original tool with the original arguments
        # First try to use the orchestrator's original_arguments
        if self.original_arguments:
            print(f"Dependencies satisfied, executing original tool {tool_name} with orchestrator original arguments: {self.original_arguments}")
            return await self.tool_runner.run_tool(tool_name, self.original_arguments)
        # Then try to use the MCP server's original_arguments
        elif hasattr(self.mcp_server, 'original_arguments') and self.mcp_server.original_arguments:
            print(f"Dependencies satisfied, executing original tool {tool_name} with MCP server original arguments: {self.mcp_server.original_arguments}")
            return await self.tool_runner.run_tool(tool_name, self.mcp_server.original_arguments)
        # Finally, fall back to the original_arguments passed to this method
        else:
            print(f"Dependencies satisfied, executing original tool {tool_name} with original arguments: {original_arguments}")
            return await self.tool_runner.run_tool(tool_name, original_arguments)
    
    def _get_dependency_arguments(self, tool_name: str, original_arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get the arguments for a dependency based on the original tool arguments.
        
        Args:
            tool_name: The name of the dependency tool
            original_arguments: The arguments for the original tool
            
        Returns:
            The arguments for the dependency tool
        """
        print(f"--- DEBUG: _get_dependency_arguments called for {tool_name} with original arguments: {original_arguments}")
        
        # For discover_databases_tool, no arguments are needed
        if tool_name == 'discover_databases' or tool_name == 'discover_databases_tool':
            return {}
        
        # For get_schema_information_tool, we need db_paths
        elif tool_name == 'get_schema_information' or tool_name == 'get_schema_information_tool':
            # If the original tool is get_table_information, we need to get the db_path from the db_name
            if 'db_name' in original_arguments:
                db_name = original_arguments['db_name']
                # Find the database path for this name
                if db_info_cache.is_valid():
                    for db in db_info_cache.db_info.get('databases', []):
                        if db.get('name') == db_name:
                            return {'db_paths': [db.get('path')]}
            
            # If db_paths is in the original arguments, use it
            if 'db_paths' in original_arguments:
                return {'db_paths': original_arguments['db_paths']}
            
            # Default case - use all available database paths
            paths = db_info_cache.get_paths()
            print(f"--- DEBUG: Using all available database paths: {paths}")
            return {'db_paths': paths}
        
        # For get_script_information_tool, we need db_paths
        elif tool_name == 'get_script_information' or tool_name == 'get_script_information_tool':
            # If db_paths is in the original arguments, use it
            if 'db_paths' in original_arguments:
                return {'db_paths': original_arguments['db_paths']}
            
            # Default case - use all available database paths
            paths = db_info_cache.get_paths()
            print(f"--- DEBUG: Using all available database paths: {paths}")
            return {'db_paths': paths}
        
        # For get_table_information_tool, we need table_name and table_path
        elif tool_name == 'get_table_information' or tool_name == 'get_table_information_tool':
            # If table_name and table_path are in the original arguments, use them
            if 'table_name' in original_arguments and 'table_path' in original_arguments:
                return {
                    'table_name': original_arguments['table_name'],
                    'table_path': original_arguments['table_path']
                }
            # If table_name and db_path are in the original arguments, use them
            elif 'table_name' in original_arguments and 'db_path' in original_arguments:
                return {
                    'table_name': original_arguments['table_name'],
                    'table_path': original_arguments['db_path']
                }
            # If table_name, db_name, and schema_name are in the original arguments, try to find the path
            elif 'table_name' in original_arguments and 'db_name' in original_arguments:
                table_name = original_arguments['table_name']
                db_name = original_arguments['db_name']
                # Try to find the database path for this name
                if db_info_cache.is_valid():
                    for db in db_info_cache.db_info.get('databases', []):
                        if db.get('name') == db_name:
                            return {
                                'table_name': table_name,
                                'table_path': db.get('path')
                            }
            
            # Default case - empty arguments with warning
            print(f"--- WARNING: Could not determine arguments for {tool_name}")
            return {}
        
        # Default case - empty arguments
        print(f"--- DEBUG: No specific argument handling for {tool_name}, returning empty dict")
        return {}