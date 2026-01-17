"""File reading tool for LangGraph agents."""

import base64
import mimetypes
from pathlib import Path
from typing import Literal

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from optifiner_worker.config import settings


class ReadTool(BaseModel):
    """Input schema for the read file tool."""

    file_path: str = Field(description="The absolute path to the file to read")
    offset: int | None = Field(
        default=None,
        description="Line number to start reading from (1-indexed). If not provided, reads from the beginning.",
    )
    limit: int | None = Field(
        default=None,
        description="Maximum number of lines to read. If not provided, reads up to max_file_lines.",
    )


DESCRIPTION = f"""Reads a file from the local filesystem.

Usage:
- The file_path parameter must be an absolute path, not a relative path
- By default, it reads up to {settings.max_file_lines} lines starting from the beginning of the file
- You can optionally specify a line offset and limit (especially handy for long files)
- Any lines longer than {settings.max_line_length} characters will be truncated
- Results are returned with line numbers starting at 1 (format: LINE_NUMBER|LINE_CONTENT)
- This tool can read images (PNG, JPG, etc) and returns base64 encoded content
- You can call this tool multiple times in parallel to read multiple files
- If a file exists but is empty, you will receive a notification"""


def _is_image_file(file_path: Path) -> bool:
    """Check if a file is an image based on its mimetype."""
    mime_type, _ = mimetypes.guess_type(str(file_path))
    return mime_type is not None and mime_type.startswith("image/")


def _read_image_file(file_path: Path) -> str:
    """Read an image file and return base64 encoded content."""
    mime_type, _ = mimetypes.guess_type(str(file_path))
    with open(file_path, "rb") as f:
        content = base64.b64encode(f.read()).decode("utf-8")
    return f"[Image file: {mime_type}]\nBase64 content: {content}"


def _read_text_file(
    file_path: Path,
    offset: int | None = None,
    limit: int | None = None,
) -> str:
    """Read a text file with optional offset and limit."""
    max_lines = limit or settings.max_file_lines
    start_line = (offset or 1) - 1  # Convert to 0-indexed

    lines = []
    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            for i, line in enumerate(f):
                if i < start_line:
                    continue
                if len(lines) >= max_lines:
                    break

                # Truncate long lines
                if len(line) > settings.max_line_length:
                    line = line[: settings.max_line_length] + "...[truncated]\n"

                # Format with line numbers (right-aligned to 6 chars)
                line_num = i + 1
                lines.append(f"{line_num:>6}|{line.rstrip()}")

    except UnicodeDecodeError:
        return f"Error: Unable to read file as text. File may be binary: {file_path}"

    if not lines:
        return "File is empty."

    return "\n".join(lines)


@tool(args_schema=ReadTool)
def read_tool(
    file_path: str,
    offset: int | None = None,
    limit: int | None = None,
) -> str:
    """Read a file from the filesystem."""
    path = Path(file_path)

    # Ensure path is within workspace
    try:
        workspace = Path(settings.workspace_path).resolve()
        resolved_path = path.resolve()
        if not str(resolved_path).startswith(str(workspace)):
            return f"Error: Path must be within workspace ({settings.workspace_path})"
    except Exception as e:
        return f"Error resolving path: {e}"

    if not path.exists():
        return f"Error: File not found: {file_path}"

    if path.is_dir():
        return f"Error: Path is a directory, not a file. Use ls_tool to list directory contents: {file_path}"

    try:
        if _is_image_file(path):
            return _read_image_file(path)
        return _read_text_file(path, offset, limit)
    except PermissionError:
        return f"Error: Permission denied reading file: {file_path}"
    except Exception as e:
        return f"Error reading file: {e}"


read_tool.__doc__ = DESCRIPTION
