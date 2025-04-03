# FMquery-Agent Architecture

## Overview

FMquery-Agent is designed to provide a natural language interface for querying FileMaker databases. It leverages the OpenAI Agents SDK for natural language processing and a Model Context Protocol (MCP) server for interacting with FileMaker databases. The agent uses a sophisticated caching and orchestration system to improve performance and user experience.

## Key Components

- **Agent (agent_mcp.py)**: The main entry point for the agent. It initializes the MCP server, sets up the agent with the appropriate prompt and model, and handles user queries.
- **MCP Server (OrchestrationMCPServerStdio)**: An MCP server that provides access to FileMaker database information. It is automatically deployed in agent_mcp.py.
    - **Database (database.py)**: Functions to retrieve database information from the MCP server.
    - **Tools (tools.py)**: Functions to retrieve tools information from the MCP server.
- **Cache (cache/)**: A hierarchical caching system that stores database and tools information to improve performance.
    - **DBInfoCache**: Stores basic database information (paths, names).
    - **ToolsCache**: Stores information about available tools from the MCP server.
    - **SchemaCache**: Stores schema information for each database.
    - **TableCache**: Stores table information for each schema.
    - **ScriptCache**: Stores script information.
- **Orchestration System (orchestration/)**: Manages tool dependencies and ensures tools are executed in the correct order.
    - **DependencyManager**: Defines tool dependencies.
    - **Orchestrator**: Executes tools based on the dependency graph.
- **Validation** 
    - **Models (models.py)**: Data models for tool arguments.
    - **Validation (validation.py & validation_decorator.py)**: Parameter validation for tool calls.
- **Prompts (prompts/)**: Contains prompt templates for the agent.

## High-Level Interactions

1.  **Initialization**:
    -   The agent initializes the MCP server.
    -   The agent loads database and tools information from the cache (if available) or fetches it from the MCP server.
    -   The agent sets up the prompt and model.
2.  **Query Processing**:
    -   The user submits a natural language query.
    -   The agent determines which tools to call based on the query.
    -   The orchestration layer checks if dependencies are satisfied in the cache.
    -   If dependencies are missing, they are automatically executed first.
    -   Results are cached at the appropriate level.
    -   The final tool is executed with validated parameters.
    -   Results are returned to the user.

## Data Flow

1.  The user submits a query to the agent.
2.  The agent uses the orchestration system to determine the necessary tools and their dependencies.
3.  The orchestration system checks the cache for the required information.
4.  If the information is not in the cache, the orchestration system calls the appropriate tools via the MCP server.
5.  The MCP server retrieves the information from the FileMaker DDR.
6.  The information is cached at the appropriate level.
7.  The agent uses the cached information and the results from the tools to generate a response to the user.

## Diagram

```mermaid
graph LR
    User[User] --> Agent(Agent)
    Agent --> Orchestration(Orchestration System)
    Orchestration --> Cache(Cache)
    Orchestration --> MCPServer(MCP Server)
    MCPServer --> FileMaker(FileMaker DDR)
    Cache --> FileMaker
    Agent --> User