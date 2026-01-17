"""List directory tool for the evolution agent."""

import os
from pathlib import Path

from langchain_core.tools import tool
from pydantic import BaseModel, Field

MAX_ENTRIES = 500


def _get_workspace_root() -> Path:
    """Get the workspace root from environment or default."""
    return Path(os.environ.get("WORKSPACE_ROOT", "/app"))


class ListDirInput(BaseModel):
    """Input schema for the list_dir tool."""

    path: str = Field(
        description="Path to the directory to list. Can be absolute or relative to workspace root."
    )
    show_hidden: bool = Field(
        default=False,
        description="If True, include hidden files and directories (starting with .).",
    )
    recursive: bool = Field(
        default=False,
        description="If True, list contents recursively.",
    )


def _resolve_path(file_path: str) -> Path:
    """Resolve the file path, making it relative to workspace if not absolute."""
    workspace = _get_workspace_root()
    path = Path(file_path)
    if not path.is_absolute():
        path = workspace / path
    return path


def _format_size(size: int) -> str:
    """Format file size in human-readable format."""
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024:
            return f"{size:.1f}{unit}" if unit != "B" else f"{size}{unit}"
        size /= 1024
    return f"{size:.1f}TB"


def _format_entry(entry: Path, base_path: Path, show_size: bool = True) -> str:
    """Format a single directory entry."""
    try:
        rel_path = entry.relative_to(base_path)
    except ValueError:
        rel_path = entry

    if entry.is_dir():
        return f"{rel_path}/"
    else:
        if show_size:
            try:
                size = _format_size(entry.stat().st_size)
                return f"{rel_path} ({size})"
            except OSError:
                return str(rel_path)
        return str(rel_path)


@tool(args_schema=ListDirInput)
def list_dir(path: str, show_hidden: bool = False, recursive: bool = False) -> str:
    """List files and directories in a given path.

    Returns a listing of the directory contents, with directories marked with
    a trailing slash and files showing their size.

    Args:
        path: Path to the directory to list.
        show_hidden: If True, include hidden files (starting with .).
        recursive: If True, list contents recursively.

    Returns:
        Directory listing or error message.
    """
    dir_path = _resolve_path(path)
    workspace = _get_workspace_root()

    if not dir_path.exists():
        return f"Error: Path not found: {dir_path}"

    if not dir_path.is_dir():
        return f"Error: Path is not a directory: {dir_path}. Use read_file to view file contents."

    try:
        if recursive:
            # Recursive listing
            entries = []
            for item in dir_path.rglob("*"):
                if not show_hidden:
                    # Skip hidden files and anything inside hidden directories
                    parts = item.relative_to(dir_path).parts
                    if any(part.startswith(".") for part in parts):
                        continue
                entries.append(item)
        else:
            # Single level listing
            entries = list(dir_path.iterdir())
            if not show_hidden:
                entries = [e for e in entries if not e.name.startswith(".")]

        if not entries:
            return f"Directory is empty: {dir_path}"

        # Sort: directories first, then files, alphabetically within each group
        dirs = sorted([e for e in entries if e.is_dir()], key=lambda x: x.name.lower())
        files = sorted([e for e in entries if e.is_file()], key=lambda x: x.name.lower())

        # Format output
        result_lines = []

        # Show path header
        try:
            rel_dir = dir_path.relative_to(workspace)
            header = f"Contents of {rel_dir}/"
        except ValueError:
            header = f"Contents of {dir_path}/"
        result_lines.append(header)
        result_lines.append("=" * len(header))

        total_entries = len(dirs) + len(files)
        shown_entries = 0

        # List directories
        for d in dirs:
            if shown_entries >= MAX_ENTRIES:
                break
            result_lines.append(_format_entry(d, dir_path, show_size=False))
            shown_entries += 1

        # List files
        for f in files:
            if shown_entries >= MAX_ENTRIES:
                break
            result_lines.append(_format_entry(f, dir_path))
            shown_entries += 1

        # Summary
        result_lines.append("")
        if total_entries > MAX_ENTRIES:
            result_lines.append(
                f"[Showing {MAX_ENTRIES} of {total_entries} entries. Use glob_search for more specific queries.]"
            )
        else:
            result_lines.append(f"[{len(dirs)} directories, {len(files)} files]")

        return "\n".join(result_lines)

    except PermissionError:
        return f"Error: Permission denied: {dir_path}"
    except Exception as e:
        return f"Error listing directory {dir_path}: {e}"
