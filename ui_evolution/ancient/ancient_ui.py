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
    page_title="Ancient CLI Emulation",
    page_icon="🖥️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Apply custom CSS to make it look like an old terminal
st.markdown("""
<style>
    body {
        background-color: #000;
        color: #33ff33;
    }
    .stTextInput > div > div > input {
        background-color: #000;
        color: #33ff33;
        border: 1px solid #33ff33;
        font-family: 'Courier New', monospace;
    }
    .stButton button {
        background-color: #000;
        color: #33ff33;
        border: 1px solid #33ff33;
        font-family: 'Courier New', monospace;
    }
    pre {
        background-color: #000;
        color: #33ff33;
        padding: 10px;
        font-family: 'Courier New', monospace;
        border: 1px solid #33ff33;
        overflow-x: auto;
    }
    .terminal {
        background-color: #000;
        color: #33ff33;
        font-family: 'Courier New', monospace;
        padding: 10px;
        border: 1px solid #33ff33;
        height: 400px;
        overflow-y: auto;
    }
</style>
""", unsafe_allow_html=True)

# Title with ASCII art
st.markdown("""
<pre>
  _____                _            _     _____ _      _____   ______                _       _   _             
 |  _  |              (_)          | |   /  __ \ |    |_   _|  | ___ \              | |     | | (_)            
 | | | | _ __   ___    _   ___   __| |   | /  \/ |      | |    | |_/ /___  _ __ ___ | | __ _| |_ _  ___  _ __  
 | | | || '_ \ / _ \  | | / _ \ / _` |   | |   | |      | |    |    // _ \| '_ ` _ \| |/ _` | __| |/ _ \| '_ \ 
 \ \_/ /| | | | (_) | | ||  __/| (_| |   | \__/\ |____ _| |_   | |\ \ (_) | | | | | | | (_| | |_| | (_) | | | |
  \___/ |_| |_|\___/  |_| \___| \__,_|    \____/\_____/\___/   \_| \_\___/|_| |_| |_|_|\__,_|\__|_|\___/|_| |_|
                                                                                                               
</pre>
""", unsafe_allow_html=True)

st.markdown("<h3 style='color: #33ff33; font-family: Courier New, monospace;'>Ancient CLI Emulation (circa 1970s)</h3>", unsafe_allow_html=True)

# Initialize session state
if 'terminal_output' not in st.session_state:
    st.session_state.terminal_output = [
        "FileMaker Database Explorer v0.1",
        "Copyright (c) 2025 Ancient Systems",
        "Type 'help' for available commands",
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

# Display terminal output
terminal_output = "\n".join(st.session_state.terminal_output)
st.markdown(f"<div class='terminal'><pre>{terminal_output}</pre></div>", unsafe_allow_html=True)

# Command input
command = st.text_input("C:\\>", key="command_input")

# Function to initialize the MCP server and agent
async def initialize_server():
    if not st.session_state.initialized:
        # Add initialization message to terminal
        st.session_state.terminal_output.append("Initializing system...")
        st.session_state.terminal_output.append("Please wait...")
        
        try:
            # Initialize the MCP server
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
            await server.__aenter__()
            
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
        st.session_state.terminal_output.append("  Any other text will be processed as a query to the FileMaker database")
        st.session_state.terminal_output.append("")
    elif command.lower() == 'clear':
        st.session_state.terminal_output = []
    elif command.lower() == 'exit':
        st.session_state.terminal_output.append("Exiting system...")
        st.session_state.terminal_output.append("Goodbye!")
        # In a real CLI, this would exit the program
    else:
        # Process the command as a query
        st.session_state.terminal_output.append(f"Processing query: {command}")
        
        try:
            # Run the query
            result = await run_query(st.session_state.server, command, st.session_state.previous_result)
            
            # Update the previous result for conversation context
            if result:
                st.session_state.previous_result = result
                
                # Split the output into lines for better terminal display
                output_lines = result.final_output.split('\n')
                for line in output_lines:
                    # Simulate a limited width terminal by truncating long lines
                    if len(line) > 80:
                        st.session_state.terminal_output.append(line[:77] + "...")
                    else:
                        st.session_state.terminal_output.append(line)
            else:
                st.session_state.terminal_output.append("ERROR: Query failed to return a result")
        except Exception as e:
            st.session_state.terminal_output.append(f"ERROR: {str(e)}")
        
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
    
    # Clear the input field after processing
    st.session_state.command_input = ""

# Initialize the server on first load
if not st.session_state.initialized:
    # Create a new event loop for async operations
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        loop.run_until_complete(initialize_server())
    finally:
        loop.close()

# Add a footer with simulated system information
st.markdown("""
<div style="position: fixed; bottom: 0; width: 100%; background-color: #000; color: #33ff33; 
            font-family: 'Courier New', monospace; padding: 5px; text-align: center; font-size: 12px;">
    Memory: 64K | CPU: 8-bit @ 1MHz | OS: DOS 1.0
</div>
""", unsafe_allow_html=True)