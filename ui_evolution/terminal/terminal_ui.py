import streamlit as st
import asyncio
import os
import sys
from dotenv import load_dotenv

# Add the parent directory to the path so we can import from fmquery.py
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Import necessary functions from fmquery.py
from fmquery import (
    Agent, OrchestrationMCPServerStdio, run_query, 
    model_choice, mcp_server_path, ddrPath, customerName, get_prompt
)

# Load environment variables
load_dotenv()

# Set page config to mimic a terminal
st.set_page_config(
    page_title="Terminal UI Emulation",
    page_icon="🖥️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Apply custom CSS to make it look like an old terminal but with some improvements
st.markdown("""
<style>
    body {
        background-color: #000080; /* Classic blue background */
        color: #ffffff;
    }
    .stTextInput > div > div > input {
        background-color: #000080;
        color: #ffffff;
        border: 1px solid #ffffff;
        font-family: 'Courier New', monospace;
    }
    .stButton button {
        background-color: #0000aa;
        color: #ffffff;
        border: 1px solid #ffffff;
        font-family: 'Courier New', monospace;
    }
    pre {
        background-color: #000080;
        color: #ffffff;
        padding: 10px;
        font-family: 'Courier New', monospace;
        border: 1px solid #ffffff;
        overflow-x: auto;
    }
    .terminal {
        background-color: #000080;
        color: #ffffff;
        font-family: 'Courier New', monospace;
        padding: 10px;
        border: 1px solid #ffffff;
        height: 400px;
        overflow-y: auto;
    }
    .menu-item {
        background-color: #0000aa;
        color: #ffffff;
        padding: 5px 10px;
        margin: 2px;
        border: 1px solid #ffffff;
        cursor: pointer;
        display: inline-block;
        font-family: 'Courier New', monospace;
    }
    .menu-bar {
        background-color: #0000aa;
        padding: 5px;
        border-bottom: 1px solid #ffffff;
        margin-bottom: 10px;
    }
</style>
""", unsafe_allow_html=True)

# Title with a more structured header
st.markdown("""
<div class="menu-bar">
    <div class="menu-item">File</div>
    <div class="menu-item">Edit</div>
    <div class="menu-item">View</div>
    <div class="menu-item">Help</div>
</div>
<h2 style='color: #ffffff; font-family: Courier New, monospace; text-align: center;'>
    Terminal UI Emulation (circa 1980s)
</h2>
""", unsafe_allow_html=True)

# Initialize session state
if 'terminal_output' not in st.session_state:
    st.session_state.terminal_output = [
        "FileMaker Database Explorer v1.2",
        "Copyright (c) 2025 Terminal Systems",
        "Type 'help' for available commands or use the menu above",
        "------------------------------------",
        ""
    ]
if 'previous_result' not in st.session_state:
    st.session_state.previous_result = None
if 'server' not in st.session_state:
    st.session_state.server = None
if 'agent' not in st.session_state:
    st.session_state.agent = None
if 'initialized' not in st.session_state:
    st.session_state.initialized = False

# Display terminal output using a dynamic placeholder
terminal_placeholder = st.empty()
def render_terminal():
    terminal_output = "\n".join(st.session_state.terminal_output)
    terminal_placeholder.markdown(f"<div class='terminal'><pre>{terminal_output}</pre></div>", unsafe_allow_html=True)
    
render_terminal()

# Create a simple menu of common commands
col1, col2, col3, col4 = st.columns(4)
with col1:
    if st.button("Help", key="help_btn"):
        async def display_tools():
            st.session_state.terminal_output.append("Available tools (live):")
            if st.session_state.server:
                try:
                    tools = await st.session_state.server.list_tools()
                    for tool in tools:
                        st.session_state.terminal_output.append(f"  - {tool}")
                except Exception as e:
                    st.session_state.terminal_output.append(f"  ERROR: {e}")
            else:
                st.session_state.terminal_output.append("  ERROR: MCP server not initialized.")
            st.session_state.terminal_output.append("")
            render_terminal()

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(display_tools())
        finally:
            loop.close()

with col2:
    if st.button("List DBs", key="list_btn"):
        async def display_databases():
            st.session_state.terminal_output.append("Available databases (live):")
            if st.session_state.server:
                try:
                    databases = await st.session_state.server.discover_databases()
                    for db in databases:
                        st.session_state.terminal_output.append(f"  - {db}")
                except Exception as e:
                    st.session_state.terminal_output.append(f"  ERROR: {e}")
            else:
                st.session_state.terminal_output.append("  ERROR: MCP server not initialized.")
            st.session_state.terminal_output.append("")
            render_terminal()

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(display_databases())
        finally:
            loop.close()
with col3:
    if st.button("Clear", key="clear_btn"):
        st.session_state.command_input = "clear"
with col4:
    if st.button("Exit", key="exit_btn"):
        st.session_state.command_input = "exit"

# Command input with a more descriptive prompt
command = st.text_input("C:\\FMQUERY>", key="command_input")

# Function to initialize the MCP server and agent
async def initialize_server():
    if not st.session_state.initialized:
        # Add initialization message to terminal
        st.session_state.terminal_output.append("Initializing system...")
        st.session_state.terminal_output.append("Please wait...")
        st.session_state.terminal_output.append(f"MCP server path: {mcp_server_path}")
        st.session_state.terminal_output.append(f"DDR path: {ddrPath}")
        st.session_state.terminal_output.append(f"Model: {model_choice}")
        
        try:
            # Initialize the MCP server
            st.session_state.terminal_output.append("Creating MCP server...")
            server = OrchestrationMCPServerStdio(
                name="Filemaker Inspector",
                params={
                    "command": "uv",
                    "args": [
                        "--directory", mcp_server_path,
                        "run", "main.py",
                        "--ddr-path", ddrPath
                    ],
                },
            )
            st.session_state.terminal_output.append("Entering MCP server context...")
            await server.__aenter__()
            st.session_state.terminal_output.append("MCP server context entered successfully.")
            
            # Create the agent
            filemaker_agent_prompt = get_prompt('base')
            agent = Agent(
                name="FileMaker Assistant",
                instructions=filemaker_agent_prompt,
                model=model_choice,
                mcp_servers=[server],
            )
            
            # Set the agent for the server
            server.set_agent(agent)
            
            # Store in session state
            st.session_state.server = server
            st.session_state.agent = agent
            st.session_state.initialized = True
            
            # Add success message to terminal
            st.session_state.terminal_output.append("System initialized successfully.")
            st.session_state.terminal_output.append("Ready for commands.")
            st.session_state.terminal_output.append("")
            
            return True
        except Exception as e:
            # Add error message to terminal
            st.session_state.terminal_output.append(f"ERROR: Failed to initialize system: {str(e)}")
            st.session_state.terminal_output.append("")
            return False
    return True

# Function to process commands
async def process_command(command):
    if command.lower() == 'help':
        st.session_state.terminal_output.append("Available commands:")
        st.session_state.terminal_output.append("  help     - Display this help message")
        st.session_state.terminal_output.append("  clear    - Clear the terminal")
        st.session_state.terminal_output.append("  exit     - Exit the program (simulated)")
        st.session_state.terminal_output.append("  You can also use the buttons above for quick access to common commands")
        st.session_state.terminal_output.append("  Any other text will be processed as a query to the FileMaker database")
        st.session_state.terminal_output.append("")
    elif command.lower() == 'clear':
        st.session_state.terminal_output = []
    elif command.lower() == 'exit':
        st.session_state.terminal_output.append("Exiting system...")
        st.session_state.terminal_output.append("Goodbye!")
        # In a real terminal UI, this would exit the program
    else:
        # Process the command as a query
        st.session_state.terminal_output.append(f"Processing query: {command}")
        st.session_state.terminal_output.append("Sending to MCP server...")
        
        try:
            # Verify server is initialized
            if not st.session_state.server:
                st.session_state.terminal_output.append("ERROR: MCP server not initialized. Attempting to reinitialize...")
                await initialize_server()
                if not st.session_state.server:
                    st.session_state.terminal_output.append("ERROR: Failed to reinitialize MCP server.")
                    return
            
            # Verify agent is initialized
            if not st.session_state.agent:
                st.session_state.terminal_output.append("ERROR: Agent not initialized.")
                return
            
            st.session_state.terminal_output.append(f"Using model: {model_choice}")
            st.session_state.terminal_output.append("Calling run_query function...")
            
            # Run the query
            result = await run_query(st.session_state.server, command, st.session_state.previous_result)
            
            # Update the previous result for conversation context
            if result:
                st.session_state.terminal_output.append("Query successful! Processing response...")
                st.session_state.previous_result = result
                
                # Split the output into lines for better terminal display
                output_lines = result.final_output.split('\n')
                for line in output_lines:
                    # Terminal UIs could handle longer lines than CLI
                    if len(line) > 100:
                        st.session_state.terminal_output.append(line[:97] + "...")
                    else:
                        st.session_state.terminal_output.append(line)
            else:
                st.session_state.terminal_output.append("ERROR: Query failed to return a result")
        except Exception as e:
            st.session_state.terminal_output.append(f"ERROR: {str(e)}")
            st.session_state.terminal_output.append(f"Error type: {type(e).__name__}")
            import traceback
            st.session_state.terminal_output.append(f"Traceback: {traceback.format_exc()}")
        
        st.session_state.terminal_output.append("")

# Process the command when entered
if command:
    # Create a new event loop for async operations
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        # Initialize the server if not already done
        if not st.session_state.initialized:
            loop.run_until_complete(initialize_server())
        
        # Only process the command if initialization was successful
        if st.session_state.initialized:
            loop.run_until_complete(process_command(command))
    finally:
        loop.close()
    
    # We can't clear the input field directly due to Streamlit limitations
    # The user will need to manually clear it

# Initialize the server on first load - this is critical for the UI to work properly
if not st.session_state.initialized:
    # Create a new event loop for async operations
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        # Force initialization on boot up
        st.session_state.terminal_output.append("Initializing MCP server on startup...")
        init_result = loop.run_until_complete(initialize_server())
        if init_result:
            st.session_state.terminal_output.append("MCP server initialized successfully on startup.")
        else:
            st.session_state.terminal_output.append("WARNING: Failed to initialize MCP server on startup.")
    finally:
        loop.close()

# Add a status bar with system information
st.markdown("""
<div style="position: fixed; bottom: 0; width: 100%; background-color: #0000aa; color: #ffffff; 
            font-family: 'Courier New', monospace; padding: 5px; text-align: left; font-size: 12px;">
    Memory: 640K | CPU: 16-bit @ 8MHz | OS: DOS 3.3 | Status: Ready
</div>
""", unsafe_allow_html=True)