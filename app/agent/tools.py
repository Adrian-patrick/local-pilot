import os
import glob
import logging

log = logging.getLogger(__name__)

def list_dir(directory: str) -> str:
    """Returns the contents of a directory."""
    if not os.path.exists(directory):
        return f"Error: Directory '{directory}' does not exist."
    if not os.path.isdir(directory):
        return f"Error: '{directory}' is not a directory."
    
    try:
        items = os.listdir(directory)
        if not items:
            return "Directory is empty."
        return "\n".join(sorted(items))
    except Exception as e:
        return f"Error reading directory: {e}"

def read_file(file_path: str) -> str:
    """Reads and returns the contents of a file."""
    if not os.path.exists(file_path):
        return f"Error: File '{file_path}' does not exist."
    if not os.path.isfile(file_path):
        return f"Error: '{file_path}' is not a file."
    
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
            # Protect against massive files crashing the context
            MAX_CHARS = 8000
            if len(content) > MAX_CHARS:
                return content[:MAX_CHARS] + f"\n\n[TRUNCATED: File exceeded {MAX_CHARS} characters. If you need more info, be specific.]"
            return content
    except UnicodeDecodeError:
        return f"Error: File '{file_path}' appears to be a binary file."
    except Exception as e:
        return f"Error reading file: {e}"

def write_file(file_path: str, content: str) -> str:
    """Writes content to a file (creates or overwrites)."""
    try:
        # Create directories if they don't exist
        os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Successfully wrote to {file_path}"
    except Exception as e:
        return f"Error writing to file: {e}"

# Tool registry for the agent
AVAILABLE_TOOLS = {
    "list_dir": list_dir,
    "read_file": read_file,
    "write_file": write_file,
}

TOOLS_DESCRIPTION = """
Available Tools:
1. list_dir(directory: str) -> str
   - Description: Lists the files and folders inside the given directory path.
   - Example Usage: Action: list_dir
                    Action Input: {"directory": "./scripts"}

2. read_file(file_path: str) -> str
   - Description: Reads the contents of a specific file.
   - Example Usage: Action: read_file
                    Action Input: {"file_path": "./main.py"}

3. write_file(file_path: str, content: str) -> str
   - Description: Creates or overwrites a file with the given content.
   - Example Usage: Action: write_file
                    Action Input: {"file_path": "./docs.md", "content": "# Documentation"}
"""
