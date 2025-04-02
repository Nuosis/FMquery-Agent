import asyncio
import os
import argparse
import json
from dotenv import load_dotenv

from agents import Agent, Runner, gen_trace_id, trace

# Import from our new modules
from models import TOOL_ARG_MODELS
from cache import db_info_cache
from logging_utils import (
    extract_tool_calls_from_result, all_tool_calls, log_tool_call, 
    logger, log_failure, log_orchestration_intervention
)
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
    logger.debug("run_query called with query: %s", query)
    
    # Check if database info cache is valid
    cache_valid = db_info_cache.is_valid()
    logger.debug("Database info cache valid: %s", cache_valid)
    
    # The agent is now created in the main function and set on the server
    # We can get it from the mcp_server
    agent = mcp_server.agent
    
    # Clear previous tool calls
    global all_tool_calls
    all_tool_calls = []
    
    # Variables to store tool call information for logging
    tool_name = None
    tool_arguments = None
    
    try:
        # If we have a previous result, use to_input_list() to maintain conversation context
        if previous_result:
            # Create input that includes previous conversation plus new query
            input_list = previous_result.to_input_list() + [{"role": "user", "content": query}]
            logger.debug("Using input_list with %d items", len(input_list))
            result = await Runner.run(starting_agent=agent, input=input_list)
        else:
            # First query in the conversation
            result = await Runner.run(starting_agent=agent, input=query)
        
        # Extract tool calls from the result
        extract_tool_calls_from_result(result)
        
        # We don't need to log tool calls from result.new_items anymore
        # since we're capturing them in real-time with callbacks
        logger.debug("Result: %s", result.final_output)
        return result
    except Exception as e:
        error_message = str(e)
        
        # Log all tool calls that were made before the error
        if all_tool_calls:
            logger.info("Error occurred after %d tool calls", len(all_tool_calls))
            for i, call in enumerate(all_tool_calls):
                logger.debug("Tool Call %d: name='%s', arguments='%s'", 
                           i+1, call['name'], call['arguments'])
        
        # Also log the most recent tool call if available
        elif tool_name or tool_arguments:
            logger.info("Error occurred during tool call")
            if tool_name:
                logger.debug("Last tool name: %s", tool_name)
            if tool_arguments:
                logger.debug("Last tool arguments: %s", tool_arguments)
        
        # Log the error
        log_failure("Query execution", error_message)
        return None
    finally:
        logger.debug("Query processing completed")


async def interactive_mode(mcp_server):
    """Run in interactive mode, allowing the user to input queries."""
    logger.info("Starting interactive mode")
    print("\nWelcome to Agent FMquery where you can query FileMaker databases using natural language.")
    print("-" * 80)
    
    # Track the previous result to maintain conversation context
    previous_result = None
    
    while True:
        query = input("\nEnter your query (or 'exit' to quit): ")
        if query.lower() == 'exit':
            logger.info("Exiting interactive mode")
            break
        
        # Pass the previous result to maintain context
        result = await run_query(mcp_server, query, previous_result)
        
        # Update the previous result for the next iteration
        if result:
            previous_result = result
            print(f"\nResult:\n{result.final_output}\n")
            print("-" * 80)


async def demo_mode(mcp_server):
    """Run a series of predefined queries to demonstrate the capabilities."""
    logger.info("Starting demo mode")
    queries = [
        "What databases can I query?",
        "Tell me about the structure of the first database. What tables does it have?",
        "How many records are in the third table in the first database?"
    ]
    
    # Track the previous result to maintain conversation context
    previous_result = None
    
    for i, query in enumerate(queries):
        logger.info("Running demo query %d: %s", i+1, query)
        print(f"\nDemo Query {i+1}: '{query}'")
        print("-" * 80)
        
        # Pass the previous result to maintain context
        result = await run_query(mcp_server, query, previous_result)
        
        # Update the previous result for the next iteration
        if result:
            previous_result = result
            print(f"\nResult:\n{result.final_output}\n")
            print("-" * 80)

