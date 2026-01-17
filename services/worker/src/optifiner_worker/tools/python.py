"""Python code execution tool for LangGraph agents."""

import subprocess
import sys
import tempfile
from pathlib import Path

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from optifiner_worker.config import settings


class PythonTool(BaseModel):
    """Input schema for the python tool."""

    code: str = Field(description="Python code to execute")
    working_directory: str | None = Field(
        default=None,
        description="Working directory for execution. Defaults to workspace root.",
    )
    timeout: int = Field(
        default=30,
        description="Timeout in seconds (max 300)",
    )


DESCRIPTION = """Execute Python code directly.

Usage:
- Executes Python code in the workspace environment
- Code runs with access to the workspace at /app
- Default timeout is 30 seconds, max is 300 seconds
- Standard library and installed packages are available
- Use for quick computations, testing snippets, or running scripts

Best practices:
- For running existing Python files, use bash_tool with 'python filename.py'
- For complex scripts, write to a file first then execute
- Print statements will appear in output

Examples:
    python_tool(code="print('Hello, World!')")
    
    python_tool(code='''
import json
data = {"key": "value"}
print(json.dumps(data, indent=2))
''')

    python_tool(code='''
import os
for f in os.listdir('/app'):
    print(f)
''')"""


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


@tool(args_schema=PythonTool)
def python_tool(
    code: str,
    working_directory: str | None = None,
    timeout: int = 30,
) -> str:
    """Execute Python code."""
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

    # Write code to temporary file
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".py",
            delete=False,
            dir=str(cwd),
        ) as f:
            f.write(code)
            temp_file = f.name
    except Exception as e:
        return f"Error creating temporary file: {e}"

    try:
        result = subprocess.run(
            [sys.executable, temp_file],
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=timeout,
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
        return f"Error: Python execution timed out after {timeout} seconds"
    except Exception as e:
        return f"Error executing Python code: {e}"
    finally:
        # Clean up temp file
        try:
            Path(temp_file).unlink()
        except Exception:
            pass


python_tool.__doc__ = DESCRIPTION
