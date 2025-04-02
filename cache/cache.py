import time
import json
import os
from typing import List, Dict, Any
from logging_utils import logger

# Create cache directory if it doesn't exist
CACHE_DIR = os.path.dirname(os.path.abspath(__file__))
os.makedirs(CACHE_DIR, exist_ok=True)

# Cache for database information
class DBInfoCache:
    def __init__(self):
        self.db_info = None  # Will store the full response from discover_databases
        self.last_updated = None
        self.cache_duration = 3600  # Cache duration in seconds (1 hour)
        self.cache_file = os.path.join(CACHE_DIR, "db_info_cache.json")
        logger.debug("DBInfoCache initialized with cache duration: %d seconds", self.cache_duration)
    
    def is_valid(self):
        """Check if the cache is still valid."""
        if not self.db_info or not self.last_updated:
            logger.debug("Cache invalid: db_info or last_updated is None")
            return False
        
        current_time = time.time()
        time_diff = current_time - self.last_updated
        is_valid = time_diff < self.cache_duration
        
        if is_valid:
            logger.debug("Cache valid: %d seconds remaining", self.cache_duration - time_diff)
        else:
            logger.debug("Cache expired: %d seconds past expiration", time_diff - self.cache_duration)
            
        return is_valid
    
    def update(self, db_info):
        """Update the cache with new database information."""
        logger.debug("Updating database info cache")
        
        if isinstance(db_info, dict) and 'databases' in db_info:
            
            # Log database names at debug level
            if logger.isEnabledFor(10):  # DEBUG level
                db_names = [db.get('name', 'unnamed') for db in db_info.get('databases', [])]
                logger.debug("Database names: %s", db_names)
        else:
            logger.warning("Updating cache with invalid db_info format: %s", type(db_info))
            
        self.db_info = db_info
        self.last_updated = time.time()
        logger.debug("Cache updated at: %s", time.ctime(self.last_updated))
    
    def clear(self):
        """Clear the cache."""
        logger.info("Clearing database info cache")
        self.db_info = None
        self.last_updated = None
        
    def save_to_disk(self):
        """Save the cache to disk for testing/reference purposes."""
        if not self.db_info:
            logger.warning("Cannot save empty cache to disk")
            return False
            
        try:
            cache_data = {
                "db_info": self.db_info,
                "last_updated": self.last_updated
            }
            
            with open(self.cache_file, 'w') as f:
                json.dump(cache_data, f, indent=2)
                
            logger.info(f"Database cache saved to {self.cache_file}")
            return True
        except Exception as e:
            logger.error(f"Failed to save database cache to disk: {str(e)}")
            return False
            
    def load_from_disk(self):
        """Load the cache from disk."""
        if not os.path.exists(self.cache_file):
            logger.warning(f"Cache file {self.cache_file} does not exist")
            return False
            
        try:
            with open(self.cache_file, 'r') as f:
                cache_data = json.load(f)
                
            self.db_info = cache_data.get("db_info")
            self.last_updated = cache_data.get("last_updated")
            
            logger.info(f"Database cache loaded from {self.cache_file}")
            return True
        except Exception as e:
            logger.error(f"Failed to load database cache from disk: {str(e)}")
            return False
    
    def get_paths(self):
        """Get a list of all database paths."""
        if not self.db_info or 'databases' not in self.db_info:
            logger.warning("Cannot get database paths: db_info is None or 'databases' not in db_info")
            return []
        
        paths = [db.get('path', '') for db in self.db_info.get('databases', [])]
        logger.debug("Retrieved %d database paths", len(paths))
        return paths
    
    def get_names(self):
        """Get a list of all database names."""
        if not self.db_info or 'databases' not in self.db_info:
            logger.warning("Cannot get database names: db_info is None or 'databases' not in db_info")
            return []
        
        names = [db.get('name', '') for db in self.db_info.get('databases', [])]
        logger.debug("Retrieved %d database names", len(names))
        return names

