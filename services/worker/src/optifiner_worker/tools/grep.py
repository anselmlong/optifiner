"""Grep tool for searching file contents using regex."""

import os
import re
from pathlib import Path
from typing import Literal

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from optifiner_worker.config import settings


class GrepTool(BaseModel):
    """Input schema for the grep tool."""

    pattern: str = Field(description="Regular expression pattern to search for")
    path: str | None = Field(
        default=None,
        description="File or directory to search in. Defaults to workspace root.",
    )
    glob_filter: str | None = Field(
        default=None,
        description="Glob pattern to filter files (e.g., '*.py', '**/*.ts')",
    )
    case_insensitive: bool = Field(
        default=False,
        description="If True, perform case-insensitive matching",
    )
    output_mode: Literal["content", "files_with_matches", "count"] = Field(
        default="content",
        description="Output mode: 'content' shows matching lines, 'files_with_matches' shows only file paths, 'count' shows match counts",
    )
    context_lines: int = Field(
        default=0,
        description="Number of context lines to show before and after matches (only for 'content' mode)",
    )
    multiline: bool = Field(
        default=False,
        description="Enable multiline mode where . matches newlines",
    )


DESCRIPTION = """A powerful search tool for finding patterns in file contents.

Usage:
- Supports full regex syntax (e.g., "log.*Error", "function\\s+\\w+")
- Filter files with glob_filter parameter (e.g., "*.py", "**/*.tsx")
- Output modes:
  - "content": shows matching lines with context (default)
  - "files_with_matches": shows only file paths containing matches
  - "count": shows match counts per file
- Use case_insensitive=True for case-insensitive search
- Use multiline=True for patterns that span multiple lines
- Use context_lines to show surrounding context

Examples:
    grep_tool(pattern="def.*main")  # Find function definitions containing 'main'
    grep_tool(pattern="TODO", glob_filter="*.py")  # Find TODOs in Python files
    grep_tool(pattern="import", output_mode="count")  # Count imports per file"""

MAX_RESULTS = 1000


def _search_file(
    file_path: Path,
    pattern: re.Pattern,
    output_mode: str,
    context_lines: int,
) -> dict | None:
    """Search a single file for the pattern."""
    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
            lines = content.split("\n")
    except Exception:
        return None

    matches = list(pattern.finditer(content))
    if not matches:
        return None

    if output_mode == "count":
        return {"file": file_path, "count": len(matches)}

    if output_mode == "files_with_matches":
        return {"file": file_path}

    # content mode - find matching lines
    matching_lines = set()
    for match in matches:
        # Find line number of match
        line_num = content[: match.start()].count("\n")
        matching_lines.add(line_num)

    # Expand with context
    lines_to_show = set()
    for line_num in matching_lines:
        for i in range(
            max(0, line_num - context_lines),
            min(len(lines), line_num + context_lines + 1),
        ):
            lines_to_show.add(i)

    # Format output
    result_lines = []
    for i in sorted(lines_to_show):
        prefix = ":" if i in matching_lines else "-"
        result_lines.append(f"{i + 1}{prefix}{lines[i]}")

    return {"file": file_path, "lines": result_lines}


def _should_include_file(file_path: Path, glob_filter: str | None) -> bool:
    """Check if file should be included based on glob filter."""
    if not glob_filter:
        return True

    from fnmatch import fnmatch

    filename = file_path.name
    rel_path = str(file_path)

    # Try matching against filename and full path
    return fnmatch(filename, glob_filter) or fnmatch(rel_path, glob_filter)


@tool(args_schema=GrepTool)
def grep_tool(
    pattern: str,
    path: str | None = None,
    glob_filter: str | None = None,
    case_insensitive: bool = False,
    output_mode: Literal["content", "files_with_matches", "count"] = "content",
    context_lines: int = 0,
    multiline: bool = False,
) -> str:
    """Search for a pattern in files."""
    workspace = Path(settings.workspace_path).resolve()

    if path:
        search_path = Path(path)
        if not search_path.is_absolute():
            search_path = workspace / path
        search_path = search_path.resolve()

        if not str(search_path).startswith(str(workspace)):
            return f"Error: Path must be within workspace ({settings.workspace_path})"
    else:
        search_path = workspace

    if not search_path.exists():
        return f"Error: Path not found: {search_path}"

    # Compile regex
    flags = re.MULTILINE if multiline else 0
    if case_insensitive:
        flags |= re.IGNORECASE
    if multiline:
        flags |= re.DOTALL

    try:
        regex = re.compile(pattern, flags)
    except re.error as e:
        return f"Error: Invalid regex pattern: {e}"

    # Collect files to search
    files_to_search = []
    if search_path.is_file():
        files_to_search = [search_path]
    else:
        for dirpath, _, filenames in os.walk(search_path):
            for filename in filenames:
                file_path = Path(dirpath) / filename
                if _should_include_file(file_path, glob_filter):
                    files_to_search.append(file_path)

    if not files_to_search:
        return f"No files to search in: {search_path}"

    # Search files
    results = []
    total_matches = 0

    for file_path in files_to_search:
        result = _search_file(file_path, regex, output_mode, context_lines)
        if result:
            results.append(result)
            if output_mode == "count":
                total_matches += result["count"]
            elif output_mode == "content":
                total_matches += len(result.get("lines", []))
            else:
                total_matches += 1

            if len(results) >= MAX_RESULTS:
                break

    if not results:
        return f"No matches found for pattern: {pattern}"

    # Format output
    output_lines = [f"Found matches in {len(results)} file(s):"]

    for result in results:
        try:
            rel_path = result["file"].relative_to(workspace)
        except ValueError:
            rel_path = result["file"]

        if output_mode == "count":
            output_lines.append(f"{rel_path}: {result['count']} matches")
        elif output_mode == "files_with_matches":
            output_lines.append(str(rel_path))
        else:
            output_lines.append(f"\n{rel_path}:")
            output_lines.extend(f"  {line}" for line in result["lines"])

    if len(results) >= MAX_RESULTS:
        output_lines.append(f"\n... results truncated at {MAX_RESULTS} files")

    return "\n".join(output_lines)


grep_tool.__doc__ = DESCRIPTION
