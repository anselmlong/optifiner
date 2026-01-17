"""Glob tool for the evolution agent - fast file pattern matching."""

import os
from pathlib import Path

from langchain_core.tools import tool
from pydantic import BaseModel, Field

MAX_RESULTS = 500


def _get_workspace_root() -> Path:
    """Get the workspace root from environment or default."""
    return Path(os.environ.get("WORKSPACE_ROOT", "/app"))


class GlobInput(BaseModel):
    """Input schema for the glob_search tool."""

    pattern: str = Field(
        description='Glob pattern to match files (e.g., "*.py", "**/*.ts", "src/**/*.js").'
    )
    path: str | None = Field(
        default=None,
        description="Directory to search in. Defaults to workspace root.",
    )


def _resolve_path(file_path: str | None) -> Path:
    """Resolve the file path, defaulting to workspace root."""
    workspace = _get_workspace_root()
    if file_path is None:
        return workspace
    path = Path(file_path)
    if not path.is_absolute():
        path = workspace / path
    return path


@tool(args_schema=GlobInput)
def glob_search(pattern: str, path: str | None = None) -> str:
    """Find files matching a glob pattern.

    Fast file pattern matching tool for finding files by name patterns.
    Returns matching file paths sorted by modification time (most recent first).

    Args:
        pattern: Glob pattern to match (e.g., "*.py", "**/*.ts").
        path: Directory to search in. Defaults to workspace root.

    Returns:
        List of matching file paths or error message.
    """
    search_path = _resolve_path(path)
    workspace = _get_workspace_root()

    if not search_path.exists():
        return f"Error: Path not found: {search_path}"

    if not search_path.is_dir():
        return f"Error: Path is not a directory: {search_path}"

    # Ensure pattern is recursive if not explicitly specified
    if not pattern.startswith("**/") and "/" not in pattern:
        search_pattern = f"**/{pattern}"
    else:
        search_pattern = pattern

    try:
        # Use pathlib glob for simplicity and reliability
        matches = list(search_path.glob(search_pattern))

        # Filter to files only
        files = [f for f in matches if f.is_file()]

        if not files:
            return f"No files found matching pattern: {pattern}"

        # Sort by modification time (most recent first)
        files.sort(key=lambda f: f.stat().st_mtime, reverse=True)

        # Build output with relative paths
        result_lines = []
        for f in files[:MAX_RESULTS]:
            try:
                rel_path = f.relative_to(workspace)
                result_lines.append(str(rel_path))
            except ValueError:
                result_lines.append(str(f))

        output = "\n".join(result_lines)

        if len(files) > MAX_RESULTS:
            output += f"\n\n[... showing {MAX_RESULTS} of {len(files)} matches]"
        else:
            output += f"\n\n[{len(files)} file(s) found]"

        return output

    except Exception as e:
        return f"Error during glob search: {e}"
