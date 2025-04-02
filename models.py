from pydantic import BaseModel, field_validator, model_validator, Field
from typing import List, Optional, Dict, Any, Union

# Define models for database information
class DataSource(BaseModel):
    name: str
    file_path: str

class Database(BaseModel):
    name: str
    path: str
    directory: str
    table_count: int
    relationship_count: int
    script_count: int
    data_sources: Optional[List[DataSource]] = None

class DatabaseInfo(BaseModel):
    databases: List[Database]
    base_directory: str
    cache_keys: Dict[str, List[str]]

# Define a model for database path validation
class DatabasePathValidationOutput(BaseModel):
    is_valid: bool
    reasoning: str
    
# Define Pydantic models for tool arguments validation
class DatabasePath(BaseModel):
    """Model for validating database paths."""
    path: str
    
    @field_validator('path')
    def validate_path(cls, path):
        """Validate that the path exists in the list of available paths or names."""
        # This is a placeholder - the actual validation will be done in the tool models
        # because we need access to the db_info_cache which isn't available here
        return path

class ToolArgBase(BaseModel):
    """Base model for all tool arguments."""
    model_config = {
        "extra": "forbid"  # Forbid extra fields
    }

class DiscoverDatabasesArgs(ToolArgBase):
    """Arguments for the discover_databases tool."""
    # No parameters required

class GetSchemaInformationArgs(ToolArgBase):
    """Arguments for the get_schema_information tool."""
    db_paths: Union[str, List[str]] = Field(..., description="Path(s) to the database(s)")
    
    @model_validator(mode='before')
    def validate_db_paths(cls, data):
        """Validate that all database paths exist in the list of available paths or names."""
        # This is just a placeholder - the actual validation will be done in validate_tool_args
        return data

class GetTableInformationArgs(ToolArgBase):
    """Arguments for the get_table_information tool."""
    table_name: str = Field(..., description="Name of the table to get information for")
    table_path: str = Field(..., description="Path to the table's database file")

class GetScriptInformationArgs(ToolArgBase):
    """Arguments for the get_script_information tool."""
    db_paths: Optional[Union[str, List[str]]] = Field(None, description="Path(s) to the database(s)")
    db_names: Optional[Union[str, List[str]]] = Field(None, description="Name(s) of the database(s)")
    
    @model_validator(mode='before')
    def validate_db_paths(cls, data):
        """Validate that all database paths exist in the list of available paths or names."""
        # This is just a placeholder - the actual validation will be done in validate_tool_args
        return data
    
    @model_validator(mode='after')
    def validate_at_least_one_param(cls, data):
        """Validate that at least one of db_paths or db_names is provided."""
        if not data.db_paths and not data.db_names:
            raise ValueError("Either db_paths or db_names must be provided")
        return data

class GetScriptDetailsArgs(ToolArgBase):
    """Arguments for the get_script_details tool."""
    script_name: str = Field(..., description="Name of the script to get details for")
    script_path: str = Field(..., description="Path to the script's database file")

class GetCustomFunctionsArgs(ToolArgBase):
    """Arguments for the get_custom_functions tool."""
    db_path: Optional[str] = Field(None, description="Path to the database")
    db_name: Optional[str] = Field(None, description="Name of the database")
    
    @model_validator(mode='after')
    def validate_at_least_one_param(cls, data):
        """Validate that at least one of db_path or db_name is provided."""
        if not data.db_path and not data.db_name:
            raise ValueError("Either db_path or db_name must be provided")
        return data

class ReadFileContentArgs(ToolArgBase):
    """Arguments for the read_file_content tool."""
    file_path: Optional[str] = Field(None, description="Path to the file to read")
    file_name: Optional[str] = Field(None, description="Name of the file to read")
    chunk_size: Optional[int] = Field(None, description="Maximum size of each chunk in bytes")
    
    @model_validator(mode='after')
    def validate_at_least_one_param(cls, data):
        """Validate that at least one of file_path or file_name is provided."""
        if not data.file_path and not data.file_name:
            raise ValueError("Either file_path or file_name must be provided")
        return data

class ReadChunkArgs(ToolArgBase):
    """Arguments for the read_chunk tool."""
    chunk_path: Optional[str] = Field(None, description="Path to the chunk file")
    chunk_name: Optional[str] = Field(None, description="Name of the chunk file")
    
    @model_validator(mode='after')
    def validate_at_least_one_param(cls, data):
        """Validate that at least one of chunk_path or chunk_name is provided."""
        if not data.chunk_path and not data.chunk_name:
            raise ValueError("Either chunk_path or chunk_name must be provided")
        return data

class CleanupOldFilesArgs(ToolArgBase):
    """Arguments for the cleanup_old_files tool."""
    max_age_seconds: Optional[int] = Field(None, description="Maximum age of files to keep in seconds")

# Map tool names to their argument models
TOOL_ARG_MODELS = {
    "discover_databases": DiscoverDatabasesArgs,
    "get_schema_information": GetSchemaInformationArgs,
    "get_table_information": GetTableInformationArgs,
    "get_script_information": GetScriptInformationArgs,
    "get_script_details": GetScriptDetailsArgs,
    "get_custom_functions": GetCustomFunctionsArgs,
    "read_file_content": ReadFileContentArgs,
    "read_chunk": ReadChunkArgs,
    "cleanup_old_files": CleanupOldFilesArgs,
}