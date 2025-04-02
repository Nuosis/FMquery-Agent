import functools
from pydantic import create_model, ValidationError, field_validator
from typing import Callable, Any, Dict, List, Type, Optional
import json
from cache import db_info_cache
from logging_utils import logger, log_validation_failure

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
                    logger.debug("Adding validator function %s for parameter %s", 
                                validator_func.__name__, param_name)
                    validators[param_name] = validator_func

            # Create a dictionary of validators for the model
            logger.debug("Creating model with validators: %s", list(validators.keys()))
            
            # Create validator methods directly in a namespace dictionary
            namespace = {}
            for param_name, validator_func in validators.items():
                logger.debug("Creating validator method for parameter %s", param_name)
                
                # Define the validator method directly in the namespace
                @field_validator(param_name)
                def validate_param(cls, v, info):
                    logger.debug("Pydantic validator called for %s with value: %s", param_name, v)
                    try:
                        # Call the validator function
                        validator_func(v)
                        logger.debug("Validator function succeeded for %s", param_name)
                        return v
                    except ValueError as e:
                        # Re-raise the error with the same message
                        logger.info("Validation failed for %s: %s", param_name, str(e))
                        raise ValueError(str(e))
                
                # Add the validator to the namespace
                namespace[f"validate_{param_name}"] = validate_param
            
            # Create the model with the namespace containing validators
            logger.debug("Creating Pydantic model with fields: %s", list(fields.keys()))
            ModelClass = create_model("ToolParameters", **fields, __validators__=namespace)

            # 2. Validate Input
            try:
                logger.debug("Validating input with Pydantic model: %s", kwargs)
                validated_data = ModelClass(**kwargs)
                logger.info("Parameter validation succeeded")
                # 5. Call the Tool
                return await func(*args, **validated_data.model_dump())
            except ValidationError as e:
                # 3. Handle Validation Errors
                logger.info("Pydantic validation error: %s", e)
                for error in e.errors():
                    param = error["loc"][0] if error["loc"] else "unknown"
                    msg = error["msg"]
                    value = kwargs.get(param, "not provided")
                    log_validation_failure(param, "valid value", f"{value} - {msg}", "raising ToolParameterValidationError")
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