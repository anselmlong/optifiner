"""Workspace isolation and path translation for running agents on host machine.

This module provides chroot-like isolation for agents:
- The actual workspace is at /tmp/optifiner_<uuid>/app/
- The agent sees and interacts with /app (virtual root)
- All file operations are transparently translated

This allows agents to work in isolated copies without affecting the original codebase.
"""

import os
import shutil
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

# Virtual root that agents see
VIRTUAL_ROOT = "/app"

# Base directory for workspace copies
WORKSPACE_BASE = Path("/tmp/optifiner_workspaces")


class WorkspaceManager:
    """Manages isolated workspace copies with path translation.
    
    Agents think they're working in /app, but they're actually working in
    /tmp/optifiner_<uuid>/app/. This provides isolation without containers.
    """
    
    def __init__(self, workspace_id: str | None = None):
        """Initialize workspace manager.
        
        Args:
            workspace_id: Optional ID for the workspace. If not provided, generates UUID.
        """
        self.workspace_id = workspace_id or str(uuid.uuid4())[:8]
        self._actual_root: Path | None = None
        self._source_path: Path | None = None
        
    @property
    def actual_root(self) -> Path:
        """Get the actual filesystem root for this workspace."""
        if self._actual_root is None:
            raise RuntimeError("Workspace not initialized. Call setup() first.")
        return self._actual_root
    
    @property 
    def virtual_root(self) -> str:
        """Get the virtual root that agents see."""
        return VIRTUAL_ROOT
    
    def setup(self, source_path: str | Path) -> Path:
        """Set up the isolated workspace by copying source.
        
        Args:
            source_path: Path to the source codebase to copy.
            
        Returns:
            The actual root path of the isolated workspace.
        """
        source = Path(source_path).resolve()
        if not source.exists():
            raise ValueError(f"Source path does not exist: {source}")
        
        self._source_path = source
        
        # Create workspace directory structure
        WORKSPACE_BASE.mkdir(parents=True, exist_ok=True)
        workspace_dir = WORKSPACE_BASE / f"ws_{self.workspace_id}"
        
        # The actual root mirrors the virtual root structure
        # Agent sees /app, actual is /tmp/optifiner_workspaces/ws_<id>/app
        self._actual_root = workspace_dir / "app"
        
        # Clean up if exists
        if workspace_dir.exists():
            shutil.rmtree(workspace_dir)
        
        # Copy source to workspace
        shutil.copytree(source, self._actual_root, symlinks=True)
        
        return self._actual_root
    
    def cleanup(self):
        """Remove the isolated workspace."""
        if self._actual_root and self._actual_root.parent.exists():
            try:
                shutil.rmtree(self._actual_root.parent)
            except Exception:
                pass
    
    def translate_to_actual(self, virtual_path: str) -> Path:
        """Translate a virtual path to the actual filesystem path.
        
        Args:
            virtual_path: Path as seen by the agent (e.g., /app/src/main.py)
            
        Returns:
            The actual filesystem path.
        """
        if self._actual_root is None:
            raise RuntimeError("Workspace not initialized. Call setup() first.")
        
        path = Path(virtual_path)
        
        # If path is already pointing to actual root, return as-is
        try:
            path.relative_to(self._actual_root)
            return path
        except ValueError:
            pass
        
        # Handle absolute paths starting with virtual root
        if str(path).startswith(VIRTUAL_ROOT):
            relative = path.relative_to(VIRTUAL_ROOT)
            return self._actual_root / relative
        
        # Handle relative paths - treat as relative to virtual root
        if not path.is_absolute():
            return self._actual_root / path
        
        # Path is absolute but not in virtual root - could be system path
        # For security, still confine to workspace
        return self._actual_root / path.name
    
    def translate_to_virtual(self, actual_path: str | Path) -> str:
        """Translate an actual filesystem path to the virtual path.
        
        Args:
            actual_path: Actual filesystem path.
            
        Returns:
            The virtual path as seen by the agent.
        """
        if self._actual_root is None:
            raise RuntimeError("Workspace not initialized. Call setup() first.")
        
        path = Path(actual_path)
        
        try:
            relative = path.relative_to(self._actual_root)
            return str(Path(VIRTUAL_ROOT) / relative)
        except ValueError:
            # Path is not in workspace, return as-is
            return str(path)
    
    def copy_back_changes(self, target_path: str | Path | None = None) -> list[str]:
        """Copy changes from isolated workspace back to source.
        
        Args:
            target_path: Where to copy changes. Defaults to original source.
            
        Returns:
            List of files that were modified.
        """
        if self._actual_root is None or self._source_path is None:
            raise RuntimeError("Workspace not initialized.")
        
        target = Path(target_path) if target_path else self._source_path
        modified_files: list[str] = []
        
        # Walk through workspace and copy changed/new files
        for root, dirs, files in os.walk(self._actual_root):
            # Skip .git directories
            dirs[:] = [d for d in dirs if d != ".git"]
            
            root_path = Path(root)
            relative_root = root_path.relative_to(self._actual_root)
            target_root = target / relative_root
            
            for file in files:
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


# Global workspace context for tools
_current_workspace: WorkspaceManager | None = None


def set_workspace(workspace: WorkspaceManager | None):
    """Set the global workspace context."""
    global _current_workspace
    _current_workspace = workspace


def get_workspace() -> WorkspaceManager | None:
    """Get the current global workspace."""
    return _current_workspace


def get_workspace_root() -> Path:
    """Get the actual workspace root for file operations.
    
    If a workspace is set, returns the actual root.
    Otherwise returns the WORKSPACE_ROOT env var or /app.
    """
    if _current_workspace:
        return _current_workspace.actual_root
    return Path(os.environ.get("WORKSPACE_ROOT", "/app"))


def translate_path(path: str) -> Path:
    """Translate a path from agent perspective to actual filesystem.
    
    Args:
        path: Path as agent sees it (may be /app/... or relative).
        
    Returns:
        Actual filesystem path.
    """
    if _current_workspace:
        return _current_workspace.translate_to_actual(path)
    
    # No workspace isolation - use direct path
    p = Path(path)
    if not p.is_absolute():
        p = get_workspace_root() / p
    return p


def translate_output(output: str) -> str:
    """Translate actual paths in output back to virtual paths.
    
    This is used to sanitize tool output so agents see virtual paths.
    """
    if not _current_workspace:
        return output
    
    actual_str = str(_current_workspace.actual_root)
    return output.replace(actual_str, VIRTUAL_ROOT)


@contextmanager
def isolated_workspace(source_path: str | Path) -> Generator[WorkspaceManager, None, None]:
    """Context manager for running code in an isolated workspace.
    
    Example:
        with isolated_workspace("/path/to/repo") as ws:
            # Agent runs here, sees /app
            # Actually working in /tmp/optifiner_workspaces/ws_<id>/app
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
