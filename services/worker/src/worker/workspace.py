"""Workspace isolation for running agents on host machine.

This module provides isolated workspace copies for agents:
- Each workspace is at /tmp/optifiner_workspaces/ws_<uuid>/
- Agents see and work with real paths (no emulation)
- All file operations are confined to the workspace for safety

The benchmark script is always at: <workspace_root>/optifiner_benchmark.py
"""

import os
import shutil
import threading
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

# Base directory for workspace copies
WORKSPACE_BASE = Path("/tmp/optifiner_workspaces")

# Standard benchmark script filename (always at workspace root)
BENCHMARK_SCRIPT_NAME = "optifiner_benchmark.py"

# Thread-local workspace context for tools
# Using threading.local() ensures each thread (agent) has its own workspace context
# This prevents race conditions when running multiple agents in parallel
_thread_local = threading.local()


class WorkspaceManager:
    """Manages isolated workspace copies.
    
    Agents work in real paths at /tmp/optifiner_workspaces/ws_<uuid>/.
    No path emulation - agents see the actual filesystem paths.
    """
    
    def __init__(self, workspace_id: str | None = None):
        """Initialize workspace manager.
        
        Args:
            workspace_id: Optional ID for the workspace. If not provided, generates UUID.
        """
        self.workspace_id = workspace_id or str(uuid.uuid4())[:8]
        self._workspace_root: Path | None = None
        self._source_path: Path | None = None
        
    @property
    def workspace_root(self) -> Path:
        """Get the workspace root path (actual filesystem path)."""
        if self._workspace_root is None:
            raise RuntimeError("Workspace not initialized. Call setup() first.")
        return self._workspace_root
    
    # Alias for backwards compatibility
    @property 
    def actual_root(self) -> Path:
        """Alias for workspace_root (backwards compatibility)."""
        return self.workspace_root
    
    @property
    def benchmark_path(self) -> Path:
        """Get the standard benchmark script path."""
        return self.workspace_root / BENCHMARK_SCRIPT_NAME
    
    def setup(self, source_path: str | Path) -> Path:
        """Set up the isolated workspace by copying source.
        
        Args:
            source_path: Path to the source codebase to copy.
            
        Returns:
            The workspace root path.
        """
        source = Path(source_path).resolve()
        if not source.exists():
            raise ValueError(f"Source path does not exist: {source}")
        
        self._source_path = source
        
        # Create workspace directory structure
        WORKSPACE_BASE.mkdir(parents=True, exist_ok=True)
        
        # Workspace is directly at /tmp/optifiner_workspaces/ws_<id>/
        self._workspace_root = WORKSPACE_BASE / f"ws_{self.workspace_id}"
        
        # Clean up if exists
        if self._workspace_root.exists():
            shutil.rmtree(self._workspace_root)
        
        # Copy source to workspace
        shutil.copytree(source, self._workspace_root, symlinks=True)
        
        return self._workspace_root
    
    def cleanup(self):
        """Remove the isolated workspace."""
        if self._workspace_root and self._workspace_root.exists():
            try:
                shutil.rmtree(self._workspace_root)
            except Exception:
                pass
    
    def resolve_path(self, path: str | Path) -> Path:
        """Resolve a path within the workspace.
        
        Args:
            path: Relative or absolute path.
            
        Returns:
            Absolute path within the workspace.
            
        Raises:
            ValueError: If path attempts to escape workspace.
        """
        if self._workspace_root is None:
            raise RuntimeError("Workspace not initialized. Call setup() first.")
        
        p = Path(path)
        
        # If already within workspace, return resolved
        if p.is_absolute():
            try:
                p.resolve().relative_to(self._workspace_root.resolve())
                return p.resolve()
            except ValueError:
                # Absolute path outside workspace - confine it
                # Use just the last component for safety
                return self._workspace_root / p.name
        
        # Relative path - resolve relative to workspace root
        resolved = (self._workspace_root / p).resolve()
        
        # Security check: ensure result is within workspace
        try:
            resolved.relative_to(self._workspace_root.resolve())
        except ValueError:
            raise ValueError(f"Path escapes workspace: {path}")
        
        return resolved
    
    def is_within_workspace(self, path: str | Path) -> bool:
        """Check if a path is within the workspace."""
        if self._workspace_root is None:
            return False
        try:
            Path(path).resolve().relative_to(self._workspace_root.resolve())
            return True
        except ValueError:
            return False
    
    def copy_back_changes(self, target_path: str | Path | None = None) -> list[str]:
        """Copy changes from isolated workspace back to source.
        
        Args:
            target_path: Where to copy changes. Defaults to original source.
            
        Returns:
            List of files that were modified.
        """
        if self._workspace_root is None or self._source_path is None:
            raise RuntimeError("Workspace not initialized.")
        
        target = Path(target_path) if target_path else self._source_path
        modified_files: list[str] = []
        
        # Walk through workspace and copy changed/new files
        for root, dirs, files in os.walk(self._workspace_root):
            # Skip .git directories
            dirs[:] = [d for d in dirs if d != ".git"]
            
            root_path = Path(root)
            relative_root = root_path.relative_to(self._workspace_root)
            target_root = target / relative_root
            
            for file in files:
                # Skip the benchmark script - it's workspace-specific
                if file == BENCHMARK_SCRIPT_NAME and root_path == self._workspace_root:
                    continue
                    
                src_file = root_path / file
                tgt_file = target_root / file
                
                # Check if file is new or modified
                if not tgt_file.exists():
                    tgt_file.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src_file, tgt_file)
                    modified_files.append(str(relative_root / file))
                elif src_file.read_bytes() != tgt_file.read_bytes():
                    shutil.copy2(src_file, tgt_file)
                    modified_files.append(str(relative_root / file))
        
        return modified_files


