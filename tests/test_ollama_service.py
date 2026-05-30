import pytest
from unittest.mock import patch, MagicMock
from app import ollama_service


def test_ollama_base_url():
    """Ensure the base URL uses 127.0.0.1 to avoid Windows IPv6 DNS timeouts."""
    assert ollama_service.OLLAMA_BASE_URL == "http://127.0.0.1:11434"


@patch("app.ollama_service.httpx.get")
def test_is_ollama_running(mock_get):
    """Test fast fail timeout logic for is_ollama_running."""
    import httpx
    
    # Mock success
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_get.return_value = mock_response
    
    assert ollama_service.is_ollama_running() is True
    
    # Mock timeout
    mock_get.side_effect = httpx.TimeoutException("Timeout")
    assert ollama_service.is_ollama_running() is False


@patch("app.ollama_service.get_ollama_models")
@patch("app.ollama_service.ensure_ollama_running")
def test_auto_select_fast_path(mock_ensure, mock_get_models):
    """Test that the fast path bypasses hardware detection when models are available."""
    mock_ensure.return_value = True
    
    # Test preferred model selection
    mock_get_models.return_value = ["random_model:1b", "gemma3:4b"]
    
    # Should instantly select gemma3:4b from preferred list
    selected = ollama_service.auto_select_and_ensure_model()
    assert selected == "gemma3:4b"
    
    # Test fallback to first available if no preferred
    mock_get_models.return_value = ["unknown_model:7b", "another_model:2b"]
    selected = ollama_service.auto_select_and_ensure_model()
    assert selected == "unknown_model:7b"
