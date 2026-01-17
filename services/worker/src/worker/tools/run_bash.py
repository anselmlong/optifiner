"""Bash execution tool for the evolution agent."""

import os
import subprocess
from pathlib import Path

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from worker.tools.path_utils import resolve_path, virtualize_path, get_workspace_root, sanitize_output

DEFAULT_TIMEOUT = 60
MAX_OUTPUT_LENGTH = 50000


class RunBashInput(BaseModel):
    """Input schema for the run_bash tool."""

    command: str = Field(
        description="The bash command to execute."
    )
    working_dir: str | None = Field(
        default=None,
        description="Working directory for the command. Defaults to workspace root.",
    )
    timeout: int = Field(
        default=DEFAULT_TIMEOUT,
        description=f"Timeout in seconds. Defaults to {DEFAULT_TIMEOUT}.",
    )


def _resolve_path(file_path: str | None) -> Path:
    """Resolve the file path using workspace-aware resolution."""
    return resolve_path(file_path)


def _truncate_output(output: str, max_length: int = MAX_OUTPUT_LENGTH) -> str:
    """Truncate output if too long, keeping head and tail."""
    if len(output) <= max_length:
        return output

    # Keep first and last portions
    head_size = max_length // 2
    tail_size = max_length // 2

    head = output[:head_size]
    tail = output[-tail_size:]
    omitted = len(output) - max_length

    return f"{head}\n\n[... {omitted} characters omitted ...]\n\n{tail}"


@tool(args_schema=RunBashInput)
def run_bash(
    command: str,
    working_dir: str | None = None,
    timeout: int = DEFAULT_TIMEOUT,
) -> str:
    """Execute a bash command.

    Runs a bash command in the workspace and returns its output.
    Commands are executed in a shell with full access to the filesystem.

    Args:
        command: The bash command to execute.
        working_dir: Working directory. Defaults to workspace root.
        timeout: Timeout in seconds.

    Returns:
        Command output (stdout + stderr) and exit code.
    """
    cwd = _resolve_path(working_dir)
    vcwd = virtualize_path(cwd)

    if not cwd.exists():
        return f"Error: Working directory not found: {vcwd}"

    try:
        # Set up environment with virtual root for any scripts that check WORKSPACE_ROOT
        env = {**os.environ, "WORKSPACE_ROOT": str(get_workspace_root())}
        
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(cwd),
            env=env,
        )

        # Combine stdout and stderr
        output_parts = []

        if result.stdout:
            output_parts.append(result.stdout)

        if result.stderr:
            if result.stdout:
                output_parts.append("\n[stderr]:")
            output_parts.append(result.stderr)

        output = "".join(output_parts).strip()
        output = _truncate_output(output)
        
        # Sanitize paths in output to show virtual paths
        output = sanitize_output(output)

        # Add exit code info
        if result.returncode != 0:
            output += f"\n\n[Exit code: {result.returncode}]"
        else:
            if not output:
                output = "[Command completed successfully with no output]"

        return output

    except subprocess.TimeoutExpired:
        return f"Error: Command timed out after {timeout} seconds. Consider increasing timeout or breaking into smaller operations."
    except Exception as e:
        return f"Error executing command: {e}"
