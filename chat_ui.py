import streamlit as st
import asyncio
import os
import json
from PIL import Image
import base64
import sys
import logging
import traceback
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='chat_ui_debug.log',
    filemode='w'
)
logger = logging.getLogger(__name__)
import time
from threading import Thread
from queue import Queue

# Import from fmquery.py
from fmquery import (
    OrchestrationMCPServerStdio,
    get_prompt,
    Agent,
    run_query
)

# Import database and tools functions
from api.database import get_database_info
from api.tools import get_tools_info

# Set page configuration
st.set_page_config(
    page_title="FMquery",
    page_icon="💬",
    layout="wide",
    initial_sidebar_state="collapsed"  # Sidebar is closed by default
)

# Define color scheme based on the logo
PRIMARY_COLOR = "#00CED1"  # Turquoise/Teal color from the logo
SECONDARY_COLOR = "#008B8B"  # Darker teal for contrast
BG_COLOR = "#f0f8ff"  # Light background color
TEXT_COLOR = "#333333"  # Dark text for readability

# Custom CSS for styling
def local_css():
    st.markdown("""
    <style>
    .main {
        background-color: #f0f8ff;
    }
    .stTextInput, .stSelectbox, .stTextArea {
        border-radius: 10px;
    }
    /* Change input field focus color from default red to our teal color */
    .stTextInput > div[data-baseweb="input"] > div,
    .stSelectbox > div[data-baseweb="select"] > div,
    .stTextArea > div[data-baseweb="textarea"] > div {
        border-color: #ddd;
    }
    .stTextInput > div[data-baseweb="input"] > div:focus-within,
    .stSelectbox > div[data-baseweb="select"] > div:focus-within,
    .stTextArea > div[data-baseweb="textarea"] > div:focus-within {
        border-color: #00CED1 !important;
        box-shadow: 0 0 0 1px #00CED1 !important;
    }
    /* Override Streamlit's default focus color */
    .stTextInput:focus-within, .stSelectbox:focus-within, .stTextArea:focus-within {
        border-color: #00CED1 !important;
        box-shadow: 0 0 0 1px #00CED1 !important;
    }
    .stButton>button {
        background-color: #00CED1;
        color: white;
        border-radius: 10px;
        border: none;
        padding: 0.5rem 1rem;
        font-weight: bold;
    }
    .stButton>button:hover {
        background-color: #008B8B;
    }
    .chat-message {
        padding: 1.5rem;
        border-radius: 10px;
        margin-bottom: 1rem;
        display: flex;
        flex-direction: row;
        align-items: flex-start;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        transition: all 0.3s ease;
    }
    .chat-message:hover {
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
    }
    .chat-message.user {
        background-color: transparent;
        justify-content: flex-end;
        flex-direction: row-reverse;
        align-items: center;
    }
    .chat-message.assistant {
        background-color: transparent;
    }
    .chat-message .avatar {
        width: 40px;
        height: 40px;
        border-radius: 50%;
        object-fit: cover;
    }
    .chat-message.assistant .avatar {
        margin-right: 1rem;
    }
    .chat-message.user .avatar {
        margin-left: 1rem;
    }
    .chat-message .message {
        flex-grow: 1;
        max-width: 80%;
    }
    .chat-message.user .message {
        text-align: right;
    }
    .stExpander {
        border-radius: 10px;
        border: 1px solid #ddd;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        margin-bottom: 2rem;
    }
    .stExpander > div:first-child {
        border-bottom: 1px solid #eee;
        padding-bottom: 0.5rem;
    }
    .logo-container {
        display: flex;
        justify-content: center;
        margin-bottom: 2rem;
    }
    .logo {
        max-width: 200px;
        transition: transform 0.3s ease;
    }
    .logo:hover {
        transform: scale(1.05);
    }
    /* Chat container styling */
    .chat-container {
        padding: 1rem;
        max-height: calc(100vh - 150px);
        overflow-y: auto;
        margin-bottom: 80px; /* Space for the input and footer */
    }
    /* Input container styling - fixed to bottom */
    .input-container {
        position: fixed;
        bottom: 0;
        left: 0;
        right: 0;
        background-color: #121212;
        padding: 10px 20px;
        z-index: 100;
        display: flex;
        flex-direction: column;
    }
    
    /* Message input styling */
    .stChatInput > div {
        border-color: #333 !important;
    }
    .stChatInput > div:focus-within {
        border-color: #00CED1 !important;
        box-shadow: 0 0 0 1px #00CED1 !important;
    }
    /* Input area styling */
    .input-area {
        padding: 1rem;
        background-color: white;
        border-radius: 10px;
        box-shadow: 0 -2px 5px rgba(0,0,0,0.03);
    }
    /* Sidebar styling */
    .sidebar .sidebar-content {
        background-color: #f8f9fa;
    }
    /* Header styling */
    .header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 1rem;
    }
    .header-title {
        margin: 0;
    }
    /* Typing indicator animation */
    .typing-indicator {
        display: flex;
        align-items: center;
    }
    .typing-indicator span {
        height: 8px;
        width: 8px;
        margin: 0 2px;
        background-color: #00CED1;
        border-radius: 50%;
        display: inline-block;
        animation: typing 1.4s infinite ease-in-out both;
    }
    .typing-indicator span:nth-child(1) {
        animation-delay: 0s;
    }
    .typing-indicator span:nth-child(2) {
        animation-delay: 0.2s;
    }
    .typing-indicator span:nth-child(3) {
        animation-delay: 0.4s;
    }
    @keyframes typing {
        0% {
            transform: scale(0);
        }
        50% {
            transform: scale(1);
        }
        100% {
            transform: scale(0);
        }
    }
    </style>
    """, unsafe_allow_html=True)

