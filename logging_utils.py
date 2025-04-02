import time
import json
from typing import List, Dict, Any, Optional
from agents.items import ToolCallItem

# Global list to store all tool calls for logging
all_tool_calls = []

# Function to log tool calls
def log_tool_call(name, arguments, result=None):
    """Log a tool call with its name, arguments, and result."""
    all_tool_calls.append({
        "name": name,
        "arguments": arguments,
        "timestamp": time.time(),
        "result": result or "{}"
    })
    print(f"\n--- Tool Call Information ---")
    print(f"name='{name}',")
    print(f"arguments='{arguments}',")
    if result:
        print(f"result='{result}',")
    print()  # Add a blank line after tool call info

# Function to extract tool calls from a result object
def extract_tool_calls_from_result(result):
    """Extract tool calls from a result object and log them."""
    #print("\n--- DEBUG: extract_tool_calls_from_result called ---")
    #print(f"Result type: {type(result)}")
    
    if hasattr(result, 'new_items') and result.new_items:
        print(f"Found {len(result.new_items)} new items in result")
        for i, item in enumerate(result.new_items):
            print(f"Examining item {i+1}, type: {type(item)}")
            if isinstance(item, ToolCallItem) and hasattr(item, 'raw_item'):
                print(f"Item {i+1} is a ToolCallItem with raw_item")
                raw_item = item.raw_item
                print(f"Raw item type: {type(raw_item)}")
                
                # Extract tool name, arguments, and result
                name = None
                arguments = None
                result_value = None
                
                if hasattr(raw_item, 'name'):
                    name = raw_item.name
                elif isinstance(raw_item, dict) and 'name' in raw_item:
                    name = raw_item['name']
                
                if hasattr(raw_item, 'arguments'):
                    arguments = raw_item.arguments
                elif isinstance(raw_item, dict) and 'arguments' in raw_item:
                    arguments = raw_item['arguments']
                
                # Extract result if available
                if hasattr(raw_item, 'result'):
                    result_value = raw_item.result
                elif isinstance(raw_item, dict) and 'result' in raw_item:
                    result_value = raw_item['result']
                
                # Log the tool call if we have a name
                if name:
                    print(f"Adding tool call to all_tool_calls: {name}")
                    log_tool_call(name, arguments or "{}", result_value)
                else:
                    print(f"WARNING: Tool call has no name, skipping")
    else:
        print("No new items found in result or result has no 'new_items' attribute")