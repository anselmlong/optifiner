"""Directory listing tool for LangGraph agents."""

import os
from pathlib import Path

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from optifiner_worker.config import settings


class LSTool(BaseModel):
    """Input schema for the ls tool."""

    target_directory: str = Field(description="Absolute path to the directory to list")
    show_hidden: bool = Field(
        default=False,
        description="If True, include hidden files (starting with .)",
    )
    recursive: bool = Field(
        default=False,
        description="If True, list contents recursively (up to 3 levels deep)",
    )


DESCRIPTION = """Lists files and directories in a given path.

Usage:
- The target_directory parameter must be an absolute path
- By default, hidden files (starting with .) are not shown
- Use show_hidden=True to include hidden files
- Use recursive=True for recursive listing (limited to 3 levels)
- For finding specific files, prefer glob_tool or grep_tool

Examples:
    ls_tool(target_directory="/app")
    ls_tool(target_directory="/app/src", show_hidden=True)
    ls_tool(target_directory="/app", recursive=True)"""


def _format_entry(path: Path, is_dir: bool) -> str:
    """Format a directory entry."""
    suffix = "/" if is_dir else ""
    try:
        size = path.stat().st_size if not is_dir else 0
        if size > 0:
            if size < 1024:
                size_str = f"{size}B"
            elif size < 1024 * 1024:
                size_str = f"{size // 1024}KB"
            else:
                size_str = f"{size // (1024 * 1024)}MB"
            return f"{path.name}{suffix} ({size_str})"
    except Exception:
        pass
    return f"{path.name}{suffix}"


def _list_directory(
    directory: Path,
    show_hidden: bool,
    current_depth: int = 0,
    max_depth: int = 3,
    prefix: str = "",
) -> list[str]:
    """List directory contents, optionally recursively."""
    entries = []

    try:
        items = sorted(directory.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
    except PermissionError:
        return [f"{prefix}[Permission denied]"]
    except Exception as e:
        return [f"{prefix}[Error: {e}]"]

    for item in items:
        # Skip hidden files unless requested
        if not show_hidden and item.name.startswith("."):
            continue

        is_dir = item.is_dir()
        entry_str = f"{prefix}{_format_entry(item, is_dir)}"
        entries.append(entry_str)

        # Recurse into subdirectories
        if is_dir and current_depth < max_depth:
            sub_entries = _list_directory(
                item,
                show_hidden,
                current_depth + 1,
                max_depth,
                prefix + "  ",
            )
            entries.extend(sub_entries)

    return entries


@tool(args_schema=LSTool)
def ls_tool(
    target_directory: str,
    show_hidden: bool = False,
    recursive: bool = False,
) -> str:
    """List contents of a directory."""
    workspace = Path(settings.workspace_path).resolve()
    path = Path(target_directory)

    if not path.is_absolute():
        path = workspace / target_directory

    path = path.resolve()

    # Ensure within workspace
    if not str(path).startswith(str(workspace)):
        return f"Error: Path must be within workspace ({settings.workspace_path})"

    if not path.exists():
        return f"Error: Directory not found: {target_directory}"

    if not path.is_dir():
        return f"Error: Path is not a directory: {target_directory}"

    max_depth = 3 if recursive else 0
    entries = _list_directory(path, show_hidden, 0, max_depth)

    if not entries:
        return f"Directory is empty: {target_directory}"

    try:
        rel_path = path.relative_to(workspace)
        header = f"Contents of {rel_path}/:"
    except ValueError:
        header = f"Contents of {path}/:"

    return header + "\n" + "\n".join(entries)


ls_tool.__doc__ = DESCRIPTION
