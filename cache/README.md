# Cache Persistence for Testing

This directory contains cache files that are used for testing and reference purposes. The cache files are JSON files that store the state of the in-memory caches used by the application.

## Cache Files

- `db_info_cache.json`: Contains cached database information
- `tools_cache.json`: Contains cached tools information

## Command-Line Options

The following command-line options have been added to `agent_mcp.py` to control cache persistence:

- `--load-cache`: Load cache from disk at startup
- `--save-cache`: Save cache to disk when updated
- `--save-on-exit`: Save cache to disk when exiting

## Usage Examples

### Load cache from disk at startup

```bash
python agent_mcp.py --load-cache
```

This will load the cache from disk at startup, which can be useful for testing with previously cached data.

### Save cache to disk when updated

```bash
python agent_mcp.py --save-cache
```

This will save the cache to disk whenever it's updated, which can be useful for capturing the cache state for later analysis.

### Save cache to disk when exiting

```bash
python agent_mcp.py --save-on-exit
```

This will save the cache to disk when the application exits, which can be useful for preserving the cache state for the next run.

### Combining options

```bash
python agent_mcp.py --load-cache --save-cache --save-on-exit
```

This will load the cache from disk at startup, save it whenever it's updated, and save it again when the application exits.

## Programmatic Usage

You can also use the cache persistence functionality programmatically:

```python
from cache import db_info_cache, tools_cache, save_all_caches, load_all_caches

# Save all caches to disk
save_all_caches()

# Load all caches from disk
load_all_caches()

# Save individual caches
db_info_cache.save_to_disk()
tools_cache.save_to_disk()

# Load individual caches
db_info_cache.load_from_disk()
tools_cache.load_from_disk()
```

## Notes

- The cache files are stored in the `cache` directory
- The cache files are JSON files that can be viewed and edited with any text editor
- The cache files are only meant for testing and reference purposes, not for production use