from __future__ import annotations

from dataclasses import dataclass


class LLMError(RuntimeError):
    pass


@dataclass(frozen=True)
class GenerationConfig:
    temperature: float = 0.2
    max_tokens: int = 512
    timeout_seconds: int = 180
