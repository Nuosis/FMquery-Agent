from typing import Dict, List, Set, Any, Optional, Tuple
from collections import defaultdict, deque
from logging_utils import logger

class DependencyGraph:
    """
    A class to manage tool dependencies and determine execution order.
    """
    def __init__(self):
        """
        Initialize the dependency graph with predefined tool dependencies.
        """
        # Define the dependency graph
        # Each tool is mapped to a list of tools it depends on
        self.graph = {
            # Original tool names
            'discover_databases': [],
            'get_schema_information': ['discover_databases'],
            'get_table_information': ['discover_databases', 'get_schema_information'],
            'get_script_information': ['discover_databases'],
            'get_script_details': ['get_script_information'],
            'get_custom_functions': ['discover_databases'],
            'get_database_by_name': ['discover_databases'],
            'get_databases_by_names': ['discover_databases'],
            # File handling tools have no dependencies
            'read_file_content': [],
            'read_chunk': [],
            'cleanup_old_files': [],
            
            # Actual tool names used in the MCP server
            'discover_databases_tool': [],
            'get_schema_information_tool': ['discover_databases_tool'],
            'get_table_information_tool': ['discover_databases_tool', 'get_schema_information_tool'],
            'get_script_information_tool': ['discover_databases_tool'],
            'get_script_details_tool': ['get_script_information_tool'],
            'get_custom_functions_tool': ['discover_databases_tool'],
            'read_file_content_tool': [],
            'read_chunk_tool': [],
            'cleanup_old_files_tool': []
        }
        
        # Build the reverse graph for easier traversal
        self.reverse_graph = defaultdict(list)
        for tool, dependencies in self.graph.items():
            for dependency in dependencies:
                self.reverse_graph[dependency].append(tool)
        
        logger.debug("DependencyGraph initialized with %d tools", len(self.graph))
    
    def get_dependencies(self, tool_name: str) -> List[str]:
        """
        Get the direct dependencies for a tool.
        
        Args:
            tool_name: The name of the tool
            
        Returns:
            List of tool names that the specified tool depends on
        """
        dependencies = self.graph.get(tool_name, [])
        logger.debug("Tool %s has %d direct dependencies: %s", 
                    tool_name, len(dependencies), dependencies)
        return dependencies
    
    def get_dependents(self, tool_name: str) -> List[str]:
        """
        Get the tools that directly depend on the specified tool.
        
        Args:
            tool_name: The name of the tool
            
        Returns:
            List of tool names that depend on the specified tool
        """
        dependents = self.reverse_graph.get(tool_name, [])
        logger.debug("Tool %s has %d direct dependents: %s", 
                    tool_name, len(dependents), dependents)
        return dependents
    
    def get_all_dependencies(self, tool_name: str) -> Set[str]:
        """
        Get all dependencies for a tool (direct and indirect).
        
        Args:
            tool_name: The name of the tool
            
        Returns:
            Set of all tool names that the specified tool depends on
        """
        if tool_name not in self.graph:
            logger.warning("Tool %s not found in dependency graph", tool_name)
            return set()
        
        all_deps = set()
        queue = deque(self.graph[tool_name])
        
        while queue:
            dep = queue.popleft()
            if dep not in all_deps:
                all_deps.add(dep)
                queue.extend(self.graph.get(dep, []))
        
        logger.debug("Tool %s has %d total dependencies: %s", 
                    tool_name, len(all_deps), all_deps)
        return all_deps
    
    def get_execution_plan(self, tool_name: str) -> List[str]:
        """
        Get the execution plan for a tool, ensuring all dependencies are executed first.
        
        Args:
            tool_name: The name of the tool
            
        Returns:
            List of tool names in the order they should be executed
        """
        if tool_name not in self.graph:
            logger.warning("Tool %s not found in dependency graph", tool_name)
            return []
        
        # Get all dependencies
        all_deps = self.get_all_dependencies(tool_name)
        
        # Add the tool itself
        all_deps.add(tool_name)
        
        # Perform topological sort
        result = []
        visited = set()
        temp_visited = set()
        
        def visit(node):
            if node in temp_visited:
                error_msg = f"Circular dependency detected involving {node}"
                logger.error(error_msg)
                raise ValueError(error_msg)
            if node in visited:
                return
            
            temp_visited.add(node)
            
            for dep in self.graph.get(node, []):
                visit(dep)
            
            temp_visited.remove(node)
            visited.add(node)
            result.append(node)
        
        # Visit all nodes in the dependency graph
        for node in all_deps:
            if node not in visited:
                visit(node)
        
        logger.debug("Execution plan for %s: %s", tool_name, result)
        return result
    
    def add_tool(self, tool_name: str, dependencies: List[str] = None) -> None:
        """
        Add a new tool to the dependency graph.
        
        Args:
            tool_name: The name of the tool
            dependencies: List of tool names that the new tool depends on
        """
        if dependencies is None:
            dependencies = []
        
        self.graph[tool_name] = dependencies
        
        # Update the reverse graph
        for dependency in dependencies:
            self.reverse_graph[dependency].append(tool_name)
        
        logger.info("Added tool %s to dependency graph with dependencies: %s", 
                   tool_name, dependencies)
    
    def remove_tool(self, tool_name: str) -> None:
        """
        Remove a tool from the dependency graph.
        
        Args:
            tool_name: The name of the tool
        """
        if tool_name in self.graph:
            # Remove from the main graph
            dependencies = self.graph.pop(tool_name)
            
            # Remove from the reverse graph
            for dependency in dependencies:
                if tool_name in self.reverse_graph[dependency]:
                    self.reverse_graph[dependency].remove(tool_name)
            
            # Remove as a dependency for other tools
            for dependent in self.reverse_graph.get(tool_name, []):
                if tool_name in self.graph[dependent]:
                    self.graph[dependent].remove(tool_name)
            
            # Remove from the reverse graph
            if tool_name in self.reverse_graph:
                del self.reverse_graph[tool_name]
            
            logger.info("Removed tool %s from dependency graph", tool_name)
        else:
            logger.warning("Attempted to remove non-existent tool %s from dependency graph", 
                          tool_name)


