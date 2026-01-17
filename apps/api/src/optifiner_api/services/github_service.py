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

    def create_branch(
        self,
        repo_dir: str,
        branch_name: str,
        from_branch: str | None = None,
    ) -> dict[str, Any]:
        """Create a new branch in the repository.

        Args:
            repo_dir: Directory name of the repository
            branch_name: Name of the new branch to create
            from_branch: Branch to create from (default: current branch)

        Returns:
            Dictionary with branch creation information
        """
        try:
            repo_path = self.workspace_root / repo_dir

            if not repo_path.exists():
                return {
                    "success": False,
                    "error": f"Repository directory not found: {repo_dir}",
                }

            repo = Repo(str(repo_path))

            # Check if branch already exists
            if branch_name in [ref.name for ref in repo.heads]:
                # Branch exists, just checkout
                repo.heads[branch_name].checkout()
                return {
                    "success": True,
                    "branch": branch_name,
                    "message": f"Switched to existing branch: {branch_name}",
                }

            # Switch to source branch if specified
            if from_branch:
                if from_branch in [ref.name for ref in repo.heads]:
                    repo.heads[from_branch].checkout()
                else:
                    return {
                        "success": False,
                        "error": f"Source branch not found: {from_branch}",
                    }

            # Create new branch from current branch
            new_branch = repo.create_head(branch_name)
            new_branch.checkout()

            return {
                "success": True,
                "branch": branch_name,
                "from_branch": repo.active_branch.name if from_branch else None,
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

    def commit_changes(
        self,
        repo_dir: str,
        commit_message: str,
        branch: str | None = None,
        files: list[str] | None = None,
        author_name: str = "Optifiner",
        author_email: str = "optifiner@example.com",
    ) -> dict[str, Any]:
        """Commit changes to the repository.

        Args:
            repo_dir: Directory name of the repository
            commit_message: Commit message
            branch: Branch name (default: current branch or create new)
            files: List of specific files to commit (None = all changes)
            author_name: Git author name
            author_email: Git author email

        Returns:
            Dictionary with commit information
        """
        try:
            repo_path = self.workspace_root / repo_dir

            if not repo_path.exists():
                return {
                    "success": False,
                    "error": f"Repository directory not found: {repo_dir}",
                }

            repo = Repo(str(repo_path))

            # Get or create branch first (before committing)
            if branch:
                if branch in [ref.name for ref in repo.heads]:
                    # Switch to existing branch if not already on it
                    if repo.active_branch.name != branch:
                        repo.heads[branch].checkout()
                else:
                    # Create new branch from current branch
                    new_branch = repo.create_head(branch)
                    new_branch.checkout()
            else:
                branch = repo.active_branch.name

            # Check if there are any changes
            if repo.is_dirty(untracked_files=True):
                # Stage files
                if files:
                    # Stage specific files
                    for file_path in files:
                        full_path = repo_path / file_path
                        if full_path.exists():
                            repo.index.add([file_path])
                        else:
                            return {
                                "success": False,
                                "error": f"File not found: {file_path}",
                            }
                else:
                    # Stage all changes
                    repo.index.add("*")

                # Create commit
                commit = repo.index.commit(
                    commit_message,
                    author=f"{author_name} <{author_email}>",
                    committer=f"{author_name} <{author_email}>",
                )

                return {
                    "success": True,
                    "commit": commit.hexsha,
                    "commit_message": commit_message,
                    "branch": branch,
                    "files_committed": files or "all changes",
                }
            else:
                return {
                    "success": False,
                    "error": "No changes to commit",
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }

    def push_changes(
        self,
        repo_dir: str,
        branch: str | None = None,
        force: bool = False,
    ) -> dict[str, Any]:
        """Push committed changes to GitHub repository.

        Args:
            repo_dir: Directory name of the repository
            branch: Branch name to push (default: current branch)
            force: Whether to force push

        Returns:
            Dictionary with push information
        """
        try:
            repo_path = self.workspace_root / repo_dir

            if not repo_path.exists():
                return {
                    "success": False,
                    "error": f"Repository directory not found: {repo_dir}",
                }

            repo = Repo(str(repo_path))

            # Determine branch to push
            if branch:
                if branch not in [ref.name for ref in repo.heads]:
                    return {
                        "success": False,
                        "error": f"Branch not found: {branch}",
                    }
                # Switch to branch if not already on it
                if repo.active_branch.name != branch:
                    repo.heads[branch].checkout()
            else:
                branch = repo.active_branch.name

            # Check if there are commits to push
            origin = repo.remotes.origin
            try:
                # Fetch latest from remote
                origin.fetch()
                
                # Check if remote branch exists
                remote_branch = f"origin/{branch}"
                if remote_branch in [ref.name for ref in repo.refs]:
                    # Compare local and remote branches
                    commits_ahead = len(list(repo.iter_commits(f"{branch}..{remote_branch}")))
                    commits_behind = len(list(repo.iter_commits(f"{remote_branch}..{branch}")))
                else:
                    # Remote branch doesn't exist, we can push
                    commits_ahead = 0
                    commits_behind = len(list(repo.iter_commits(branch)))

                if commits_behind == 0 and not force:
                    return {
                        "success": False,
                        "error": "No commits to push",
                    }

                # Push to remote
                if force:
                    origin.push(branch, force=True)
                else:
                    try:
                        origin.push(branch, force=False)
                    except Exception as push_error:
                        # If push fails, try to set upstream
                        try:
                            origin.push(branch, set_upstream=True, force=False)
                        except Exception:
                            return {
                                "success": False,
                                "error": f"Failed to push: {str(push_error)}",
                            }

                return {
                    "success": True,
                    "branch": branch,
                    "commits_pushed": commits_behind,
                }
            except Exception as e:
                return {
                    "success": False,
                    "error": f"Failed to push: {str(e)}",
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }

    def create_pull_request(
        self,
        repo_dir: str,
        branch: str,
        title: str,
        body: str | None = None,
        base_branch: str | None = None,
    ) -> dict[str, Any]:
        """Create a pull request for a pushed branch.

        Args:
            repo_dir: Directory name of the repository
            branch: Branch name (head branch for PR)
            title: Pull request title
            body: Pull request body/description
            base_branch: Base branch for PR (default: repository default branch)

        Returns:
            Dictionary with pull request information
        """
        if not self.github:
            return {
                "success": False,
                "error": "GitHub token not configured",
            }

        try:
            repo_path = self.workspace_root / repo_dir

            if not repo_path.exists():
                return {
                    "success": False,
                    "error": f"Repository directory not found: {repo_dir}",
                }

            repo = Repo(str(repo_path))

            # Extract owner and repo name from remote URL
            origin = repo.remotes.origin
            remote_url = origin.url

            if "github.com" not in remote_url:
                return {
                    "success": False,
                    "error": "Repository is not a GitHub repository",
                }

            # Parse URL like https://github.com/owner/repo.git or git@github.com:owner/repo.git
            if remote_url.startswith("git@"):
                # SSH format: git@github.com:owner/repo.git
                parts = remote_url.replace("git@github.com:", "").replace(".git", "").split("/")
            else:
                # HTTPS format: https://github.com/owner/repo.git
                parts = remote_url.replace(".git", "").split("/")

            owner = parts[-2]
            repo_name = parts[-1]

            github_repo = self.github.get_repo(f"{owner}/{repo_name}")

            # Determine base branch
            if not base_branch:
                base_branch = github_repo.default_branch

            # Check if branch exists on remote
            try:
                github_repo.get_branch(branch)
            except Exception:
                return {
                    "success": False,
                    "error": f"Branch '{branch}' not found on remote repository",
                }

            # Get latest commit message if body not provided
            if not body:
                try:
                    latest_commit = repo.head.commit
                    commit_message = latest_commit.message
                    body = f"Automated changes from Optifiner\n\n{commit_message}"
                except Exception:
                    body = "Automated changes from Optifiner"

            # Create pull request
            pr = github_repo.create_pull(
                title=title,
                body=body,
                head=branch,
                base=base_branch,
            )

            return {
                "success": True,
                "pull_request": {
                    "number": pr.number,
                    "url": pr.html_url,
                    "title": pr.title,
                    "state": pr.state,
                    "head": pr.head.ref,
                    "base": pr.base.ref,
                },
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }

    def get_repository_status(self, repo_dir: str) -> dict[str, Any]:
        """Get the status of a repository (changes, branch, etc.).

        Args:
            repo_dir: Directory name of the repository

        Returns:
            Dictionary with repository status
        """
        try:
            repo_path = self.workspace_root / repo_dir

            if not repo_path.exists():
                return {
                    "success": False,
                    "error": f"Repository directory not found: {repo_dir}",
                }

            repo = Repo(str(repo_path))

            # Get changed files
            changed_files = []
            for item in repo.index.diff(None):
                changed_files.append(item.a_path)

            # Get untracked files
            untracked_files = repo.untracked_files

            # Get status
            is_dirty = repo.is_dirty(untracked_files=True)

            return {
                "success": True,
                "repo_dir": repo_dir,
                "branch": repo.active_branch.name if repo.active_branch else None,
                "commit": repo.head.commit.hexsha if repo.head.commit else None,
                "is_dirty": is_dirty,
                "changed_files": changed_files,
                "untracked_files": untracked_files,
                "has_changes": len(changed_files) > 0 or len(untracked_files) > 0,
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }
