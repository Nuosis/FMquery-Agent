import asyncio
import os
import argparse
import json
from dotenv import load_dotenv

from agents import Agent, Runner, gen_trace_id, trace

# Import from our new modules
from models import TOOL_ARG_MODELS
from cache import db_info_cache
from logging_utils import extract_tool_calls_from_result, all_tool_calls, log_tool_call
from database import get_database_info, get_available_db_paths
from orchestration import OrchestrationMCPServerStdio
from validation import tool_specs
from validation_decorator import validate_tool_parameters, ToolParameterValidationError

# This script uses the OpenAI Agents SDK to interact with FileMaker databases
# It maintains conversation context across multiple queries using result.to_input_list()

# Load environment variables
load_dotenv()

# Get model from environment or use default
model_choice = os.getenv('MODEL_CHOICE', 'gpt-4o-mini')

# Path to the MCP server
mcp_server_path = "/Users/marcusswift/python/mcp/mcp-filemaker-inspector"

# Path to FileMaker DDR
ddrPath = "/Users/marcusswift/Documents/fileMakerDevelopment/AL3/Miro/DDR/HTML"

# customer
customerName = "Miro"

async def run_query(mcp_server, query, previous_result=None):
    """Run a query against the MCP server using an agent."""
    #print("\n--- DEBUG: run_query called ---")
    
    # Check if database info cache is valid
    print(f"Database info cache valid: {db_info_cache.is_valid()}")
    if db_info_cache.is_valid():
        print(f"Cache contains {len(db_info_cache.get_paths())} database paths")
    
    # The agent is now created in the main function and set on the server
    # We can get it from the mcp_server
    agent = mcp_server.agent
    
    # Clear previous tool calls
    global all_tool_calls
    all_tool_calls = []
    
    # Variables to store tool call information for logging
    tool_name = None
    tool_arguments = None
    print("\n--- Running Query ---")
    
    try:
        
        # If we have a previous result, use to_input_list() to maintain conversation context
        if previous_result:
            # Create input that includes previous conversation plus new query
            input_list = previous_result.to_input_list() + [{"role": "user", "content": query}]
            print(f"Using input_list with {len(input_list)} items")
            result = await Runner.run(starting_agent=agent, input=input_list)
        else:
            # First query in the conversation
            result = await Runner.run(starting_agent=agent, input=query)
        
        # Extract tool calls from the result
        extract_tool_calls_from_result(result)
        
        # We don't need to log tool calls from result.new_items anymore
        # since we're capturing them in real-time with callbacks
            
        print(f"\nResult:\n{result.final_output}\n")
        return result
    except Exception as e:
        error_message = str(e)
        
        # Print all tool calls that were made before the error
        if all_tool_calls:
            print("\n--- All Tool Calls Before Error ---")
            for i, call in enumerate(all_tool_calls):
                print(f"Tool Call {i+1}:")
                print(f"  name='{call['name']}',")
                print(f"  arguments='{call['arguments']}',")
                print()
        
        # Also print the most recent tool call if available
        elif tool_name or tool_arguments:
            print("\n--- Last Tool Call Before Error ---")
            if tool_name:
                print(f"name='{tool_name}',")
            if tool_arguments:
                print(f"arguments='{tool_arguments}',")
            print()
        
        # Streamlined error reporting - just print once with helpful context
        print(f"\nError: {error_message}")
        return None
    finally:
        print("-" * 80)


async def interactive_mode(mcp_server):
    """Run in interactive mode, allowing the user to input queries."""
    print("\nWelcome to Agent FMquery where you can query FileMaker databases using natural language.")
    print("-" * 80)
    
    # Track the previous result to maintain conversation context
    previous_result = None
    
    while True:
        query = input("\nEnter your query (or 'exit' to quit): ")
        if query.lower() == 'exit':
            break
        
        # Pass the previous result to maintain context
        result = await run_query(mcp_server, query, previous_result)
        
        # Update the previous result for the next iteration
        if result:
            previous_result = result


async def demo_mode(mcp_server):
    """Run a series of predefined queries to demonstrate the capabilities."""
    queries = [
        "What databases can I query?",
        "Tell me about the structure of the first database. What tables does it have?",
        "How many records are in the third table in the first database?"
    ]
    
    # Track the previous result to maintain conversation context
    previous_result = None
    
    for query in queries:
        # Pass the previous result to maintain context
        result = await run_query(mcp_server, query, previous_result)
        
        # Update the previous result for the next iteration
        if result:
            previous_result = result

async def single_prompt_mode(mcp_server, prompt):
    """Run a single prompt and exit."""
    print(f"\nRunning prompt: '{prompt}'")
    print("-" * 80)
    
    # Run the query without previous context
    result = await run_query(mcp_server, prompt)
    
    # No need to update previous_result since we're exiting after this
    return result


async def main():
    parser = argparse.ArgumentParser(description='FileMaker Database Explorer')
    parser.add_argument('--demo', '-d', action='store_true', help='Run in demo mode with predefined queries')
    parser.add_argument('--model', '-m', type=str, help='Specify the model to use (e.g., gpt-4o, gpt-4o-mini)')
    parser.add_argument('--prompt', '-p', type=str, help='Run a single prompt and exit')
    args = parser.parse_args()

    # Update model choice if specified in command line
    global model_choice
    if args.model:
        model_choice = args.model
        print(f"Using model: {model_choice}")

    try:
        # Use our OrchestrationMCPServerStdio instead of ValidatingMCPServerStdio
        async with OrchestrationMCPServerStdio(
            name="Filemaker Inspector",
            params={
                "command": "uv",
                "args": [
                    "--directory", mcp_server_path,
                    "run", "main.py",
                    "--ddr-path", ddrPath
                ],
            },
        ) as server:
            # Create the agent
            agent = Agent(
                name="FileMaker Assistant",
                instructions="""
                You are a helpful assistant specialized in working with FileMaker databases.
                Use the tools provided by the MCP server to assist with tasks related to FileMaker databases.
                Be concise and informative in your responses.
                
                HANDLING LARGE RESULTS:
                Some tool results may be too large to process directly. In these cases, the tool will store the result in a file
                and return a response with "status": "file_stored". When you receive such a response, use the file path provided
                in the response to access the stored result.
                
                If the file is very large, it may be chunked into multiple files. In this case, the response will have
                "status": "file_chunked" and a list of "chunk_paths". You should retrieve each chunk and combine them.
                
                Example workflow for handling large results:
                1. If a tool returns {"status": "file_stored", "file_path": "/path/to/file.json"}, use the file path to access the content.
                2. If a tool returns {"status": "file_chunked", "chunk_paths": ["/path/to/chunk1.json", "/path/to/chunk2.json"]},
                   retrieve each chunk and combine them.
                """,
                model=model_choice,
                mcp_servers=[server],
            )
            
            # Set the agent for the server
            server.set_agent(agent)
            trace_id = gen_trace_id()
            with trace(workflow_name=f"MCP Filemaker Inspector {customerName}", trace_id=trace_id):
                print(f"View trace: https://platform.openai.com/traces/{trace_id}\n")
                
                # Fetch database information before starting any mode
                try:
                    await get_database_info(server, force_refresh=True)
                    print("Database information fetched successfully.")
                except Exception as e:
                    print(f"Error fetching initial database information: {e}")
                    print("Continuing anyway, but some features may not work correctly.")
                
                if args.prompt:
                    # Run a single prompt and exit
                    await single_prompt_mode(server, args.prompt)
                elif args.demo:
                    # Run in demo mode with predefined queries
                    await demo_mode(server)
                else:
                    # Run in interactive mode by default
                    await interactive_mode(server)
    except Exception as e:
        print(f"Error setting up MCP server: {e}")
        print("Make sure the MCP server path is correct and the server is available.")


def run_sync():
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nExiting...")
    except Exception as e:
        print(f"An error occurred: {e}")


if __name__ == "__main__":
    run_sync()