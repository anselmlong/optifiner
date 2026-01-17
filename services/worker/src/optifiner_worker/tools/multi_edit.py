"""Multi-edit tool for making multiple edits to a single file."""

from pathlib import Path

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from optifiner_worker.config import settings


class EditOperation(BaseModel):
    """A single edit operation."""

    old_string: str = Field(description="The exact string to find and replace")
    new_string: str = Field(description="The string to replace old_string with")
    replace_all: bool = Field(
        default=False,
        description="If True, replace all occurrences of old_string",
    )


class MultiEditTool(BaseModel):
    """Input schema for the multi-edit tool."""

    file_path: str = Field(description="The absolute path to the file to edit")
    edits: list[EditOperation] = Field(
        description="List of edit operations to perform in sequence"
    )


DESCRIPTION = """Makes multiple edits to a single file in one operation.

Usage:
- Use read_tool first to understand the file content
- All edits are applied in sequence, in the order provided
- Each edit operates on the result of the previous edit
- All edits must be valid for the operation to succeed - if any edit fails, none will be applied
- This tool is ideal when you need to make several changes to different parts of the same file

For each edit:
- old_string: The exact text to replace (must match exactly including whitespace)
- new_string: The replacement text
- replace_all: If True, replace all occurrences; if False, old_string must be unique

Example:
    multi_edit_tool(
        file_path="/app/main.py",
        edits=[
            {"old_string": "import os", "new_string": "import os\\nimport sys"},
            {"old_string": "def main():", "new_string": "def main() -> None:"},
        ]
    )

WARNING:
- Plan edits carefully to avoid conflicts between sequential operations
- Earlier edits may affect text that later edits are trying to find"""


@tool(args_schema=MultiEditTool)
def multi_edit_tool(file_path: str, edits: list[dict]) -> str:
    """Apply multiple edits to a file in sequence."""
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
        # Allow creating new file if first edit has empty old_string
        if edits and edits[0].get("old_string", "") == "":
            try:
                path.parent.mkdir(parents=True, exist_ok=True)
                content = edits[0].get("new_string", "")
                remaining_edits = edits[1:]
            except Exception as e:
                return f"Error creating file: {e}"
        else:
            return f"Error: File not found: {file_path}"
    else:
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            remaining_edits = edits
        except Exception as e:
            return f"Error reading file: {e}"

    # Validate and apply all edits
    results = []
    for i, edit in enumerate(remaining_edits):
        old_string = edit.get("old_string", "")
        new_string = edit.get("new_string", "")
        replace_all = edit.get("replace_all", False)

        if old_string == new_string:
            return f"Error in edit {i + 1}: old_string and new_string must be different"

        count = content.count(old_string)

        if count == 0:
            return f"Error in edit {i + 1}: old_string not found in file (after applying previous edits). Make sure it matches exactly."

        if count > 1 and not replace_all:
            return f"Error in edit {i + 1}: old_string found {count} times. Provide more context or set replace_all=True."

        # Apply edit
        if replace_all:
            content = content.replace(old_string, new_string)
            results.append(f"Edit {i + 1}: Replaced {count} occurrence(s)")
        else:
            content = content.replace(old_string, new_string, 1)
            results.append(f"Edit {i + 1}: Replaced 1 occurrence")

    # Write the final content
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
    except Exception as e:
        return f"Error writing file: {e}"

    return f"Successfully applied {len(edits)} edit(s) to {file_path}:\n" + "\n".join(results)


multi_edit_tool.__doc__ = DESCRIPTION
