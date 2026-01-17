"""Glob tool for finding files by pattern."""

import os
from fnmatch import fnmatch
from pathlib import Path

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from optifiner_worker.config import settings


class GlobTool(BaseModel):
    """Input schema for the glob tool."""

    pattern: str = Field(
        description="Glob pattern to match files (e.g., '**/*.py', 'src/**/*.ts')"
    )
    target_directory: str | None = Field(
        default=None,
        description="Directory to search in. Defaults to workspace root.",
    )


DESCRIPTION = """Fast file pattern matching tool for finding files.

Usage:
- Supports standard glob patterns like "**/*.py" or "src/**/*.ts"
- ** matches any number of directories
- * matches any characters except path separator
- ? matches any single character
- Returns matching file paths sorted by modification time (newest first)
- Use this tool when you need to find files by name patterns

Examples:
    glob_tool(pattern="**/*.py")  # Find all Python files
    glob_tool(pattern="src/**/*.ts")  # Find TypeScript files in src
    glob_tool(pattern="**/test_*.py")  # Find test files
    glob_tool(pattern="**/*.{js,ts}")  # Find JS or TS files"""


def _glob_match(root: Path, pattern: str) -> list[Path]:
    """Match files using glob pattern."""
    matches = []

    # Handle ** prefix
    if pattern.startswith("**/"):
        sub_pattern = pattern[3:]
        for dirpath, _, filenames in os.walk(root):
            for filename in filenames:
                if fnmatch(filename, sub_pattern) or fnmatch(
                    str(Path(dirpath) / filename), pattern
                ):
                    matches.append(Path(dirpath) / filename)
    else:
        # Use pathlib glob
        try:
            matches = list(root.glob(pattern))
        except Exception:
            # Fallback to manual matching
            for dirpath, _, filenames in os.walk(root):
                for filename in filenames:
                    full_path = Path(dirpath) / filename
                    rel_path = full_path.relative_to(root)
                    if fnmatch(str(rel_path), pattern):
                        matches.append(full_path)

    return matches


@tool(args_schema=GlobTool)
def glob_tool(pattern: str, target_directory: str | None = None) -> str:
    """Find files matching a glob pattern."""
    workspace = Path(settings.workspace_path).resolve()

    if target_directory:
        search_dir = Path(target_directory)
        if not search_dir.is_absolute():
            search_dir = workspace / target_directory
        search_dir = search_dir.resolve()

        # Ensure within workspace
        if not str(search_dir).startswith(str(workspace)):
            return f"Error: Directory must be within workspace ({settings.workspace_path})"
    else:
        search_dir = workspace

    if not search_dir.exists():
        return f"Error: Directory not found: {search_dir}"

    if not search_dir.is_dir():
        return f"Error: Path is not a directory: {search_dir}"

    try:
        # Auto-prepend **/ if pattern doesn't start with it and doesn't contain path separator
        search_pattern = pattern
        if not pattern.startswith("**/") and "/" not in pattern:
            search_pattern = f"**/{pattern}"

        matches = _glob_match(search_dir, search_pattern)

        # Filter to only files
        matches = [m for m in matches if m.is_file()]

        # Sort by modification time (newest first)
        matches.sort(key=lambda p: p.stat().st_mtime, reverse=True)

        if not matches:
            return f"No files found matching pattern: {pattern}"

        # Format output with relative paths
        results = []
        for match in matches[:100]:  # Limit to 100 results
            try:
                rel_path = match.relative_to(workspace)
                results.append(str(rel_path))
            except ValueError:
                results.append(str(match))

        output = f"Found {len(matches)} file(s) matching '{pattern}':\n"
        output += "\n".join(f"  {r}" for r in results)

        if len(matches) > 100:
            output += f"\n  ... and {len(matches) - 100} more files"

        return output

    except Exception as e:
        return f"Error searching for files: {e}"


glob_tool.__doc__ = DESCRIPTION
