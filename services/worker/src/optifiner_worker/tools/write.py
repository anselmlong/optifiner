"""File writing tool for LangGraph agents."""

import os
from pathlib import Path

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from optifiner_worker.config import settings


class WriteTool(BaseModel):
    """Input schema for the write file tool."""

    file_path: str = Field(description="The absolute path to the file to write")
    content: str = Field(description="The content to write to the file")


DESCRIPTION = """Writes a file to the local filesystem.

Usage:
- This tool will overwrite the existing file if there is one at the provided path
- For existing files, it's recommended to use the read_tool first to understand current content
- Parent directories will be created automatically if they don't exist
- Use edit_tool for making targeted changes to existing files instead of full rewrites"""


@tool(args_schema=WriteTool)
def write_tool(file_path: str, content: str) -> str:
    """Write content to a file."""
    path = Path(file_path)

    # Ensure path is within workspace
    try:
        workspace = Path(settings.workspace_path).resolve()
        resolved_path = path.resolve() if path.exists() else (workspace / path).resolve()
        if not str(resolved_path).startswith(str(workspace)):
            return f"Error: Path must be within workspace ({settings.workspace_path})"
    except Exception as e:
        return f"Error resolving path: {e}"

    try:
        # Create parent directories if needed
        path.parent.mkdir(parents=True, exist_ok=True)

        # Write the file
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

        # Get file stats
        stat = os.stat(path)
        line_count = content.count("\n") + (1 if content and not content.endswith("\n") else 0)

        return f"Successfully wrote {stat.st_size} bytes ({line_count} lines) to {file_path}"

    except PermissionError:
        return f"Error: Permission denied writing to file: {file_path}"
    except Exception as e:
        return f"Error writing file: {e}"


write_tool.__doc__ = DESCRIPTION
