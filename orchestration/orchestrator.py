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
from logging_utils import logger, log_orchestration_intervention, log_failure


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
        logger.debug("Checking if dependency is satisfied for tool: %s", tool_name)
        
        # For discover_databases, check if the database info cache is valid
        if tool_name == 'discover_databases':
            is_valid = db_info_cache.is_valid()
            logger.debug("Database info cache is %s", "valid" if is_valid else "invalid")
            return is_valid
        
        # For get_schema_information, check if the schema cache is valid for the specified database
        elif tool_name == 'get_schema_information':
            if not arguments or 'db_paths' not in arguments:
                logger.debug("No db_paths in arguments for get_schema_information")
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
                    logger.debug("Database info cache is invalid")
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
                    logger.debug("No schema information for database: %s", db_name)
                    return False
            
            logger.debug("Schema information is available for all databases")
            return True
        
        # For get_table_information, check if the table cache is valid for the specified table
        elif tool_name == 'get_table_information':
            if not arguments or 'table_name' not in arguments:
                logger.debug("No table_name in arguments for get_table_information")
                return False
            
            # We need the database name and schema name to check the table cache
            # This information should be in the arguments
            if 'db_name' not in arguments or 'schema_name' not in arguments:
                logger.debug("Missing db_name or schema_name in arguments for get_table_information")
                return False
            
            table_name = arguments['table_name']
            db_name = arguments['db_name']
            schema_name = arguments['schema_name']
            
            # Check if the table is in the cache
            table_info = table_cache.get_table(db_name, schema_name, table_name)
            logger.debug("Table information for %s.%s.%s is %s", 
                        db_name, schema_name, table_name, 
                        "available" if table_info else "not available")
            return table_info is not None
        
        # For get_script_information, check if the script cache is valid
        elif tool_name == 'get_script_information':
            if not arguments or 'db_paths' not in arguments:
                logger.debug("No db_paths in arguments for get_script_information")
                return False
            
            # For now, just check if we have any scripts in the cache
            # This is a simplification - in reality, we'd need to check specific scripts
            scripts = script_cache.get_scripts()
            logger.debug("Script cache has %d scripts", len(scripts))
            return len(scripts) > 0
        
        # For get_script_details, check if the script details are in the cache
        elif tool_name == 'get_script_details':
            if not arguments or 'script_name' not in arguments:
                logger.debug("No script_name in arguments for get_script_details")
                return False
            
            script_name = arguments['script_name']
            
            # Check if the script is in the cache
            script_info = script_cache.get_script(script_name)
            logger.debug("Script information for %s is %s", 
                        script_name, "available" if script_info else "not available")
            return script_info is not None
        
        # For get_custom_functions, check if the database info cache is valid
        elif tool_name == 'get_custom_functions':
            is_valid = db_info_cache.is_valid()
            logger.debug("Database info cache is %s", "valid" if is_valid else "invalid")
            return is_valid
        
        # For get_database_by_name and get_databases_by_names, check if the database info cache is valid
        elif tool_name in ['get_database_by_name', 'get_databases_by_names']:
            is_valid = db_info_cache.is_valid()
            logger.debug("Database info cache is %s", "valid" if is_valid else "invalid")
            return is_valid
        
        # For file handling tools, always return True (no dependencies)
        elif tool_name in ['read_file_content', 'read_chunk', 'cleanup_old_files']:
            logger.debug("No dependencies for file handling tool: %s", tool_name)
            return True
        
        # Default case - unknown tool
        logger.debug("Unknown tool: %s", tool_name)
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
        logger.info("Running tool: %s with arguments: %s", tool_name, arguments)
        
        try:
            # Use MCPServerStdio.call_tool directly to bypass the orchestration layer
            result = await MCPServerStdio.call_tool(self.mcp_server, tool_name, arguments)

            
            # Process and cache the result
            await self._process_and_cache_result(tool_name, arguments, result)
            
            return result
        except Exception as e:
            log_failure(f"Tool {tool_name}", str(e))
            raise
    
    async def _process_and_cache_result(self, tool_name: str, arguments: Dict[str, Any], result: Any) -> None:
        """
        Process and cache the result of a tool call.
        
        Args:
            tool_name: The name of the tool
            arguments: The arguments for the tool
            result: The result of the tool call
        """
        logger.debug("Processing and caching result for tool: %s", tool_name)
        
        # Extract the text content from the result
        content = None
        if hasattr(result, 'content') and result.content:
            logger.debug("Result has content with %d items", len(result.content))
            for i, content_item in enumerate(result.content):
                if hasattr(content_item, 'text') and content_item.text:
                    logger.debug("Processing content item %d with text", i)
                    try:
                        content = json.loads(content_item.text)
                        logger.debug("Successfully parsed JSON content")
                        break
                    except json.JSONDecodeError as e:
                        logger.debug("JSON decode error: %s", e)
                        # If it's not valid JSON, keep it as is
                        content = content_item.text
        
        if content is None:
            logger.warning("Could not extract content from result for tool %s", tool_name)
            return
        
        # Cache the result based on the tool
        if tool_name == 'discover_databases' or tool_name == 'discover_databases_tool':
            # Ensure content is a dictionary before using get
            if isinstance(content, dict):
                logger.info("Updating database info cache with %d databases", 
                           len(content.get('databases', [])))
                db_info_cache.update(content)
                # Verify the cache was updated
                paths = db_info_cache.get_paths()
                logger.debug("After update, db_info_cache has %d paths", len(paths))
            else:
                logger.warning("Content is not a dictionary for tool %s", tool_name)
        
        elif tool_name == 'get_schema_information':
            # Cache schema information
            if isinstance(content, dict) and 'schemas' in content:
                schema_count = len(content['schemas'])
                logger.info("Caching %d schemas", schema_count)
                for schema in content['schemas']:
                    db_name = schema.get('database_name', '')
                    schema_name = schema.get('name', '')
                    if db_name and schema_name:
                        schema_cache.update_schema(db_name, schema_name, schema)
                        logger.debug("Updated schema cache for %s.%s", db_name, schema_name)
            else:
                logger.warning("Content is not a dictionary or missing 'schemas' for tool %s", tool_name)
        
        elif tool_name == 'get_table_information':
            # Cache table information
            if isinstance(content, dict) and 'table' in content:
                table = content['table']
                db_name = table.get('database_name', '')
                schema_name = table.get('schema_name', '')
                table_name = table.get('name', '')
                if db_name and schema_name and table_name:
                    table_cache.update_table(db_name, schema_name, table_name, table)
                    logger.info("Updated table cache for %s.%s.%s", db_name, schema_name, table_name)
            else:
                logger.warning("Content is not a dictionary or missing 'table' for tool %s", tool_name)
        
        elif tool_name == 'get_script_information':
            # Cache script information
            if isinstance(content, dict) and 'scripts' in content:
                script_count = len(content['scripts'])
                logger.info("Caching %d scripts", script_count)
                for script in content['scripts']:
                    script_id = script.get('id', '')
                    if script_id:
                        script_cache.update_script(script_id, script)
                        logger.debug("Updated script cache for script %s", script_id)
            else:
                logger.warning("Content is not a dictionary or missing 'scripts' for tool %s", tool_name)
        
        elif tool_name == 'get_script_details':
            # Cache script details
            if isinstance(content, dict) and 'script' in content:
                script = content['script']
                script_id = script.get('id', '')
                if script_id:
                    script_cache.update_script(script_id, script)
                    logger.info("Updated script details cache for script %s", script_id)
            else:
                logger.warning("Content is not a dictionary or missing 'script' for tool %s", tool_name)


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
        logger.debug("Orchestrator.execute_tool called for %s", tool_name)
        
        # Ensure arguments is a dictionary
        if arguments is None:
            arguments = {}
            
        # Store original arguments for later use
        original_arguments = arguments.copy()
        
        # Store the original arguments in the orchestrator for this tool
        if hasattr(self.mcp_server, 'original_arguments') and self.mcp_server.original_arguments:
            self.original_arguments = self.mcp_server.original_arguments
            logger.debug("Stored MCP server original arguments in orchestrator")
            
        # Check if the tool exists in the dependency graph
        if tool_name not in self.dependency_graph.graph:
            logger.info("Tool %s not found in dependency graph, executing directly", tool_name)
            return await self.tool_runner.run_tool(tool_name, arguments)
        
        # Check if all dependencies are satisfied
        dependencies_satisfied, missing_dependencies = await self.dependency_resolver.resolve_dependencies(
            tool_name, self.cache_checker
        )
        
        # If all dependencies are satisfied, execute the tool with the original arguments
        if dependencies_satisfied:
            # First try to use the orchestrator's original_arguments
            if self.original_arguments:
                logger.info("All dependencies satisfied for tool %s, executing with orchestrator original arguments", tool_name)
                return await self.tool_runner.run_tool(tool_name, self.original_arguments)
            # Then try to use the MCP server's original_arguments
            elif hasattr(self.mcp_server, 'original_arguments') and self.mcp_server.original_arguments:
                logger.info("All dependencies satisfied for tool %s, executing with MCP server original arguments", tool_name)
                return await self.tool_runner.run_tool(tool_name, self.mcp_server.original_arguments)
            # Finally, fall back to the original_arguments passed to this method
            else:
                logger.info("All dependencies satisfied for tool %s, executing with original arguments", tool_name)
                return await self.tool_runner.run_tool(tool_name, original_arguments)
        
        # If there are missing dependencies, execute them first
        log_orchestration_intervention(
            tool_name, 
            f"Missing dependencies: {missing_dependencies}", 
            "Executing dependencies first"
        )
        
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
            logger.info("Executing dependency %s with arguments: %s", plan_tool, dependency_arguments)
            await self.tool_runner.run_tool(plan_tool, dependency_arguments)
        
        # Now execute the original tool with the original arguments
        # First try to use the orchestrator's original_arguments
        if self.original_arguments:
            logger.info("Dependencies satisfied, executing original tool %s with orchestrator original arguments", tool_name)
            return await self.tool_runner.run_tool(tool_name, self.original_arguments)
        # Then try to use the MCP server's original_arguments
        elif hasattr(self.mcp_server, 'original_arguments') and self.mcp_server.original_arguments:
            logger.info("Dependencies satisfied, executing original tool %s with MCP server original arguments", tool_name)
            return await self.tool_runner.run_tool(tool_name, self.mcp_server.original_arguments)
        # Finally, fall back to the original_arguments passed to this method
        else:
            logger.info("Dependencies satisfied, executing original tool %s with original arguments", tool_name)
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
        logger.debug("Getting dependency arguments for %s", tool_name)
        
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
            logger.debug("Using all available database paths: %s", paths)
            return {'db_paths': paths}
        
        # For get_script_information_tool, we need db_paths
        elif tool_name == 'get_script_information' or tool_name == 'get_script_information_tool':
            # If db_paths is in the original arguments, use it
            if 'db_paths' in original_arguments:
                return {'db_paths': original_arguments['db_paths']}
            
            # Default case - use all available database paths
            paths = db_info_cache.get_paths()
            logger.debug("Using all available database paths: %s", paths)
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
            logger.warning("Could not determine arguments for %s", tool_name)
            return {}
        
        # Default case - empty arguments
        logger.debug("No specific argument handling for %s, returning empty dict", tool_name)
        return {}