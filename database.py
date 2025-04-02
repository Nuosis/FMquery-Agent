import json
import time
import argparse
from typing import Dict, List, Any, Optional
from agents.mcp import MCPServer

from cache import db_info_cache
from logging_utils import logger, log_failure

# Function to get database information from the MCP server
async def get_database_info(mcp_server, force_refresh=False, save_to_disk=False):
    """
    Get database information from the MCP server using the discover_databases_tool.
    
    Args:
        mcp_server: The MCP server to query
        force_refresh: If True, force a refresh of the cache
        
    Returns:
        Dictionary containing database information
    """
    # Check if we have a valid cache and don't need to force refresh
    if db_info_cache.is_valid() and not force_refresh:
        logger.info("Using cached database information")
        return db_info_cache.db_info
    
    try:
        
        # Measure time for the direct tool call
        start_time = time.time()
        
        # Call the discover_databases_tool directly
        logger.debug("Calling discover_databases_tool")
        result = await mcp_server.call_tool("discover_databases_tool", {})
        
        # Calculate and log execution time
        end_time = time.time()
        execution_time = end_time - start_time
        logger.info("Database discovery completed in %.2f seconds", execution_time)
        
        # Extract the text content from the result
        db_info = None
        if hasattr(result, 'content') and result.content:
            logger.debug("Processing result content with %d items", len(result.content))
            for content_item in result.content:
                if hasattr(content_item, 'text') and content_item.text:
                    json_str = content_item.text
                    
                    # Parse the JSON
                    logger.debug("Parsing JSON response")
                    db_info = json.loads(json_str)
                    
                    # Log success
                    db_count = len(db_info.get('databases', []))
                    logger.info("Successfully extracted information for %d databases", db_count)
                    
                    # Log database names at debug level
                    if logger.isEnabledFor(10):  # DEBUG level
                        db_names = [db.get('name', 'unnamed') for db in db_info.get('databases', [])]
                        logger.debug("Database names: %s", db_names)
                    break
        
        # If we couldn't extract the database info, raise an exception
        if not db_info:
            error_msg = "Failed to extract database information from discover_databases_tool result"
            # Log a concise message at INFO level
            log_failure("Database information fetch", "Failed to extract database information", "Raising exception")
            # Log detailed error at DEBUG level
            logger.debug("%s. Result type: %s", error_msg, type(result))
            raise RuntimeError(error_msg)
        
        # Store the database info in the cache
        logger.debug("Updating database info cache")
        db_info_cache.update(db_info)
        
        # Save to disk if requested
        if save_to_disk:
            logger.info("Saving database cache to disk")
            db_info_cache.save_to_disk()
        return db_info
    except Exception as e:
        log_failure("Database information fetch", str(e))
        # Propagate the exception instead of returning an empty dict
        raise

# Function to get available database paths from the MCP server (for backward compatibility)
async def get_available_db_paths(mcp_server, force_refresh=False, save_to_disk=False):
    """
    Get a list of available database paths from the MCP server.
    
    Args:
        mcp_server: The MCP server to query
        force_refresh: If True, force a refresh of the cache
        
    Returns:
        List of available database paths
    """
    logger.debug("Getting available database paths (force_refresh=%s)", force_refresh)
    
    # Get the database info
    db_info = await get_database_info(mcp_server, force_refresh, save_to_disk)
    
    # Extract paths from the database info
    paths = db_info_cache.get_paths()
    logger.info("Retrieved %d database paths", len(paths))
    return paths