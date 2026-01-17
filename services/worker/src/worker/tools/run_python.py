"""Python execution tool for the evolution agent.

This tool is for executing Python code provided as a string argument.
The code is written to a temporary file in the workspace and executed
from the workspace root as the working directory.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from worker.tools.path_utils import resolve_path, get_workspace_root

DEFAULT_TIMEOUT = 60
MAX_OUTPUT_LENGTH = 50000

# Temp scripts are stored in a dedicated folder within workspace
TEMP_SCRIPTS_DIR = ".optifiner_temp"


class RunPythonInput(BaseModel):
    """Input schema for the run_python tool."""

    code: str = Field(
        description="Python code to execute. The code is written to a temporary script and run."
    )
    timeout: int = Field(
        default=DEFAULT_TIMEOUT,
        description=f"Timeout in seconds. Defaults to {DEFAULT_TIMEOUT}.",
    )


class RunPythonFileInput(BaseModel):
    """Input schema for running a Python file."""

    file_path: str = Field(
        description="Path to the Python file to execute (relative to workspace root or absolute)."
    )
    args: list[str] = Field(
        default_factory=list,
        description="Command line arguments to pass to the script.",
    )
    timeout: int = Field(
        default=DEFAULT_TIMEOUT,
        description=f"Timeout in seconds. Defaults to {DEFAULT_TIMEOUT}.",
    )


def _truncate_output(output: str, max_length: int = MAX_OUTPUT_LENGTH) -> str:
    """Truncate output if too long, keeping head and tail."""
    if len(output) <= max_length:
        return output

    head_size = max_length // 2
    tail_size = max_length // 2

    head = output[:head_size]
    tail = output[-tail_size:]
    omitted = len(output) - max_length

    return f"{head}\n\n[... {omitted} characters omitted ...]\n\n{tail}"


def _get_python_executable() -> str:
    """Get the Python executable to use for running scripts."""
    # First try sys.executable (the current Python interpreter)
    if sys.executable:
        return sys.executable
    # Fallback to python3, then python
    if shutil.which("python3"):
        return "python3"
    if shutil.which("python"):
        return "python"
    # Last resort
    return "python3"


def _get_temp_scripts_dir() -> Path:
    """Get (and create) the temp scripts directory within workspace."""
    workspace_root = get_workspace_root()
    temp_dir = workspace_root / TEMP_SCRIPTS_DIR
    temp_dir.mkdir(parents=True, exist_ok=True)
    return temp_dir


def _execute_python(
    cmd: list[str],
    cwd: Path,
    timeout: int,
) -> str:
    """Execute a Python command and return formatted output."""
    try:
        # Set up environment with workspace root
        env = {**os.environ, "WORKSPACE_ROOT": str(cwd)}
        
        result = subprocess.run(
            cmd,
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

        # Add exit code info for failures
        if result.returncode != 0:
            output += f"\n\n[Exit code: {result.returncode}]"
        else:
            if not output:
                output = "[Code executed successfully with no output]"

        return output

    except subprocess.TimeoutExpired:
        return f"Error: Execution timed out after {timeout} seconds."
    except Exception as e:
        return f"Error executing Python: {e}"


@tool(args_schema=RunPythonInput)
def run_python(
    code: str,
    timeout: int = DEFAULT_TIMEOUT,
) -> str:
    """Execute Python code.

    Runs Python code by writing it to a temporary script file in the workspace
    and executing it. The working directory is always the workspace root
    (the codebase location).

    This tool is for running code snippets, not for running existing files.
    Use run_python_file to run existing Python files.

    Args:
        code: Python code to execute.
        timeout: Timeout in seconds.

    Returns:
        Execution output (stdout + stderr) and exit code.
    """
    workspace_root = get_workspace_root()
    
    if not workspace_root.exists():
        return f"Error: Workspace root not found: {workspace_root}"

    # Write code to a temporary file in the workspace's temp dir
    temp_dir = _get_temp_scripts_dir()
    
    import uuid
    script_name = f"temp_script_{uuid.uuid4().hex[:8]}.py"
    script_path = temp_dir / script_name
    
    try:
        script_path.write_text(code, encoding="utf-8")
    except Exception as e:
        return f"Error creating temporary script: {e}"

    try:
        cmd = [_get_python_executable(), str(script_path)]
        # Always run from workspace root (codebase location)
        return _execute_python(cmd, workspace_root, timeout)
    finally:
        # Clean up temp file
        try:
            script_path.unlink()
        except Exception:
            pass


@tool(args_schema=RunPythonFileInput)
def run_python_file(
    file_path: str,
    args: list[str] | None = None,
    timeout: int = DEFAULT_TIMEOUT,
) -> str:
    """Execute a Python file.

    Runs a Python script file with optional arguments. The working directory
    is always the workspace root (the codebase location).

    Args:
        file_path: Path to the Python file to execute (relative or absolute).
        args: Command line arguments to pass to the script.
        timeout: Timeout in seconds.

    Returns:
        Execution output (stdout + stderr) and exit code.
    """
    script_path = resolve_path(file_path)
    workspace_root = get_workspace_root()

    if not script_path.exists():
        return f"Error: File not found: {script_path}"

    if not script_path.is_file():
        return f"Error: Path is not a file: {script_path}"

    cmd = [_get_python_executable(), str(script_path)]
    if args:
        cmd.extend(args)

    # Always run from workspace root (codebase location)
    return _execute_python(cmd, workspace_root, timeout)
