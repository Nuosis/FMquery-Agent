import asyncio
import os
import shutil
import argparse
from dotenv import load_dotenv

from agents import Agent, Runner, gen_trace_id, trace
from agents.mcp import MCPServer, MCPServerStdio

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
    agent = Agent(
        name="FileMaker Assistant",
        instructions="""
        You are a helpful assistant specialized in working with FileMaker databases.
        Use the tools provided by the MCP server to assist with tasks related to FileMaker databases.
        Be concise and informative in your responses.
        """,
        model=model_choice,
        mcp_servers=[mcp_server],
    )

    print(f"\nRunning query: {query}")
    try:
        # If we have a previous result, use to_input_list() to maintain conversation context
        if previous_result:
            # Create input that includes previous conversation plus new query
            input_list = previous_result.to_input_list() + [{"role": "user", "content": query}]
            result = await Runner.run(starting_agent=agent, input=input_list)
        else:
            # First query in the conversation
            result = await Runner.run(starting_agent=agent, input=query)
            
        print(f"\nResult:\n{result.final_output}\n")
        return result
    except Exception as e:
        error_message = str(e)
        print(f"\nError: {error_message}")
        if "context_length_exceeded" in error_message:
            print("\nThe query resulted in too much data for the model to process.")
            print("Try making your query more specific, for example:")
            print("- Instead of asking about all tables, ask about a specific table")
            print("- Instead of asking for all fields, ask for the most important fields")
            print("- Break your query into smaller, more focused questions")
        return None
        return None
    finally:
        print("-" * 80)


async def interactive_mode(mcp_server):
    """Run in interactive mode, allowing the user to input queries."""
    print("\nWelcome to Agent FMquery where you can query FileMaker databases using natural language.")
    print("Example queries:")
    print("  - What databases can I query?")
    print("  - Tell me about the structure of the FOTS_STUDENTS database.")
    print("  - How many records are in the Customer table in the NAEMT_CRM database?")
    print("  - Show me the field names in the first table of the FOTS_MGR database.")
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


async def main():
    parser = argparse.ArgumentParser(description='FileMaker Database Explorer')
    parser.add_argument('--demo', '-d', action='store_true', help='Run in demo mode with predefined queries')
    parser.add_argument('--model', '-m', type=str, help='Specify the model to use (e.g., gpt-4o, gpt-4o-mini)')
    args = parser.parse_args()

    # Update model choice if specified in command line
    global model_choice
    if args.model:
        model_choice = args.model
        print(f"Using model: {model_choice}")

    try:
        async with MCPServerStdio(
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
            trace_id = gen_trace_id()
            with trace(workflow_name=f"MCP Filemaker Inspector {customerName}", trace_id=trace_id):
                print(f"View trace: https://platform.openai.com/traces/{trace_id}\n")
                
                if args.demo:
                    # Run in demo mode with predefined queries
                    await demo_mode(server)
                else:
                    # Run in interactive mode by default
                    await interactive_mode(server)
    except Exception as e:
        print(f"Error setting up MCP server: {e}")
        print("Make sure the MCP server path is correct and the server is available.")
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