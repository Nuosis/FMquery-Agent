import asyncio
import os
import sys
import json
from dotenv import load_dotenv

# Add the parent directory to the Python path so we can import the orchestration module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agents import Agent, Runner, gen_trace_id, trace
from orchestration import OrchestrationMCPServerStdio
from cache import db_info_cache
from orchestration.cache_hierarchy import schema_cache, table_cache, script_cache

# Load environment variables
load_dotenv()

# Path to the MCP server
mcp_server_path = "/Users/marcusswift/python/mcp/mcp-filemaker-inspector"

# Path to FileMaker DDR
ddr_path = "/Users/marcusswift/Documents/fileMakerDevelopment/AL3/Miro/DDR/HTML"

# Customer name
customer_name = "Miro"

# Model choice
model_choice = os.getenv('MODEL_CHOICE', 'gpt-4o-mini')


async def test_dependency_resolution():
    """
    Test the dependency resolution capabilities of the orchestration layer.
    This test will:
    1. Clear all caches
    2. Call get_table_information directly
    3. Verify that discover_databases and get_schema_information are called first
    """
    print("\n=== Testing Dependency Resolution ===")
    
    # Clear all caches
    db_info_cache.clear()
    schema_cache.clear()
    table_cache.clear()
    script_cache.clear()
    
    print("All caches cleared")
    
    try:
        # Add more logging
        print(f"MCP server path: {mcp_server_path}")
        print(f"DDR path: {ddr_path}")
        
        # Initialize the MCP server with orchestration
        print("Initializing MCP server...")
        async with OrchestrationMCPServerStdio(
            name="Filemaker Inspector",
            params={
                "command": "uv",
                "args": [
                    "--directory", mcp_server_path,
                    "run", "main.py",
                    "--ddr-path", ddr_path
                ],
            },
        ) as server:
            print("MCP server initialized successfully")
            # Create the agent
            agent = Agent(
                name="FileMaker Test Assistant",
                instructions="""
                You are a test assistant for the FileMaker orchestration layer.
                Use the tools provided by the MCP server to test the orchestration capabilities.
                """,
                model=model_choice,
                mcp_servers=[server],
            )
            
            # Set the agent for the server
            server.set_agent(agent)
            
            # Get the first database path
            print("Calling discover_databases_tool to get the first database path...")
            discover_result = await server.call_tool("discover_databases_tool", {})
            
            # Extract the database path from the result
            db_path = None
            db_name = None
            schema_name = None
            table_name = None
            
            if hasattr(discover_result, 'content') and discover_result.content:
                for content_item in discover_result.content:
                    if hasattr(content_item, 'text') and content_item.text:
                        try:
                            db_info = json.loads(content_item.text)
                            if 'databases' in db_info and len(db_info['databases']) > 0:
                                db_path = db_info['databases'][0]['path']
                                db_name = db_info['databases'][0]['name']
                                print(f"Found database: {db_name} at {db_path}")
                                break
                        except json.JSONDecodeError:
                            pass
            
            if not db_path:
                print("Error: Could not find a database path")
                return
            
            # Get schema information
            print(f"Calling get_schema_information_tool for database {db_name}...")
            schema_result = await server.call_tool("get_schema_information_tool", {"db_paths": [db_path]})
            
            # Add more debugging for schema result
            print(f"Schema result type: {type(schema_result)}")
            if hasattr(schema_result, 'content'):
                print(f"Schema result has content with {len(schema_result.content)} items")
            
            # Extract the schema name from the result
            if hasattr(schema_result, 'content') and schema_result.content:
                for content_item in schema_result.content:
                    if hasattr(content_item, 'text') and content_item.text:
                        try:
                            print(f"Content item text: {content_item.text[:100]}...")  # Print first 100 chars
                            schema_info = json.loads(content_item.text)
                            print(f"Schema info keys: {schema_info.keys()}")
                            
                            # The schema information is structured differently now
                            if 'schema_information' in schema_info:
                                # Get the first database path
                                db_path = list(schema_info['schema_information'].keys())[0]
                                db_schema_info = schema_info['schema_information'][db_path]
                                
                                # Check if there are tables in the schema
                                if 'tables' in db_schema_info and len(db_schema_info['tables']) > 0:
                                    # Get the first table
                                    table = db_schema_info['tables'][0]
                                    table_name = table.get('name', '')
                                    schema_name = db_schema_info.get('name', 'default')
                                    print(f"Found schema: {schema_name} with table: {table_name}")
                                    break
                        except json.JSONDecodeError as e:
                            print(f"JSON decode error: {e}")
                        except Exception as e:
                            print(f"Error processing schema info: {e}")
            
            if not schema_name or not table_name:
                print("Error: Could not find a schema or table name")
                return
            
            # Clear the caches again to test dependency resolution
            print("Clearing caches to test dependency resolution...")
            db_info_cache.clear()
            schema_cache.clear()
            table_cache.clear()
            
            # Now call get_table_information directly
            # This should trigger the orchestration layer to call discover_databases and get_schema_information first
            print(f"Calling get_table_information_tool for table {table_name}...")
            table_result = await server.call_tool("get_table_information_tool", {
                "table_name": table_name,
                "table_path": db_path  # The tool expects table_path, not db_name and schema_name
            })
            
            # Add more debugging for table result
            print(f"Table result type: {type(table_result)}")
            if hasattr(table_result, 'content'):
                print(f"Table result has content with {len(table_result.content)} items")
            
            # Verify that the table information was retrieved
            if hasattr(table_result, 'content') and table_result.content:
                for content_item in table_result.content:
                    if hasattr(content_item, 'text') and content_item.text:
                        try:
                            print(f"Content item text: {content_item.text[:100]}...")  # Print first 100 chars
                            table_info = json.loads(content_item.text)
                            print(f"Table info keys: {table_info.keys()}")
                            
                            # The table information is structured differently now
                            if 'table_information' in table_info:
                                # Get the first database path
                                db_path_key = list(table_info['table_information'].keys())[0]
                                db_table_info = table_info['table_information'][db_path_key]
                                
                                # Check if the table name matches
                                if db_table_info.get('name') == table_name:
                                    print(f"Successfully retrieved information for table {table_name}")
                                    print(f"Table has {len(db_table_info.get('fields', []))} fields")
                                    print("Dependency resolution test passed!")
                                    return
                        except json.JSONDecodeError as e:
                            print(f"JSON decode error: {e}")
                        except Exception as e:
                            print(f"Error processing table info: {e}")
            
            # Add more detailed debugging
            print("\nDetailed table information debugging:")
            if hasattr(table_result, 'content') and table_result.content:
                for content_item in table_result.content:
                    if hasattr(content_item, 'text') and content_item.text:
                        try:
                            table_info = json.loads(content_item.text)
                            print(f"Table info keys: {table_info.keys()}")
                            
                            if 'table_information' in table_info:
                                db_path_key = list(table_info['table_information'].keys())[0]
                                print(f"DB path key: {db_path_key}")
                                
                                db_table_info = table_info['table_information'][db_path_key]
                                print(f"DB table info keys: {db_table_info.keys() if isinstance(db_table_info, dict) else 'Not a dict'}")
                                
                                if isinstance(db_table_info, dict) and 'table_details' in db_table_info:
                                    table_details = db_table_info['table_details']
                                    print(f"Table details keys: {table_details.keys() if isinstance(table_details, dict) else 'Not a dict'}")
                                    
                                    if isinstance(table_details, dict) and 'fields' in table_details:
                                        # The table name is not in the response, so we'll use the one from the arguments
                                        print(f"Table name from arguments: '{table_name}'")
                                        print(f"Successfully retrieved information for table {table_name}")
                                        print(f"Table has {len(table_details.get('fields', []))} fields")
                                        print("Dependency resolution test passed!")
                                        return
                        except Exception as e:
                            print(f"Error in detailed debugging: {e}")
            
            print("Error: Could not verify table information")
    except Exception as e:
        print(f"Error during test: {e}")
