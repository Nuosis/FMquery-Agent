# Prompt Testing Environment

A Streamlit-based testing environment for evaluating prompt responses and tool call parameters without executing the tools.

## Features

- Select from available prompts in the system
- Test questions against selected prompts
- View raw tool call details when a tool would be called
- Analyze expected parameters for specific tools

## Usage

### Running the Application

```bash
# Navigate to the project root directory
cd /path/to/FMquery-Agent

# Standard version (with more dependencies)
./prompts/test/run_test_app.py
# or
streamlit run prompts/test/streamlit_test_app.py

# Simplified version (minimal dependencies)
./prompts/test/run_simple_test_app.py
# or
streamlit run prompts/test/simple_test_app.py
```

### Testing Workflow

1. **Select a Prompt (Required)**
   - Choose from the available prompts in the dropdown menu
   - The prompt selection is mandatory before proceeding

2. **Enter a Question**
   - Type your test question in the text area
   - Questions can be designed to elicit normal responses or tool calls

3. **Generate Response**
   - Click the "Generate Response" button
   - The system will process your question using the selected prompt

4. **View Results**
   - For regular responses: The text will be displayed directly
   - For tool calls: The tool name and parameters will be displayed in a formatted view
   - You can copy the tool call JSON for further analysis

### Parameter Analysis

To check what parameters would be expected for a specific tool:
1. Enter the tool name in the "Enter a tool name to see expected parameters" field
2. The system will display the expected parameters for that tool

## Files

- `streamlit_test_app.py` - Main Streamlit application
- `simple_test_app.py` - Simplified version with minimal dependencies
- `test_utils.py` - Helper functions for the main application
- `run_test_app.py` - Convenience script to launch the main application
- `run_simple_test_app.py` - Convenience script to launch the simplified application
- `README.md` - This documentation file

## Troubleshooting

If you encounter import errors with the standard version, try using the simplified version instead. The simplified version has all functionality in a single file with minimal dependencies on the main project.

## Implementation Details

The testing environment works by:
1. Loading prompts from the main prompts.py module
2. Using the OpenAI API with tool definitions but preventing execution
3. Parsing and formatting the responses to show tool calls when they would occur
4. Enforcing a strict workflow where prompt selection is required

## Notes

- This environment is for testing purposes only and does not execute any tools
- All responses are generated using the OpenAI API
- The tool parameter information is based on the tool specifications in the system