"""GitHub integration service."""

import os
import shutil
from pathlib import Path
from typing import Any

from git import Repo
from github import Github
from github.Repository import Repository

from optifiner_api.config import settings


class GitHubService:
    """Service for GitHub repository operations."""

    def __init__(self):
        """Initialize GitHub service."""
        self.github = Github(settings.GITHUB_TOKEN) if settings.GITHUB_TOKEN else None
        self.workspace_root = Path(settings.WORKER_WORKSPACE_PATH)

    def clone_repository(
        self,
        repo_url: str,
        branch: str | None = None,
        target_dir: str | None = None,
    ) -> dict[str, Any]:
        """Clone a GitHub repository.

        Args:
            repo_url: GitHub repository URL (https or git format)
            branch: Branch to clone (default: default branch)
            target_dir: Target directory name (default: repo name)

        Returns:
            Dictionary with clone information
        """
        try:
            # Extract repo name from URL
            if repo_url.endswith(".git"):
                repo_url = repo_url[:-4]
            repo_name = repo_url.split("/")[-1]

            # Determine target directory
            if target_dir is None:
                target_dir = repo_name

            target_path = self.workspace_root / target_dir

            # Remove existing directory if it exists
            if target_path.exists():
                shutil.rmtree(target_path)

            # Clone repository
            if branch:
                repo = Repo.clone_from(repo_url, str(target_path), branch=branch)
            else:
                repo = Repo.clone_from(repo_url, str(target_path))

            return {
                "success": True,
                "path": str(target_path),
                "repo_name": repo_name,
                "branch": repo.active_branch.name if repo.active_branch else None,
                "commit": repo.head.commit.hexsha,
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }

    def get_repository_info(self, owner: str, repo_name: str) -> dict[str, Any]:
        """Get repository information from GitHub API.

        Args:
            owner: Repository owner
            repo_name: Repository name

        Returns:
            Dictionary with repository information
        """
        if not self.github:
            return {
                "success": False,
                "error": "GitHub token not configured",
            }

        try:
            repo: Repository = self.github.get_repo(f"{owner}/{repo_name}")

            return {
                "success": True,
                "name": repo.name,
                "full_name": repo.full_name,
                "description": repo.description,
                "default_branch": repo.default_branch,
                "language": repo.language,
                "stars": repo.stargazers_count,
                "forks": repo.forks_count,
                "url": repo.html_url,
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }

    def update_repository(self, repo_dir: str) -> dict[str, Any]:
        """Update (pull) an existing repository.

        Args:
            repo_dir: Directory name of the repository

        Returns:
            Dictionary with update information
        """
        try:
            repo_path = self.workspace_root / repo_dir

            if not repo_path.exists():
                return {
                    "success": False,
                    "error": f"Repository directory not found: {repo_dir}",
                }

            repo = Repo(str(repo_path))
            repo.remotes.origin.pull()

            return {
                "success": True,
                "path": str(repo_path),
                "branch": repo.active_branch.name if repo.active_branch else None,
                "commit": repo.head.commit.hexsha,
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }

    def list_repositories(self) -> list[dict[str, Any]]:
        """List all cloned repositories in workspace.

        Returns:
            List of repository information dictionaries
        """
        repos = []
        if not self.workspace_root.exists():
            return repos

        for item in self.workspace_root.iterdir():
            if item.is_dir():
                git_dir = item / ".git"
                if git_dir.exists():
                    try:
                        repo = Repo(str(item))
                        repos.append(
                            {
                                "name": item.name,
                                "path": str(item),
                                "branch": repo.active_branch.name if repo.active_branch else None,
                                "commit": repo.head.commit.hexsha[:8] if repo.head.commit else None,
                            }
                        )
                    except Exception:
                        pass

        return repos