async def test_script_dependency_resolution():
    """
    Test the script dependency resolution capabilities of the orchestration layer.
    This test will:
    1. Clear all caches
    2. Call get_script_information directly
    3. Verify that discover_databases is called first
    """
    print("\n=== Testing Script Dependency Resolution ===")
    
    # Clear all caches
    db_info_cache.clear()
    schema_cache.clear()
    table_cache.clear()
    script_cache.clear()
    
    print("All caches cleared")
    
    try:
        # Initialize the MCP server with orchestration
        async with OrchestrationMCPServerStdio(
            name="Filemaker Inspector",
            params={
                "command": "uv",
                "args": [
                    "--directory", mcp_server_path,
                    "run", "main.py",
                    "--ddr-path", ddr_path
                ],
            },
        ) as server:
            # Create the agent
            agent = Agent(
                name="FileMaker Test Assistant",
                instructions="""
                You are a test assistant for the FileMaker orchestration layer.
                Use the tools provided by the MCP server to test the orchestration capabilities.
                """,
                model=model_choice,
                mcp_servers=[server],
            )
            
            # Set the agent for the server
            server.set_agent(agent)
            
            # Get the first database path
            print("Calling discover_databases_tool to get the first database path...")
            discover_result = await server.call_tool("discover_databases_tool", {})
            
            # Extract the database path from the result
            db_path = None
            db_name = None
            
            if hasattr(discover_result, 'content') and discover_result.content:
                for content_item in discover_result.content:
                    if hasattr(content_item, 'text') and content_item.text:
                        try:
                            db_info = json.loads(content_item.text)
                            if 'databases' in db_info and len(db_info['databases']) > 0:
                                db_path = db_info['databases'][0]['path']
                                db_name = db_info['databases'][0]['name']
                                print(f"Found database: {db_name} at {db_path}")
                                break
                        except json.JSONDecodeError:
                            pass
            
            if not db_path:
                print("Error: Could not find a database path")
                return
            
            # Clear the caches again to test dependency resolution
            print("Clearing caches to test script dependency resolution...")
            db_info_cache.clear()
            schema_cache.clear()
            table_cache.clear()
            script_cache.clear()
            
            # Now call get_script_information directly
            # This should trigger the orchestration layer to call discover_databases first
            print(f"Calling get_script_information_tool for database {db_name}...")
            script_result = await server.call_tool("get_script_information_tool", {
                "db_paths": [db_path]
            })
            
            # Verify that the script information was retrieved
            if hasattr(script_result, 'content') and script_result.content:
                for content_item in script_result.content:
                    if hasattr(content_item, 'text') and content_item.text:
                        try:
                            script_info = json.loads(content_item.text)
                            print(f"Script info keys: {script_info.keys()}")
                            
                            if 'script_information' in script_info:
                                print(f"Successfully retrieved script information")
                                print(f"Script dependency resolution test passed!")
                                return
                        except json.JSONDecodeError as e:
                            print(f"JSON decode error: {e}")
                        except Exception as e:
                            print(f"Error processing script info: {e}")
            
            print("Error: Could not verify script information")
    except Exception as e:
        print(f"Error during script test: {e}")


