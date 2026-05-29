from __future__ import annotations

from dataclasses import dataclass


STRICT_MODE = "selected_files_only"
SMART_MODE = "files_ai_knowledge"
ANSWER_MODES = {STRICT_MODE, SMART_MODE}


def normalize_answer_mode(answer_mode: str | None) -> str:
    value = (answer_mode or STRICT_MODE).strip().lower()
    return value if value in ANSWER_MODES else STRICT_MODE


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
