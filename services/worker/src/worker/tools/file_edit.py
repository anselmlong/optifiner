"""File edit tool for the evolution agent - performs exact string replacements."""

from pathlib import Path

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from worker.tools.path_utils import resolve_path, virtualize_path


class EditFileInput(BaseModel):
    """Input schema for the edit_file tool."""

    file_path: str = Field(
        description="The path to the file to edit. Can be absolute or relative to workspace root."
    )
    old_string: str = Field(
        description="The exact text to find and replace. Must match the file content exactly, including whitespace and indentation."
    )
    new_string: str = Field(description="The text to replace old_string with.")
    replace_all: bool = Field(
        default=False,
        description="If True, replace all occurrences of old_string. If False (default), only replace the first occurrence and fail if not unique.",
    )


def _resolve_path(file_path: str) -> Path:
    """Resolve the file path using workspace-aware resolution."""
    return resolve_path(file_path)


@tool(args_schema=EditFileInput)
def edit_file(
    file_path: str, old_string: str, new_string: str, replace_all: bool = False
) -> str:
    """Perform exact string replacement in a file.

    Finds and replaces text in a file. The old_string must match exactly,
    including all whitespace and indentation.

    Args:
        file_path: Path to the file to edit.
        old_string: The exact text to find and replace.
        new_string: The text to replace old_string with.
        replace_all: If True, replace all occurrences. If False, require unique match.

    Returns:
        Success message with details, or error description.
    """
    path = _resolve_path(file_path)

    vpath = virtualize_path(path)
    
    if not path.exists():
        return f"Error: File not found: {vpath}"

    if not path.is_file():
        return f"Error: Path is not a file: {vpath}"

    if old_string == new_string:
        return "Error: old_string and new_string are identical. No changes needed."

    try:
        # Read current content
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        # Count occurrences
        count = content.count(old_string)

        if count == 0:
            # Provide helpful context for debugging
            if old_string.strip() in content:
                return f"Error: old_string not found in {vpath}. The text exists with different whitespace - check indentation and line endings."
            return f"Error: old_string not found in {vpath}. Use read_file to verify the exact content."

        if count > 1 and not replace_all:
            return f"Error: old_string found {count} times in {vpath}. Use replace_all=True to replace all occurrences, or provide more context to make the match unique."

        # Perform replacement
        if replace_all:
            new_content = content.replace(old_string, new_string)
            replaced_count = count
        else:
            new_content = content.replace(old_string, new_string, 1)
            replaced_count = 1

        # Write back
        with open(path, "w", encoding="utf-8") as f:
            f.write(new_content)

        # Calculate line changes for feedback
        old_lines = old_string.count("\n") + 1
        new_lines = new_string.count("\n") + 1
        line_diff = new_lines - old_lines

        diff_msg = ""
        if line_diff > 0:
            diff_msg = f" (+{line_diff} lines)"
        elif line_diff < 0:
            diff_msg = f" ({line_diff} lines)"

        if replace_all and replaced_count > 1:
            return f"Successfully replaced {replaced_count} occurrences in {vpath}{diff_msg}"
        return f"Successfully edited {vpath}{diff_msg}"

    except PermissionError:
        return f"Error: Permission denied: {vpath}"
    except UnicodeDecodeError:
        return f"Error: Cannot edit binary file: {vpath}"
    except Exception as e:
        return f"Error editing file {vpath}: {e}"