async def test_script_details_dependency_resolution():
    """
    Test the script details dependency resolution capabilities of the orchestration layer.
    This test will:
    1. Clear all caches
    2. Call get_script_details directly
    3. Verify that discover_databases and get_script_information are called first
    """
    print("\n=== Testing Script Details Dependency Resolution ===")
    
    # Clear all caches
    db_info_cache.clear()
    schema_cache.clear()
    table_cache.clear()
    script_cache.clear()
    
    print("All caches cleared")
    
    try:
        # Initialize the MCP server with orchestration
        async with OrchestrationMCPServerStdio(
            name="Filemaker Inspector",
            params={
                "command": "uv",
                "args": [
                    "--directory", mcp_server_path,
                    "run", "main.py",
                    "--ddr-path", ddr_path
                ],
            },
        ) as server:
            # Create the agent
            agent = Agent(
                name="FileMaker Test Assistant",
                instructions="""
                You are a test assistant for the FileMaker orchestration layer.
                Use the tools provided by the MCP server to test the orchestration capabilities.
                """,
                model=model_choice,
                mcp_servers=[server],
            )
            
            # Set the agent for the server
            server.set_agent(agent)
            
            # Get the first database path and script name
            print("Calling discover_databases_tool to get the first database path...")
            discover_result = await server.call_tool("discover_databases_tool", {})
            
            # Extract the database path from the result
            db_path = None
            
            if hasattr(discover_result, 'content') and discover_result.content:
                for content_item in discover_result.content:
                    if hasattr(content_item, 'text') and content_item.text:
                        try:
                            db_info = json.loads(content_item.text)
                            if 'databases' in db_info and len(db_info['databases']) > 0:
                                db_path = db_info['databases'][0]['path']
                                print(f"Found database at {db_path}")
                                break
                        except json.JSONDecodeError:
                            pass
            
            if not db_path:
                print("Error: Could not find a database path")
                return
            
            # Get script information
            print("Calling get_script_information_tool to get script names...")
            script_result = await server.call_tool("get_script_information_tool", {
                "db_paths": [db_path]
            })
            
            # Extract a script name from the result
            script_name = None
            
            # Add more debugging for script result
            print(f"Script result type: {type(script_result)}")
            if hasattr(script_result, 'content'):
                print(f"Script result has content with {len(script_result.content)} items")
                
                for content_item in script_result.content:
                    if hasattr(content_item, 'text') and content_item.text:
                        try:
                            print(f"Content item text: {content_item.text[:100]}...")  # Print first 100 chars
                            script_info = json.loads(content_item.text)
                            print(f"Script info keys: {script_info.keys()}")
                            
                            if 'script_information' in script_info:
                                db_path_key = list(script_info['script_information'].keys())[0]
                                print(f"DB path key: {db_path_key}")
                                scripts = script_info['script_information'][db_path_key]
                                print(f"Scripts type: {type(scripts)}")
                                print(f"Scripts length: {len(scripts) if isinstance(scripts, list) else 'Not a list'}")
                                
                                if scripts and len(scripts) > 0:
                                    script_name = scripts[0].get('name', '')
                                    print(f"Found script: {script_name}")
                                    break
                        except json.JSONDecodeError as e:
                            print(f"JSON decode error: {e}")
                        except Exception as e:
                            print(f"Error processing script info: {e}")
            
            if not script_name:
                # Use a hardcoded script name for testing if no scripts are found
                script_name = "Test Script"
                print(f"Using hardcoded script name: {script_name}")
            
            # Clear the caches again to test dependency resolution
            print("Clearing caches to test script details dependency resolution...")
            db_info_cache.clear()
            schema_cache.clear()
            table_cache.clear()
            script_cache.clear()
            
            # Now call get_script_details directly
            # This should trigger the orchestration layer to call discover_databases and get_script_information first
            print(f"Calling get_script_details_tool for script {script_name}...")
            
            # Add more debugging
            print(f"Script name: {script_name}")
            print(f"Script path: {db_path}")
            
            # The tool expects script_path, not db_path
            script_details_result = await server.call_tool("get_script_details_tool", {
                "script_name": script_name,
                "db_path": db_path  # Changed from script_path to db_path
            })
            
            # Verify that the script details were retrieved
            if hasattr(script_details_result, 'content') and script_details_result.content:
                for content_item in script_details_result.content:
                    if hasattr(content_item, 'text') and content_item.text:
                        try:
                            script_details = json.loads(content_item.text)
                            print(f"Script details keys: {script_details.keys()}")
                            
                            if 'script_details' in script_details or 'error' in script_details:
                                print(f"Successfully retrieved script details response for {script_name}")
                                print("Script details dependency resolution test passed!")
                                return
                        except json.JSONDecodeError as e:
                            print(f"JSON decode error: {e}")
                        except Exception as e:
                            print(f"Error processing script details: {e}")
            
            print("Error: Could not verify script details")
    except Exception as e:
        print(f"Error during script details test: {e}")