def set_workspace(workspace: WorkspaceManager | None):
    """Set the workspace context for the current thread.
    
    This must be called before any tools are used to ensure they
    operate within the correct workspace.
    """
    _thread_local.workspace = workspace


def get_workspace() -> WorkspaceManager | None:
    """Get the workspace for the current thread.
    
    Returns None if no workspace is set.
    """
    return getattr(_thread_local, 'workspace', None)


def get_workspace_root() -> Path:
    """Get the workspace root for file operations.
    
    Priority:
    1. Thread-local workspace (set via set_workspace)
    2. WORKSPACE_ROOT environment variable
    3. Current working directory
    
    Returns:
        Path to the workspace root directory.
    """
    workspace = get_workspace()
    if workspace:
        return workspace.workspace_root
    
    env_root = os.environ.get("WORKSPACE_ROOT")
    if env_root:
        return Path(env_root)
    
    return Path.cwd()


def get_benchmark_path() -> Path:
    """Get the standard benchmark script path.
    
    Returns:
        Path to optifiner_benchmark.py in the workspace root.
    """
    return get_workspace_root() / BENCHMARK_SCRIPT_NAME


def resolve_path(path: str | Path) -> Path:
    """Resolve a path within the workspace.
    
    If a workspace manager is active, uses its path resolution.
    Otherwise, resolves relative to workspace root.
    
    Args:
        path: Relative or absolute path.
        
    Returns:
        Resolved absolute path.
    """
    workspace = get_workspace()
    if workspace:
        return workspace.resolve_path(path)
    
    # No workspace isolation - direct path resolution
    p = Path(path)
    if not p.is_absolute():
        p = get_workspace_root() / p
    return p.resolve()


@contextmanager
def isolated_workspace(source_path: str | Path) -> Generator[WorkspaceManager, None, None]:
    """Context manager for running code in an isolated workspace.
    
    Example:
        with isolated_workspace("/path/to/repo") as ws:
            # Agent works in /tmp/optifiner_workspaces/ws_<id>/
            # Real paths, no emulation
            run_agent(...)
            
            # Copy changes back if successful
            ws.copy_back_changes()
    """
    workspace = WorkspaceManager()
    workspace.setup(source_path)
    
    old_workspace = get_workspace()
    set_workspace(workspace)
    
    try:
        yield workspace
    finally:
        set_workspace(old_workspace)
        # Note: cleanup is NOT automatic - caller decides when to cleanup
        # workspace.cleanup()
