# FMquery-Agent Deployment

This document describes the deployment process for FMquery-Agent.

## Environment Setup

-   **Operating System**: macOS, Linux, or Windows
-   **Python**: 3.8 or higher
-   **FileMaker DDR HTML files**: Located in a directory accessible to the MCP server.
-   **MCP Server**: The `mcp-filemaker-inspector` server must be running and accessible.

## Dependencies

-   Python packages listed in `requirements.txt`. Install using:

    ```bash
    pip install -r requirements.txt
    ```

-   The `mcp-server-fastmcp` package is required for the MCP server.

## Deployment Steps

1.  **Clone the repository**:

    ```bash
    git clone <repository-url>
    cd FMquery-Agent
    ```

2.  **Create a virtual environment**:

    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3.  **Install dependencies**:

    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure the `.env` file**:

    ```env
    OPENAI_API_KEY=your_api_key_here
    MODEL_CHOICE=gpt-4o-mini  # or another model of your choice
    ```

5.  **Configure the FileMaker DDR path in `agent_mcp.py`**:

    ```python
    # Path to FileMaker DDR
    ddrPath = "/path/to/your/FileMaker/DDR/HTML"

    # Customer name
    customerName = "YourCustomerName"
    ```

6.  **Deploy the MCP server**:

    -   Follow the instructions in the `mcp-filemaker-inspector/README.md` file to deploy the MCP server.
    -   Ensure the MCP server is running and accessible.

7.  **Run the agent**:

    ```bash
    python agent_mcp.py
    ```

## CI/CD Workflows

-   This project does not currently have a CI/CD workflow.
-   To set up a CI/CD workflow, you can use tools like GitHub Actions, GitLab CI, or Jenkins.
-   The workflow should:
    -   Run unit tests.
    -   Lint the code.
    -   Deploy the agent to a staging environment.
    -   Run integration tests.
    -   Deploy the agent to a production environment.

## Notes

-   Ensure the MCP server is properly configured and accessible before running the agent.
-   Monitor the agent logs for any errors or issues.
-   Consider using a process manager like `systemd` or `supervisor` to ensure the agent is always running.