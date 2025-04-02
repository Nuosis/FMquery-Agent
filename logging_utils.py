import time
import json
import os
import sys
import logging
from logging.handlers import RotatingFileHandler
from typing import List, Dict, Any, Optional

try:
    from agents.items import ToolCallItem
except ImportError:
    # Define a placeholder for when the import is not available
    class ToolCallItem:
        pass

# Constants
DEFAULT_LOG_LEVEL = "DEBUG"
DEFAULT_LOG_FILE = "agent_debug.log"
MAX_LOG_SIZE = 10 * 1024 * 1024  # 10MB
BACKUP_COUNT = 5

# Global list to store all tool calls for logging (maintained for compatibility)
all_tool_calls = []

# Initialize root logger
logger = None

class ToolCallHandler(logging.Handler):
    """Custom logging handler that tracks tool calls in memory."""
    
    def __init__(self, level=logging.INFO):
        super().__init__(level)
        self.tool_calls = []
    
    def emit(self, record):
        """Process a log record and store tool calls if applicable."""
        if hasattr(record, 'tool_name'):
            self.tool_calls.append({
                "name": record.tool_name,
                "arguments": getattr(record, 'tool_arguments', "{}"),
                "timestamp": time.time(),
                "result": getattr(record, 'tool_result', "{}")
            })


def setup_logging(log_level=None, log_file=None):
    """
    Set up the logging system with appropriate handlers.
    
    Args:
        log_level: Logging level (DEBUG, INFO, etc.). Defaults to INFO or env var.
        log_file: Path to debug log file. Defaults to agent_debug.log or env var.
    
    Returns:
        The configured root logger.
    """
    global logger
    
    # Get configuration from environment or use defaults
    if log_level is None:
        log_level = os.environ.get("LOG_LEVEL", DEFAULT_LOG_LEVEL)
    
    if log_file is None:
        log_file = os.environ.get("LOG_FILE", DEFAULT_LOG_FILE)
    
    # Convert string log level to logging constant
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Create a root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)  # Capture all messages at root
    
    # Clear any existing handlers
    root_logger.handlers = []
    
    # Create formatter
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    
    # Add stdout handler for INFO and above
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setLevel(logging.INFO)  # Always show INFO+ on stdout
    stream_handler.setFormatter(formatter)
    root_logger.addHandler(stream_handler)
    
    # Add file handler for DEBUG and above if in DEBUG mode
    if numeric_level <= logging.DEBUG:
        file_handler = RotatingFileHandler(
            log_file, 
            maxBytes=MAX_LOG_SIZE, 
            backupCount=BACKUP_COUNT
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    # Set log level for HTTP-related loggers to WARNING to avoid INFO-level HTTP logs
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    
    
    # Add custom tool call handler
    tool_handler = ToolCallHandler(level=logging.INFO)
    root_logger.addHandler(tool_handler)
    
    logger = root_logger
    return root_logger


def get_module_logger(name):
    """
    Get a logger for a specific module.
    
    Args:
        name: The name of the module.
        
    Returns:
        A logger configured for the module.
    """
    if logger is None:
        setup_logging()
    
    return logging.getLogger(name)


def log_tool_call(name, arguments, result=None):
    """
    Log a tool call with its name, arguments, and result.
    
    Args:
        name: The name of the tool.
        arguments: The arguments passed to the tool.
        result: The result of the tool call (optional).
    """
    # Initialize logging if not already done
    if logger is None:
        setup_logging()
    
    # Create a log record with extra attributes for the tool call handler
    extra = {
        'tool_name': name,
        'tool_arguments': arguments,
        'tool_result': result or "{}"
    }
    
    # Log a concise message at INFO level
    logger.info("Tool Call: %s", name, extra=extra)
    
    # Log detailed arguments at DEBUG level
    logger.debug("Tool Call: %s with args: %s", name, arguments, extra=extra)
    
    # Only log results at DEBUG level unless there's an error
    if result:
        if isinstance(result, dict) and result.get('error'):
            logger.info("Tool Call Failed: %s - %s", name, result.get('error'))
        else:
            logger.debug("Tool Result: %s", result)
    
    # Maintain existing tool call tracking for backward compatibility
    all_tool_calls.append({
        "name": name,
        "arguments": arguments,
        "timestamp": time.time(),
        "result": result or "{}"
    })


def log_validation_failure(parameter, expected, actual, action_taken=None):
    """
    Log a validation failure at DEBUG level (was INFO).
    
    Args:
        parameter: The parameter that failed validation.
        expected: What was expected.
        actual: What was actually provided.
        action_taken: What action was taken (terminal, returned to LLM, etc.).
    """
    if logger is None:
        setup_logging()
    
    # Log detailed information at DEBUG level
    debug_message = f"Validation Failed: Parameter '{parameter}' - Expected: {expected}, Actual: {actual}"
    if action_taken:
        debug_message += f" - Action: {action_taken}"
    logger.debug(debug_message)


def log_orchestration_intervention(tool_name, reason, action_taken):
    """
    Log when orchestration intervention is required.
    
    Args:
        tool_name: The name of the tool being orchestrated.
        reason: The reason orchestration was required.
        action_taken: What action orchestration took.
    """
    if logger is None:
        setup_logging()
    
    # Log a concise message at INFO level
    logger.info("Orchestration Required: %s - Action: %s", tool_name, action_taken)
    
    # Log detailed reason at DEBUG level
    logger.debug("Orchestration Required: %s - Reason: %s - Action: %s",
                tool_name, reason, action_taken)


def log_workaround(issue, workaround):
    """
    Log when a workaround is employed.
    
    Args:
        issue: The issue that required a workaround.
        workaround: The workaround that was employed.
    """
    if logger is None:
        setup_logging()
    
    logger.info("Workaround Employed: %s - Solution: %s", issue, workaround)


def log_failure(operation, reason, impact=None):
    """
    Log a failure with a concise explanation.
    
    Args:
        operation: The operation that failed.
        reason: The reason for the failure.
        impact: The impact of the failure (optional).
    """
    if logger is None:
        setup_logging()
    
    # Log a concise message at INFO level
    info_message = f"Operation Failed: {operation}"
    if impact:
        info_message += f" - Impact: {impact}"
    logger.info(info_message)
    
    # Log detailed reason at DEBUG level
    debug_message = f"Operation Failed: {operation} - Reason: {reason}"
    if impact:
        debug_message += f" - Impact: {impact}"
    logger.debug(debug_message)


def extract_tool_calls_from_result(result):
    """
    Extract tool calls from a result object and log them.
    
    Args:
        result: The result object containing tool calls.
    """
    # Initialize logging if not already done
    if logger is None:
        setup_logging()
    
    logger.debug("Extracting tool calls from result")
    
    if hasattr(result, 'new_items') and result.new_items:
        item_count = len(result.new_items)
        logger.debug("Found %d new items in result", item_count)
        
        tool_call_count = 0
        for i, item in enumerate(result.new_items):
            if isinstance(item, ToolCallItem) and hasattr(item, 'raw_item'):
                logger.debug("Processing ToolCallItem %d", i+1)
                raw_item = item.raw_item
                
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
                    tool_call_count += 1
                    log_tool_call(name, arguments or "{}", result_value)
                else:
                    logger.warning("Found ToolCallItem without a name, skipping")
        
        if tool_call_count > 0:
            logger.info("Processed %d tool calls from result", tool_call_count)
    else:
        logger.debug("No tool calls found in result")


# Initialize logging when module is imported
setup_logging()