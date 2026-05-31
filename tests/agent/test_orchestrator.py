import os
import pytest
from app.agent.orchestrator import AgentOrchestrator


def test_initialization():
    # Test Groq model detection
    orch_groq = AgentOrchestrator(model="groq:llama3", base_dir="C:\\test")
    assert orch_groq.is_groq is True
    assert orch_groq.model == "llama3"

    # Test local model detection
    orch_local = AgentOrchestrator(model="gemma3:4b", base_dir="C:\\test")
    assert orch_local.is_groq is False
    assert orch_local.model == "gemma3:4b"

    # Test initial messages structure
    assert len(orch_local.messages) == 1
    assert orch_local.messages[0]["role"] == "system"


def test_resolve_path():
    orch = AgentOrchestrator(model="test", base_dir="C:\\base\\dir")
    
    # Absolute paths should remain unchanged
    abs_path = "C:\\another\\dir\\file.txt"
    assert orch._resolve_path(abs_path) == abs_path

    # Relative paths should be joined with base_dir
    rel_path = "subdir\\file.txt"
    expected = os.path.normpath("C:\\base\\dir\\subdir\\file.txt")
    assert orch._resolve_path(rel_path) == expected


def test_truncate_messages():
    orch = AgentOrchestrator(model="test", base_dir="C:\\test")
    
    # Create a large dummy message history
    orch.messages.append({"role": "user", "content": "A" * 10000})
    orch.messages.append({"role": "assistant", "content": "B" * 10000})
    orch.messages.append({"role": "user", "content": "C" * 1000})
    
    # Add 6 more tiny messages
    for i in range(6):
        orch.messages.append({"role": "assistant", "content": f"msg{i}"})
        
    assert len(orch.messages) == 10
    
    orch._truncate_messages()
    
    # Should keep system prompt (idx 0) + last 6 messages
    assert len(orch.messages) == 7
    assert orch.messages[0]["role"] == "system"
    assert orch.messages[1]["content"] == "msg0"
    assert orch.messages[-1]["content"] == "msg5"


def test_multiline_json_parsing(mocker):
    """Test the robust JSON parsing logic we added for multiline Action Inputs."""
    orch = AgentOrchestrator(model="test", base_dir="C:\\test")
    
    # Mock the LLM to return a complex multiline response with trailing garbage
    mock_response = '''Thought: Let me write a file.
Action: write_file
Action Input: {
  "file_path": "C:\\\\test\\\\file.txt",
  "content": "Line 1\\nLine 2"
} }`
PAUSE'''

    # Mock the stream and the tool call
    final_response = "Thought: I am done.\nFinal Answer: Done."
    mocker.patch("app.ollama_service.ask_ollama_stream_messages", side_effect=[[mock_response], [final_response]])
    mock_tool = mocker.patch.dict("app.agent.orchestrator.AVAILABLE_TOOLS", {"write_file": mocker.MagicMock(return_value="Success")})
    
    # Run the loop (it will yield the tokens and the tool execution log)
    list(orch.run("task"))
    
    # Verify the tool was called with the correctly parsed multiline args
    mock_tool["write_file"].assert_called_once_with(file_path="C:\\test\\file.txt", content="Line 1\nLine 2")


def test_interception_logic(mocker):
    """Test that the agent intercepts premature Final Answer if file creation was requested."""
    orch = AgentOrchestrator(model="test", base_dir="C:\\test")
    
    # Task explicitly asks to write a file
    task = "create a summary file"
    
    # First response: agent tries to cheat and skip tools
    cheat_response = "Thought: I'll just output text.\nFinal Answer: Here is the summary."
    # Second response: agent complies and uses the tool
    comply_response = "Thought: Oops.\nAction: write_file\nAction Input: {\"file_path\": \"test.txt\", \"content\": \"a\"}\nPAUSE"
    # Third response: agent finishes
    final_response = "Thought: Done.\nFinal Answer: File created."
    
    mocker.patch("app.ollama_service.ask_ollama_stream_messages", side_effect=[[cheat_response], [comply_response], [final_response]])
    mock_tool = mocker.patch.dict("app.agent.orchestrator.AVAILABLE_TOOLS", {"write_file": mocker.MagicMock(return_value="Success")})
    
    # Run the loop and collect output
    outputs = list(orch.run(task))
    output_str = "".join(outputs)
    
    # Verify interception message was yielded
    assert "System Interception" in output_str
    assert "You MUST use the `write_file` tool" in output_str
    
    # Verify the tool was eventually called
    mock_tool["write_file"].assert_called_once()
    
    # Verify that the system message was injected into the history
    assert orch.messages[2]["content"] == cheat_response
    assert "System Error" in orch.messages[3]["content"]
