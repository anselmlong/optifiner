"""Grep tool for the evolution agent - powerful regex search using ripgrep."""

import subprocess
from pathlib import Path
from typing import Literal

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from worker.tools.path_utils import resolve_path, virtualize_path, get_workspace_root, sanitize_output

MAX_RESULTS = 500


class GrepInput(BaseModel):
    """Input schema for the grep tool."""

    pattern: str = Field(
        description="Regular expression pattern to search for (ripgrep syntax)."
    )
    path: str | None = Field(
        default=None,
        description="File or directory to search in. Defaults to workspace root.",
    )
    glob: str | None = Field(
        default=None,
        description='Glob pattern to filter files (e.g., "*.py", "**/*.ts").',
    )
    file_type: str | None = Field(
        default=None,
        description='File type to search (e.g., "py", "js", "rust"). More efficient than glob for standard types.',
    )
    output_mode: Literal["content", "files_with_matches", "count"] = Field(
        default="files_with_matches",
        description='Output mode: "content" shows matching lines, "files_with_matches" shows file paths, "count" shows match counts.',
    )
    context_lines: int | None = Field(
        default=None,
        description="Number of context lines to show before and after each match (only for content mode).",
    )
    case_insensitive: bool = Field(
        default=False,
        description="If True, search case-insensitively.",
    )
    multiline: bool = Field(
        default=False,
        description="If True, enable multiline mode where . matches newlines and patterns can span lines.",
    )


def _resolve_path(file_path: str | None) -> Path:
    """Resolve the file path using workspace-aware resolution."""
    return resolve_path(file_path)


def _build_rg_command(
    pattern: str,
    path: Path,
    glob: str | None,
    file_type: str | None,
    output_mode: str,
    context_lines: int | None,
    case_insensitive: bool,
    multiline: bool,
) -> list[str]:
    """Build the ripgrep command with appropriate flags."""
    cmd = ["rg", "--color=never", "--no-heading"]

    # Pattern
    cmd.extend(["--regexp", pattern])

    # Output mode
    if output_mode == "files_with_matches":
        cmd.append("--files-with-matches")
    elif output_mode == "count":
        cmd.append("--count")
    else:  # content
        cmd.append("--line-number")
        if context_lines is not None and context_lines > 0:
            cmd.extend(["-C", str(context_lines)])

    # Filters
    if glob:
        cmd.extend(["--glob", glob])

    if file_type:
        cmd.extend(["--type", file_type])

    # Options
    if case_insensitive:
        cmd.append("--ignore-case")

    if multiline:
        cmd.extend(["--multiline", "--multiline-dotall"])

    # Path
    cmd.append(str(path))

    return cmd


@tool(args_schema=GrepInput)
def grep(
    pattern: str,
    path: str | None = None,
    glob: str | None = None,
    file_type: str | None = None,
    output_mode: Literal["content", "files_with_matches", "count"] = "files_with_matches",
    context_lines: int | None = None,
    case_insensitive: bool = False,
    multiline: bool = False,
) -> str:
    """Search for patterns in files using ripgrep.

    A powerful search tool supporting full regex syntax. Use this for finding
    code patterns, function definitions, variable usages, etc.

    Args:
        pattern: Regular expression pattern to search for.
        path: File or directory to search in. Defaults to workspace root.
        glob: Glob pattern to filter files (e.g., "*.py").
        file_type: File type to search (e.g., "py", "js").
        output_mode: "content" (matching lines), "files_with_matches" (paths), or "count".
        context_lines: Lines of context around matches (content mode only).
        case_insensitive: If True, ignore case.
        multiline: If True, allow patterns to span multiple lines.

    Returns:
        Search results or error message.
    """
    search_path = _resolve_path(path)
    vpath = virtualize_path(search_path)

    if not search_path.exists():
        return f"Error: Path not found: {vpath}"

    cmd = _build_rg_command(
        pattern=pattern,
        path=search_path,
        glob=glob,
        file_type=file_type,
        output_mode=output_mode,
        context_lines=context_lines,
        case_insensitive=case_insensitive,
        multiline=multiline,
    )

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
            cwd=str(get_workspace_root()),
        )

        # ripgrep returns 1 for no matches (not an error)
        if result.returncode == 1 and not result.stderr:
            return f"No matches found for pattern: {pattern}"

        if result.returncode != 0 and result.returncode != 1:
            error_msg = result.stderr.strip() if result.stderr else "Unknown error"
            return f"Error running ripgrep: {error_msg}"

        output = result.stdout.strip()

        if not output:
            return f"No matches found for pattern: {pattern}"

        # Sanitize paths in output to show virtual paths
        output = sanitize_output(output)

        # Count and potentially truncate results
        lines = output.split("\n")
        total_lines = len(lines)

        if total_lines > MAX_RESULTS:
            output = "\n".join(lines[:MAX_RESULTS])
            output += f"\n\n[... truncated. Showing {MAX_RESULTS} of at least {total_lines} results. Narrow your search.]"

        return output

    except subprocess.TimeoutExpired:
        return "Error: Search timed out after 30 seconds. Try a more specific pattern or path."
    except FileNotFoundError:
        # ripgrep not available - fall back to Python grep
        return _python_grep(pattern, search_path, case_insensitive)
    except Exception as e:
        return f"Error executing grep: {e}"


def _python_grep(pattern: str, search_path: Path, case_insensitive: bool = False) -> str:
    """Fallback grep implementation using Python re module."""
    import re

    flags = re.IGNORECASE if case_insensitive else 0
    try:
        regex = re.compile(pattern, flags)
    except re.error as e:
        return f"Error: Invalid regex pattern: {e}"

    matches = []

    def search_file(file_path: Path):
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                for line_num, line in enumerate(f, 1):
                    if regex.search(line):
                        virt_path = virtualize_path(file_path)
                        matches.append(f"{virt_path}:{line_num}:{line.rstrip()}")
        except Exception:
            pass

    if search_path.is_file():
        search_file(search_path)
    else:
        for file_path in search_path.rglob("*"):
            if file_path.is_file():
                search_file(file_path)
                if len(matches) >= MAX_RESULTS:
                    break

    if not matches:
        return f"No matches found for pattern: {pattern}"

    return "\n".join(matches[:MAX_RESULTS])
