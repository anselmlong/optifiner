"""GitHub integration service."""

import logging
import os
import shutil
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import jwt
import requests
from git import Actor, Repo
from github import Github
from github.Repository import Repository

from optifiner_api.config import settings

logger = logging.getLogger(__name__)


class GitHubService:
    """Service for GitHub repository operations using GitHub App authentication."""

    def __init__(self):
        """Initialize GitHub service."""
        # Resolve workspace path relative to project root
        workspace_path = settings.WORKER_WORKSPACE_PATH
        if not Path(workspace_path).is_absolute():
            project_root = Path(__file__).parent.parent.parent.parent.parent.parent
            self.workspace_root = project_root / workspace_path
        else:
            self.workspace_root = Path(workspace_path)
        
        self._github_app_token: str | None = None
        self._github_app_token_expires: float = 0
        self._cached_installation_id: str | None = None
        
        # Configure git to prevent password prompts
        self._configure_git_credentials()
        
        # Ensure workspace directory exists and is writable
        self._ensure_workspace_writable()
        
        # Initialize GitHub client using GitHub App authentication
        self.github = self._get_github_client()
    
    def _configure_git_credentials(self) -> None:
        """Configure git to prevent password prompts."""
        os.environ["GIT_TERMINAL_PROMPT"] = "0"
        os.environ["GIT_ASKPASS"] = "echo"
        os.environ["GIT_CREDENTIAL_HELPER"] = ""
        os.environ["GIT_CREDENTIAL_MANAGER"] = ""
        logger.debug(f"[GitHubService] Git credentials configured to prevent prompts")
    
    def _update_remote_url_with_token(self, repo: Repo, repo_path: Path) -> None:
        """Update the remote URL to include GitHub App token."""
        try:
            origin = repo.remotes.origin
            current_url = origin.url
            
            # Extract owner from URL to get the correct installation token
            owner = None
            if "github.com" in current_url:
                if current_url.startswith("git@"):
                    repo_path_part = current_url.split(":")[-1].replace(".git", "")
                else:
                    # Handle both https://github.com/... and https://x-access-token:...@github.com/...
                    repo_path_part = current_url.split("github.com/")[-1].replace(".git", "")
                
                parts = repo_path_part.split("/")
                if len(parts) >= 2:
                    owner = parts[0]
            
            # Get token for the specific owner's installation
            auth_token = self._get_installation_token(owner)
            if not auth_token:
                logger.warning(f"[GitHubService] Could not get auth token for owner '{owner}'")
                return
            
            # Build the authenticated URL
            if current_url.startswith("git@github.com:"):
                # Convert SSH to HTTPS with token
                ssh_path = current_url.replace("git@github.com:", "").replace(".git", "")
                new_url = f"https://x-access-token:{auth_token}@github.com/{ssh_path}.git"
            elif "github.com" in current_url:
                # Handle HTTPS URLs (with or without existing token)
                # Strip any existing authentication
                if "@github.com" in current_url:
                    # URL has auth - extract the path part
                    path_part = current_url.split("github.com/")[-1]
                    new_url = f"https://x-access-token:{auth_token}@github.com/{path_part}"
                else:
                    # Plain HTTPS URL
                    new_url = current_url.replace("https://github.com/", f"https://x-access-token:{auth_token}@github.com/")
                    new_url = new_url.replace("http://github.com/", f"http://x-access-token:{auth_token}@github.com/")
            else:
                return
            
            # Ensure URL ends with .git
            if not new_url.endswith(".git"):
                new_url = f"{new_url}.git"
            
            origin.set_url(new_url, origin.url)
            logger.debug(f"[GitHubService] Updated remote URL for owner '{owner}'")
        except Exception as e:
            logger.warning(f"[GitHubService] Failed to update remote URL with token: {e}")
    
    def _ensure_workspace_writable(self) -> None:
        """Ensure workspace directory exists and is writable."""
        try:
            if not self.workspace_root.exists():
                self.workspace_root.mkdir(parents=True, exist_ok=True)
                os.chmod(self.workspace_root, 0o755)
            else:
                test_file = self.workspace_root / ".test_write"
                try:
                    test_file.touch()
                    test_file.unlink()
                except (OSError, PermissionError):
                    try:
                        os.chmod(self.workspace_root, 0o755)
                        test_file.touch()
                        test_file.unlink()
                    except (OSError, PermissionError) as e:
                        raise PermissionError(
                            f"Workspace directory {self.workspace_root} is not writable."
                        ) from e
        except PermissionError:
            raise
        except Exception as e:
            raise OSError(f"Could not access workspace directory {self.workspace_root}: {e}") from e
    
    def _get_github_app_jwt(self) -> str | None:
        """Generate JWT token for GitHub App authentication."""
        if not settings.GITHUB_APP_ID or not settings.GITHUB_APP_PRIVATE_KEY:
            return None
        
        try:
            private_key = settings.GITHUB_APP_PRIVATE_KEY
            private_key_path = Path(private_key)
            if not private_key_path.is_absolute():
                project_root = Path(__file__).parent.parent.parent.parent.parent.parent
                private_key_path = project_root / private_key
            
            if private_key_path.exists() and private_key_path.is_file():
                with open(private_key_path, "r") as f:
                    private_key = f.read()
            
            if not private_key or not private_key.strip():
                return None
            
            now = int(time.time())
            payload = {
                "iat": now - 60,
                "exp": now + (10 * 60),
                "iss": settings.GITHUB_APP_ID,
            }
            
            return jwt.encode(payload, private_key, algorithm="RS256")
        except Exception as e:
            logger.error(f"[GitHubService] Error generating GitHub App JWT: {e}")
            return None
    
    def _get_installation_id(self, owner: str | None = None) -> str | None:
        """Get installation ID for GitHub App.
        
        Args:
            owner: Optional owner/account to find installation for. If not provided,
                   returns the first available installation.
        """
        # Only use cache if no specific owner requested
        if not owner and self._cached_installation_id:
            return self._cached_installation_id
        
        if not settings.GITHUB_APP_CLIENT_ID:
            return None
        
        jwt_token = self._get_github_app_jwt()
        if not jwt_token:
            return None
        
        try:
            url = "https://api.github.com/app/installations"
            headers = {
                "Authorization": f"Bearer {jwt_token}",
                "Accept": "application/vnd.github.v3+json",
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            installations = response.json()
            if not installations:
                logger.warning("[GitHubService] No installations found for GitHub App")
                return None
            
            # Log all installations for debugging
            logger.info(f"[GitHubService] Found {len(installations)} installation(s):")
            for inst in installations:
                account = inst.get("account", {})
                logger.info(f"  - Installation {inst.get('id')}: {account.get('login')} ({account.get('type')})")
            
            # If owner specified, find matching installation
            if owner:
                for inst in installations:
                    account = inst.get("account", {})
                    if account.get("login", "").lower() == owner.lower():
                        installation_id = str(inst.get("id"))
                        logger.info(f"[GitHubService] Using installation {installation_id} for owner '{owner}'")
                        return installation_id
                
                logger.warning(f"[GitHubService] No installation found for owner '{owner}'")
                # Fall back to first installation
            
            # Use first installation
            installation = installations[0]
            installation_id = str(installation.get("id"))
            account_login = installation.get("account", {}).get("login", "unknown")
            
            if installation_id:
                logger.info(f"[GitHubService] Using installation {installation_id} (account: {account_login})")
                if not owner:
                    self._cached_installation_id = installation_id
                return installation_id
                
        except Exception as e:
            logger.error(f"[GitHubService] Error getting installation ID: {e}")
            return None
        
        return None
    
    def _get_installation_token(self, owner: str | None = None) -> str | None:
        """Get installation access token for GitHub App.
        
        Args:
            owner: Optional owner to get installation token for.
        """
        # Only use cache if no specific owner requested
        if not owner and self._github_app_token and time.time() < self._github_app_token_expires:
            return self._github_app_token
        
        installation_id = self._get_installation_id(owner)
        if not installation_id:
            return None
        
        jwt_token = self._get_github_app_jwt()
        if not jwt_token:
            return None
        
        try:
            url = f"https://api.github.com/app/installations/{installation_id}/access_tokens"
            headers = {
                "Authorization": f"Bearer {jwt_token}",
                "Accept": "application/vnd.github.v3+json",
            }
            
            response = requests.post(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            token = data.get("token")
            expires_at = data.get("expires_at")
            
            if token:
                # Only cache if not owner-specific
                if not owner:
                    self._github_app_token = token
                    if expires_at:
                        try:
                            exp_str = expires_at.replace("Z", "+00:00")
                            exp_time = datetime.fromisoformat(exp_str)
                            self._github_app_token_expires = exp_time.timestamp() - 600
                        except Exception:
                            self._github_app_token_expires = time.time() + (50 * 60)
                    else:
                        self._github_app_token_expires = time.time() + (50 * 60)
                
                return token
        except Exception as e:
            logger.error(f"[GitHubService] Error getting installation token: {e}")
            return None
        
        return None
    
    def _get_github_client(self, owner: str | None = None) -> Github | None:
        """Get GitHub client using GitHub App installation token.
        
        Args:
            owner: Optional owner to get client for specific installation.
        """
        installation_token = self._get_installation_token(owner)
        if installation_token:
            return Github(installation_token)
        return None
    
    def _get_configuration_error(self) -> str:
        """Get detailed error message about missing GitHub App configuration."""
        missing = []
        if not settings.GITHUB_APP_ID:
            missing.append("GITHUB_APP_ID")
        if not settings.GITHUB_APP_PRIVATE_KEY:
            missing.append("GITHUB_APP_PRIVATE_KEY")
        if not settings.GITHUB_APP_CLIENT_ID:
            missing.append("GITHUB_APP_CLIENT_ID")
        
        if missing:
            return f"GitHub App not configured. Missing: {', '.join(missing)}"
        return "GitHub App configuration issue. Check logs for details."
    
    def _get_auth_token(self) -> str | None:
        """Get GitHub App installation token."""
        return self._get_installation_token()

    def clone_repository(
        self,
        repo_url: str,
        branch: str | None = None,
        target_dir: str | None = None,
    ) -> dict[str, Any]:
        """Clone a GitHub repository."""
        try:
            original_url = repo_url
            if repo_url.endswith(".git"):
                repo_url = repo_url[:-4]
            repo_name = repo_url.split("/")[-1]

            if target_dir is None:
                target_dir = repo_name

            target_path = self.workspace_root / target_dir

            if target_path.exists():
                shutil.rmtree(target_path)

            clone_url = original_url
            is_ssh = clone_url.startswith("git@") or clone_url.startswith("ssh://")
            is_authenticated = "@github.com" in clone_url and not is_ssh
            
            auth_token = self._get_auth_token()
            if not is_ssh and not is_authenticated and "github.com" in clone_url and auth_token:
                # GitHub App installation tokens require x-access-token as username
                if clone_url.startswith("https://"):
                    clone_url = clone_url.replace("https://", f"https://x-access-token:{auth_token}@")
                elif clone_url.startswith("http://"):
                    clone_url = clone_url.replace("http://", f"http://x-access-token:{auth_token}@")
            
            repo = None
            try:
                if branch:
                    repo = Repo.clone_from(clone_url, str(target_path), branch=branch)
                else:
                    repo = Repo.clone_from(clone_url, str(target_path))
            except Exception as e:
                if (clone_url.startswith("https://") or clone_url.startswith("http://")) and not is_ssh:
                    ssh_url = clone_url
                    if "@github.com" in ssh_url:
                        parts = ssh_url.split("@")
                        if len(parts) > 1:
                            ssh_url = parts[-1]
                    ssh_url = ssh_url.replace("https://", "").replace("http://", "")
                    if "github.com/" in ssh_url:
                        ssh_url = ssh_url.replace("github.com/", "github.com:")
                    ssh_url = f"git@{ssh_url}"
                    if not ssh_url.endswith(".git"):
                        ssh_url = f"{ssh_url}.git"
                    
                    try:
                        if branch:
                            repo = Repo.clone_from(ssh_url, str(target_path), branch=branch)
                        else:
                            repo = Repo.clone_from(ssh_url, str(target_path))
                    except Exception as ssh_error:
                        raise Exception(f"HTTPS failed: {e}; SSH fallback failed: {ssh_error}")
                else:
                    raise

            if repo is None:
                raise Exception("Failed to clone repository")

            try:
                self._update_remote_url_with_token(repo, target_path)
            except Exception:
                pass

            return {
                "success": True,
                "path": str(target_path),
                "repo_name": repo_name,
                "branch": repo.active_branch.name if repo.active_branch else None,
                "commit": repo.head.commit.hexsha,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def create_branch(
        self,
        repo_dir: str,
        branch_name: str,
        from_branch: str | None = None,
    ) -> dict[str, Any]:
        """Create a new branch in the repository."""
        if not self.github:
            return {"success": False, "error": self._get_configuration_error()}

        try:
            repo_path = self.workspace_root / repo_dir
            if not repo_path.exists():
                return {"success": False, "error": f"Repository not found: {repo_dir}"}

            local_repo = Repo(str(repo_path))
            
            try:
                self._update_remote_url_with_token(local_repo, repo_path)
            except Exception:
                pass
            
            remote_url = local_repo.remotes.origin.url
            
            if "github.com" in remote_url:
                if remote_url.startswith("git@"):
                    repo_path_part = remote_url.split(":")[-1].replace(".git", "")
                else:
                    repo_path_part = remote_url.split("github.com/")[-1].replace(".git", "")
                    if "@" in repo_path_part:
                        repo_path_part = repo_path_part.split("@")[-1]
                
                parts = repo_path_part.split("/")
                if len(parts) >= 2:
                    owner = parts[0]
                    repo_name = parts[1]
                else:
                    return {"success": False, "error": f"Could not parse repo from URL: {remote_url}"}
            else:
                return {"success": False, "error": f"Not a GitHub repository: {remote_url}"}

            logger.info(f"[GitHubService] Accessing repository: {owner}/{repo_name}")
            
            # Get GitHub client for the specific owner's installation
            github_client = self._get_github_client(owner)
            if not github_client:
                return {
                    "success": False, 
                    "error": f"Could not get GitHub client for owner '{owner}'. "
                             f"Ensure the GitHub App is installed on the '{owner}' account."
                }
            
            try:
                github_repo = github_client.get_repo(f"{owner}/{repo_name}")
            except Exception as e:
                error_msg = str(e)
                if "404" in error_msg:
                    return {
                        "success": False, 
                        "error": f"Repository '{owner}/{repo_name}' not found or GitHub App does not have access. "
                                 f"Ensure the GitHub App is installed on the '{owner}' account and has access to '{repo_name}'."
                    }
                raise
            
            try:
                existing_branch = github_repo.get_branch(branch_name)
                try:
                    local_repo.git.checkout(branch_name)
                except Exception:
                    local_repo.git.checkout("-b", branch_name, f"origin/{branch_name}")
                
                return {
                    "success": True,
                    "branch": branch_name,
                    "message": f"Branch already exists: {branch_name}",
                    "commit": existing_branch.commit.sha,
                }
            except Exception:
                pass

            if from_branch:
                try:
                    source_branch = github_repo.get_branch(from_branch)
                    source_sha = source_branch.commit.sha
                except Exception as e:
                    return {"success": False, "error": f"Source branch '{from_branch}' not found: {e}"}
            else:
                default_branch = github_repo.default_branch
                source_branch = github_repo.get_branch(default_branch)
                source_sha = source_branch.commit.sha
                from_branch = default_branch

            github_repo.create_git_ref(ref=f"refs/heads/{branch_name}", sha=source_sha)

            # Fetch and checkout the new branch locally
            try:
                local_repo.git.fetch("origin")
                local_repo.git.checkout("-b", branch_name, f"origin/{branch_name}")
            except Exception as e:
                # If remote checkout fails, try to create branch locally from current HEAD
                logger.warning(f"[GitHubService] Could not checkout remote branch, creating locally: {e}")
                try:
                    local_repo.git.checkout("-b", branch_name)
                except Exception as e2:
                    logger.error(f"[GitHubService] Failed to create local branch: {e2}")
                    return {"success": False, "error": f"Branch created on remote but failed to checkout locally: {e2}"}

            return {
                "success": True,
                "branch": branch_name,
                "from_branch": from_branch,
                "commit": source_sha,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def commit_changes(
        self,
        repo_dir: str,
        commit_message: str,
        branch: str,
        files: list[str] | None = None,
    ) -> dict[str, Any]:
        """Commit and push changes using git (fast method).
        
        Uses git commit + git push instead of GitHub API for speed.
        Commits are made as the GitHub App bot user.
        """
        try:
            repo_path = self.workspace_root / repo_dir
            if not repo_path.exists():
                return {"success": False, "error": f"Repository not found: {repo_dir}"}

            local_repo = Repo(str(repo_path))
            
            # Extract owner from remote URL for authentication
            remote_url = local_repo.remotes.origin.url
            owner = None
            if "github.com" in remote_url:
                if remote_url.startswith("git@"):
                    repo_path_part = remote_url.split(":")[-1].replace(".git", "")
                else:
                    repo_path_part = remote_url.split("github.com/")[-1].replace(".git", "")
                parts = repo_path_part.split("/")
                if len(parts) >= 2:
                    owner = parts[0]
            
            logger.info(f"[GitHubService] Committing changes for owner '{owner}'")

            # Make sure we're on the right branch
            try:
                if local_repo.active_branch.name != branch:
                    local_repo.git.checkout(branch)
            except Exception as e:
                logger.warning(f"[GitHubService] Could not checkout branch {branch}: {e}")
                # Branch might not exist locally - try to create it
                try:
                    # First try to fetch and track remote branch
                    local_repo.git.fetch("origin")
                    local_repo.git.checkout("-b", branch, f"origin/{branch}")
                    logger.info(f"[GitHubService] Created local branch {branch} tracking origin/{branch}")
                except Exception:
                    # Remote branch might not exist yet, create local branch from current HEAD
                    try:
                        local_repo.git.checkout("-b", branch)
                        logger.info(f"[GitHubService] Created new local branch {branch}")
                    except Exception as e2:
                        return {"success": False, "error": f"Failed to checkout or create branch {branch}: {e2}"}

            # Stage files
            if files:
                for file_path in files:
                    local_repo.git.add(file_path)
            else:
                local_repo.git.add("-A")

            # Check if there are staged changes
            if not local_repo.index.diff("HEAD") and not local_repo.untracked_files:
                return {"success": False, "error": "No changes to commit"}

            # GitHub App bot user credentials
            BOT_NAME = "optifiner[bot]"
            BOT_EMAIL = "optifiner[bot]@users.noreply.github.com"
            
            # Configure git user as GitHub App bot for commits
            with local_repo.config_writer() as config:
                config.set_value("user", "email", BOT_EMAIL)
                config.set_value("user", "name", BOT_NAME)

            # Commit with explicit author and committer to ensure bot attribution
            bot_actor = Actor(BOT_NAME, BOT_EMAIL)
            commit = local_repo.index.commit(
                commit_message,
                author=bot_actor,
                committer=bot_actor,
            )
            commit_hash = commit.hexsha
            logger.info(f"[GitHubService] Created commit {commit_hash[:8]} as {BOT_NAME}")

            # Get installation token for push
            auth_token = self._get_installation_token(owner)
            if not auth_token:
                return {
                    "success": False, 
                    "error": f"Could not get auth token for owner '{owner}'",
                    "commit_hash": commit_hash
                }

            # Build authenticated push URL
            if remote_url.startswith("git@github.com:"):
                path_part = remote_url.replace("git@github.com:", "").replace(".git", "")
                push_url = f"https://x-access-token:{auth_token}@github.com/{path_part}.git"
            elif "github.com" in remote_url:
                # Strip any existing auth and rebuild
                if "@github.com" in remote_url:
                    path_part = remote_url.split("github.com/")[-1]
                else:
                    path_part = remote_url.replace("https://github.com/", "").replace("http://github.com/", "")
                if not path_part.endswith(".git"):
                    path_part = f"{path_part}.git"
                push_url = f"https://x-access-token:{auth_token}@github.com/{path_part}"
            else:
                return {"success": False, "error": f"Not a GitHub URL: {remote_url}", "commit_hash": commit_hash}

            # Push using authenticated URL directly
            try:
                local_repo.git.push(push_url, f"HEAD:{branch}", "--set-upstream")
                logger.info(f"[GitHubService] Pushed commit {commit_hash[:8]} to {branch}")
            except Exception as e:
                return {"success": False, "error": f"Push failed: {e}", "commit_hash": commit_hash}

            return {
                "success": True,
                "commit_hash": commit_hash,
                "commit_message": commit_message,
                "branch": branch,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def push_changes(
        self,
        repo_dir: str,
        branch: str,
        force: bool = False,
    ) -> dict[str, Any]:
        """Push changes to remote (already done in commit_changes, this is a no-op)."""
        # Since commit_changes now does the push, this is mostly a no-op
        # but we keep it for compatibility
        return {
            "success": True,
            "branch": branch,
            "message": "Push handled by commit_changes",
        }

    def get_repository_info(self, owner: str, repo_name: str) -> dict[str, Any]:
        """Get repository information from GitHub API."""
        if not self.github:
            return {"success": False, "error": self._get_configuration_error()}

        try:
            logger.info(f"[GitHubService] Getting info for repository: {owner}/{repo_name}")
            
            # Get GitHub client for the specific owner's installation
            github_client = self._get_github_client(owner)
            if not github_client:
                return {
                    "success": False, 
                    "error": f"Could not get GitHub client for owner '{owner}'. "
                             f"Ensure the GitHub App is installed on the '{owner}' account."
                }
            
            repo: Repository = github_client.get_repo(f"{owner}/{repo_name}")
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
            error_msg = str(e)
            if "404" in error_msg:
                return {
                    "success": False, 
                    "error": f"Repository '{owner}/{repo_name}' not found or GitHub App does not have access. "
                             f"Ensure the GitHub App is installed on the '{owner}' account and has access to '{repo_name}'."
                }
            return {"success": False, "error": error_msg}

    def update_repository(self, repo_dir: str) -> dict[str, Any]:
        """Update (pull) an existing repository."""
        try:
            repo_path = self.workspace_root / repo_dir
            if not repo_path.exists():
                return {"success": False, "error": f"Repository not found: {repo_dir}"}

            repo = Repo(str(repo_path))
            remote_url = repo.remotes.origin.url
            
            # Extract owner from remote URL for authentication
            owner = None
            if "github.com" in remote_url:
                if remote_url.startswith("git@"):
                    repo_path_part = remote_url.split(":")[-1].replace(".git", "")
                else:
                    repo_path_part = remote_url.split("github.com/")[-1].replace(".git", "")
                parts = repo_path_part.split("/")
                if len(parts) >= 2:
                    owner = parts[0]
            
            # Get installation token for pull
            auth_token = self._get_installation_token(owner)
            if not auth_token:
                return {"success": False, "error": f"Could not get auth token for owner '{owner}'"}

            # Build authenticated fetch URL
            if remote_url.startswith("git@github.com:"):
                path_part = remote_url.replace("git@github.com:", "").replace(".git", "")
                fetch_url = f"https://x-access-token:{auth_token}@github.com/{path_part}.git"
            elif "github.com" in remote_url:
                if "@github.com" in remote_url:
                    path_part = remote_url.split("github.com/")[-1]
                else:
                    path_part = remote_url.replace("https://github.com/", "").replace("http://github.com/", "")
                if not path_part.endswith(".git"):
                    path_part = f"{path_part}.git"
                fetch_url = f"https://x-access-token:{auth_token}@github.com/{path_part}"
            else:
                return {"success": False, "error": f"Not a GitHub URL: {remote_url}"}

            # Fetch and merge using authenticated URL
            current_branch = repo.active_branch.name if repo.active_branch else "main"
            repo.git.fetch(fetch_url, current_branch)
            repo.git.merge(f"FETCH_HEAD")

            return {
                "success": True,
                "path": str(repo_path),
                "branch": repo.active_branch.name if repo.active_branch else None,
                "commit": repo.head.commit.hexsha,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def list_repositories(self) -> list[dict[str, Any]]:
        """List all cloned repositories in workspace."""
        repos = []
        if not self.workspace_root.exists():
            return repos

        for item in self.workspace_root.iterdir():
            if item.is_dir():
                git_dir = item / ".git"
                if git_dir.exists():
                    try:
                        repo = Repo(str(item))
                        repos.append({
                            "name": item.name,
                            "path": str(item),
                            "branch": repo.active_branch.name if repo.active_branch else None,
                            "commit": repo.head.commit.hexsha[:8] if repo.head.commit else None,
                        })
                    except Exception:
                        pass
        return repos

    def create_pull_request(
        self,
        repo_dir: str,
        branch: str,
        title: str,
        body: str | None = None,
        base_branch: str | None = None,
    ) -> dict[str, Any]:
        """Create a pull request for a pushed branch."""
        if not self.github:
            return {"success": False, "error": self._get_configuration_error()}

        try:
            repo_path = self.workspace_root / repo_dir
            if not repo_path.exists():
                return {"success": False, "error": f"Repository not found: {repo_dir}"}

            repo = Repo(str(repo_path))
            origin = repo.remotes.origin
            remote_url = origin.url

            if "github.com" not in remote_url:
                return {"success": False, "error": "Not a GitHub repository"}

            # Parse owner/repo from remote URL (handles token-embedded URLs)
            if remote_url.startswith("git@"):
                repo_path_part = remote_url.replace("git@github.com:", "").replace(".git", "")
            else:
                repo_path_part = remote_url.split("github.com/")[-1].replace(".git", "")
                if "@" in repo_path_part:
                    repo_path_part = repo_path_part.split("@")[-1]

            parts = repo_path_part.split("/")
            if len(parts) < 2:
                return {"success": False, "error": f"Could not parse owner/repo from URL: {remote_url}"}
            
            owner = parts[0]
            repo_name = parts[1]

            logger.info(f"[GitHubService] Creating PR for repository: {owner}/{repo_name}")
            
            # Get GitHub client for the specific owner's installation
            github_client = self._get_github_client(owner)
            if not github_client:
                return {
                    "success": False, 
                    "error": f"Could not get GitHub client for owner '{owner}'. "
                             f"Ensure the GitHub App is installed on the '{owner}' account."
                }
            
            try:
                github_repo = github_client.get_repo(f"{owner}/{repo_name}")
            except Exception as e:
                error_msg = str(e)
                if "404" in error_msg:
                    return {
                        "success": False, 
                        "error": f"Repository '{owner}/{repo_name}' not found or GitHub App does not have access. "
                                 f"Ensure the GitHub App is installed on the '{owner}' account and has access to '{repo_name}'."
                    }
                raise

            if not base_branch:
                base_branch = github_repo.default_branch

            try:
                github_repo.get_branch(branch)
            except Exception:
                return {"success": False, "error": f"Branch '{branch}' not found on remote"}

            if not body:
                try:
                    latest_commit = repo.head.commit
                    body = f"Automated changes from Optifiner\n\n{latest_commit.message}"
                except Exception:
                    body = "Automated changes from Optifiner"

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
            return {"success": False, "error": str(e)}

    def get_repository_status(self, repo_dir: str) -> dict[str, Any]:
        """Get the status of a repository."""
        try:
            repo_path = self.workspace_root / repo_dir
            if not repo_path.exists():
                return {"success": False, "error": f"Repository not found: {repo_dir}"}

            repo = Repo(str(repo_path))

            changed_files = [item.a_path for item in repo.index.diff(None)]
            untracked_files = repo.untracked_files
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
            return {"success": False, "error": str(e)}
