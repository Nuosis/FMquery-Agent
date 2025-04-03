# API Reference for FMquery-Agent MCP Server

This document describes the API endpoints for the FMquery-Agent MCP server.

## Tools

### Database Discovery Tool (`discover_databases`)

This tool analyzes the directory structure and identifies the available databases by looking for subdirectories with '_ddr' suffix. It returns:

- A list of available databases with basic information
- The base directory where the DDR files are located
- Available cache keys for each database

The tool automatically runs the caching mechanism if:

- The cache doesn't exist
- The DDR files have been modified since the cache was created

Example response:

```json
{
  "base_directory": "/path/to/ddr/files",
  "databases": [
    {
      "name": "Database1",
      "path": "/path/to/ddr/files/Database1_ddr",
      "cache_keys": ["tables", "relationships", "scripts"]
    },
    {
      "name": "Database2",
      "path": "/path/to/ddr/files/Database2_ddr",
      "cache_keys": ["tables", "relationships", "scripts"]
    }
  ]
}
```

### Schema Information Tool (`get_schema_information`)

This tool extracts schema information for specified databases, including:

- Database name
- Data sources
- Tables and their details
- Relationships

It accepts a list of database paths and returns detailed schema information for each database.

Example response:

```json
{
  "databases": [
    {
      "name": "Database1",
      "tables": [
        {
          "name": "Table1",
          "field_count": 10,
          "record_count": 100,
          "occurrences": "2"
        }
      ],
      "relationships": [
        {
          "name": "Table1=Table2",
          "join": [
            [
              {
                "table_occurrence": "Table1",
                "field": "ID",
                "type": "="
              },
              {
                "table_occurrence": "Table2",
                "field": "Table1_ID"
              }
            ]
          ]
        }
      ]
    }
  ]
}
```

### Table Information Tool (`get_table_information`)

This tool extracts detailed information about a specific table, including:

- Table name
- Fields and their details (name, type, options)
- Relationships involving this table

It accepts a table name and returns detailed information about the table.

Example response:

```json
{
  "table": {
    "name": "Table1",
    "fields": [
      {
        "name": "ID",
        "type": "Number",
        "options": "Auto-Enter, Not Empty"
      },
      {
        "name": "Name",
        "type": "Text",
        "options": "Not Empty"
      }
    ],
    "relationships": [
      {
        "name": "Table1=Table2",
        "join": [
          [
            {
              "table_occurrence": "Table1",
              "field": "ID",
              "type": "="
            },
            {
              "table_occurrence": "Table2",
              "field": "Table1_ID"
            }
          ]
        ]
      }
    ]
  }
}
```

### Script Information Tool (`get_script_information`)

This tool extracts script information for specified databases, including:

- Scripts and their details
- Script steps
- Custom functions

It accepts a list of database paths and returns detailed script information for each database.

Example response:

```json
{
  "databases": [
    {
      "name": "Database1",
      "scripts": [
        {
          "name": "Script1",
          "info": "Performs action X"
        },
        {
          "name": "Script2",
          "info": "Performs action Y"
        }
      ],
      "custom_functions": [
        {
          "name": "CustomFunction1",
          "parameters": ["param1", "param2"],
          "calculation": "param1 + param2"
        }
      ]
    }
  ]
}
```

### Script Details Tool (`get_script_details`)

This tool extracts detailed information about a specific script, including:

- Script name
- Script steps
- Referenced layouts, fields, scripts, tables, and custom functions

It accepts a script name and returns detailed information about the script.

Example response:

```json
{
  "script": {
    "name": "Script1",
    "steps": [
      {
        "number": "1",
        "text": "Go to Layout [\"Layout1\"]"
      },
      {
        "number": "2",
        "text": "Set Field [Table1::Field1; \"Value\"]"
      }
    ],
    "layouts_used_in_this_script": ["Layout1"],
    "fields_used_in_this_script": ["Table1::Field1"],
    "scripts_used_in_this_script": [],
    "tables_used_in_this_script": ["Table1"]
    }
}
```

### Custom Functions Tool (`get_custom_functions`)

This tool extracts custom functions from a specified database, including:

- Function name
- Parameters
- Calculation formula

It accepts a database path and returns detailed information about the custom functions.

Example response:

```json
{
  "custom_functions": [
    {
      "name": "CustomFunction1",
      "parameters": ["param1", "param2"],
      "calculation": "param1 + param2"
    },
    {
      "name": "CustomFunction2",
      "parameters": ["text"],
      "calculation": "Upper(text)"
    }
  ]
}
### List Tools Tool (`list_tools`)

This tool lists the available tools provided by the MCP server.

Example response:

```json
{
  "tools": [
    "discover_databases",
    "get_schema_information",
    "get_table_information",
    "get_script_information",
    "get_script_details",
    "get_custom_functions"
  ]
}
```