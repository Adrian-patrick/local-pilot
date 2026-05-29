from __future__ import annotations

from ..context_collector import collect_context
from ..rag import chunk_text
from ..rag_store import (
    connect,
    content_hash,
    create_workspace,
    get_item,
    path_id,
    replace_chunks,
    upsert_item,
)
from .models import WorkspaceState


def collect_and_index(paths: list[str]) -> tuple[WorkspaceState, str]:
    contexts = [collect_context(path) for path in paths]
    item_ids = [_ensure_indexed(context) for context in contexts]
    workspace_id = _workspace_id(item_ids)
    selection_type = "single" if len(item_ids) == 1 else "multi"
    title = _workspace_title(contexts)

    with connect() as con:
        create_workspace(
            con,
            workspace_id=workspace_id,
            title=title,
            selection_type=selection_type,
            item_ids=item_ids,
        )

    workspace = WorkspaceState(
        id=workspace_id,
        item_ids=item_ids,
        title=title,
        selection_type=selection_type,
        selection_label=title,
        paths=[context["path"] for context in contexts],
    )
    extracted_text = "\n\n".join(context.get("text") or "" for context in contexts)
    return workspace, extracted_text


def _ensure_indexed(context: dict) -> str:
    item_id = path_id(context["path"])
    text = context.get("text") or ""
    item_hash = content_hash(text)

    with connect() as con:
        existing = get_item(con, item_id)
        if existing and existing["content_hash"] == item_hash:
            return item_id

        chunks = chunk_text(text, source=context["path"])
        upsert_item(
            con,
            item_id=item_id,
            path=context["path"],
            kind=context["kind"],
            name=context["name"],
            item_hash=item_hash,
        )
        replace_chunks(con, item_id, chunks)

    return item_id


def _workspace_id(item_ids: list[str]) -> str:
    return "ws_" + content_hash("|".join(sorted(item_ids)))[:24]


def _workspace_title(contexts: list[dict]) -> str:
    if len(contexts) == 1:
        return contexts[0]["path"]
    return f"{len(contexts)} selected items"
