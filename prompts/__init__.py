"""
This package contains prompt-related functionality for the FMquery-Agent system.
"""

from .prompts import (
    construct_prompt,
    serve_prompt,
    get_filemaker_agent_prompt,
    get_prompt,
    available_prompts,
    default_prompt
)

__all__ = [
    'construct_prompt',
    'serve_prompt',
    'get_filemaker_agent_prompt',
    'get_prompt',
    'available_prompts',
    'default_prompt'
]