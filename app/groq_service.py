"""Groq API inference service.

Handles streaming inference for cloud-based LLM generation via Groq API.
"""

from __future__ import annotations

import json
import logging
import re
import time
from typing import Iterator

import httpx

log = logging.getLogger(__name__)

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

def _parse_reset_time_to_timestamp(time_str: str) -> float:
    """Parse a Groq reset string (e.g. '5.43s', '14m12.3s') to an absolute Unix timestamp."""
    if not time_str or time_str == "?":
        return 0.0
    
    total_seconds = 0.0
    # Match optional minutes and optional seconds
    match = re.match(r'(?:(\d+)m)?(?:(\d+(?:\.\d+)?)s)?', time_str.strip())
    if match:
        minutes = match.group(1)
        seconds = match.group(2)
        if minutes:
            total_seconds += int(minutes) * 60
        if seconds:
            total_seconds += float(seconds)
            
    return time.time() + total_seconds

def ask_groq_stream(model: str, prompt: str, api_key: str, on_rate_limit=None) -> Iterator[str]:
    """Send a prompt to the Groq API and yield response tokens as they stream in.
    
    If on_rate_limit is provided, it will be called with the rate limit header dict
    once the response headers are received.
    """
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": model,
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "stream": True,
        "temperature": 0.2
    }

    # Strict timeouts: 10s to connect, 30s to read between chunks
    timeout = httpx.Timeout(30.0, connect=10.0)

    try:
        with httpx.stream("POST", GROQ_API_URL, headers=headers, json=payload, timeout=timeout) as response:
            if response.status_code != 200:
                err_msg = response.read().decode("utf-8")
                raise RuntimeError(f"Groq API Error {response.status_code}: {err_msg}")
            
            # Extract Rate Limit headers
            if on_rate_limit:
                limits = {
                    "req_remain": response.headers.get("x-ratelimit-remaining-requests", "?"),
                    "req_limit": response.headers.get("x-ratelimit-limit-requests", "?"),
                    "req_reset_ts": _parse_reset_time_to_timestamp(response.headers.get("x-ratelimit-reset-requests", "")),
                    "tok_remain": response.headers.get("x-ratelimit-remaining-tokens", "?"),
                    "tok_limit": response.headers.get("x-ratelimit-limit-tokens", "?"),
                    "tok_reset_ts": _parse_reset_time_to_timestamp(response.headers.get("x-ratelimit-reset-tokens", "")),
                }
                on_rate_limit(limits)
            
            for line in response.iter_lines():
                if not line or not line.startswith("data: "):
                    continue
                
                data_str = line[len("data: "):]
                if data_str.strip() == "[DONE]":
                    break
                
                try:
                    data = json.loads(data_str)
                    content = data.get("choices", [{}])[0].get("delta", {}).get("content", "")
                    if content:
                        yield content
                except json.JSONDecodeError:
                    continue
    except httpx.TimeoutException:
        raise TimeoutError("Groq API Timeout: The server took too long to respond.")
    except httpx.RequestError as e:
        raise ConnectionError(f"Failed to connect to Groq API: {e}")


def ask_groq_stream_messages(model: str, messages: list[dict], api_key: str, on_rate_limit=None) -> Iterator[str]:
    """Send a structured messages list to the Groq API and yield response tokens.
    
    Unlike ask_groq_stream which takes a single string prompt, this function
    accepts a list of message dicts with 'role' and 'content' keys, allowing
    proper system/user/assistant message separation.
    """
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": model,
        "messages": messages,
        "stream": True,
        "temperature": 0.2
    }

    timeout = httpx.Timeout(30.0, connect=10.0)

    try:
        with httpx.stream("POST", GROQ_API_URL, headers=headers, json=payload, timeout=timeout) as response:
            if response.status_code != 200:
                err_msg = response.read().decode("utf-8")
                raise RuntimeError(f"Groq API Error {response.status_code}: {err_msg}")
            
            if on_rate_limit:
                limits = {
                    "req_remain": response.headers.get("x-ratelimit-remaining-requests", "?"),
                    "req_limit": response.headers.get("x-ratelimit-limit-requests", "?"),
                    "req_reset_ts": _parse_reset_time_to_timestamp(response.headers.get("x-ratelimit-reset-requests", "")),
                    "tok_remain": response.headers.get("x-ratelimit-remaining-tokens", "?"),
                    "tok_limit": response.headers.get("x-ratelimit-limit-tokens", "?"),
                    "tok_reset_ts": _parse_reset_time_to_timestamp(response.headers.get("x-ratelimit-reset-tokens", "")),
                }
                on_rate_limit(limits)
            
            for line in response.iter_lines():
                if not line or not line.startswith("data: "):
                    continue
                
                data_str = line[len("data: "):]
                if data_str.strip() == "[DONE]":
                    break
                
                try:
                    data = json.loads(data_str)
                    content = data.get("choices", [{}])[0].get("delta", {}).get("content", "")
                    if content:
                        yield content
                except json.JSONDecodeError:
                    continue
    except httpx.TimeoutException:
        raise TimeoutError("Groq API Timeout: The server took too long to respond.")
    except httpx.RequestError as e:
        raise ConnectionError(f"Failed to connect to Groq API: {e}")
