import functools
from pydantic import create_model, ValidationError, field_validator
from typing import Callable, Any, Dict, List, Type, Optional
import json
from cache import db_info_cache

def validate_tool_parameters(tool_spec: Dict[str, Any]):
    """
    Decorator to validate tool call parameters using Pydantic.

    Args:
        tool_spec: A dictionary containing the tool's parameter specifications.
                   Example:
                   {
                       "param1": {"type": "str", "required": True},
                       "param2": {"type": "int", "required": False},
                       "param3": {"type": "str", "required": True, "validator": validate_param3}
                   }
                   
                   The "validator" key is optional and should be a function that takes the parameter value
                   and returns True if it's valid, or raises a ValueError with a descriptive message if not.
    """
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # 1. Define a Pydantic Model
            fields = {}
            validators = {}
            
            for param_name, param_spec in tool_spec.items():
                param_type = param_spec.get("type", "str")  # Default to string if type is not specified
                required = param_spec.get("required", True)  # Default to required if not specified
                validator_func = param_spec.get("validator")  # Optional validator function

                # Map string types to Python types
                if param_type == "str":
                    python_type = str
                elif param_type == "int":
                    python_type = int
                elif param_type == "float":
                    python_type = float
                elif param_type == "bool":
                    python_type = bool
                elif param_type == "list":
                    python_type = list
                else:
                    python_type = str  # Default to string

                fields[param_name] = (python_type, ... if required else None)
                
                # If a validator function is provided, add it to the validators dictionary
                if validator_func:
                    #print(f"\n--- DEBUG: Adding validator function {validator_func.__name__} for parameter {param_name} ---")
                    validators[param_name] = validator_func

            # Create a dictionary of validators for the model
            #print(f"\n--- DEBUG: Adding validators to the model: {validators} ---")
            
            # Create validator methods directly in a namespace dictionary
            namespace = {}
            for param_name, validator_func in validators.items():
                #print(f"--- DEBUG: Creating validator method for parameter {param_name} ---")
                
                # Define the validator method directly in the namespace
                @field_validator(param_name)
                def validate_param(cls, v, info):
                    print(f"\n--- DEBUG: Pydantic validator called for {param_name} with value: {v} ---")
                    try:
                        # Call the validator function
                        #print(f"--- DEBUG: Calling validator function: {validator_func.__name__} ---")
                        validator_func(v)
                        #print(f"--- DEBUG: Validator function succeeded ---")
                        return v
                    except ValueError as e:
                        # Re-raise the error with the same message
                        print(f"--- DEBUG: Validator function raised ValueError: {e} ---")
                        raise ValueError(str(e))
                
                # Add the validator to the namespace
                namespace[f"validate_{param_name}"] = validate_param
            
            # Create the model with the namespace containing validators
            #print(f"--- DEBUG: Creating model with namespace: {namespace.keys()} ---")
            ModelClass = create_model("ToolParameters", **fields, __validators__=namespace)

            # 2. Validate Input
            try:
                #print(f"\n--- DEBUG: Validating input with Pydantic model: {kwargs} ---")
                validated_data = ModelClass(**kwargs)
                print(f"--- DEBUG: Validation succeeded ---")
                # 5. Call the Tool
                return await func(*args, **validated_data.model_dump())
            except ValidationError as e:
                # 3. Handle Validation Errors
                print(f"--- DEBUG: Pydantic validation error: {e} ---")
                raise ToolParameterValidationError(e.errors(), kwargs)

        return wrapper
    return decorator

class ToolParameterValidationError(Exception):
    """
    Custom exception for tool parameter validation errors.
    """
    def __init__(self, errors, original_params):
        self.errors = errors
        self.original_params = original_params
        super().__init__(f"Tool parameter validation failed: {errors}")

    def to_dict(self):
        """
        Convert the error to a dictionary format suitable for LLM revision.
        """
        changes = []
        for error in self.errors:
            changes.append({
                "parameter": error["loc"][0],
                "reason": error["msg"],
                "original_value": self.original_params.get(error["loc"][0])
            })
        return {
            "errors": self.errors,
            "original_params": self.original_params,
            "changes": changes
        }