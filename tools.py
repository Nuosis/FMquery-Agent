import json
import time
import argparse
from typing import Dict, List, Any, Optional
from agents.mcp import MCPServer

from cache import tools_cache
from logging_utils import logger, log_failure

# Function to get tools information from the MCP server
async def get_tools_info(mcp_server, force_refresh=False, save_to_disk=False):
    """
    Get tools information from the MCP server using the list_tools_tool.
    
    Args:
        mcp_server: The MCP server to query
        force_refresh: If True, force a refresh of the cache
        
    Returns:
        Dictionary containing tools information
    """
    # Check if we have a valid cache and don't need to force refresh
    if tools_cache.is_valid() and not force_refresh:
        logger.info("Using cached tools information")
        return tools_cache.tools_info
    
    try:
        # Measure time for the direct tool call
        start_time = time.time()
        
        # Call the list_tools_tool directly
        logger.debug("Calling list_tools_tool")
        result = await mcp_server.call_tool("list_tools_tool", {})
        
        # Calculate and log execution time
        end_time = time.time()
        execution_time = end_time - start_time
        logger.info("Tools listing completed in %.2f seconds", execution_time)
        
        # Extract the text content from the result
        tools_info = None
        if hasattr(result, 'content') and result.content:
            logger.debug("Processing result content with %d items", len(result.content))
            for content_item in result.content:
                if hasattr(content_item, 'text') and content_item.text:
                    json_str = content_item.text
                    
                    # Parse the JSON
                    logger.debug("Parsing JSON response")
                    tools_info = json.loads(json_str)
                    
                    # Log success
                    tool_count = len(tools_info.get('tools', []))
                    logger.info("Successfully extracted information for %d tools", tool_count)
                    
                    # Log tool names at debug level
                    if logger.isEnabledFor(10):  # DEBUG level
                        tool_names = [tool.get('name', 'unnamed') for tool in tools_info.get('tools', [])]
                        logger.debug("Tool names: %s", tool_names)
                    break
        
        # If we couldn't extract the tools info, raise an exception
        if not tools_info:
            error_msg = "Failed to extract tools information from list_tools_tool result"
            # Log a concise message at INFO level
            log_failure("Tools information fetch", "Failed to extract tools information", "Raising exception")
            # Log detailed error at DEBUG level
            logger.debug("%s. Result type: %s", error_msg, type(result))
            raise RuntimeError(error_msg)
        
        # Store the tools info in the cache
        logger.debug("Updating tools info cache")
        tools_cache.update(tools_info)
        
        # Save to disk if requested
        if save_to_disk:
            logger.info("Saving tools cache to disk")
            tools_cache.save_to_disk()
        return tools_info
    except Exception as e:
        log_failure("Tools information fetch", str(e))
        # Propagate the exception instead of returning an empty dict
        raise