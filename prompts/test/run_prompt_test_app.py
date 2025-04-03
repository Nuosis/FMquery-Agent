#!/usr/bin/env python3
"""
Launcher script for the simplified Streamlit testing environment.

This script provides a simple way to launch the simplified Streamlit app
for testing prompt responses and tool calls.
"""

import os
import sys
import subprocess
from pathlib import Path

def main():
    """Launch the simplified Streamlit app."""
    # Get the directory of this script
    script_dir = Path(__file__).parent.absolute()
    
    # Get the path to the Streamlit app
    app_path = script_dir / "prompt_test_app.py"
    
    # Check if the app exists
    if not app_path.exists():
        print(f"Error: Could not find Streamlit app at {app_path}")
        sys.exit(1)
    
    # Launch the Streamlit app
    print(f"Launching Streamlit app from {app_path}")
    try:
        subprocess.run(["streamlit", "run", str(app_path)], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error launching Streamlit app: {e}")
        sys.exit(1)
    except FileNotFoundError:
        print("Error: Streamlit not found. Please make sure it's installed.")
        print("You can install it with: pip install streamlit")
        sys.exit(1)

if __name__ == "__main__":
    main()