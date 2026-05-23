from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path


DB_PATH = Path(__file__).resolve().parents[2] / "data" / "local_pilot.db"


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()


def path_id(path: str) -> str:
    return hashlib.sha256(str(Path(path).resolve()).lower().encode("utf-8")).hexdigest()[:24]


def connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    _init_db(con)
    return con


def _init_db(con: sqlite3.Connection) -> None:
    con.executescript(
        """
        CREATE TABLE IF NOT EXISTS items (
            id TEXT PRIMARY KEY,
            path TEXT NOT NULL,
            kind TEXT NOT NULL,
            name TEXT NOT NULL,
            content_hash TEXT NOT NULL,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS chunks (
            id TEXT PRIMARY KEY,
            item_id TEXT NOT NULL,
            chunk_index INTEGER NOT NULL,
            text TEXT NOT NULL,
            source TEXT NOT NULL,
            metadata TEXT NOT NULL DEFAULT '{}',
            FOREIGN KEY(item_id) REFERENCES items(id)
        );

        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_id TEXT NOT NULL,
            workspace_id TEXT,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(item_id) REFERENCES items(id)
        );

        CREATE TABLE IF NOT EXISTS workspaces (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            selection_type TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS workspace_items (
            workspace_id TEXT NOT NULL,
            item_id TEXT NOT NULL,
            position INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (workspace_id, item_id),
            FOREIGN KEY(workspace_id) REFERENCES workspaces(id),
            FOREIGN KEY(item_id) REFERENCES items(id)
        );
        """
    )
    _ensure_column(con, "messages", "workspace_id", "TEXT")
    con.commit()


def _ensure_column(con: sqlite3.Connection, table: str, column: str, definition: str) -> None:
    columns = {row["name"] for row in con.execute(f"PRAGMA table_info({table})")}
    if column not in columns:
        con.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def get_item(con: sqlite3.Connection, item_id: str) -> sqlite3.Row | None:
    return con.execute("SELECT * FROM items WHERE id=?", (item_id,)).fetchone()


def upsert_item(
    con: sqlite3.Connection,
    *,
    item_id: str,
    path: str,
    kind: str,
    name: str,
    item_hash: str,
) -> None:
    con.execute(
        """
        INSERT INTO items (id, path, kind, name, content_hash)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            path=excluded.path,
            kind=excluded.kind,
            name=excluded.name,
            content_hash=excluded.content_hash,
            updated_at=CURRENT_TIMESTAMP
        """,
        (item_id, path, kind, name, item_hash),
    )
    con.commit()


def replace_chunks(con: sqlite3.Connection, item_id: str, chunks: list[dict]) -> None:
    con.execute("DELETE FROM chunks WHERE item_id=?", (item_id,))
    con.executemany(
        """
        INSERT INTO chunks (id, item_id, chunk_index, text, source, metadata)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        [
            (
                f"{item_id}:{chunk['chunk_index']}",
                item_id,
                chunk["chunk_index"],
                chunk["text"],
                chunk["source"],
                json.dumps(chunk.get("metadata", {})),
            )
            for chunk in chunks
        ],
    )
    con.commit()


def load_chunks(con: sqlite3.Connection, item_id: str) -> list[dict]:
    rows = con.execute(
        "SELECT * FROM chunks WHERE item_id=? ORDER BY chunk_index",
        (item_id,),
    ).fetchall()
    return [
        {
            "id": row["id"],
            "item_id": row["item_id"],
            "chunk_index": row["chunk_index"],
            "text": row["text"],
            "source": row["source"],
            "metadata": json.loads(row["metadata"] or "{}"),
        }
        for row in rows
    ]


def create_workspace(
    con: sqlite3.Connection,
    *,
    workspace_id: str,
    title: str,
    selection_type: str,
    item_ids: list[str],
) -> None:
    con.execute(
        """
        INSERT INTO workspaces (id, title, selection_type)
        VALUES (?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            title=excluded.title,
            selection_type=excluded.selection_type,
            updated_at=CURRENT_TIMESTAMP
        """,
        (workspace_id, title, selection_type),
    )
    con.execute("DELETE FROM workspace_items WHERE workspace_id=?", (workspace_id,))
    con.executemany(
        """
        INSERT INTO workspace_items (workspace_id, item_id, position)
        VALUES (?, ?, ?)
        """,
        [(workspace_id, item_id, index) for index, item_id in enumerate(item_ids)],
    )
    con.commit()


def load_workspace_items(con: sqlite3.Connection, workspace_id: str) -> list[sqlite3.Row]:
    return con.execute(
        """
        SELECT items.*
        FROM workspace_items
        JOIN items ON items.id = workspace_items.item_id
        WHERE workspace_items.workspace_id=?
        ORDER BY workspace_items.position
        """,
        (workspace_id,),
    ).fetchall()


def load_workspace_chunks(con: sqlite3.Connection, workspace_id: str) -> list[dict]:
    rows = con.execute(
        """
        SELECT chunks.*
        FROM workspace_items
        JOIN chunks ON chunks.item_id = workspace_items.item_id
        WHERE workspace_items.workspace_id=?
        ORDER BY workspace_items.position, chunks.chunk_index
        """,
        (workspace_id,),
    ).fetchall()
    return [
        {
            "id": row["id"],
            "item_id": row["item_id"],
            "chunk_index": row["chunk_index"],
            "text": row["text"],
            "source": row["source"],
            "metadata": json.loads(row["metadata"] or "{}"),
        }
        for row in rows
    ]


def save_message(
    con: sqlite3.Connection,
    item_id: str,
    role: str,
    content: str,
    workspace_id: str | None = None,
) -> None:
    con.execute(
        "INSERT INTO messages (item_id, workspace_id, role, content) VALUES (?, ?, ?, ?)",
        (item_id, workspace_id, role, content),
    )
    con.commit()


def load_history(con: sqlite3.Connection, item_id: str, limit: int = 8) -> list[dict]:
    rows = con.execute(
        """
        SELECT role, content, created_at
        FROM messages
        WHERE item_id=?
        ORDER BY id DESC
        LIMIT ?
        """,
        (item_id, limit),
    ).fetchall()
    return [
        {"role": row["role"], "content": row["content"], "created_at": row["created_at"]}
        for row in reversed(rows)
    ]


def load_workspace_history(con: sqlite3.Connection, workspace_id: str, limit: int = 8) -> list[dict]:
    rows = con.execute(
        """
        SELECT role, content, created_at
        FROM messages
        WHERE workspace_id=?
        ORDER BY id DESC
        LIMIT ?
        """,
        (workspace_id, limit),
    ).fetchall()
    return [
        {"role": row["role"], "content": row["content"], "created_at": row["created_at"]}
        for row in reversed(rows)
    ]