class DependencyResolver:
    """
    A class to resolve dependencies for tool calls.
    """
    def __init__(self, dependency_graph: DependencyGraph):
        """
        Initialize the dependency resolver.
        
        Args:
            dependency_graph: The dependency graph to use
        """
        self.dependency_graph = dependency_graph
        logger.debug("DependencyResolver initialized")
    
    async def resolve_dependencies(self, tool_name: str, cache_checker) -> Tuple[bool, List[str]]:
        """
        Check if all dependencies for a tool are satisfied.
        
        Args:
            tool_name: The name of the tool
            cache_checker: An object that can check if data is in the cache
            
        Returns:
            Tuple of (dependencies_satisfied, missing_dependencies)
        """
        # Get the direct dependencies for the tool
        dependencies = self.dependency_graph.get_dependencies(tool_name)
        
        # If there are no dependencies, we're good to go
        if not dependencies:
            logger.debug("Tool %s has no dependencies", tool_name)
            return True, []
        
        # Check if each dependency is satisfied
        missing_dependencies = []
        for dependency in dependencies:
            # Check if the dependency's data is in the cache
            is_satisfied = await cache_checker.is_dependency_satisfied(dependency)
            if not is_satisfied:
                logger.debug("Dependency %s for tool %s is not satisfied", 
                            dependency, tool_name)
                missing_dependencies.append(dependency)
        
        # If there are no missing dependencies, we're good to go
        dependencies_satisfied = len(missing_dependencies) == 0
        if dependencies_satisfied:
            logger.debug("All dependencies for tool %s are satisfied", tool_name)
        else:
            logger.info("Tool %s has %d missing dependencies: %s", 
                       tool_name, len(missing_dependencies), missing_dependencies)
        
        return dependencies_satisfied, missing_dependencies
    
    def get_execution_plan(self, tool_name: str) -> List[str]:
        """
        Get the execution plan for a tool.
        
        Args:
            tool_name: The name of the tool
            
        Returns:
            List of tool names in the order they should be executed
        """
        plan = self.dependency_graph.get_execution_plan(tool_name)
        logger.debug("Execution plan for %s: %s", tool_name, plan)
        return plan


# Initialize the dependency graph
dependency_graph = DependencyGraph()