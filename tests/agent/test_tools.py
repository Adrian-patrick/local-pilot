import os
import tempfile
import pytest
from app.agent.tools import tree_dir, read_file, write_file, list_dir

@pytest.fixture
def temp_workspace():
    """Create a temporary directory structure for testing tools."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create some files
        with open(os.path.join(temp_dir, "test1.txt"), "w") as f:
            f.write("Hello World\nLine 2")
            
        # Create a subdirectory with a file
        sub_dir = os.path.join(temp_dir, "subdir")
        os.mkdir(sub_dir)
        with open(os.path.join(sub_dir, "test2.txt"), "w") as f:
            f.write("Subdir content")
            
        yield temp_dir


def test_tree_dir(temp_workspace):
    # Test depth 1
    result_d1 = tree_dir(directory=temp_workspace, max_depth=1)
    assert "test1.txt" in result_d1
    assert "subdir" in result_d1
    assert "test2.txt" not in result_d1  # Exceeds depth 1

    # Test depth 2
    result_d2 = tree_dir(directory=temp_workspace, max_depth=2)
    assert "test2.txt" in result_d2


def test_read_file(temp_workspace):
    file_path = os.path.join(temp_workspace, "test1.txt")
    
    # Read entire file
    content = read_file(file_path=file_path)
    assert "Hello World\nLine 2" in content
    
    # Read non-existent file
    error_content = read_file(file_path=os.path.join(temp_workspace, "missing.txt"))
    assert "does not exist" in error_content


def test_write_file(temp_workspace):
    new_file = os.path.join(temp_workspace, "new.md")
    
    # Write new file
    result = write_file(file_path=new_file, content="# Heading\nTest")
    assert "Successfully wrote" in result
    
    # Verify content
    with open(new_file, "r") as f:
        assert f.read() == "# Heading\nTest"
        
    # Overwrite existing file
    result_overwrite = write_file(file_path=new_file, content="Overwritten")
    assert "Successfully wrote" in result_overwrite
    
    with open(new_file, "r") as f:
        assert f.read() == "Overwritten"
