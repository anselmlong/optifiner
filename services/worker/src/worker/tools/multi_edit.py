"""Multi-edit tool for the evolution agent - performs multiple edits to a single file."""

import os
from pathlib import Path
from typing import Any

from langchain_core.tools import tool
from pydantic import BaseModel, Field


def _get_workspace_root() -> Path:
    """Get the workspace root from environment or default."""
    return Path(os.environ.get("WORKSPACE_ROOT", "/app"))


class EditOperation(BaseModel):
    """A single edit operation."""

    old_string: str = Field(
        description="The exact text to find and replace."
    )
    new_string: str = Field(
        description="The text to replace old_string with."
    )
    replace_all: bool = Field(
        default=False,
        description="If True, replace all occurrences of old_string.",
    )


class MultiEditInput(BaseModel):
    """Input schema for the multi_edit tool."""

    file_path: str = Field(
        description="The path to the file to edit. Can be absolute or relative to workspace root."
    )
    edits: list[EditOperation] = Field(
        description="List of edit operations to perform in sequence."
    )


def _resolve_path(file_path: str) -> Path:
    """Resolve the file path, making it relative to workspace if not absolute."""
    path = Path(file_path)
    if not path.is_absolute():
        path = _get_workspace_root() / path
    return path


def _apply_edit(content: str, edit: EditOperation, edit_index: int) -> tuple[str, str]:
    """Apply a single edit operation. Returns (new_content, status_message) or raises."""
    old_string = edit.old_string
    new_string = edit.new_string
    replace_all = edit.replace_all

    if old_string == new_string:
        raise ValueError(f"Edit {edit_index + 1}: old_string and new_string are identical")

    count = content.count(old_string)

    if count == 0:
        if old_string.strip() in content:
            raise ValueError(
                f"Edit {edit_index + 1}: old_string not found (exists with different whitespace)"
            )
        raise ValueError(f"Edit {edit_index + 1}: old_string not found in file")

    if count > 1 and not replace_all:
        raise ValueError(
            f"Edit {edit_index + 1}: old_string found {count} times (use replace_all=True or add context)"
        )

    if replace_all:
        new_content = content.replace(old_string, new_string)
        return new_content, f"replaced {count} occurrence(s)"
    else:
        new_content = content.replace(old_string, new_string, 1)
        return new_content, "replaced 1 occurrence"


@tool(args_schema=MultiEditInput)
def multi_edit(file_path: str, edits: list[dict[str, Any]]) -> str:
    """Perform multiple edits to a single file atomically.

    All edits are applied in sequence. If any edit fails, none are applied.
    This is more efficient than multiple edit_file calls when making several
    changes to the same file.

    Args:
        file_path: Path to the file to edit.
        edits: List of edit operations, each with old_string, new_string, and optional replace_all.

    Returns:
        Success message with details, or error description.
    """
    path = _resolve_path(file_path)

    if not path.exists():
        # Allow creating new file if first edit has empty old_string
        if edits and edits[0].get("old_string", "") == "":
            try:
                path.parent.mkdir(parents=True, exist_ok=True)
                content = ""
            except Exception as e:
                return f"Error creating file {path}: {e}"
        else:
            return f"Error: File not found: {path}"
    else:
        if not path.is_file():
            return f"Error: Path is not a file: {path}"

        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
        except UnicodeDecodeError:
            return f"Error: Cannot edit binary file: {path}"
        except Exception as e:
            return f"Error reading file {path}: {e}"

    if not edits:
        return "Error: No edits provided"

    # Convert dicts to EditOperation objects
    edit_ops = []
    for i, edit_dict in enumerate(edits):
        try:
            edit_ops.append(EditOperation(**edit_dict))
        except Exception as e:
            return f"Error in edit {i + 1} specification: {e}"

    # Validate all edits first (dry run)
    test_content = content
    edit_results = []

    for i, edit in enumerate(edit_ops):
        try:
            test_content, status = _apply_edit(test_content, edit, i)
            edit_results.append(status)
        except ValueError as e:
            return f"Error: {e}. No changes were made."

    # All edits validated - apply for real
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(test_content)
    except PermissionError:
        return f"Error: Permission denied: {path}"
    except Exception as e:
        return f"Error writing file {path}: {e}"

    # Build summary
    summary_parts = [f"Successfully applied {len(edits)} edit(s) to {path}:"]
    for i, result in enumerate(edit_results):
        summary_parts.append(f"  {i + 1}. {result}")

    return "\n".join(summary_parts)
