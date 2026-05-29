"""Ollama local LLM HTTP client with auto-setup capabilities.

Replaces the Rust get_ollama_models() and ask_ollama() Tauri commands.
Enhanced with:
  - Auto-detection and model pulling
  - Streaming response support
  - Connection health checks
  - Automatic Ollama server startup
"""

from __future__ import annotations

import json
import logging
import subprocess
import time
from typing import Generator

import httpx

from app.system_detector import detect_system

log = logging.getLogger(__name__)

OLLAMA_BASE_URL = "http://localhost:11434"
CONNECT_TIMEOUT = 3.0  # seconds — fast fail for status checks
GENERATE_TIMEOUT = 300.0  # seconds — generous for local LLM inference
PULL_TIMEOUT = 600.0  # seconds — model downloads can take a while


# ── Connection Management ─────────────────────────────────────────────────

def is_ollama_running() -> bool:
    """Check if the Ollama server is reachable."""
    try:
        response = httpx.get(f"{OLLAMA_BASE_URL}/", timeout=CONNECT_TIMEOUT)
        return response.status_code == 200
    except (httpx.ConnectError, httpx.TimeoutException):
        return False


def ensure_ollama_running() -> bool:
    """Start the Ollama server if it's not running. Returns True if reachable."""
    if is_ollama_running():
        return True

    log.info("Ollama not running, attempting to start...")
    try:
        subprocess.Popen(
            ["ollama", "serve"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        # Wait for it to come up
        for _ in range(15):
            time.sleep(1)
            if is_ollama_running():
                log.info("Ollama server started successfully.")
                return True
        log.warning("Ollama server did not start within 15 seconds.")
    except FileNotFoundError:
        log.error("Ollama binary not found. Please install Ollama first.")
    except OSError as exc:
        log.error("Failed to start Ollama: %s", exc)

    return False


# ── Model Management ──────────────────────────────────────────────────────

def get_ollama_models() -> list[str]:
    """Fetch sorted list of model names from the local Ollama server.

    Raises:
        ConnectionError: If Ollama is not running or unreachable.
        RuntimeError: If the response is malformed.
    """
    try:
        response = httpx.get(
            f"{OLLAMA_BASE_URL}/api/tags",
            timeout=CONNECT_TIMEOUT,
        )
    except (httpx.ConnectError, httpx.TimeoutException) as exc:
        raise ConnectionError(
            f"Ollama server is not running on {OLLAMA_BASE_URL}. (Error: {exc})"
        ) from exc

    if response.status_code != 200:
        raise RuntimeError(f"Ollama server returned error: {response.status_code}")

    try:
        data = response.json()
        models = [m["name"] for m in data.get("models", [])]
        models.sort()
        return models
    except (KeyError, TypeError, ValueError) as exc:
        raise RuntimeError(f"Failed to parse Ollama models response: {exc}") from exc


def is_model_available(model_name: str) -> bool:
    """Check if a specific model is already downloaded."""
    try:
        models = get_ollama_models()
        # Ollama model names can be "qwen2.5:7b" or "qwen2.5:7b-instruct-q4_K_M"
        # Match by prefix
        return any(
            m == model_name or m.startswith(model_name.split(":")[0])
            for m in models
        )
    except (ConnectionError, RuntimeError):
        return False


def pull_model(
    model_name: str,
    progress_callback: "callable[[str, float], None] | None" = None,
) -> bool:
    """Pull (download) a model from the Ollama registry.

    Args:
        model_name: The model tag to pull (e.g. "qwen2.5:7b")
        progress_callback: Optional callback(status_text, percent_0_to_1)

    Returns:
        True if the pull succeeded.
    """
    log.info("Pulling model: %s", model_name)

    try:
        with httpx.stream(
            "POST",
            f"{OLLAMA_BASE_URL}/api/pull",
            json={"name": model_name, "stream": True},
            timeout=httpx.Timeout(PULL_TIMEOUT, connect=CONNECT_TIMEOUT),
        ) as response:
            if response.status_code != 200:
                log.error("Pull request failed: %s", response.status_code)
                return False

            for line in response.iter_lines():
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    status = data.get("status", "")
                    total = data.get("total", 0)
                    completed = data.get("completed", 0)

                    percent = completed / total if total > 0 else 0.0

                    if progress_callback:
                        progress_callback(status, percent)

                    if status == "success":
                        log.info("Model %s pulled successfully.", model_name)
                        return True

                except json.JSONDecodeError:
                    continue

    except (httpx.ConnectError, httpx.TimeoutException) as exc:
        log.error("Failed to pull model %s: %s", model_name, exc)
        return False

    return True


def auto_select_and_ensure_model(
    progress_callback: "callable[[str, float], None] | None" = None,
) -> str | None:
    """Detect system hardware, select the best model, and pull it if needed.

    Returns the model name if successful, None on failure.
    """
    if not ensure_ollama_running():
        return None

    # Fast path: check if any target model is already available to skip slow hardware detection
    try:
        available = get_ollama_models()
        for target in ["qwen3:latest", "qwen2.5:3b", "phi3:3.8b", "qwen2.5:1.5b", "qwen2.5:14b"]:
            if target in available:
                log.info("Fast path: Model %s is already available.", target)
                return target
    except (ConnectionError, RuntimeError) as exc:
        log.warning("Could not query models for fast path: %s", exc)

    # Slow path
    sys_info = detect_system()
    recommended = sys_info.recommended_model
    log.info(
        "Recommended model: %s (GPU: %s, %.1fGB VRAM, %.1fGB RAM)",
        recommended,
        sys_info.gpu_name,
        sys_info.gpu_vram_gb,
        sys_info.total_ram_gb,
    )

    # Check if already available
    try:
        available = get_ollama_models()
        if recommended in available:
            log.info("Model %s is already available.", recommended)
            return recommended

        # We just use the recommended model


    except (ConnectionError, RuntimeError) as exc:
        log.warning("Could not query models: %s", exc)

    # Pull the recommended model
    if progress_callback:
        progress_callback(f"Downloading {recommended}...", 0.0)

    success = pull_model(recommended, progress_callback)
    if success:
        return recommended

    # Fallback: try a smaller model
    fallback = "qwen2.5:1.5b"
    if fallback != recommended:
        log.info("Trying fallback model: %s", fallback)
        if progress_callback:
            progress_callback(f"Trying fallback {fallback}...", 0.0)
        if pull_model(fallback, progress_callback):
            return fallback

    return None


# ── LLM Inference ─────────────────────────────────────────────────────────

def ask_ollama(model: str, prompt: str) -> str:
    """Send a prompt to Ollama and return the generated response.

    Raises:
        ConnectionError: If Ollama is unreachable.
        RuntimeError: If the response is an error or malformed.
    """
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
    }

    try:
        response = httpx.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json=payload,
            timeout=GENERATE_TIMEOUT,
        )
    except (httpx.ConnectError, httpx.TimeoutException) as exc:
        raise ConnectionError(f"Failed to connect to Ollama: {exc}") from exc

    if response.status_code != 200:
        raise RuntimeError(f"Ollama returned an error status: {response.status_code}")

    try:
        data = response.json()
        return data["response"]
    except (KeyError, TypeError, ValueError) as exc:
        raise RuntimeError(f"Failed to parse Ollama response: {exc}") from exc


def ask_ollama_stream(model: str, prompt: str) -> Generator[str, None, None]:
    """Stream tokens from Ollama one at a time.

    Yields:
        Individual token strings as they arrive.

    Raises:
        ConnectionError: If Ollama is unreachable.
        RuntimeError: On protocol errors.
    """
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": True,
    }

    try:
        with httpx.stream(
            "POST",
            f"{OLLAMA_BASE_URL}/api/generate",
            json=payload,
            timeout=httpx.Timeout(GENERATE_TIMEOUT, connect=CONNECT_TIMEOUT),
        ) as response:
            if response.status_code != 200:
                raise RuntimeError(
                    f"Ollama returned error status: {response.status_code}"
                )

            for line in response.iter_lines():
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    token = data.get("response", "")
                    if token:
                        yield token
                    if data.get("done", False):
                        return
                except json.JSONDecodeError:
                    continue

    except (httpx.ConnectError, httpx.TimeoutException) as exc:
        raise ConnectionError(f"Failed to connect to Ollama: {exc}") from exc
