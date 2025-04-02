# OpenAI Agents

This repository contains examples of using the OpenAI Agents SDK to build intelligent travel planning agents with progressively advanced capabilities.

## Project Structure

## Setup

1. Install the required dependencies:

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

2. Create a `.env` file with your OpenAI API key:

```env
OPENAI_API_KEY=your_api_key_here
MODEL_CHOICE=gpt-4o-mini  # or another model of your choice
```

## Running the Agent
```bash
uv run agent_mcp.py --prompt "what scripts might be related to printing in Miro_Printing"
```