# Function to load and display images
def load_image(image_path):
    return Image.open(image_path)

# Function to convert image to base64 for avatar display
def get_image_base64(image_path):
    with open(image_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode()

# Load environment variables from .env file
load_dotenv()

# Get environment variables with defaults
openai_api_key = os.getenv('OPENAI_API_KEY', '')
model_choice = os.getenv('MODEL_CHOICE', 'gpt-4o-mini')
mcp_server_path = os.getenv('MCP_PATH', '/Users/marcusswift/python/mcp/mcp-filemaker-inspector')
ddr_path = os.getenv('DDR_PATH', '/Users/marcusswift/Documents/fileMakerDevelopment/AL3/Miro/DDR/HTML')
customer_name = os.getenv('CUST_NAME', 'Miro')

# Initialize session state variables if they don't exist
if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'openai_api_key' not in st.session_state:
    st.session_state.openai_api_key = openai_api_key
if 'openai_model' not in st.session_state:
    st.session_state.openai_model = model_choice
if 'ddr' not in st.session_state:
    st.session_state.ddr = ddr_path
if 'customer_name' not in st.session_state:
    st.session_state.customer_name = customer_name
if 'processing' not in st.session_state:
    st.session_state.processing = False
if 'mcp_server' not in st.session_state:
    st.session_state.mcp_server = None
if 'agent' not in st.session_state:
    st.session_state.agent = None
if 'previous_result' not in st.session_state:
    st.session_state.previous_result = None
if 'server_initialized' not in st.session_state:
    st.session_state.server_initialized = False
if 'initialization_attempted' not in st.session_state:
    st.session_state.initialization_attempted = False

# Function to update the .env file with new values
def update_env_file(key, value):
    try:
        # Read the current .env file
        with open('.env', 'r') as file:
            lines = file.readlines()
        
        # Check if the key exists and update it, or add it if it doesn't exist
        key_exists = False
        for i, line in enumerate(lines):
            if line.strip() and not line.strip().startswith('#'):  # Skip comments and empty lines
                if line.split('=')[0].strip() == key:
                    lines[i] = f"{key}={value}\n"
                    key_exists = True
                    break
        
        # If the key doesn't exist, add it
        if not key_exists:
            lines.append(f"{key}={value}\n")
        
        # Write the updated content back to the .env file
        with open('.env', 'w') as file:
            file.writelines(lines)
        
        # Also update the environment variable in the current process
        os.environ[key] = value
        
        # Log the update
        print(f"Updated {key} in .env file")
        if 'logger' in globals():
            logger.debug(f"Updated {key} in .env file")
        
        return True
    except Exception as e:
        print(f"Error updating .env file: {str(e)}")
        if 'logger' in globals():
            logger.error(f"Error updating .env file: {str(e)}")
        return False

# Function to run async code
def run_async(coro):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)

