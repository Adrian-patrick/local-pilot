"""Structured LLM prompt builder.

Replicates the prompt template from AskSection.tsx handleSubmit().
"""

from __future__ import annotations

from app.file_service import FileMetadata


def build_prompt(
    metadata: FileMetadata | None,
    file_content: str,
    user_query: str,
) -> str:
    """Build a structured prompt string for the Ollama LLM.

    When metadata is provided, the prompt includes file/directory details
    and content. Otherwise it falls back to a general assistant prompt.
    """
    if metadata is not None:
        kind = "directory" if metadata.is_dir else "file"
        kind_upper = "DIRECTORY" if metadata.is_dir else "FILE"
        tree_or_contents = "DIRECTORY TREE" if metadata.is_dir else "FILE CONTENTS"

        size_line = "" if metadata.is_dir else f"Size: {metadata.file_size} bytes\n"

        return (
            f"You are Local Pilot, an offline, highly intelligent software developer assistant.\n"
            f"You are helping the user with their loaded {kind}.\n"
            f"\n"
            f"---\n"
            f"{kind_upper} DETAILS:\n"
            f"Name: {metadata.file_name}\n"
            f"Path: {metadata.full_path}\n"
            f"{size_line}"
            f"Last Modified: {metadata.last_modified}\n"
            f"---\n"
            f"{tree_or_contents}:\n"
            f"{file_content}\n"
            f"---\n"
            f"\n"
            f"INSTRUCTIONS:\n"
            f"- Analyze the {kind if metadata.is_dir else 'file contents'} and metadata provided above.\n"
            f"- Answer the user's question directly, clearly, and concisely.\n"
            f"- For code improvements or explanations, write premium clean code blocks with clear syntax.\n"
            f"\n"
            f"USER QUERY:\n"
            f"{user_query}"
        )
    else:
        return (
            f"You are Local Pilot, an offline, highly intelligent software developer assistant.\n"
            f"Please answer the user's question directly, clearly, and concisely.\n"
            f"\n"
            f"USER QUERY:\n"
            f"{user_query}"
        )
