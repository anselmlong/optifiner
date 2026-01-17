"""File edit tool for the evolution agent - performs exact string replacements."""

from difflib import SequenceMatcher
from pathlib import Path

from langchain_core.tools import tool
from pydantic import AliasChoices, BaseModel, Field

from worker.tools.path_utils import resolve_path, virtualize_path


class EditFileInput(BaseModel):
    """Input schema for the edit_file tool."""

    file_path: str = Field(
        description="The path to the file to edit. Can be absolute or relative to workspace root.",
        validation_alias=AliasChoices("file_path", "path"),
    )
    old_string: str = Field(
        description="The exact text to find and replace. Must match the file content exactly, including whitespace and indentation."
    )
    new_string: str = Field(description="The text to replace old_string with.")
    replace_all: bool = Field(
        default=False,
        description="If True, replace all occurrences of old_string. If False (default), only replace the first occurrence and fail if not unique.",
    )


def _resolve_path(file_path: str) -> Path:
    """Resolve the file path using workspace-aware resolution."""
    return resolve_path(file_path)


def _find_similar_content(content: str, old_string: str, max_suggestions: int = 3) -> list[tuple[int, str, float]]:
    """Find content in the file that's similar to old_string.
    
    Returns list of (line_number, line_content, similarity_score) tuples.
    """
    lines = content.split('\n')
    old_lines = old_string.split('\n')
    old_first_line = old_lines[0].strip()
    
    if not old_first_line:
        return []
    
    suggestions = []
    
    for i, line in enumerate(lines):
        line_stripped = line.strip()
        if not line_stripped:
            continue
        
        # Calculate similarity using SequenceMatcher
        similarity = SequenceMatcher(None, old_first_line.lower(), line_stripped.lower()).ratio()
        
        # Also check for substring containment
        if old_first_line[:30].lower() in line_stripped.lower():
            similarity = max(similarity, 0.7)
        if line_stripped[:30].lower() in old_first_line.lower():
            similarity = max(similarity, 0.6)
        
        if similarity >= 0.5:  # At least 50% similar
            suggestions.append((i + 1, line[:100], similarity))
    
    # Sort by similarity descending and return top matches
    suggestions.sort(key=lambda x: -x[2])
    return suggestions[:max_suggestions]


def _find_edit_context(content: str, old_string: str) -> dict:
    """Find context about where an edit string might match.
    
    Returns a dict with:
    - found: bool - whether exact match was found
    - line: int - line number if found
    - count: int - number of occurrences if found
    - similar: list - similar content suggestions if not found
    - whitespace_issue: bool - if the content exists with different whitespace
    """
    result = {
        "found": False,
        "line": None,
        "count": 0,
        "similar": [],
        "whitespace_issue": False,
    }
    
    if old_string in content:
        idx = content.index(old_string)
        line_num = content[:idx].count('\n') + 1
        result["found"] = True
        result["line"] = line_num
        result["count"] = content.count(old_string)
        return result
    
    # Check if it's a whitespace issue
    old_stripped = old_string.strip()
    if old_stripped and old_stripped in content:
        result["whitespace_issue"] = True
    
    # Find similar content
    result["similar"] = _find_similar_content(content, old_string)
    
    return result


def _format_edit_error(vpath: str, context: dict, old_string: str) -> str:
    """Format a helpful error message when edit fails."""
    if context["whitespace_issue"]:
        return (
            f"Error: old_string not found in {vpath}. "
            f"The text exists with DIFFERENT WHITESPACE - check indentation and line endings.\n\n"
            f"Tip: Use read_file to see the exact content, paying attention to spaces vs tabs and line breaks."
        )
    
    if context["similar"]:
        suggestions = "\n".join(
            f"  Line {num}: {line}{'...' if len(line) >= 100 else ''} (similarity: {sim:.0%})"
            for num, line, sim in context["similar"]
        )
        
        # Show what the agent was looking for
        old_preview = old_string[:100].replace('\n', '\\n')
        if len(old_string) > 100:
            old_preview += "..."
        
        return (
            f"Error: old_string not found in {vpath}.\n\n"
            f"You searched for:\n  \"{old_preview}\"\n\n"
            f"Similar content found at:\n{suggestions}\n\n"
            f"Tip: Use read_file to see the exact content around these lines, "
            f"then use that exact text (including whitespace) in old_string."
        )
    
    return (
        f"Error: old_string not found in {vpath}. "
        f"The content doesn't appear to exist in this file.\n\n"
        f"Tip: Use read_file to verify the file contents before editing."
    )


@tool(args_schema=EditFileInput)
def edit_file(
    file_path: str, old_string: str, new_string: str, replace_all: bool = False
) -> str:
    """Perform exact string replacement in a file.

    Finds and replaces text in a file. The old_string must match exactly,
    including all whitespace and indentation.

    Args:
        file_path: Path to the file to edit.
        old_string: The exact text to find and replace.
        new_string: The text to replace old_string with.
        replace_all: If True, replace all occurrences. If False, require unique match.

    Returns:
        Success message with details, or error description.
    """
    path = _resolve_path(file_path)

    vpath = virtualize_path(path)
    
    if not path.exists():
        return f"Error: File not found: {vpath}"

    if not path.is_file():
        return f"Error: Path is not a file: {vpath}"

    if old_string == new_string:
        return "Error: old_string and new_string are identical. No changes needed."

    try:
        # Read current content
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        # Use pre-edit validation to find context
        edit_context = _find_edit_context(content, old_string)

        if not edit_context["found"]:
            # Provide helpful error with suggestions
            return _format_edit_error(vpath, edit_context, old_string)

        count = edit_context["count"]

        if count > 1 and not replace_all:
            # Show where the duplicates are
            lines_with_match = []
            search_pos = 0
            for _ in range(min(count, 5)):  # Show up to 5 locations
                idx = content.find(old_string, search_pos)
                if idx == -1:
                    break
                line_num = content[:idx].count('\n') + 1
                lines_with_match.append(str(line_num))
                search_pos = idx + 1
            
            locations = ", ".join(lines_with_match)
            if count > 5:
                locations += f", ... ({count - 5} more)"
            
            return (
                f"Error: old_string found {count} times in {vpath} (lines: {locations}). "
                f"Use replace_all=True to replace all occurrences, or provide more surrounding "
                f"context to make the match unique."
            )

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

        # Calculate line changes for feedback
        old_lines = old_string.count("\n") + 1
        new_lines = new_string.count("\n") + 1
        line_diff = new_lines - old_lines

        diff_msg = ""
        if line_diff > 0:
            diff_msg = f" (+{line_diff} lines)"
        elif line_diff < 0:
            diff_msg = f" ({line_diff} lines)"

        if replace_all and replaced_count > 1:
            return f"Successfully replaced {replaced_count} occurrences in {vpath}{diff_msg}"
        return f"Successfully edited {vpath}{diff_msg}"

    except PermissionError:
        return f"Error: Permission denied: {vpath}"
    except UnicodeDecodeError:
        return f"Error: Cannot edit binary file: {vpath}"
    except Exception as e:
        return f"Error editing file {vpath}: {e}"