# Initialize MCP server and agent
async def initialize_server():
    try:
        # Use OrchestrationMCPServerStdio
        server = OrchestrationMCPServerStdio(
            name="Filemaker Inspector",
            params={
                "command": "uv",
                "args": [
                    "--directory", mcp_server_path,
                    "run", "main.py",
                    "--ddr-path", st.session_state.ddr
                ],
            },
        )
        await server.__aenter__()
        
        # Create the agent
        filemaker_agent_prompt = get_prompt('base')
        
        # Ensure the API key is set in the environment
        if st.session_state.openai_api_key:
            os.environ["OPENAI_API_KEY"] = st.session_state.openai_api_key
            print(f"Setting OpenAI API key for agent: {st.session_state.openai_api_key[:4]}...{st.session_state.openai_api_key[-4:]}")
            if 'logger' in globals():
                logger.debug(f"Setting OpenAI API key for agent: {st.session_state.openai_api_key[:4]}...{st.session_state.openai_api_key[-4:]}")
        else:
            print("Warning: OpenAI API key not set in session state")
            if 'logger' in globals():
                logger.warning("OpenAI API key not set in session state")
        
        # Import model_choice from fmquery.py to use the exact same model
        from fmquery import model_choice
        
        logger.debug(f"Using model_choice from fmquery.py: {model_choice}")
        
        # Create the agent with the exact same parameters as in fmquery.py
        agent = Agent(
            name="FileMaker Assistant",
            instructions=filemaker_agent_prompt,
            model=model_choice,  # Use model_choice from fmquery.py instead of st.session_state.openai_model
            mcp_servers=[server],
        )
        
        # Log agent creation
        print(f"Created agent with model: {st.session_state.openai_model}")
        if 'logger' in globals():
            logger.debug(f"Created agent with model: {st.session_state.openai_model}")
            logger.debug(f"Agent instructions length: {len(filemaker_agent_prompt)}")
        
        # Set the agent for the server
        server.set_agent(agent)
        
        # Fetch database information
        await get_database_info(server, force_refresh=True, save_to_disk=False)
        
        # Fetch tools information
        await get_tools_info(server, force_refresh=True, save_to_disk=False)
        
        return server, agent
    except Exception as e:
        st.error(f"Error initializing MCP server: {str(e)}")
        return None, None

# Display success message if it exists and is less than 3 seconds old
if 'success_message' in st.session_state:
    current_time = time.time()
    message_time = st.session_state.success_message['time']
    
    # Only show the message if it's less than 3 seconds old
    if current_time - message_time < 3:
        st.success(st.session_state.success_message['text'])
    else:
        # Remove the message from session state after 3 seconds
        if 'success_message' in st.session_state:
            del st.session_state.success_message

# Initialize server on app startup
if not st.session_state.server_initialized and not st.session_state.initialization_attempted:
    st.session_state.initialization_attempted = True
    with st.spinner("Initializing FileMaker query system..."):
        try:
            server, agent = run_async(initialize_server())
            if server and agent:
                st.session_state.mcp_server = server
                st.session_state.agent = agent
                st.session_state.server_initialized = True
                
                # Add a success message to session state with a timestamp
                if 'success_message' not in st.session_state:
                    st.session_state.success_message = {
                        'text': "FileMaker query system initialized successfully!",
                        'time': time.time()
                    }
            else:
                st.error("Failed to initialize FileMaker query system. Please refresh the page to try again.")
        except Exception as e:
            st.error(f"Error initializing FileMaker query system: {str(e)}")

