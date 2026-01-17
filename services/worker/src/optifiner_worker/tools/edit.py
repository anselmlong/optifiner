"""File editing tool with string replacement for LangGraph agents."""

from pathlib import Path

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from optifiner_worker.config import settings


class EditTool(BaseModel):
    """Input schema for the edit file tool."""

    file_path: str = Field(description="The absolute path to the file to edit")
    old_string: str = Field(description="The exact string to find and replace")
    new_string: str = Field(description="The string to replace old_string with")
    replace_all: bool = Field(
        default=False,
        description="If True, replace all occurrences of old_string. If False, old_string must be unique.",
    )


DESCRIPTION = """Performs exact string replacements in files.

Usage:
- Use the read_tool first to understand the file content before editing
- Preserve exact indentation (tabs/spaces) as it appears in the file
- The edit will FAIL if old_string is not unique in the file (unless replace_all=True)
- Provide a larger string with more surrounding context to make old_string unique
- Use replace_all=True for replacing/renaming strings across the entire file (e.g., renaming a variable)
- old_string and new_string must be different

Example:
    edit_tool(
        file_path="/app/main.py",
        old_string="def old_function():\\n    return 1",
        new_string="def old_function():\\n    return 2"
    )"""


@tool(args_schema=EditTool)
def edit_tool(
    file_path: str,
    old_string: str,
    new_string: str,
    replace_all: bool = False,
) -> str:
    """Edit a file by replacing old_string with new_string."""
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
        return f"Error: Path is a directory, not a file: {file_path}"

    if old_string == new_string:
        return "Error: old_string and new_string must be different"

    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        # Check for occurrences
        count = content.count(old_string)

        if count == 0:
            return f"Error: old_string not found in file. Make sure it matches exactly including whitespace and indentation."

        if count > 1 and not replace_all:
            return f"Error: old_string found {count} times in file. Either provide more context to make it unique, or set replace_all=True."

        # Perform replacement
        if replace_all:
            new_content = content.replace(old_string, new_string)
            replaced_count = count
        else:
            new_content = content.replace(old_string, new_string, 1)
            replaced_count = 1

        # Write back
        with open(path, "w", encoding="utf-8") as f:
            f.write(new_content)

        return f"Successfully replaced {replaced_count} occurrence(s) in {file_path}"

    except PermissionError:
        return f"Error: Permission denied editing file: {file_path}"
    except UnicodeDecodeError:
        return f"Error: File appears to be binary and cannot be edited as text: {file_path}"
    except Exception as e:
        return f"Error editing file: {e}"


edit_tool.__doc__ = DESCRIPTION
