import json
import time
from typing import Dict, List, Any, Optional
from agents.mcp import MCPServer

from cache import db_info_cache

# Function to get database information from the MCP server
async def get_database_info(mcp_server, force_refresh=False):
    """
    Get database information from the MCP server using the discover_databases tool.
    
    Args:
        mcp_server: The MCP server to query
        force_refresh: If True, force a refresh of the cache
        
    Returns:
        Dictionary containing database information
    """
    # Check if we have a valid cache and don't need to force refresh
    if db_info_cache.is_valid() and not force_refresh:
        print("Using cached database information")
        return db_info_cache.db_info
    
    try:
        print("Fetching database information...")
        
        # Measure time for the direct tool call
        start_time = time.time()
        
        # Call the discover_databases tool directly
        result = await mcp_server.call_tool("discover_databases", {})
        
        # Calculate and print execution time
        end_time = time.time()
        execution_time = end_time - start_time
        print(f"Tool call completed in {execution_time:.2f} seconds")
        
        # Extract the text content from the result
        db_info = None
        if hasattr(result, 'content') and result.content:
            for content_item in result.content:
                if hasattr(content_item, 'text') and content_item.text:
                    json_str = content_item.text
                    
                    # Parse the JSON
                    db_info = json.loads(json_str)
                    
                    # Log success
                    print(f"Successfully extracted database information")
                    print(f"Found {len(db_info.get('databases', []))} databases")
                    break
        
        # If we couldn't extract the database info, raise an exception
        if not db_info:
            error_msg = "Failed to extract database information from discover_databases tool result."
            print(f"Error: {error_msg}")
            print(f"Result type: {type(result)}")
            raise RuntimeError(error_msg)
        
        # Store the database info in the cache
        db_info_cache.update(db_info)
        print(f"Updated database info cache with {len(db_info.get('databases', []))} databases")
        return db_info
    except Exception as e:
        print(f"Error fetching database information: {e}")
        # Propagate the exception instead of returning an empty dict
        raise

# Function to get available database paths from the MCP server (for backward compatibility)
async def get_available_db_paths(mcp_server, force_refresh=False):
    """
    Get a list of available database paths from the MCP server.
    
    Args:
        mcp_server: The MCP server to query
        force_refresh: If True, force a refresh of the cache
        
    Returns:
        List of available database paths
    """
    # Get the database info
    db_info = await get_database_info(mcp_server, force_refresh)
    
    # Extract paths from the database info
    return db_info_cache.get_paths()