import time
import json
from typing import List, Dict, Any

# Cache for database information
class DBInfoCache:
    def __init__(self):
        self.db_info = None  # Will store the full response from discover_databases
        self.last_updated = None
        self.cache_duration = 3600  # Cache duration in seconds (1 hour)
    
    def is_valid(self):
        """Check if the cache is still valid."""
        if not self.db_info or not self.last_updated:
            return False
        
        current_time = time.time()
        return (current_time - self.last_updated) < self.cache_duration
    
    def update(self, db_info):
        """Update the cache with new database information."""
        print(f"db_info_cache.update() called with db_info type: {type(db_info)}")
        if isinstance(db_info, dict) and 'databases' in db_info:
            print(f"db_info_cache.update() - db_info contains {len(db_info.get('databases', []))} databases")
        self.db_info = db_info
        self.last_updated = time.time()
    
    def clear(self):
        """Clear the cache."""
        self.db_info = None
        self.last_updated = None
    
    def get_paths(self):
        """Get a list of all database paths."""
        if not self.db_info or 'databases' not in self.db_info:
            print("Warning: db_info_cache.get_paths() - db_info is None or 'databases' not in db_info")
            return []
        
        paths = [db.get('path', '') for db in self.db_info.get('databases', [])]
        print(f"db_info_cache.get_paths() returning {len(paths)} paths: {paths}")
        return paths
    
    def get_names(self):
        """Get a list of all database names."""
        if not self.db_info or 'databases' not in self.db_info:
            return []
        
        return [db.get('name', '') for db in self.db_info.get('databases', [])]

# Initialize the cache
db_info_cache = DBInfoCache()