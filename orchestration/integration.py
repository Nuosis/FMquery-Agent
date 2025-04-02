import json
from typing import Dict, List, Any, Optional, Tuple
from agents.mcp import MCPServerStdio
from agents import Agent, Runner

from validation import ValidatingMCPServerStdio, tool_specs
from validation_decorator import validate_tool_parameters, ToolParameterValidationError
from orchestration.orchestrator import Orchestrator


class OrchestrationMCPServerStdio(ValidatingMCPServerStdio):
    """
    A wrapper around ValidatingMCPServerStdio that adds orchestration capabilities.
    This class ensures that tool calls are executed in the correct order based on dependencies,
    and that all parameters are validated before execution.
    """
    
    def __init__(self, *args, **kwargs):
        """
        Initialize the orchestration MCP server.
        """
        super().__init__(*args, **kwargs)
        self.orchestrator = None
        self.original_arguments = {}  # Initialize original_arguments
    
    def set_agent(self, agent):
        """
        Set the agent for this server and initialize the orchestrator.
        
        Args:
            agent: The agent to use
        """
        super().set_agent(agent)
        self.orchestrator = Orchestrator(self)
    
    async def call_tool(self, name, arguments):
        """
        Validate tool arguments and orchestrate tool execution.
        
        Args:
            name: The name of the tool to call
            arguments: The arguments to pass to the tool
            
        Returns:
            The result of the tool call
        """
        print(f"\n--- DEBUG: OrchestrationMCPServerStdio.call_tool called for {name} with arguments: {arguments} ---")
        
        # Ensure the orchestrator is initialized
        if self.orchestrator is None:
            raise ValueError("Orchestrator not initialized. Call set_agent() before using call_tool().")
        
        # Apply the validation decorator
        # Store a reference to self for use in the nested function
        outer_self = self
        
        @validate_tool_parameters(tool_specs.get(name, {}))
        async def call_tool_with_validation(name, **kwargs):
            # Use the orchestrator to execute the tool
            # Pass the arguments correctly
            print(f"--- DEBUG: Passing arguments to execute_tool: {kwargs}")
            # Store the original arguments in a variable that will be accessible to the orchestrator
            outer_self.original_arguments = kwargs
            # Also store the original arguments in the orchestrator
            if outer_self.orchestrator:
                outer_self.orchestrator.original_arguments = kwargs
                print(f"--- DEBUG: Stored original arguments in orchestrator: {kwargs}")
            return await outer_self.orchestrator.execute_tool(name, kwargs)
        
        try:
            # Parse arguments if they're a string
            if isinstance(arguments, str):
                try:
                    arguments = json.loads(arguments)
                except json.JSONDecodeError:
                    # If it's not valid JSON, keep it as is
                    pass
            
            # Call the tool with validation and orchestration
            print(f"--- DEBUG: Calling call_tool_with_validation with arguments: {arguments}")
            result = await call_tool_with_validation(name, **arguments)
            print(f"--- DEBUG: call_tool_with_validation returned result type: {type(result)}")
            return result
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