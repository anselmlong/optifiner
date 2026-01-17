"""Bash execution tool for the evolution agent.

Commands are executed from the workspace root (codebase location) as
the working directory.
"""

import os
import subprocess
from pathlib import Path

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from worker.tools.path_utils import get_workspace_root

DEFAULT_TIMEOUT = 60
MAX_OUTPUT_LENGTH = 50000


class RunBashInput(BaseModel):
    """Input schema for the run_bash tool."""

    command: str = Field(
        description="The bash command to execute."
    )
    timeout: int = Field(
        default=DEFAULT_TIMEOUT,
        description=f"Timeout in seconds. Defaults to {DEFAULT_TIMEOUT}.",
    )


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
    timeout: int = DEFAULT_TIMEOUT,
) -> str:
    """Execute a bash command.

    Runs a bash command with the workspace root (codebase location) as
    the working directory. Commands have full access to the workspace
    filesystem.

    Args:
        command: The bash command to execute.
        timeout: Timeout in seconds.

    Returns:
        Command output (stdout + stderr) and exit code.
    """
    workspace_root = get_workspace_root()

    if not workspace_root.exists():
        return f"Error: Workspace root not found: {workspace_root}"

    try:
        # Set up environment with workspace root
        env = {**os.environ, "WORKSPACE_ROOT": str(workspace_root)}
        
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(workspace_root),
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
