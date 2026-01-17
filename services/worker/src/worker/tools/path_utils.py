"""Centralized path utilities for all tools.

This module provides workspace-aware path resolution that works with
both isolated workspaces (chroot-like) and direct execution.
"""

import os
from pathlib import Path

# Import workspace management
from worker.workspace import get_workspace, translate_path as _ws_translate, translate_output, VIRTUAL_ROOT


def get_workspace_root() -> Path:
    """Get the workspace root for file operations.
    
    If a workspace manager is active (isolated execution), returns the actual
    filesystem root. Otherwise returns WORKSPACE_ROOT env var or /app.
    """
    ws = get_workspace()
    if ws:
        return ws.actual_root
    return Path(os.environ.get("WORKSPACE_ROOT", VIRTUAL_ROOT))


def resolve_path(file_path: str | None) -> Path:
    """Resolve a file path to the actual filesystem path.
    
    Handles:
    - Absolute paths starting with /app (virtual root)
    - Relative paths (relative to workspace root)
    - Already resolved paths
    
    Args:
        file_path: Path as seen by the agent (may be /app/... or relative).
        
    Returns:
        Actual filesystem path.
    """
    if file_path is None:
        return get_workspace_root()
    
    # Use workspace translation if available
    ws = get_workspace()
    if ws:
        return _ws_translate(file_path)
    
    # No workspace isolation - direct path resolution
    path = Path(file_path)
    if not path.is_absolute():
        path = get_workspace_root() / path
    return path


def virtualize_path(actual_path: str | Path) -> str:
    """Convert an actual filesystem path to a virtual path for agent display.
    
    Args:
        actual_path: The real filesystem path.
        
    Returns:
        The path as the agent should see it (with /app prefix).
    """
    ws = get_workspace()
    if ws:
        return ws.translate_to_virtual(actual_path)
    return str(actual_path)


def sanitize_output(output: str) -> str:
    """Sanitize output to replace actual paths with virtual paths.
    
    Args:
        output: Raw output that may contain actual filesystem paths.
        
    Returns:
        Output with paths translated to virtual paths.
    """
    return translate_output(output)
