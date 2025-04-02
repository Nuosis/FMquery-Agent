import asyncio
import os
import sys
from dotenv import load_dotenv

# Import from agent_mcp.py
from agent_mcp import ValidatingMCPServerStdio, run_query, get_database_info

# Load environment variables
load_dotenv()

# Path to the MCP server - using the same as in agent_mcp.py
mcp_server_path = "/Users/marcusswift/python/mcp/mcp-filemaker-inspector"

# Path to FileMaker DDR - using the same as in agent_mcp.py
ddrPath = "/Users/marcusswift/Documents/fileMakerDevelopment/AL3/Miro/DDR/HTML"

async def test_invalid_path():
    """Test the behavior of the system with an invalid database path."""
    print("\n=== Testing Invalid Database Path ===\n")

    try:
        # Set up the MCP server with our ValidatingMCPServerStdio
        async with ValidatingMCPServerStdio(
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
            # First, get the database info to populate the cache
            print("\n--- Fetching database information to populate cache ---")
            try:
                db_info = await get_database_info(server, force_refresh=True)
                print("Database information fetched successfully.")
            except Exception as e:
                print(f"Error fetching database information: {e}")
                return

            # Now try to call get_schema_information with an invalid path
            print("\n--- Testing get_schema_information with invalid path ---")
            invalid_path = "invalid_database_path"
            try:
                result = await server.call_tool(
                    "get_schema_information", {"db_paths": [invalid_path]}
                )
                print("\n--- Tool call succeeded despite invalid path ---")
                print(f"Result: {result}")
            except Exception as e:
                print("\n--- Tool call failed as expected ---")
                print(f"Error: {e}")
                
            # Now try to call get_schema_information with a database name (not a path)
            print("\n--- Testing get_schema_information with database name instead of path ---")
            db_name = "Miro_Printing"  # This is a name, not a path
            try:
                result = await server.call_tool(
                    "get_schema_information", {"db_paths": [db_name]}
                )
                print("\n--- Tool call succeeded despite using a name instead of path ---")
                print(f"Result: {result}")
            except Exception as e:
                print("\n--- Tool call failed as expected ---")
                print(f"Error: {e}")
                result = await server.call_tool(
                    "get_schema_information", {"db_paths": [invalid_path]}
                )
                print("\n--- Tool call succeeded despite invalid path ---")
                print(f"Result: {result}")
            except Exception as e:
                print("\n--- Tool call failed as expected ---")
                print(f"Error: {e}")

    except Exception as e:
        print(f"\nError during test: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(test_invalid_path())
    except KeyboardInterrupt:
        print("\nTest interrupted.")
    except Exception as e:
        print(f"An error occurred: {e}")