# Cache for tools information
class ToolsCache:
    def __init__(self):
        self.tools_info = None  # Will store the full response from list_tools_tool
        self.last_updated = None
        self.cache_duration = 3600  # Cache duration in seconds (1 hour)
        self.cache_file = os.path.join(CACHE_DIR, "tools_cache.json")
        logger.debug("ToolsCache initialized with cache duration: %d seconds", self.cache_duration)
    
    def is_valid(self):
        """Check if the cache is still valid."""
        if not self.tools_info or not self.last_updated:
            logger.debug("Tools cache invalid: tools_info or last_updated is None")
            return False
        
        current_time = time.time()
        time_diff = current_time - self.last_updated
        is_valid = time_diff < self.cache_duration
        
        if is_valid:
            logger.debug("Tools cache valid: %d seconds remaining", self.cache_duration - time_diff)
        else:
            logger.debug("Tools cache expired: %d seconds past expiration", time_diff - self.cache_duration)
            
        return is_valid
    
    def update(self, tools_info):
        """Update the cache with new tools information."""
        logger.debug("Updating tools info cache")
        
        if isinstance(tools_info, dict) and 'tools' in tools_info:
            # Log tool names at debug level
            if logger.isEnabledFor(10):  # DEBUG level
                tool_names = [tool.get('name', 'unnamed') for tool in tools_info.get('tools', [])]
                logger.debug("Tool names: %s", tool_names)
        else:
            logger.warning("Updating tools cache with invalid tools_info format: %s", type(tools_info))
            
        self.tools_info = tools_info
        self.last_updated = time.time()
        logger.debug("Tools cache updated at: %s", time.ctime(self.last_updated))
    
    def clear(self):
        """Clear the cache."""
        logger.info("Clearing tools info cache")
        self.tools_info = None
        self.last_updated = None
        
    def save_to_disk(self):
        """Save the tools cache to disk for testing/reference purposes."""
        if not self.tools_info:
            logger.warning("Cannot save empty tools cache to disk")
            return False
            
        try:
            cache_data = {
                "tools_info": self.tools_info,
                "last_updated": self.last_updated
            }
            
            with open(self.cache_file, 'w') as f:
                json.dump(cache_data, f, indent=2)
                
            logger.info(f"Tools cache saved to {self.cache_file}")
            return True
        except Exception as e:
            logger.error(f"Failed to save tools cache to disk: {str(e)}")
            return False
            
    def load_from_disk(self):
        """Load the tools cache from disk."""
        if not os.path.exists(self.cache_file):
            logger.warning(f"Cache file {self.cache_file} does not exist")
            return False
            
        try:
            with open(self.cache_file, 'r') as f:
                cache_data = json.load(f)
                
            self.tools_info = cache_data.get("tools_info")
            self.last_updated = cache_data.get("last_updated")
            
            logger.info(f"Tools cache loaded from {self.cache_file}")
            return True
        except Exception as e:
            logger.error(f"Failed to load tools cache from disk: {str(e)}")
            return False
    
    def get_tool_names(self):
        """Get a list of all tool names."""
        if not self.tools_info or 'tools' not in self.tools_info:
            logger.warning("Cannot get tool names: tools_info is None or 'tools' not in tools_info")
            return []
        
        names = [tool.get('name', '') for tool in self.tools_info.get('tools', [])]
        logger.debug("Retrieved %d tool names", len(names))
        return names
    
    def get_tool_info(self, tool_name):
        """Get information about a specific tool."""
        if not self.tools_info or 'tools' not in self.tools_info:
            logger.warning("Cannot get tool info: tools_info is None or 'tools' not in tools_info")
            return None
        
        for tool in self.tools_info.get('tools', []):
            if tool.get('name') == tool_name:
                return tool
        
        logger.warning("Tool %s not found in tools cache", tool_name)
        return None

# Initialize the caches
db_info_cache = DBInfoCache()
tools_cache = ToolsCache()

def save_all_caches():
    """Save all caches to disk."""
    db_result = db_info_cache.save_to_disk()
    tools_result = tools_cache.save_to_disk()
    return db_result and tools_result
    
def load_all_caches():
    """Load all caches from disk."""
    db_result = db_info_cache.load_from_disk()
    tools_result = tools_cache.load_from_disk()
    return db_result and tools_result