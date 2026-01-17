"""Bash command execution tool for LangGraph agents."""

import asyncio
import os
import subprocess
from pathlib import Path

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from optifiner_worker.config import settings


class BashTool(BaseModel):
    """Input schema for the bash tool."""

    command: str = Field(description="The bash command to execute")
    working_directory: str | None = Field(
        default=None,
        description="Working directory for the command. Defaults to workspace root.",
    )
    timeout: int = Field(
        default=30,
        description="Timeout in seconds (max 300)",
    )


DESCRIPTION = """Execute bash commands in the workspace.

Usage:
- Commands run in a sandboxed container environment
- Default timeout is 30 seconds, max is 300 seconds
- Working directory defaults to workspace root (/app)
- Commands have access to standard Unix utilities
- Long-running commands should be avoided

Best practices:
- Use specific tools (read_tool, glob_tool, grep_tool) instead of cat, find, grep when possible
- For file operations, prefer the dedicated file tools
- Use this for git commands, package management, build tools, etc.

Examples:
    bash_tool(command="git status")
    bash_tool(command="pip install -r requirements.txt", timeout=120)
    bash_tool(command="python -m pytest tests/", working_directory="/app")
    bash_tool(command="ls -la")"""


def _truncate_output(output: str, max_size: int = None) -> str:
    """Truncate output if too long."""
    max_size = max_size or settings.max_output_size
    if len(output) <= max_size:
        return output

    half = max_size // 2
    return (
        output[:half]
        + f"\n\n... [{len(output) - max_size} characters truncated] ...\n\n"
        + output[-half:]
    )


@tool(args_schema=BashTool)
def bash_tool(
    command: str,
    working_directory: str | None = None,
    timeout: int = 30,
) -> str:
    """Execute a bash command."""
    workspace = Path(settings.workspace_path).resolve()

    # Determine working directory
    if working_directory:
        cwd = Path(working_directory)
        if not cwd.is_absolute():
            cwd = workspace / working_directory
        cwd = cwd.resolve()

        if not str(cwd).startswith(str(workspace)):
            return f"Error: Working directory must be within workspace ({settings.workspace_path})"

        if not cwd.exists():
            return f"Error: Working directory not found: {working_directory}"
    else:
        cwd = workspace

    # Limit timeout
    timeout = min(timeout, 300)

    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=timeout,
            env={**os.environ, "HOME": str(workspace), "PWD": str(cwd)},
        )

        output_parts = []

        if result.stdout:
            output_parts.append(f"stdout:\n{result.stdout}")

        if result.stderr:
            output_parts.append(f"stderr:\n{result.stderr}")

        if not output_parts:
            output_parts.append("(no output)")

        output = "\n\n".join(output_parts)
        output = _truncate_output(output)

        exit_info = f"Exit code: {result.returncode}"

        return f"{exit_info}\n\n{output}"

    except subprocess.TimeoutExpired:
        return f"Error: Command timed out after {timeout} seconds"
    except Exception as e:
        return f"Error executing command: {e}"


bash_tool.__doc__ = DESCRIPTION
