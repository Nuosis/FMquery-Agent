"""
Utility functions for the Streamlit testing environment.

This module provides helper functions for:
1. Loading prompts from prompts.py
2. Generating responses without executing tools
3. Detecting and formatting tool calls
"""

import os
import sys
import json
import re
from typing import Dict, Any, List, Tuple, Optional, Union

# Add parent directory to path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Import from project modules
from prompts.prompts import available_prompts, get_prompt

# Import OpenAI for API calls
import openai

def get_available_prompts() -> Dict[str, str]:
    """
    Get all available prompts from prompts.py.
    
    Returns:
        Dict[str, str]: Dictionary of prompt names and their descriptions
    """
    prompt_dict = {}
    for name, prompt in available_prompts.items():
        # Extract first line as description or use name if not available
        description = name.capitalize()
        if prompt:
            first_line = prompt.strip().split('\n')[0]
            if first_line:
                description = first_line.strip().strip('"\'')
        
        prompt_dict[name] = description
    
    return prompt_dict

def generate_response(
    prompt_name: str, 
    question: str, 
    model: str = "gpt-4o-mini"
) -> Dict[str, Any]:
    """
    Generate a response using the OpenAI API without executing tools.
    
    Args:
        prompt_name: Name of the prompt to use
        question: User's question
        model: OpenAI model to use
        
    Returns:
        Dict containing either:
        - 'text': The text response if no tool call was made
        - 'tool_call': Tool call details if a tool would be called
    """
    # Get the prompt template
    prompt_template = get_prompt(prompt_name)
    
    # Create messages for the API call
    messages = [
        {"role": "system", "content": prompt_template},
        {"role": "user", "content": question}
    ]
    
    # Make the API call with tool choice set to "auto"
    response = openai.chat.completions.create(
        model=model,
        messages=messages,
        tools=[{"type": "function", "function": {"name": "any_tool", "description": "Any tool"}}],
        tool_choice="auto"
    )
    
    # Extract the response
    message = response.choices[0].message
    
    # Check if there's a tool call
    if message.tool_calls:
        tool_call = message.tool_calls[0]
        
        # Parse the function arguments
        try:
            arguments = json.loads(tool_call.function.arguments)
        except json.JSONDecodeError:
            arguments = tool_call.function.arguments
            
        # Return tool call details
        return {
            "is_tool_call": True,
            "tool_name": tool_call.function.name,
            "tool_arguments": arguments
        }
    else:
        # Return text response
        return {
            "is_tool_call": False,
            "text": message.content
        }

def format_tool_call(tool_name: str, tool_arguments: Dict[str, Any]) -> str:
    """
    Format a tool call for display.
    
    Args:
        tool_name: Name of the tool
        tool_arguments: Arguments for the tool
        
    Returns:
        Formatted string representation of the tool call
    """
    # Format the arguments as JSON with indentation
    formatted_args = json.dumps(tool_arguments, indent=2)
    
    # Create a formatted string
    formatted_call = f"""
    Tool: {tool_name}
    
    Arguments:
    ```json
    {formatted_args}
    ```
    """
    
    return formatted_call

def get_expected_parameters(tool_name: str) -> str:
    """
    Get the expected parameters for a tool.
    
    Args:
        tool_name: Name of the tool
        
    Returns:
        Formatted string describing the expected parameters
    """
    # Common tool parameters based on tool name patterns
    if "discover_databases" in tool_name:
        return f"""
        Tool: {tool_name}
        
        No parameters required for this tool.
        """
    elif "get_schema_information" in tool_name:
        return f"""
        Tool: {tool_name}
        
        Parameters:
        - db_paths (list, required): List of database paths to get schema information for
        """
    elif "get_table_information" in tool_name:
        return f"""
        Tool: {tool_name}
        
        Parameters:
        - table_name (str, required): Name of the table to get information for
        - table_path (str, required): Path to the table
        """
    elif "get_script_information" in tool_name:
        return f"""
        Tool: {tool_name}
        
        Parameters:
        - db_paths (list, required): List of database paths to get script information for
        """
    elif "get_script_details" in tool_name:
        return f"""
        Tool: {tool_name}
        
        Parameters:
        - script_name (str, required): Name of the script to get details for
        - script_path (str, required): Path to the script
        """
    elif "get_custom_functions" in tool_name:
        return f"""
        Tool: {tool_name}
        
        Parameters:
        - db_path (str, required): Database path to get custom functions for
        """
    else:
        return f"""
        Tool: {tool_name}
        
        Parameters information not available for this tool.
        Try entering a question that would use this tool to see what parameters it expects.
        """