async def single_prompt_mode(mcp_server, prompt):
    """Run a single prompt and exit."""
    logger.info("Running single prompt mode with prompt: %s", prompt)
    print(f"\nRunning prompt: '{prompt}'")
    print("-" * 80)
    
    # Run the query without previous context
    result = await run_query(mcp_server, prompt)
    
    # Display the result
    if result:
        print(f"\nResult:\n{result.final_output}\n")
        print("-" * 80)
    
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
        logger.info("Using model: %s", model_choice)

    try:
        # Use our OrchestrationMCPServerStdio instead of ValidatingMCPServerStdio
        logger.info("Initializing MCP server")
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
            # Get database paths and names from cache
            from cache import db_info_cache
            db_paths = db_info_cache.get_paths()
            db_names = db_info_cache.get_names()
            
            # Format the database information for the instructions
            db_paths_str = ", ".join([f'"{path}"' for path in db_paths]) if db_paths else "No database paths available yet"
            db_names_str = ", ".join([f'"{name}"' for name in db_names]) if db_names else "No database names available yet"
            
            # Create the agent
            logger.info("Creating agent with model: %s", model_choice)
            agent = Agent(
                name="FileMaker Assistant",
                instructions=f"""
                You are a helpful assistant specialized in working with FileMaker databases.
                Use the tools provided by the MCP server to assist with tasks related to FileMaker databases.
                Be concise and informative in your responses.
                
                WORKING WITH DATABASE PATHS AND NAMES:
                When using tools that require database paths or names, always use actual values from the database cache.
                The database cache is initialized on startup and contains valid paths and names.
                
                AVAILABLE DATABASE PATHS:
                [{db_paths_str}]
                
                AVAILABLE DATABASE NAMES:
                [{db_names_str}]
                
                For tools like get_script_information_tool and get_schema_information_tool that require db_paths:
                - Use actual database paths from the list above
                - DO NOT use placeholder paths like 'path/to/database'
                - If you don't know the specific path, use all available paths from the list above
                
                For tools that accept db_names:
                - Use actual database names from the list above
                - DO NOT make up database names
                
                HANDLING LARGE RESULTS:
                Some tool results may be too large to process directly. In these cases, the tool will store the result in a file
                and return a response with "status": "file_stored". When you receive such a response, use the file path provided
                in the response to access the stored result.
                
                If the file is very large, it may be chunked into multiple files. In this case, the response will have
                "status": "file_chunked" and a list of "chunk_paths". You should retrieve each chunk and combine them.
                
                Example workflow for handling large results:
                1. If a tool returns {{"status": "file_stored", "file_path": "/path/to/file.json"}}, use the file path to access the content.
                2. If a tool returns {{"status": "file_chunked", "chunk_paths": ["/path/to/chunk1.json", "/path/to/chunk2.json"]}},
                   retrieve each chunk and combine them.
                """,
                model=model_choice,
                mcp_servers=[server],
            )
            
            # Set the agent for the server
            server.set_agent(agent)
            
            # Fetch database information before starting any mode
            try:
                await get_database_info(server, force_refresh=True)
            except Exception as e:
                if args.prompt:
                    # If --prompt flag is provided, fail the initialization
                    log_failure("Initial database information fetch", str(e),
                              "Initialization failed due to database discovery error")
                    # Re-raise the exception to fail the initialization process
                    raise
                else:
                    # In interactive or demo mode, continue with a warning
                    log_failure("Initial database information fetch", str(e),
                              "Continuing anyway, but some features may not work correctly")
                
            if args.prompt:
                # Only set up tracing when running in prompt mode
                trace_id = gen_trace_id()
                with trace(workflow_name=f"MCP Filemaker Inspector {customerName}", trace_id=trace_id):
                    logger.info("Trace ID: %s", trace_id)
                    
                    # Run a single prompt and exit
                    await single_prompt_mode(server, args.prompt)
            elif args.demo:
                # Run in demo mode with predefined queries
                await demo_mode(server)
            else:
                # Run in interactive mode by default
                await interactive_mode(server)
    except Exception as e:
        log_failure("MCP server setup", str(e), 
                   "Make sure the MCP server path is correct and the server is available")


def run_sync():
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Exiting due to keyboard interrupt")
        print("\nExiting...")
    except Exception as e:
        log_failure("Main execution", str(e))


if __name__ == "__main__":
    run_sync()