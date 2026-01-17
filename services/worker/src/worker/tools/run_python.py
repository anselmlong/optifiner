"""Python execution tool for the evolution agent."""

import os
import subprocess
import tempfile
from pathlib import Path

from langchain_core.tools import tool
from pydantic import BaseModel, Field

DEFAULT_TIMEOUT = 60
MAX_OUTPUT_LENGTH = 50000


def _get_workspace_root() -> Path:
    """Get the workspace root from environment or default."""
    return Path(os.environ.get("WORKSPACE_ROOT", "/app"))


class RunPythonInput(BaseModel):
    """Input schema for the run_python tool."""

    code: str = Field(
        description="Python code to execute."
    )
    working_dir: str | None = Field(
        default=None,
        description="Working directory for execution. Defaults to workspace root.",
    )
    timeout: int = Field(
        default=DEFAULT_TIMEOUT,
        description=f"Timeout in seconds. Defaults to {DEFAULT_TIMEOUT}.",
    )


class RunPythonFileInput(BaseModel):
    """Input schema for running a Python file."""

    file_path: str = Field(
        description="Path to the Python file to execute."
    )
    args: list[str] = Field(
        default_factory=list,
        description="Command line arguments to pass to the script.",
    )
    working_dir: str | None = Field(
        default=None,
        description="Working directory for execution. Defaults to workspace root.",
    )
    timeout: int = Field(
        default=DEFAULT_TIMEOUT,
        description=f"Timeout in seconds. Defaults to {DEFAULT_TIMEOUT}.",
    )


def _resolve_path(file_path: str | None) -> Path:
    """Resolve the file path, defaulting to workspace root."""
    workspace = _get_workspace_root()
    if file_path is None:
        return workspace
    path = Path(file_path)
    if not path.is_absolute():
        path = workspace / path
    return path


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


def _execute_python(
    cmd: list[str],
    cwd: Path,
    timeout: int,
) -> str:
    """Execute a Python command and return formatted output."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(cwd),
            env={**os.environ, "WORKSPACE_ROOT": str(_get_workspace_root())},
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
    working_dir: str | None = None,
    timeout: int = DEFAULT_TIMEOUT,
) -> str:
    """Execute Python code.

    Runs Python code in the workspace and returns its output.
    The code is written to a temporary file and executed.

    Args:
        code: Python code to execute.
        working_dir: Working directory. Defaults to workspace root.
        timeout: Timeout in seconds.

    Returns:
        Execution output (stdout + stderr) and exit code.
    """
    cwd = _resolve_path(working_dir)

    if not cwd.exists():
        return f"Error: Working directory not found: {cwd}"

    # Write code to a temporary file
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".py",
            delete=False,
            dir=str(cwd),
        ) as f:
            f.write(code)
            temp_path = f.name
    except Exception as e:
        return f"Error creating temporary file: {e}"

    try:
        cmd = ["python", temp_path]
        return _execute_python(cmd, cwd, timeout)
    finally:
        # Clean up temp file
        try:
            Path(temp_path).unlink()
        except Exception:
            pass


@tool(args_schema=RunPythonFileInput)
def run_python_file(
    file_path: str,
    args: list[str] | None = None,
    working_dir: str | None = None,
    timeout: int = DEFAULT_TIMEOUT,
) -> str:
    """Execute a Python file.

    Runs a Python script file with optional arguments.

    Args:
        file_path: Path to the Python file to execute.
        args: Command line arguments to pass to the script.
        working_dir: Working directory. Defaults to workspace root.
        timeout: Timeout in seconds.

    Returns:
        Execution output (stdout + stderr) and exit code.
    """
    script_path = _resolve_path(file_path)

    if not script_path.exists():
        return f"Error: File not found: {script_path}"

    if not script_path.is_file():
        return f"Error: Path is not a file: {script_path}"

    cwd = _resolve_path(working_dir)
    if not cwd.exists():
        cwd = script_path.parent

    cmd = ["python", str(script_path)]
    if args:
        cmd.extend(args)

    return _execute_python(cmd, cwd, timeout)
