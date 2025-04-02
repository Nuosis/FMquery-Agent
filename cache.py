import time
import json
from typing import List, Dict, Any
from logging_utils import logger

# Cache for database information
class DBInfoCache:
    def __init__(self):
        self.db_info = None  # Will store the full response from discover_databases
        self.last_updated = None
        self.cache_duration = 3600  # Cache duration in seconds (1 hour)
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
            db_count = len(db_info.get('databases', []))
            logger.info("Updating cache with %d databases", db_count)
            
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

# Initialize the cache
db_info_cache = DBInfoCache()