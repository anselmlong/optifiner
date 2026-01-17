"""File read tool for the evolution agent."""

import base64
import mimetypes
from pathlib import Path

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from worker.tools.path_utils import resolve_path, virtualize_path, sanitize_output

MAX_LINES_TO_READ = 2000
MAX_LINE_LENGTH = 2000

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".svg"}


class ReadFileInput(BaseModel):
    """Input schema for the read_file tool."""

    file_path: str = Field(
        description="The path to the file to read. Can be absolute or relative to workspace root."
    )
    offset: int | None = Field(
        default=None,
        description="Line number to start reading from (1-indexed). If not provided, starts from the beginning.",
    )
    limit: int | None = Field(
        default=None,
        description=f"Maximum number of lines to read. Defaults to {MAX_LINES_TO_READ}.",
    )


def _resolve_path(file_path: str) -> Path:
    """Resolve the file path using workspace-aware resolution."""
    return resolve_path(file_path)


def _is_image_file(path: Path) -> bool:
    """Check if the file is an image based on extension."""
    return path.suffix.lower() in IMAGE_EXTENSIONS


def _read_image(path: Path) -> str:
    """Read an image file and return base64 encoded content."""
    mime_type, _ = mimetypes.guess_type(str(path))
    if mime_type is None:
        mime_type = "application/octet-stream"

    with open(path, "rb") as f:
        content = base64.b64encode(f.read()).decode("utf-8")

    return f"[Image file: {path.name}]\nMIME type: {mime_type}\nBase64 content:\n{content}"


def _read_text_file(path: Path, offset: int | None, limit: int | None) -> str:
    """Read a text file with optional offset and limit."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except UnicodeDecodeError:
        # Try with latin-1 as fallback
        with open(path, "r", encoding="latin-1") as f:
            lines = f.readlines()

    if not lines:
        return "File is empty."

    total_lines = len(lines)

    # Apply offset (1-indexed)
    start_idx = 0
    if offset is not None:
        start_idx = max(0, offset - 1)

    # Apply limit
    max_lines = limit if limit is not None else MAX_LINES_TO_READ
    end_idx = min(start_idx + max_lines, total_lines)

    # Format output with line numbers (cat -n style)
    result_lines = []
    for i in range(start_idx, end_idx):
        line_num = i + 1
        line_content = lines[i].rstrip("\n\r")

        # Truncate long lines
        if len(line_content) > MAX_LINE_LENGTH:
            line_content = line_content[:MAX_LINE_LENGTH] + "..."

        # Right-align line number to 6 characters
        result_lines.append(f"{line_num:6}|{line_content}")

    # Add metadata if truncated
    result = "\n".join(result_lines)
    if end_idx < total_lines:
        remaining = total_lines - end_idx
        result += f"\n\n[... {remaining} more lines. Use offset={end_idx + 1} to continue reading.]"

    return result


def _read_notebook(path: Path) -> str:
    """Read a Jupyter notebook and return formatted content."""
    import json

    with open(path, "r", encoding="utf-8") as f:
        notebook = json.load(f)

    cells = notebook.get("cells", [])
    result_parts = []

    for i, cell in enumerate(cells):
        cell_type = cell.get("cell_type", "unknown")
        source = "".join(cell.get("source", []))

        result_parts.append(f"--- Cell {i + 1} [{cell_type}] ---")
        result_parts.append(source)

        # Include outputs for code cells
        if cell_type == "code":
            outputs = cell.get("outputs", [])
            for output in outputs:
                output_type = output.get("output_type", "")
                if output_type == "stream":
                    text = "".join(output.get("text", []))
                    result_parts.append(f"[Output: {output.get('name', 'stdout')}]\n{text}")
                elif output_type in ("execute_result", "display_data"):
                    data = output.get("data", {})
                    if "text/plain" in data:
                        text = "".join(data["text/plain"])
                        result_parts.append(f"[Output]\n{text}")
                elif output_type == "error":
                    ename = output.get("ename", "Error")
                    evalue = output.get("evalue", "")
                    result_parts.append(f"[Error: {ename}] {evalue}")

        result_parts.append("")

    return "\n".join(result_parts)


@tool(args_schema=ReadFileInput)
def read_file(file_path: str, offset: int | None = None, limit: int | None = None) -> str:
    """Read a file from the filesystem.

    Reads a file and returns its contents with line numbers. Supports text files,
    images (returns base64), and Jupyter notebooks.

    Args:
        file_path: Path to the file to read. Can be absolute or relative to workspace.
        offset: Line number to start reading from (1-indexed).
        limit: Maximum number of lines to read.

    Returns:
        File contents with line numbers, or error message if file cannot be read.
    """
    path = _resolve_path(file_path)

    if not path.exists():
        return f"Error: File not found: {virtualize_path(path)}"

    if not path.is_file():
        return f"Error: Path is not a file: {virtualize_path(path)}. Use list_dir to view directory contents."

    try:
        # Handle images
        if _is_image_file(path):
            return _read_image(path)

        # Handle Jupyter notebooks
        if path.suffix.lower() == ".ipynb":
            return _read_notebook(path)

        # Handle regular text files
        return _read_text_file(path, offset, limit)

    except PermissionError:
        return f"Error: Permission denied: {virtualize_path(path)}"
    except Exception as e:
        return f"Error reading file {virtualize_path(path)}: {e}"