# Apply custom CSS
local_css()

# Sidebar configuration
with st.sidebar:
    st.title("Configuration")
    
    st.subheader("Customer Information")
    customer_name = st.text_input("Customer Name", value=st.session_state.customer_name)
    ddr = st.text_input("DDR", value=st.session_state.ddr)
    
    if customer_name != st.session_state.customer_name:
        st.session_state.customer_name = customer_name
        # Update the .env file
        if update_env_file("CUST_NAME", customer_name):
            st.success("Customer name updated and saved to .env file")
    
    if ddr != st.session_state.ddr:
        st.session_state.ddr = ddr
        # Update the .env file
        if update_env_file("DDR_PATH", ddr):
            st.success("DDR path updated and saved to .env file")
    
    st.subheader("OpenAI Settings")
    openai_api_key = st.text_input("OpenAI API Key", value=st.session_state.openai_api_key, type="password")
    openai_model = st.selectbox(
        "OpenAI Model",
        options=["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"],
        index=0 if st.session_state.openai_model == "gpt-4o" else
              1 if st.session_state.openai_model == "gpt-4o-mini" else
              2 if st.session_state.openai_model == "gpt-4-turbo" else 3
    )
    
    if openai_api_key != st.session_state.openai_api_key:
        st.session_state.openai_api_key = openai_api_key
        # Set the API key in the environment
        os.environ["OPENAI_API_KEY"] = openai_api_key
        # Update the .env file
        if update_env_file("OPENAI_API_KEY", openai_api_key):
            st.success("OpenAI API key updated and saved to .env file")
        print(f"Updated OpenAI API key: {openai_api_key[:4]}...{openai_api_key[-4:] if openai_api_key else ''}")
        if 'logger' in globals():
            logger.debug(f"Updated OpenAI API key: {openai_api_key[:4]}...{openai_api_key[-4:] if openai_api_key else ''}")
    
    if openai_model != st.session_state.openai_model:
        st.session_state.openai_model = openai_model
        # Update the .env file
        if update_env_file("MODEL_CHOICE", openai_model):
            st.success(f"OpenAI model updated to {openai_model} and saved to .env file")
        print(f"Updated OpenAI model to: {openai_model}")
        if 'logger' in globals():
            logger.debug(f"Updated OpenAI model to: {openai_model}")

# Main content
# No title, as requested

# Chat container for messages
st.markdown('<div class="chat-container">', unsafe_allow_html=True)

# Display welcome message if no messages yet
if not st.session_state.messages:
    st.markdown(
        """
        <div style="text-align: center; padding: 3rem; color: #888;">
            <img src="data:image/png;base64,{}" style="width: 100px; margin-bottom: 1rem;">
            <h3>Welcome to FMquery</h3>
            <p>Start a conversation by typing a message below.</p>
        </div>
        """.format(get_image_base64("assets/clarity.png")),
        unsafe_allow_html=True
    )

# Display chat messages
for i, message in enumerate(st.session_state.messages):
    if message["role"] == "assistant":
        avatar_img = "assets/clarity.png"
        avatar_html = f'<img src="data:image/png;base64,{get_image_base64(avatar_img)}" class="avatar">'
    else:
        # Use Person-alpha.png for user
        avatar_img = "assets/Person-alpha.png"
        avatar_html = f'<img src="data:image/png;base64,{get_image_base64(avatar_img)}" class="avatar">'
    
    st.markdown(
        f"""
        <div class="chat-message {message["role"]}">
            {avatar_html}
            <div class="message">{message["content"]}</div>
        </div>
        """,
        unsafe_allow_html=True
    )

st.markdown('</div>', unsafe_allow_html=True)

# Add a typing indicator when processing - outside the chat container but before the input
if st.session_state.processing:
    st.markdown(
        """
        <div class="chat-message assistant" style="padding: 0.8rem; align-items: center; background-color: transparent; margin-bottom: 0.5rem; border-left: none;">
            <img src="data:image/png;base64,{}" class="avatar">
            <div class="typing-indicator">
                <span></span>
                <span></span>
                <span></span>
            </div>
        </div>
        """.format(get_image_base64("assets/Charlie.png")),
        unsafe_allow_html=True
    )

