from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class WorkspaceState:
    id: str
    item_ids: list[str]
    title: str
    selection_type: str
    selection_label: str
    paths: list[str]


@dataclass(frozen=True)
class RetrievalResult:
    chunk: dict
    score: float
    reason: str


@dataclass(frozen=True)
class AgentResult:
    answer: str
    validation: str
    sources: list[str]
