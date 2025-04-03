import json
from typing import Dict, List, Any, Optional, Tuple
from agents.mcp import MCPServerStdio
from agents import Agent, Runner

from validation.validation import ValidatingMCPServerStdio, tool_specs
from validation.validation_decorator import validate_tool_parameters, ToolParameterValidationError
from orchestration.orchestrator import Orchestrator
from utils.logging_utils import logger, log_failure


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
        logger.debug("OrchestrationMCPServerStdio initialized")
    
    def set_agent(self, agent):
        """
        Set the agent for this server and initialize the orchestrator.
        
        Args:
            agent: The agent to use
        """
        super().set_agent(agent)
        self.orchestrator = Orchestrator(self)
        logger.info("Agent set and orchestrator initialized")
    
    async def call_tool(self, name, arguments):
        """
        Validate tool arguments and orchestrate tool execution.
        
        Args:
            name: The name of the tool to call
            arguments: The arguments to pass to the tool
            
        Returns:
            The result of the tool call
        """
        logger.debug("OrchestrationMCPServerStdio.call_tool called for %s", name)
        
        # Ensure the orchestrator is initialized
        if self.orchestrator is None:
            error_msg = "Orchestrator not initialized. Call set_agent() before using call_tool()"
            # Log a concise message at INFO level
            log_failure("Tool execution", "Orchestrator not initialized", "Raising exception")
            # Log detailed error at DEBUG level
            logger.debug(error_msg)
            raise ValueError(error_msg)
        
        # Apply the validation decorator
        # Store a reference to self for use in the nested function
        outer_self = self
        
        @validate_tool_parameters(tool_specs.get(name, {}))
        async def call_tool_with_validation(name, **kwargs):
            # Use the orchestrator to execute the tool
            # Pass the arguments correctly
            logger.debug("Passing arguments to execute_tool: %s", kwargs)
            # Store the original arguments in a variable that will be accessible to the orchestrator
            outer_self.original_arguments = kwargs
            # Also store the original arguments in the orchestrator
            if outer_self.orchestrator:
                outer_self.orchestrator.original_arguments = kwargs
                logger.debug("Stored original arguments in orchestrator")
            return await outer_self.orchestrator.execute_tool(name, kwargs)
        
        try:
            # Parse arguments if they're a string
            if isinstance(arguments, str):
                try:
                    arguments = json.loads(arguments)
                    logger.debug("Parsed arguments from JSON string")
                except json.JSONDecodeError:
                    # If it's not valid JSON, keep it as is
                    logger.debug("Arguments are not valid JSON, using as-is")
                    pass
            
            # Call the tool with validation and orchestration
            logger.debug("Calling tool %s with validation", name)
            result = await call_tool_with_validation(name, **arguments)
            logger.debug("Tool call completed with result type: %s", type(result))
            return result
        except ToolParameterValidationError as e:
            # LLM Revision Mechanism
            logger.debug("Tool parameter validation error: %s", e)
            error_dict = e.to_dict()
            
            # Send the error message and original parameters to the LLM
            try:
                logger.info("Requesting parameter revision from LLM for tool '%s' with arguments: %s", name, error_dict["original_params"])
                llm_response = await self.revise_parameters(name, error_dict["original_params"], error_dict["changes"])
                
                # Retry the validation with the revised parameters
                try:
                    revised_params = llm_response["revised_parameters"]
                    logger.info("Retrying tool call '%s' with revised parameters: %s", name, revised_params)
                    return await call_tool_with_validation(name, **revised_params)
                except ToolParameterValidationError as e:
                    log_failure("Tool parameter validation",
                               f"Validation failed after revision for tool '{name}'",
                               f"Original args: {error_dict['original_params']}, Revised args: {revised_params}")
                    raise  # Re-raise the original exception
            except Exception as e:
                log_failure("Parameter revision", f"Error during revision for tool '{name}': {str(e)}",
                           f"Original args: {error_dict['original_params']}")
                raise  # Re-raise the original exception