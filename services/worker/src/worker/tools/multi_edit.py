"""Multi-edit tool for the evolution agent - performs multiple edits to a single file."""

import logging
from pathlib import Path
from typing import Any

from langchain_core.tools import tool
from pydantic import AliasChoices, BaseModel, Field

from worker.tools.path_utils import resolve_path, virtualize_path

logger = logging.getLogger(__name__)


def _normalize_whitespace(text: str) -> str:
    """Normalize line endings and trailing whitespace."""
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    lines = text.split('\n')
    return '\n'.join(line.rstrip() for line in lines)


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
        description="The path to the file to edit. Can be absolute or relative to workspace root.",
        validation_alias=AliasChoices("file_path", "path"),
    )
    edits: list[EditOperation] = Field(
        description="List of edit operations to perform in sequence."
    )


def _resolve_path(file_path: str) -> Path:
    """Resolve the file path using workspace-aware resolution."""
    return resolve_path(file_path)


def _apply_edit(content: str, edit: EditOperation, edit_index: int) -> tuple[str, str, bool]:
    """Apply a single edit operation. Returns (new_content, status_message, was_normalized) or raises."""
    old_string = edit.old_string
    new_string = edit.new_string
    replace_all = edit.replace_all

    if old_string == new_string:
        raise ValueError(f"Edit {edit_index + 1}: old_string and new_string are identical")

    count = content.count(old_string)
    normalized = False

    # If not found, try with normalized whitespace
    if count == 0:
        norm_content = _normalize_whitespace(content)
        norm_old = _normalize_whitespace(old_string)
        norm_count = norm_content.count(norm_old)
        
        if norm_count > 0:
            # Use normalized versions
            normalized = True
            content = norm_content
            old_string = norm_old
            new_string = _normalize_whitespace(new_string)
            count = norm_count
        else:
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
        status = f"replaced {count} occurrence(s)"
    else:
        new_content = content.replace(old_string, new_string, 1)
        status = "replaced 1 occurrence"
    
    if normalized:
        status += " (normalized)"
    return new_content, status, normalized


@tool(args_schema=MultiEditInput)
def multi_edit(file_path: str, edits: list[EditOperation | dict[str, Any]]) -> str:
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
    vpath = virtualize_path(path)

    if not path.exists():
        # Allow creating new file if first edit has empty old_string
        first_edit = edits[0]
        first_old = first_edit.old_string if isinstance(first_edit, EditOperation) else first_edit.get("old_string", "")
        if edits and first_old == "":
            try:
                path.parent.mkdir(parents=True, exist_ok=True)
                content = ""
            except Exception as e:
                return f"Error creating file {vpath}: {e}"
        else:
            return f"Error: File not found: {vpath}"
    else:
        if not path.is_file():
            return f"Error: Path is not a file: {vpath}"

        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
        except UnicodeDecodeError:
            return f"Error: Cannot edit binary file: {vpath}"
        except Exception as e:
            return f"Error reading file {vpath}: {e}"

    if not edits:
        return "Error: No edits provided"

    # Convert dicts to EditOperation objects (edits may already be EditOperation if parsed by Pydantic)
    logger.debug(f"multi_edit called on {vpath} with {len(edits)} edit(s)")
    edit_ops = []
    for i, edit_item in enumerate(edits):
        try:
            # Handle both EditOperation objects (from Pydantic schema) and dicts (from direct calls)
            if isinstance(edit_item, EditOperation):
                edit_op = edit_item
                old_str = edit_op.old_string
                new_str = edit_op.new_string
            elif isinstance(edit_item, dict):
                # Check for required fields
                if 'old_string' not in edit_item:
                    err = f"Error in edit {i + 1}: missing 'old_string' field. Got keys: {list(edit_item.keys())}"
                    logger.error(f"multi_edit {vpath}: {err}")
                    return err
                if 'new_string' not in edit_item:
                    err = f"Error in edit {i + 1}: missing 'new_string' field. Got keys: {list(edit_item.keys())}"
                    logger.error(f"multi_edit {vpath}: {err}")
                    return err
                old_str = edit_item.get('old_string', '')
                new_str = edit_item.get('new_string', '')
                edit_op = EditOperation(**edit_item)
            else:
                err = f"Error in edit {i + 1}: expected EditOperation or dict, got {type(edit_item).__name__}"
                logger.error(f"multi_edit {vpath}: {err}")
                return err
            
            # Log the full edit for debugging
            logger.debug(
                f"Edit {i + 1} - old_string ({len(old_str)} chars, {old_str.count(chr(10))+1} lines):\n"
                f"---OLD_STRING_START---\n{old_str}\n---OLD_STRING_END---"
            )
            logger.debug(
                f"Edit {i + 1} - new_string ({len(new_str)} chars, {new_str.count(chr(10))+1} lines):\n"
                f"---NEW_STRING_START---\n{new_str}\n---NEW_STRING_END---"
            )
            
            edit_ops.append(edit_op)
        except Exception as e:
            # Log full details before truncating for return message
            logger.error(
                f"multi_edit {vpath}: Error parsing edit {i + 1}: {e}\n"
                f"Full edit_item:\n{edit_item}"
            )
            # Truncate the preview for return message to avoid hiding the actual error
            if isinstance(edit_item, dict):
                preview_keys = list(edit_item.keys())
                old_preview = str(edit_item.get('old_string', ''))[:50] + '...' if len(str(edit_item.get('old_string', ''))) > 50 else str(edit_item.get('old_string', ''))
                new_preview = str(edit_item.get('new_string', ''))[:50] + '...' if len(str(edit_item.get('new_string', ''))) > 50 else str(edit_item.get('new_string', ''))
                return f"Error in edit {i + 1} specification: {e}. Keys: {preview_keys}, old_string preview: {repr(old_preview)}, new_string preview: {repr(new_preview)}"
            else:
                return f"Error in edit {i + 1} specification: {e}"

    # Validate all edits first (dry run)
    test_content = content
    edit_results = []

    for i, edit in enumerate(edit_ops):
        try:
            test_content, status, _ = _apply_edit(test_content, edit, i)
            edit_results.append(status)
            logger.debug(f"Edit {i + 1} validated: {status}")
        except ValueError as e:
            # Log full context for debugging
            logger.error(
                f"multi_edit {vpath}: Edit {i + 1} failed: {e}\n"
                f"old_string ({len(edit.old_string)} chars):\n"
                f"---OLD_STRING_START---\n{edit.old_string}\n---OLD_STRING_END---\n"
                f"File content length: {len(content)} chars"
            )
            return f"Error: {e}. No changes were made."

    # All edits validated - apply for real
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(test_content)
    except PermissionError:
        logger.error(f"multi_edit {vpath}: Permission denied")
        return f"Error: Permission denied: {vpath}"
    except Exception as e:
        logger.error(f"multi_edit {vpath}: Write error: {e}")
        return f"Error writing file {vpath}: {e}"

    # Build summary
    summary_parts = [f"Successfully applied {len(edits)} edit(s) to {vpath}:"]
    for i, result in enumerate(edit_results):
        summary_parts.append(f"  {i + 1}. {result}")

    logger.info(f"multi_edit {vpath}: Successfully applied {len(edits)} edit(s)")
    return "\n".join(summary_parts)