# Create a fixed container at the bottom for input and footer
st.markdown('<div class="input-container">', unsafe_allow_html=True)

# Input area
user_input = st.chat_input("Type your message here...")

st.markdown('</div>', unsafe_allow_html=True)
# Process user input
if user_input:
    # Add logging to see if this code is executed
    print(f"Received user input: '{user_input}'")
    if 'logger' in globals():
        logger.debug(f"Received user input in UI: '{user_input}'")
    
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": user_input})
    
    # Set processing state to True
    st.session_state.processing = True
    
    # Store the input in session state to persist across reruns
    st.session_state.current_input = user_input
    
    # Rerun to update UI with user message and typing indicator
    st.rerun()
    
# Check if there's a current input to process (after rerun)
if 'current_input' in st.session_state and st.session_state.processing:
    # Get the input from session state
    current_input = st.session_state.current_input
    print(f"Processing stored input after rerun: '{current_input}'")
    if 'logger' in globals():
        logger.debug(f"Processing stored input after rerun: '{current_input}'")
    
    # Check if server is initialized
    if not st.session_state.server_initialized:
        st.error("FileMaker query system is not initialized yet. Please refresh the page to try again.")
        # Reset processing state
        st.session_state.processing = False
        if 'current_input' in st.session_state:
            del st.session_state.current_input
    else:
        try:
            # Run query using fmquery.py
            async def process_query():
                # Use the current_input from session state
                current_input = st.session_state.current_input
                
                # Log the query to stdout for debugging
                print(f"\nProcessing query: '{current_input}'")
                logger.debug(f"Starting to process query: '{current_input}'")
                    
                # Ensure the agent is properly set on the server
                if not st.session_state.mcp_server.agent:
                    print("Agent not set on server, setting it now")
                    logger.debug("Agent not set on server, setting it now")
                    try:
                        st.session_state.mcp_server.set_agent(st.session_state.agent)
                        logger.debug("Successfully set agent on server")
                    except Exception as e:
                        logger.error(f"Error setting agent on server: {e}", exc_info=True)
                        print(f"Error setting agent on server: {e}")
                
                # Instead of using run_query, directly use Runner.run like in the terminal version
                # This ensures the input is sent directly to the agent
                try:
                    # Try to import the entire agents module first to check if it's available
                    import agents
                    logger.debug(f"Successfully imported agents module: {agents}")
                    logger.debug(f"agents module path: {agents.__file__}")
                    logger.debug(f"agents module contains: {dir(agents)}")
                    
                    # Now try to import Runner specifically
                    from agents import Runner
                    logger.debug(f"Successfully imported Runner from agents: {Runner}")
                    logger.debug(f"Runner class attributes: {dir(Runner)}")
                    logger.debug(f"Runner.run is callable: {callable(getattr(Runner, 'run', None))}")
                except ImportError as e:
                    logger.error(f"Error importing Runner from agents: {e}", exc_info=True)
                    print(f"Error importing Runner from agents: {e}")
                    
                    # Try to find the agents module in sys.path
                    import sys
                    logger.debug(f"sys.path: {sys.path}")
                    raise
                
                try:
                    # If we have a previous result, use to_input_list() to maintain conversation context
                    if st.session_state.previous_result:
                        # Create input that includes previous conversation plus new query
                        input_list = st.session_state.previous_result.to_input_list() + [{"role": "user", "content": current_input}]
                        print(f"Using input_list with {len(input_list)} items")
                        print(f"Input list content: {json.dumps(input_list, indent=2)}")
                        logger.debug(f"Using input_list with {len(input_list)} items")
                        logger.debug(f"Input list content: {json.dumps(input_list, indent=2)}")
                        
                        # Ensure the agent is properly initialized
                        print(f"Agent model: {st.session_state.agent.model}")
                        print(f"Agent name: {st.session_state.agent.name}")
                        logger.debug(f"Agent model: {st.session_state.agent.model}")
                        logger.debug(f"Agent name: {st.session_state.agent.name}")
                        
                        # Run the query with the agent
                        logger.debug("About to call Runner.run with input_list")
                        try:
                            # Log the API key status (masked for security)
                            api_key = os.environ.get("OPENAI_API_KEY", "")
                            if api_key:
                                logger.debug(f"Using OpenAI API key: {api_key[:4]}...{api_key[-4:]} (length: {len(api_key)})")
                            else:
                                logger.error("OPENAI_API_KEY environment variable not set")
                                print("OPENAI_API_KEY environment variable not set")
                            
                            # Log the agent configuration
                            logger.debug(f"Agent configuration: model={st.session_state.agent.model}, name={st.session_state.agent.name}")
                            logger.debug(f"Agent instructions length: {len(st.session_state.agent.instructions) if hasattr(st.session_state.agent, 'instructions') else 'N/A'}")
                            
                            # Call Runner.run with the input list
                            logger.debug("About to call Runner.run with these parameters:")
                            logger.debug(f"Agent type: {type(st.session_state.agent)}")
                            logger.debug(f"Input type: {type(input_list)}")
                            logger.debug(f"Input length: {len(input_list)}")
                            
                            result = await Runner.run(starting_agent=st.session_state.agent, input=input_list)
                            logger.debug(f"Runner.run completed, result type: {type(result) if result else 'None'}")
                            
                            # Log the result
                            if result:
                                logger.debug("Successfully called Runner.run with input_list")
                                logger.debug(f"Result type: {type(result)}")
                                if hasattr(result, 'final_output'):
                                    logger.debug(f"Result final_output: {result.final_output[:100]}...")
                                else:
                                    logger.debug("Result has no final_output attribute")
                            else:
                                logger.error("Runner.run returned None")
                                print("Runner.run returned None")
                        except Exception as e:
                            logger.error(f"Error calling Runner.run with input_list: {e}", exc_info=True)
                            print(f"Error calling Runner.run with input_list: {e}")
                            raise
                    else:
                        # First query in the conversation
                        print("First query in conversation, using direct input")
                        print(f"Direct input: {current_input}")
                        logger.debug("First query in conversation, using direct input")
                        logger.debug(f"Direct input: {current_input}")
                        
                        # Ensure the agent is properly initialized
                        print(f"Agent model: {st.session_state.agent.model}")
                        print(f"Agent name: {st.session_state.agent.name}")
                        logger.debug(f"Agent model: {st.session_state.agent.model}")
                        logger.debug(f"Agent name: {st.session_state.agent.name}")
                        
                        # Run the query with the agent
                        logger.debug("About to call Runner.run with direct input")
                        try:
                            # Log the API key status (masked for security)
                            api_key = os.environ.get("OPENAI_API_KEY", "")
                            if api_key:
                                logger.debug(f"Using OpenAI API key: {api_key[:4]}...{api_key[-4:]} (length: {len(api_key)})")
                            else:
                                logger.error("OPENAI_API_KEY environment variable not set")
                                print("OPENAI_API_KEY environment variable not set")
                            
                            # Log the agent configuration
                            logger.debug(f"Agent configuration: model={st.session_state.agent.model}, name={st.session_state.agent.name}")
                            logger.debug(f"Agent instructions length: {len(st.session_state.agent.instructions) if hasattr(st.session_state.agent, 'instructions') else 'N/A'}")
                            
                            # Call Runner.run with the input
                            logger.debug("About to call Runner.run with direct input:")
                            logger.debug(f"Agent type: {type(st.session_state.agent)}")
                            logger.debug(f"Input type: {type(current_input)}")
                            logger.debug(f"Input content: '{current_input}'")
                            
                            # Use the same approach as the interactive_mode function in fmquery.py
                            try:
                                logger.debug("Using the same approach as the interactive_mode function in fmquery.py")
                                
                                # Import necessary functions from fmquery.py
                                from fmquery import gen_trace_id, trace, customerName, run_query
                                
                                # Set up tracing like in the command-line interface
                                trace_id = gen_trace_id()
                                logger.debug(f"Generated trace ID: {trace_id}")
                                
                                # Use the exact same workflow name as in the command-line interface
                                with trace(workflow_name=f"MCP Filemaker Inspector {customerName}", trace_id=trace_id):
                                    logger.debug(f"Using trace with ID: {trace_id} and workflow name: MCP Filemaker Inspector {customerName}")
                                    
                                    # Use run_query with previous_result to maintain conversation context
                                    # This is how interactive_mode in fmquery.py maintains context
                                    result = await run_query(st.session_state.mcp_server, current_input, st.session_state.previous_result)
                                
                                logger.debug(f"run_query with tracing completed, result type: {type(result) if result else 'None'}")
                            except Exception as e:
                                logger.error(f"Error using run_query: {e}", exc_info=True)
                                logger.debug("Falling back to direct Runner.run")
                                
                                # Fall back to direct Runner.run
                                result = await Runner.run(starting_agent=st.session_state.agent, input=current_input)
                                logger.debug(f"Runner.run completed, result type: {type(result) if result else 'None'}")
                            
                            # Log the result
                            if result:
                                logger.debug("Successfully called Runner.run with direct input")
                                logger.debug(f"Result type: {type(result)}")
                                if hasattr(result, 'final_output'):
                                    logger.debug(f"Result final_output: {result.final_output[:100]}...")
                                else:
                                    logger.debug("Result has no final_output attribute")
                            else:
                                logger.error("Runner.run returned None")
                                print("Runner.run returned None")
                        except Exception as e:
                            logger.error(f"Error calling Runner.run with direct input: {e}", exc_info=True)
                            print(f"Error calling Runner.run with direct input: {e}")
                            raise
                    
                    # Log the result for debugging
                    if result:
                        print(f"\nQuery result received: {result.final_output[:50]}...")
                        print(f"Result type: {type(result)}")
                        print(f"Result has new_items: {hasattr(result, 'new_items')}")
                        logger.debug(f"Query result received: {result.final_output[:50]}...")
                        logger.debug(f"Result type: {type(result)}")
                        logger.debug(f"Result has new_items: {hasattr(result, 'new_items')}")
                        if hasattr(result, 'new_items'):
                            logger.debug(f"Number of new items: {len(result.new_items)}")
                            logger.debug(f"New items: {result.new_items}")
                    else:
                        logger.error("No result received from Runner.run")
                        print("No result received from Runner.run")
                        # Try to get more information about what might have gone wrong
                        logger.error("Checking OpenAI API key status...")
                        api_key = os.environ.get("OPENAI_API_KEY", "")
                        if api_key:
                            logger.debug(f"API key is set (length: {len(api_key)})")
                        else:
                            logger.error("API key is not set!")
                    
                    return result
                except Exception as e:
                    print(f"Error running query directly: {str(e)}")
                    # Fall back to run_query if direct method fails
                    print("Falling back to run_query method")
                    result = await run_query(
                        st.session_state.mcp_server,
                        current_input,
                        st.session_state.previous_result
                    )
                    return result
            
            # Run the query
            result = run_async(process_query())
            
            if result:
                # Update previous result for context
                st.session_state.previous_result = result
                
                # Add assistant's response to chat history
                assistant_response = result.final_output
                st.session_state.messages.append({"role": "assistant", "content": assistant_response})
            else:
                # Handle error case
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": "I encountered an error processing your request. Please try again."
                })
            # Set processing state to False and clear current_input
            st.session_state.processing = False
            if 'current_input' in st.session_state:
                del st.session_state.current_input
            
            # Rerun to update the UI with the new message
            st.rerun()
            
            
        except Exception as e:
            # Set processing state to False on error
            st.session_state.processing = False
            st.error(f"Error: {str(e)}")

# Typing indicator moved to chat container

# Footer removed (already moved under the message input)
