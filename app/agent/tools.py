import os
import logging

log = logging.getLogger(__name__)

def _format_size(size_bytes: int) -> str:
    """Format a byte count into a human-readable string."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"

def list_dir(directory: str) -> str:
    """Returns the contents of a directory with type indicators and sizes."""
    if not os.path.exists(directory):
        return f"Error: Directory '{directory}' does not exist."
    if not os.path.isdir(directory):
        return f"Error: '{directory}' is not a directory."
    
    try:
        items = os.listdir(directory)
        if not items:
            return "Directory is empty."
        
        results = []
        for item in sorted(items):
            full_path = os.path.join(directory, item)
            if os.path.isdir(full_path):
                # Count children for directories
                try:
                    child_count = len(os.listdir(full_path))
                except PermissionError:
                    child_count = "?"
                results.append(f"[DIR]  {item}/  ({child_count} items)")
            else:
                try:
                    size = _format_size(os.path.getsize(full_path))
                except OSError:
                    size = "?"
                results.append(f"[FILE] {item}  ({size})")
        return "\n".join(results)
    except Exception as e:
        return f"Error reading directory: {e}"


def tree_dir(directory: str, max_depth: int = 3) -> str:
    """Returns a recursive tree view of a directory up to max_depth levels deep."""
    if not os.path.exists(directory):
        return f"Error: Directory '{directory}' does not exist."
    if not os.path.isdir(directory):
        return f"Error: '{directory}' is not a directory."
    
    lines = [f"{os.path.basename(directory)}/"]
    _tree_recursive(directory, "", lines, current_depth=0, max_depth=max_depth)
    
    # Cap output at 4000 chars to protect context
    result = "\n".join(lines)
    if len(result) > 4000:
        result = result[:4000] + "\n... [TRUNCATED — tree too large]"
    return result

def _tree_recursive(dir_path: str, prefix: str, lines: list, current_depth: int, max_depth: int):
    """Recursive helper for tree_dir."""
    if current_depth >= max_depth:
        return
    
    try:
        entries = sorted(os.listdir(dir_path))
    except PermissionError:
        lines.append(f"{prefix}[Permission Denied]")
        return
    
    # Separate dirs and files
    dirs = [e for e in entries if os.path.isdir(os.path.join(dir_path, e))]
    files = [e for e in entries if os.path.isfile(os.path.join(dir_path, e))]
    
    all_items = [(d, True) for d in dirs] + [(f, False) for f in files]
    
    for i, (name, is_dir) in enumerate(all_items):
        is_last = (i == len(all_items) - 1)
        connector = "└── " if is_last else "├── "
        full_path = os.path.join(dir_path, name)
        
        if is_dir:
            try:
                child_count = len(os.listdir(full_path))
            except PermissionError:
                child_count = "?"
            lines.append(f"{prefix}{connector}{name}/  ({child_count} items)")
            extension = "    " if is_last else "│   "
            _tree_recursive(full_path, prefix + extension, lines, current_depth + 1, max_depth)
        else:
            try:
                size = _format_size(os.path.getsize(full_path))
            except OSError:
                size = "?"
            lines.append(f"{prefix}{connector}{name}  ({size})")


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
            MAX_CHARS = 6000
            if len(content) > MAX_CHARS:
                return content[:MAX_CHARS] + f"\n\n[TRUNCATED: File exceeded {MAX_CHARS} characters.]"
            return content
    except UnicodeDecodeError:
        # For binary files, return useful metadata instead of an error
        size = _format_size(os.path.getsize(file_path))
        ext = os.path.splitext(file_path)[1]
        return f"[Binary file: {os.path.basename(file_path)}, Size: {size}, Type: {ext}]"
    except Exception as e:
        return f"Error reading file: {e}"

def write_file(file_path: str, content: str) -> str:
    """Writes content to a file (creates or overwrites)."""
    try:
        # Create directories if they don't exist
        os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Successfully wrote {len(content)} characters to {file_path}"
    except Exception as e:
        return f"Error writing to file: {e}"

# Tool registry for the agent
AVAILABLE_TOOLS = {
    "list_dir": list_dir,
    "tree_dir": tree_dir,
    "read_file": read_file,
    "write_file": write_file,
}

TOOLS_DESCRIPTION = """
Available Tools:

1. list_dir(directory: str) -> str
   Lists files and folders inside a directory, showing [DIR] or [FILE] with sizes.
   Example: Action: list_dir
            Action Input: {"directory": "C:\\\\Users\\\\adria\\\\Desktop\\\\gaming"}

2. tree_dir(directory: str, max_depth: int) -> str
   Shows a full recursive tree view of a directory (like the 'tree' command). 
   Use this FIRST when exploring a new folder — it gives you the complete picture in one call.
   max_depth defaults to 3. Set it lower for huge directories.
   Example: Action: tree_dir
            Action Input: {"directory": "C:\\\\Users\\\\adria\\\\Desktop\\\\project", "max_depth": 2}

3. read_file(file_path: str) -> str
   Reads the full text content of a file. Binary files return metadata instead.
   Example: Action: read_file
            Action Input: {"file_path": "C:\\\\Users\\\\adria\\\\Desktop\\\\project\\\\README.md"}

4. write_file(file_path: str, content: str) -> str
   Creates or overwrites a file with the given content.
   Example: Action: write_file
            Action Input: {"file_path": "C:\\\\Users\\\\adria\\\\Desktop\\\\docs.md", "content": "# My Documentation\\n\\nDetailed content here..."}
"""
