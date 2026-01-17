"""File write tool for the evolution agent."""

from pathlib import Path

from langchain_core.tools import tool
from pydantic import AliasChoices, BaseModel, Field

from worker.tools.path_utils import resolve_path, virtualize_path


class WriteFileInput(BaseModel):
    """Input schema for the write_file tool."""

    file_path: str = Field(
        description="The path to the file to write. Can be absolute or relative to workspace root.",
        validation_alias=AliasChoices("file_path", "path"),
    )
    content: str = Field(description="The content to write to the file.")


def _resolve_path(file_path: str) -> Path:
    """Resolve the file path using workspace-aware resolution."""
    return resolve_path(file_path)


@tool(args_schema=WriteFileInput)
def write_file(file_path: str, content: str) -> str:
    """Write content to a file.

    Creates a new file or overwrites an existing file with the provided content.
    Parent directories will be created if they don't exist.

    Args:
        file_path: Path to the file to write. Can be absolute or relative to workspace.
        content: The content to write to the file.

    Returns:
        Success message or error description.
    """
    path = _resolve_path(file_path)

    try:
        # Create parent directories if needed
        path.parent.mkdir(parents=True, exist_ok=True)

        # Write the file
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

        # Count lines for feedback
        line_count = content.count("\n") + (1 if content and not content.endswith("\n") else 0)

        return f"Successfully wrote {line_count} lines to {virtualize_path(path)}"

    except PermissionError:
        return f"Error: Permission denied: {virtualize_path(path)}"
    except Exception as e:
        return f"Error writing file {virtualize_path(path)}: {e}"
