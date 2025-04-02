import time
import json
from typing import List, Dict, Any, Optional, Union

# Base Cache class that all specific caches will inherit from
class BaseCache:
    def __init__(self, cache_duration: int = 3600):
        """
        Initialize the base cache.
        
        Args:
            cache_duration: Cache duration in seconds (default: 1 hour)
        """
        self.data = {}  # Dictionary to store cached data
        self.last_updated = {}  # Dictionary to store last update timestamps
        self.cache_duration = cache_duration  # Cache duration in seconds
    
    def is_valid(self, key: str) -> bool:
        """
        Check if the cache for a specific key is still valid.
        
        Args:
            key: The cache key to check
            
        Returns:
            bool: True if the cache is valid, False otherwise
        """
        if key not in self.data or key not in self.last_updated:
            return False
        
        current_time = time.time()
        return (current_time - self.last_updated[key]) < self.cache_duration
    
    def update(self, key: str, data: Any) -> None:
        """
        Update the cache with new data.
        
        Args:
            key: The cache key to update
            data: The data to store in the cache
        """
        self.data[key] = data
        self.last_updated[key] = time.time()
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get data from the cache.
        
        Args:
            key: The cache key to retrieve
            
        Returns:
            The cached data, or None if the key is not in the cache or is invalid
        """
        if not self.is_valid(key):
            return None
        
        return self.data.get(key)
    
    def clear(self, key: Optional[str] = None) -> None:
        """
        Clear the cache for a specific key or all keys.
        
        Args:
            key: The cache key to clear, or None to clear all keys
        """
        if key is None:
            self.data = {}
            self.last_updated = {}
        else:
            if key in self.data:
                del self.data[key]
            if key in self.last_updated:
                del self.last_updated[key]
    
    def get_keys(self) -> List[str]:
        """
        Get a list of all valid cache keys.
        
        Returns:
            List of valid cache keys
        """
        return [key for key in self.data.keys() if self.is_valid(key)]


# Schema Cache class for storing schema information
class SchemaCache(BaseCache):
    def __init__(self, cache_duration: int = 3600):
        """
        Initialize the schema cache.
        
        Args:
            cache_duration: Cache duration in seconds (default: 1 hour)
        """
        super().__init__(cache_duration)
    
    def get_schema_key(self, db_name: str, schema_name: str) -> str:
        """
        Generate a cache key for a schema.
        
        Args:
            db_name: The name of the database
            schema_name: The name of the schema
            
        Returns:
            The cache key for the schema
        """
        return f"db:{db_name}:schema:{schema_name}"
    
    def update_schema(self, db_name: str, schema_name: str, schema_info: Dict[str, Any]) -> None:
        """
        Update the cache with new schema information.
        
        Args:
            db_name: The name of the database
            schema_name: The name of the schema
            schema_info: The schema information to cache
        """
        key = self.get_schema_key(db_name, schema_name)
        self.update(key, schema_info)
    
    def get_schema(self, db_name: str, schema_name: str) -> Optional[Dict[str, Any]]:
        """
        Get schema information from the cache.
        
        Args:
            db_name: The name of the database
            schema_name: The name of the schema
            
        Returns:
            The cached schema information, or None if not in cache or invalid
        """
        key = self.get_schema_key(db_name, schema_name)
        return self.get(key)
    
    def clear_schema(self, db_name: str, schema_name: str) -> None:
        """
        Clear the cache for a specific schema.
        
        Args:
            db_name: The name of the database
            schema_name: The name of the schema
        """
        key = self.get_schema_key(db_name, schema_name)
        self.clear(key)
    
    def clear_database_schemas(self, db_name: str) -> None:
        """
        Clear all schema caches for a specific database.
        
        Args:
            db_name: The name of the database
        """
        prefix = f"db:{db_name}:schema:"
        keys_to_clear = [key for key in self.data.keys() if key.startswith(prefix)]
        for key in keys_to_clear:
            self.clear(key)
    
    def get_tables(self, db_name: str, schema_name: str) -> List[str]:
        """
        Get a list of tables for a specific schema.
        
        Args:
            db_name: The name of the database
            schema_name: The name of the schema
            
        Returns:
            List of table names, or empty list if schema not in cache or invalid
        """
        schema_info = self.get_schema(db_name, schema_name)
        if not schema_info or 'tables' not in schema_info:
            return []
        
        return [table.get('name', '') for table in schema_info.get('tables', [])]


# Table Cache class for storing table information
class TableCache(BaseCache):
    def __init__(self, cache_duration: int = 3600):
        """
        Initialize the table cache.
        
        Args:
            cache_duration: Cache duration in seconds (default: 1 hour)
        """
        super().__init__(cache_duration)
    
    def get_table_key(self, db_name: str, schema_name: str, table_name: str) -> str:
        """
        Generate a cache key for a table.
        
        Args:
            db_name: The name of the database
            schema_name: The name of the schema
            table_name: The name of the table
            
        Returns:
            The cache key for the table
        """
        return f"db:{db_name}:schema:{schema_name}:table:{table_name}"
    
    def update_table(self, db_name: str, schema_name: str, table_name: str, table_info: Dict[str, Any]) -> None:
        """
        Update the cache with new table information.
        
        Args:
            db_name: The name of the database
            schema_name: The name of the schema
            table_name: The name of the table
            table_info: The table information to cache
        """
        key = self.get_table_key(db_name, schema_name, table_name)
        self.update(key, table_info)
    
    def get_table(self, db_name: str, schema_name: str, table_name: str) -> Optional[Dict[str, Any]]:
        """
        Get table information from the cache.
        
        Args:
            db_name: The name of the database
            schema_name: The name of the schema
            table_name: The name of the table
            
        Returns:
            The cached table information, or None if not in cache or invalid
        """
        key = self.get_table_key(db_name, schema_name, table_name)
        return self.get(key)
    
    def clear_table(self, db_name: str, schema_name: str, table_name: str) -> None:
        """
        Clear the cache for a specific table.
        
        Args:
            db_name: The name of the database
            schema_name: The name of the schema
            table_name: The name of the table
        """
        key = self.get_table_key(db_name, schema_name, table_name)
        self.clear(key)
    
    def clear_schema_tables(self, db_name: str, schema_name: str) -> None:
        """
        Clear all table caches for a specific schema.
        
        Args:
            db_name: The name of the database
            schema_name: The name of the schema
        """
        prefix = f"db:{db_name}:schema:{schema_name}:table:"
        keys_to_clear = [key for key in self.data.keys() if key.startswith(prefix)]
        for key in keys_to_clear:
            self.clear(key)
    
    def get_fields(self, db_name: str, schema_name: str, table_name: str) -> List[str]:
        """
        Get a list of fields for a specific table.
        
        Args:
            db_name: The name of the database
            schema_name: The name of the schema
            table_name: The name of the table
            
        Returns:
            List of field names, or empty list if table not in cache or invalid
        """
        table_info = self.get_table(db_name, schema_name, table_name)
        if not table_info or 'fields' not in table_info:
            return []
        
        return [field.get('name', '') for field in table_info.get('fields', [])]


# Script Cache class for storing script information
class ScriptCache(BaseCache):
    def __init__(self, cache_duration: int = 3600):
        """
        Initialize the script cache.
        
        Args:
            cache_duration: Cache duration in seconds (default: 1 hour)
        """
        super().__init__(cache_duration)
    
    def get_script_key(self, script_id: str) -> str:
        """
        Generate a cache key for a script.
        
        Args:
            script_id: The ID of the script
            
        Returns:
            The cache key for the script
        """
        return f"script:{script_id}"
    
    def update_script(self, script_id: str, script_info: Dict[str, Any]) -> None:
        """
        Update the cache with new script information.
        
        Args:
            script_id: The ID of the script
            script_info: The script information to cache
        """
        key = self.get_script_key(script_id)
        self.update(key, script_info)
    
    def get_script(self, script_id: str) -> Optional[Dict[str, Any]]:
        """
        Get script information from the cache.
        
        Args:
            script_id: The ID of the script
            
        Returns:
            The cached script information, or None if not in cache or invalid
        """
        key = self.get_script_key(script_id)
        return self.get(key)
    
    def clear_script(self, script_id: str) -> None:
        """
        Clear the cache for a specific script.
        
        Args:
            script_id: The ID of the script
        """
        key = self.get_script_key(script_id)
        self.clear(key)
    
    def get_scripts(self) -> List[str]:
        """
        Get a list of all script IDs in the cache.
        
        Returns:
            List of script IDs
        """
        script_keys = [key for key in self.get_keys() if key.startswith("script:")]
        return [key.split(":", 1)[1] for key in script_keys]


# Initialize the caches
schema_cache = SchemaCache()
table_cache = TableCache()
script_cache = ScriptCache()