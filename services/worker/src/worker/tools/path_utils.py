"""Centralized path utilities for all tools.

This module provides workspace-aware path resolution. Agents work with
real filesystem paths (no emulation).
"""

import os
from pathlib import Path

from worker.workspace import (
    get_workspace,
    get_workspace_root as _ws_get_root,
    resolve_path as _ws_resolve,
    get_benchmark_path,
    BENCHMARK_SCRIPT_NAME,
)


def get_workspace_root() -> Path:
    """Get the workspace root for file operations.
    
    Returns the actual workspace root path. No emulation.
    """
    return _ws_get_root()


def resolve_path(file_path: str | None) -> Path:
    """Resolve a file path within the workspace.
    
    Handles:
    - Absolute paths (checked to be within workspace)
    - Relative paths (relative to workspace root)
    
    Args:
        file_path: Path to resolve. None returns workspace root.
        
    Returns:
        Resolved absolute filesystem path.
    """
    if file_path is None:
        return get_workspace_root()
    
    return _ws_resolve(file_path)


def is_safe_path(path: str | Path) -> bool:
    """Check if a path is safe (within workspace bounds).
    
    Args:
        path: Path to check.
        
    Returns:
        True if path is within the workspace.
    """
    ws = get_workspace()
    if ws:
        return ws.is_within_workspace(path)
    
    # No workspace - allow any path (direct execution mode)
    return True


def get_benchmark_script_path() -> Path:
    """Get the standard benchmark script path.
    
    The benchmark is always at: <workspace_root>/optifiner_benchmark.py
    
    Returns:
        Path to the benchmark script.
    """
    return get_benchmark_path()


def virtualize_path(actual_path: str | Path) -> str:
    """Convert a path to string for display.
    
    In the new architecture, we use real paths (no emulation).
    This function just converts to string for consistency.
    
    Args:
        actual_path: The filesystem path.
        
    Returns:
        The path as a string.
    """
    return str(actual_path)


def sanitize_output(output: str) -> str:
    """Sanitize output for display.
    
    In the new architecture, we use real paths (no emulation).
    This function passes through unchanged.
    
    Args:
        output: Raw output.
        
    Returns:
        Output unchanged.
    """
    return output


__all__ = [
    "get_workspace_root",
    "resolve_path",
    "is_safe_path",
    "get_benchmark_script_path",
    "virtualize_path",
    "sanitize_output",
    "BENCHMARK_SCRIPT_NAME",
]
