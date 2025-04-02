# FMquery-Agent

A sophisticated FileMaker database query agent built with the OpenAI Agents SDK. This tool allows users to query FileMaker databases using natural language, with intelligent caching and orchestration to improve performance and user experience.

## Project Overview

FMquery-Agent connects to FileMaker databases through a Model Context Protocol (MCP) server, allowing users to:

- Discover available databases
- Query database schemas and table structures
- Retrieve script information
- Analyze relationships between tables
- Ask natural language questions about database content and structure

The agent maintains conversation context across multiple queries and uses a sophisticated caching and orchestration system to improve performance.

## Project Structure

- `agent_mcp.py`: Main entry point for the agent
- `cache.py`: Basic database and tools information caching
- `database.py`: Functions to retrieve database information
- `tools.py`: Functions to retrieve tools information
- `logging_utils.py`: Logging utilities
- `models.py`: Data models for tool arguments
- `validation.py` & `validation_decorator.py`: Parameter validation for tool calls
- `orchestration/`: Advanced orchestration system
  - `cache_hierarchy.py`: Hierarchical caching system
  - `dependency_manager.py`: Tool dependency management
  - `orchestrator.py`: Main orchestration engine
  - `integration.py`: Integration with MCP server

## Cache Structure

The project implements a hierarchical caching system to efficiently store and retrieve database information:

### Cache Hierarchy

1. **Database-level cache** (`DBInfoCache` in `cache.py`)
   - Stores basic database information (paths, names)
   - Cache key: Simple in-memory object

2. **Tools-level cache** (`ToolsCache` in `cache.py`)
   - Stores information about available tools from the MCP server
   - Cache key: Simple in-memory object

3. **Schema-level cache** (`SchemaCache` in `orchestration/cache_hierarchy.py`)
   - Stores schema information for each database
   - Cache key format: `db:{db_name}:schema:{schema_name}`

4. **Table-level cache** (`TableCache` in `orchestration/cache_hierarchy.py`)
   - Stores table information for each schema
   - Cache key format: `db:{db_name}:schema:{schema_name}:table:{table_name}`

5. **Script-level cache** (`ScriptCache` in `orchestration/cache_hierarchy.py`)
   - Stores script information
   - Cache key format: `script:{script_id}`

Each cache level has methods to check validity, update, clear, and retrieve data. The cache duration is configurable (default: 1 hour).

## Orchestration System

The orchestration system manages tool dependencies and ensures tools are executed in the correct order:

### Dependency Graph

Tool dependencies are defined as follows:
- `discover_databases`: No dependencies (foundational tool)
- `list_tools`: No dependencies (foundational tool)
- `get_schema_information`: Requires output from `discover_databases`
- `get_table_information`: Requires output from `discover_databases` and `get_schema_information`
- `get_script_information`: Requires output from `discover_databases`
- `get_script_details`: Requires output from `get_script_information`
- `get_custom_functions`: Requires output from `discover_databases`

### Orchestration Flow

1. System initializes by caching database and tools information
2. User submits a natural language query
3. Agent determines which tools to call
4. Orchestration layer checks if dependencies are satisfied in the cache
5. If dependencies are missing, they are automatically executed first
6. Results are cached at the appropriate level
7. Final tool is executed with validated parameters
8. Results are returned to the user

## Setup

1. Install the required dependencies:

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

2. Create a `.env` file with your OpenAI API key:

```env
OPENAI_API_KEY=your_api_key_here
MODEL_CHOICE=gpt-4o-mini  # or another model of your choice
```

3. Configure the FileMaker DDR path in `agent_mcp.py`:

```python
# Path to FileMaker DDR
ddrPath = "/path/to/your/FileMaker/DDR/HTML"

# Customer name
customerName = "YourCustomerName"
```

## Running the Agent

### Interactive Mode (Default)

```bash
python agent_mcp.py
```

This starts an interactive session where you can ask multiple questions with conversation context maintained between queries.

### Single Query Mode

```bash
python agent_mcp.py --prompt "what scripts might be related to printing in Miro_Printing"
```

This runs a single query and exits.

### Demo Mode

```bash
python agent_mcp.py --demo
```

This runs a series of predefined queries to demonstrate the capabilities of the agent.

### Specifying a Different Model

```bash
python agent_mcp.py --model gpt-4o
```

This allows you to specify a different OpenAI model to use for the agent.

### Specifying a Different Prompt Template

```bash
python agent_mcp.py --prompt-template enhanced
```

This allows you to select a different prompt template for the agent. Available templates:
- `base` (default): Basic FileMaker assistant prompt
- `enhanced`: More detailed prompt with advanced analysis techniques

## Benefits

- **Natural language interface**: Query FileMaker databases using plain English
- **Intelligent caching**: Improves performance by caching database information
- **Automatic dependency resolution**: Tools are executed in the correct order
- **Conversation context**: Maintains context across multiple queries
- **Parameter validation**: Ensures tool calls have valid parameters