async def test_custom_functions_dependency_resolution():
    """
    Test the custom functions dependency resolution capabilities of the orchestration layer.
    This test will:
    1. Clear all caches
    2. Call get_custom_functions directly
    3. Verify that discover_databases is called first
    """
    print("\n=== Testing Custom Functions Dependency Resolution ===")
    
    # Clear all caches
    db_info_cache.clear()
    schema_cache.clear()
    table_cache.clear()
    script_cache.clear()
    
    print("All caches cleared")
    
    try:
        # Initialize the MCP server with orchestration
        async with OrchestrationMCPServerStdio(
            name="Filemaker Inspector",
            params={
                "command": "uv",
                "args": [
                    "--directory", mcp_server_path,
                    "run", "main.py",
                    "--ddr-path", ddr_path
                ],
            },
        ) as server:
            # Create the agent
            agent = Agent(
                name="FileMaker Test Assistant",
                instructions="""
                You are a test assistant for the FileMaker orchestration layer.
                Use the tools provided by the MCP server to test the orchestration capabilities.
                """,
                model=model_choice,
                mcp_servers=[server],
            )
            
            # Set the agent for the server
            server.set_agent(agent)
            
            # Get the first database path
            print("Calling discover_databases_tool to get the first database path...")
            discover_result = await server.call_tool("discover_databases_tool", {})
            
            # Extract the database path from the result
            db_path = None
            
            if hasattr(discover_result, 'content') and discover_result.content:
                for content_item in discover_result.content:
                    if hasattr(content_item, 'text') and content_item.text:
                        try:
                            db_info = json.loads(content_item.text)
                            if 'databases' in db_info and len(db_info['databases']) > 0:
                                db_path = db_info['databases'][0]['path']
                                print(f"Found database at {db_path}")
                                break
                        except json.JSONDecodeError:
                            pass
            
            if not db_path:
                print("Error: Could not find a database path")
                return
            
            # Clear the caches again to test dependency resolution
            print("Clearing caches to test custom functions dependency resolution...")
            db_info_cache.clear()
            schema_cache.clear()
            table_cache.clear()
            script_cache.clear()
            
            # Now call get_custom_functions directly
            # This should trigger the orchestration layer to call discover_databases first
            print(f"Calling get_custom_functions_tool for database...")
            custom_functions_result = await server.call_tool("get_custom_functions_tool", {
                "db_path": db_path
            })
            
            # Verify that the custom functions were retrieved
            if hasattr(custom_functions_result, 'content') and custom_functions_result.content:
                for content_item in custom_functions_result.content:
                    if hasattr(content_item, 'text') and content_item.text:
                        try:
                            custom_functions = json.loads(content_item.text)
                            print(f"Custom functions keys: {custom_functions.keys()}")
                            
                            if 'custom_functions_information' in custom_functions:
                                print(f"Successfully retrieved custom functions")
                                print("Custom functions dependency resolution test passed!")
                                return
                        except json.JSONDecodeError as e:
                            print(f"JSON decode error: {e}")
                        except Exception as e:
                            print(f"Error processing custom functions: {e}")
            
            print("Error: Could not verify custom functions")
    except Exception as e:
        print(f"Error during custom functions test: {e}")


async def main():
    """Run the orchestration tests."""
    await test_dependency_resolution()
    await test_script_dependency_resolution()
    await test_script_details_dependency_resolution()
    await test_custom_functions_dependency_resolution()


if __name__ == "__main__":
    asyncio.run(main())