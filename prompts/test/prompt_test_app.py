"""
Simple Streamlit Testing Environment for Prompt Responses and Tool Calls

This is a simplified version that minimizes dependencies on the main project.
"""

import os
import sys
import json
import streamlit as st
from typing import Dict, Any, List, Optional

# Add parent directory to path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Import necessary modules
from prompts.prompts import available_prompts, get_prompt, get_filemaker_agent_prompt
from cache.cache import load_all_caches, db_info_cache, tools_cache

# Import OpenAI for API calls
import openai

# Set page configuration
st.set_page_config(
    page_title="Prompt Testing Environment",
    page_icon="🧪",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS to ensure the Generate Response button is blue
st.markdown("""
<style>
    .stButton>button {
        color: white;
        background-color: #0066cc;
        border-color: #0066cc;
    }
    .stButton>button:hover {
        color: white;
        background-color: #0052a3;
        border-color: #0052a3;
    }
</style>
""", unsafe_allow_html=True)

# Load all caches from disk
load_all_caches()

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

# Get available tools from the cache
available_tools = []
if tools_cache.tools_info and 'tools' in tools_cache.tools_info:
    for tool in tools_cache.tools_info['tools']:
        tool_name = tool.get('mcp_name', '')
        if tool_name:
            available_tools.append(tool_name)

# Initialize session state for storing app state
if "prompt_selected" not in st.session_state:
    st.session_state.prompt_selected = True  # Set to True by default since we have a default prompt
if "current_prompt" not in st.session_state:
    st.session_state.current_prompt = "base"  # Initialize with the default "base" prompt
if "response" not in st.session_state:
    st.session_state.response = None
if "question" not in st.session_state:
    st.session_state.question = ""
if "question_input" not in st.session_state:
    st.session_state.question_input = ""
if "cache_data" not in st.session_state:
    st.session_state.cache_data = cache_data
if "selected_tool" not in st.session_state:
    st.session_state.selected_tool = ""  # No tool selected by default

# Utility functions
def get_available_prompts() -> Dict[str, str]:
    """Get all available prompts from prompts.py."""
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
def generate_response(prompt_name: str, question: str, model: str = "gpt-4o-mini") -> Dict[str, Any]:
    """Generate a response using the OpenAI API without executing tools."""
    # Get the prompt template with cache data
    if prompt_name == "base":
        prompt_template = get_filemaker_agent_prompt(st.session_state.cache_data)
    else:
        prompt_template = get_prompt(prompt_name, st.session_state.cache_data)
    
    # Append the JSON-only instruction to the prompt
    prompt_template += "\n\nRespond in JSON only. No explanation necessary."
    
    # Create messages for the API call
    messages = [
        {"role": "system", "content": prompt_template},
        {"role": "user", "content": question}
    ]
    
    # Get the actual tool definitions from the tools_cache
    tools = []
    if tools_cache.tools_info and 'tools' in tools_cache.tools_info:
        for tool in tools_cache.tools_info['tools']:
            tool_name = tool.get('mcp_name', '')
            tool_description = tool.get('description', '')
            tool_parameters = {}
            
            # Build parameters schema
            if 'parameters' in tool:
                properties = {}
                required = []
                
                for param in tool['parameters']:
                    param_name = param.get('name', '')
                    param_type = param.get('type', 'string')
                    param_required = param.get('required', False)
                    param_description = param.get('description', '')
                    
                    # Convert parameter types to valid OpenAI schema types
                    if param_type.lower() == 'int':
                        openai_type = 'integer'
                    elif param_type.lower() == 'float':
                        openai_type = 'number'
                    elif param_type.lower() == 'bool':
                        openai_type = 'boolean'
                    elif param_type.lower() == 'list':
                        openai_type = 'array'
                    elif param_type.lower() == 'dict':
                        openai_type = 'object'
                    else:
                        openai_type = 'string'
                    
                    properties[param_name] = {
                        "type": openai_type,
                        "description": param_description
                    }
                    
                    if param_required:
                        required.append(param_name)
                
                tool_parameters = {
                    "type": "object",
                    "properties": properties
                }
                
                if required:
                    tool_parameters["required"] = required
            
            # Add the tool definition
            tools.append({
                "type": "function",
                "function": {
                    "name": tool_name,
                    "description": tool_description,
                    "parameters": tool_parameters
                }
            })
    
    # If no tools were found in the cache, use a generic tool definition
    if not tools:
        tools = [{"type": "function", "function": {"name": "any_tool", "description": "Any tool"}}]
    
    # Make the API call with tool choice set to "auto"
    response = openai.chat.completions.create(
        model=model,
        messages=messages,
        tools=tools,
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
            "tool_arguments": arguments,
            "prompt": prompt_template,
            "question": question,
            "messages": messages
        }
    else:
        # Return text response
        return {
            "is_tool_call": False,
            "text": message.content,
            "prompt": prompt_template,
            "question": question,
            "messages": messages
        }

def format_tool_call(tool_name: str, tool_arguments: Dict[str, Any]) -> str:
    """Format a tool call for display."""
    # Format the arguments as JSON with indentation
    formatted_args = json.dumps(tool_arguments, indent=2)
    
    # Format the raw JSON response
    raw_json = json.dumps({"tool": tool_name, "arguments": tool_arguments}, indent=2)
    
    # Create a formatted string
    formatted_call = f"""
    Tool: {tool_name}
    
    Arguments:
    ```json
    {formatted_args}
    ```
    
    Raw JSON Response:
    ```json
    {raw_json}
    ```
    """
    
    return formatted_call

def get_expected_parameters(tool_name: str) -> str:
    """Get the expected parameters for a tool."""
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

# Event handlers
def on_prompt_select():
    """Handle prompt selection event"""
    # Check if prompt_selector exists in session state
    if "prompt_selector" in st.session_state:
        st.session_state.prompt_selected = True
        st.session_state.current_prompt = st.session_state.prompt_selector
        st.session_state.response = None  # Clear previous response
        # Force a rerun to update the UI
        st.experimental_rerun()

def on_question_submit():
    """Handle question submission event"""
    if not st.session_state.prompt_selected:
        st.error("Please select a prompt first")
        return
    
    # Get the question from the text area
    question = st.session_state.question_input
    
    # Store the question in session state
    st.session_state.question = question
    
    # Generate response
    with st.spinner("Generating response..."):
        response = generate_response(
            st.session_state.current_prompt,
            question
        )
    
    # Store the response in session state
    st.session_state.response = response

# Main application
def main():
    """Main application function"""
    # Application header
    st.title("Prompt Testing Environment")
    st.markdown("""
    This application allows you to test prompt responses and tool calls without executing the tools.
    Select a prompt, enter a question, and see the response or tool call details.
    """)
    
    # Sidebar for configuration
    with st.sidebar:
        st.header("Configuration")
        
        # Model selection (for future use)
        model = st.selectbox(
            "Model",
            ["gpt-4o-mini", "gpt-4o", "gpt-4-turbo"],
            index=0
        )
        
        # Get available prompts
        available_prompt_dict = get_available_prompts()
        
        # Initialize prompt_selector in session state if it doesn't exist
        if "prompt_selector" not in st.session_state:
            # Set to "base" by default
            st.session_state.prompt_selector = "base"
        
        # Prompt selector
        st.selectbox(
            "Select Prompt (Required)",
            options=list(available_prompt_dict.keys()),
            format_func=lambda x: f"{x}: {available_prompt_dict[x][:50]}...",
            key="prompt_selector",
            on_change=on_prompt_select
        )
        
        # Display selected prompt info
        if st.session_state.prompt_selected:
            st.success(f"Using prompt: {st.session_state.current_prompt}")
    # Main content area - ensure clear separation between input and response
    st.markdown("---")
    col1, col2 = st.columns([1, 2])  # Input column 1/3, Response column 2/3
    
    
    # Input column
    with col1:
        st.header("Input")
        
        # Question input - always enabled since we have a default prompt
        st.text_area(
            "Enter your question",
            height=150,
            key="question_input",
            help="Enter a question to test the prompt response"
        )
        
        # Submit button - always enabled (explicitly set to blue)
        st.button(
            "Generate Response",
            on_click=on_question_submit,
            type="primary",
            use_container_width=True
        )
        
        # Tool selector dropdown
        if st.session_state.prompt_selected:
            st.selectbox(
                "Select a tool to see parameters",
                options=[""] + available_tools,
                index=0,  # Default to no tool selected
                format_func=lambda x: x if x else "No tool selected",
                key="selected_tool",
                help="Select a tool to see its expected parameters"
            )
            
            # Show tool parameters if a tool is selected
            if st.session_state.selected_tool:
                st.info(get_expected_parameters(st.session_state.selected_tool))
    
    # Output column
    with col2:
        st.header("Response")
        
        # Display response if available
        if st.session_state.response:
            response = st.session_state.response
            
            # Show the original question
            st.subheader("Question")
            st.write(st.session_state.question)
            
            # Show the prompt that was used
            st.subheader("Prompt Used")
            with st.expander("View Prompt"):
                st.code(response.get("prompt", "No prompt available"), language="text")
            
            # Show the response
            st.subheader("Result")
            
            if response.get("is_tool_call", False):
                # Display tool call details
                st.info("Tool Call Detected")
                
                # Format and display the tool call
                tool_name = response.get("tool_name", "unknown_tool")
                tool_args = response.get("tool_arguments", {})
                
                st.code(format_tool_call(tool_name, tool_args), language="text")
                
                # Add a copy button for the tool call
                st.download_button(
                    label="Copy Tool Call JSON",
                    data=json.dumps({
                        "prompt": response.get("prompt", ""),
                        "question": response.get("question", ""),
                        "tool": tool_name,
                        "arguments": tool_args
                    }, indent=2),
                    file_name=f"{tool_name}_call.json",
                    mime="application/json"
                )
                
                # Add a button to view the messages sent to the API
                with st.expander("View API Messages"):
                    st.json(response.get("messages", []))
            else:
                # Display text response
                st.write(response.get("text", "No response generated"))
                
                # Add a button to view the messages sent to the API
                with st.expander("View API Messages"):
                    st.json(response.get("messages", []))

if __name__ == "__main__":
    main()