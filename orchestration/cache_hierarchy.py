import time
import json
from typing import List, Dict, Any, Optional, Union
from logging_utils import logger

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
        logger.debug("BaseCache initialized with cache duration: %d seconds", self.cache_duration)
    
    def is_valid(self, key: str) -> bool:
        """
        Check if the cache for a specific key is still valid.
        
        Args:
            key: The cache key to check
            
        Returns:
            bool: True if the cache is valid, False otherwise
        """
        if key not in self.data or key not in self.last_updated:
            logger.debug("Cache key '%s' not found or no timestamp", key)
            return False
        
        current_time = time.time()
        time_diff = current_time - self.last_updated[key]
        is_valid = time_diff < self.cache_duration
        
        if is_valid:
            logger.debug("Cache key '%s' is valid (%d seconds remaining)", 
                        key, self.cache_duration - time_diff)
        else:
            logger.debug("Cache key '%s' has expired (%d seconds past expiration)", 
                        key, time_diff - self.cache_duration)
            
        return is_valid
    
    def update(self, key: str, data: Any) -> None:
        """
        Update the cache with new data.
        
        Args:
            key: The cache key to update
            data: The data to store in the cache
        """
        logger.debug("Updating cache for key '%s'", key)
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
            logger.debug("Cache miss for key '%s'", key)
            return None
        
        logger.debug("Cache hit for key '%s'", key)
        return self.data.get(key)
    
    def clear(self, key: Optional[str] = None) -> None:
        """
        Clear the cache for a specific key or all keys.
        
        Args:
            key: The cache key to clear, or None to clear all keys
        """
        if key is None:
            logger.info("Clearing entire cache (%d keys)", len(self.data))
            self.data = {}
            self.last_updated = {}
        else:
            if key in self.data:
                logger.info("Clearing cache for key '%s'", key)
                del self.data[key]
            if key in self.last_updated:
                del self.last_updated[key]
    
    def get_keys(self) -> List[str]:
        """
        Get a list of all valid cache keys.
        
        Returns:
            List of valid cache keys
        """
        valid_keys = [key for key in self.data.keys() if self.is_valid(key)]
        logger.debug("Retrieved %d valid cache keys", len(valid_keys))
        return valid_keys


# Schema Cache class for storing schema information
class SchemaCache(BaseCache):
    def __init__(self, cache_duration: int = 3600):
        """
        Initialize the schema cache.
        
        Args:
            cache_duration: Cache duration in seconds (default: 1 hour)
        """
        super().__init__(cache_duration)
        logger.debug("SchemaCache initialized")
    
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
        logger.info("Updating schema cache for %s.%s", db_name, schema_name)
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
        schema_info = self.get(key)
        if schema_info:
            logger.debug("Retrieved schema information for %s.%s from cache", db_name, schema_name)
        else:
            logger.debug("Schema information for %s.%s not found in cache", db_name, schema_name)
        return schema_info
    
    def clear_schema(self, db_name: str, schema_name: str) -> None:
        """
        Clear the cache for a specific schema.
        
        Args:
            db_name: The name of the database
            schema_name: The name of the schema
        """
        key = self.get_schema_key(db_name, schema_name)
        logger.info("Clearing schema cache for %s.%s", db_name, schema_name)
        self.clear(key)
    
    def clear_database_schemas(self, db_name: str) -> None:
        """
        Clear all schema caches for a specific database.
        
        Args:
            db_name: The name of the database
        """
        prefix = f"db:{db_name}:schema:"
        keys_to_clear = [key for key in self.data.keys() if key.startswith(prefix)]
        logger.info("Clearing %d schema caches for database %s", len(keys_to_clear), db_name)
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
            logger.debug("No table information found for %s.%s", db_name, schema_name)
            return []
        
        tables = [table.get('name', '') for table in schema_info.get('tables', [])]
        logger.debug("Retrieved %d tables for %s.%s", len(tables), db_name, schema_name)
        return tables


# Table Cache class for storing table information
class TableCache(BaseCache):
    def __init__(self, cache_duration: int = 3600):
        """
        Initialize the table cache.
        
        Args:
            cache_duration: Cache duration in seconds (default: 1 hour)
        """
        super().__init__(cache_duration)
        logger.debug("TableCache initialized")
    
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
        logger.info("Updating table cache for %s.%s.%s", db_name, schema_name, table_name)
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
        table_info = self.get(key)
        if table_info:
            logger.debug("Retrieved table information for %s.%s.%s from cache", 
                        db_name, schema_name, table_name)
        else:
            logger.debug("Table information for %s.%s.%s not found in cache", 
                        db_name, schema_name, table_name)
        return table_info
    
    def clear_table(self, db_name: str, schema_name: str, table_name: str) -> None:
        """
        Clear the cache for a specific table.
        
        Args:
            db_name: The name of the database
            schema_name: The name of the schema
            table_name: The name of the table
        """
        key = self.get_table_key(db_name, schema_name, table_name)
        logger.info("Clearing table cache for %s.%s.%s", db_name, schema_name, table_name)
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
        logger.info("Clearing %d table caches for schema %s.%s", 
                   len(keys_to_clear), db_name, schema_name)
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
            logger.debug("No field information found for %s.%s.%s", 
                        db_name, schema_name, table_name)
            return []
        
        fields = [field.get('name', '') for field in table_info.get('fields', [])]
        logger.debug("Retrieved %d fields for %s.%s.%s", 
                    len(fields), db_name, schema_name, table_name)
        return fields


# Script Cache class for storing script information
class ScriptCache(BaseCache):
    def __init__(self, cache_duration: int = 3600):
        """
        Initialize the script cache.
        
        Args:
            cache_duration: Cache duration in seconds (default: 1 hour)
        """
        super().__init__(cache_duration)
        logger.debug("ScriptCache initialized")
    
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
        logger.info("Updating script cache for script %s", script_id)
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
        script_info = self.get(key)
        if script_info:
            logger.debug("Retrieved script information for %s from cache", script_id)
        else:
            logger.debug("Script information for %s not found in cache", script_id)
        return script_info
    
    def clear_script(self, script_id: str) -> None:
        """
        Clear the cache for a specific script.
        
        Args:
            script_id: The ID of the script
        """
        key = self.get_script_key(script_id)
        logger.info("Clearing script cache for script %s", script_id)
        self.clear(key)
    
    def get_scripts(self) -> List[str]:
        """
        Get a list of all script IDs in the cache.
        
        Returns:
            List of script IDs
        """
        script_keys = [key for key in self.get_keys() if key.startswith("script:")]
        script_ids = [key.split(":", 1)[1] for key in script_keys]
        logger.debug("Retrieved %d script IDs from cache", len(script_ids))
        return script_ids


# Initialize the caches
schema_cache = SchemaCache()
table_cache = TableCache()
script_cache = ScriptCache()