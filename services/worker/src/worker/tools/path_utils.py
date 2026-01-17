"""Centralized path utilities for all tools.

This module provides workspace-aware path resolution. All tools should use
these functions for path operations to ensure consistent behavior.

The workspace root is determined in this order:
1. Thread-local workspace (set via workspace.set_workspace())
2. WORKSPACE_ROOT environment variable  
3. Current working directory

The benchmark script is always at: <workspace_root>/optifiner_benchmark.py
"""

import os
from pathlib import Path

from worker.workspace import (
    get_workspace,
    get_workspace_root as ws_get_root,
    resolve_path as ws_resolve,
    get_benchmark_path as ws_get_benchmark,
    BENCHMARK_SCRIPT_NAME,
)


def get_workspace_root() -> Path:
    """Get the workspace root for file operations.
    
    Returns the actual workspace root path based on context:
    - If a WorkspaceManager is set for this thread, returns its root
    - Otherwise checks WORKSPACE_ROOT env var
    - Falls back to cwd
    
    Returns:
        Path to the workspace root directory.
    """
    return ws_get_root()


def resolve_path(file_path: str | None) -> Path:
    """Resolve a file path within the workspace.
    
    Handles:
    - None: returns workspace root
    - Absolute paths: validated to be within workspace (if managed)
    - Relative paths: resolved relative to workspace root
    
    Args:
        file_path: Path to resolve. None returns workspace root.
        
    Returns:
        Resolved absolute filesystem path.
    """
    if file_path is None:
        return get_workspace_root()
    
    return ws_resolve(file_path)


def is_safe_path(path: str | Path) -> bool:
    """Check if a path is safe (within workspace bounds).
    
    Args:
        path: Path to check.
        
    Returns:
        True if path is within the workspace (or no workspace is active).
    """
    ws = get_workspace()
    if ws:
        return ws.is_within_workspace(path)
    
    # No workspace isolation - allow any path (direct execution mode)
    return True


def get_benchmark_script_path() -> Path:
    """Get the standard benchmark script path.
    
    The benchmark is always at: <workspace_root>/optifiner_benchmark.py
    
    Returns:
        Path to the benchmark script.
    """
    return ws_get_benchmark()


def virtualize_path(actual_path: str | Path) -> str:
    """Convert a path to string for display.
    
    In the current architecture, we use real paths (no emulation).
    This function just converts to string for consistency.
    
    Args:
        actual_path: The filesystem path.
        
    Returns:
        The path as a string.
    """
    return str(actual_path)


def sanitize_output(output: str) -> str:
    """Sanitize output for display.
    
    In the current architecture, we use real paths (no emulation).
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
