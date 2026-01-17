"""GitHub integration service."""

import base64
import json
import logging
import os
import shutil
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import jwt
import requests
from git import Repo
from github import Github
from github.Repository import Repository
from github.InputGitTreeElement import InputGitTreeElement
from github.InputGitAuthor import InputGitAuthor

from optifiner_api.config import settings

logger = logging.getLogger(__name__)


class GitHubService:
    """Service for GitHub repository operations using GitHub App authentication."""

    def __init__(self):
        """Initialize GitHub service."""
        # Resolve workspace path relative to project root
        workspace_path = settings.WORKER_WORKSPACE_PATH
        if not Path(workspace_path).is_absolute():
            # If relative path, resolve from project root
            # File is at: apps/api/src/optifiner_api/services/github_service.py
            # Project root is 6 levels up: services -> optifiner_api -> src -> api -> apps -> project_root
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
        """Configure git to prevent password prompts.
        
        Sets environment variables to disable git credential prompts and
        ensures all git operations use GitHub App authentication.
        """
        # Disable git terminal prompts (prevents password prompts)
        os.environ["GIT_TERMINAL_PROMPT"] = "0"
        
        # Disable git askpass (prevents credential prompts)
        # Use a helper that returns empty string
        os.environ["GIT_ASKPASS"] = "echo"
        
        # Disable credential helper prompts
        os.environ["GIT_CREDENTIAL_HELPER"] = ""
        
        # Disable credential manager
        os.environ["GIT_CREDENTIAL_MANAGER"] = ""
        
        logger.debug(f"[GitHubService] Git credentials configured to prevent prompts")
    
    def _update_remote_url_with_token(self, repo: Repo, repo_path: Path) -> None:
        """Update the remote URL to include GitHub App token to prevent password prompts.
        
        Args:
            repo: GitPython Repo object
            repo_path: Path to the repository
        """
        try:
            auth_token = self._get_auth_token()
            if not auth_token:
                logger.debug(f"[GitHubService] No auth token available, skipping remote URL update")
                return
            
            # Get current remote URL
            origin = repo.remotes.origin
            current_url = origin.url
            
            # Check if URL already has authentication
            if "@github.com" in current_url and not current_url.startswith("git@"):
                logger.debug(f"[GitHubService] Remote URL already authenticated")
                return
            
            # Update remote URL to include token
            if current_url.startswith("https://github.com/"):
                # HTTPS URL without token
                new_url = current_url.replace("https://", f"https://{auth_token}@")
                origin.set_url(new_url, origin.url)
                logger.debug(f"[GitHubService] Updated remote URL to use GitHub App token")
            elif current_url.startswith("git@github.com:"):
                # SSH URL - convert to HTTPS with token
                ssh_path = current_url.replace("git@github.com:", "").replace(".git", "")
                new_url = f"https://{auth_token}@github.com/{ssh_path}.git"
                origin.set_url(new_url, origin.url)
                logger.debug(f"[GitHubService] Converted SSH remote URL to HTTPS with token")
        except Exception as e:
            logger.warning(f"[GitHubService] Failed to update remote URL with token: {e}")
    
    def _ensure_workspace_writable(self) -> None:
        """Ensure workspace directory exists and is writable.
        
        Creates the directory if it doesn't exist and sets appropriate permissions.
        """
        try:
            # Create directory if it doesn't exist
            if not self.workspace_root.exists():
                self.workspace_root.mkdir(parents=True, exist_ok=True)
                # Set permissions to be writable by owner
                os.chmod(self.workspace_root, 0o755)
                print(f"Created workspace directory: {self.workspace_root}")
            else:
                # Check if directory is writable
                test_file = self.workspace_root / ".test_write"
                try:
                    test_file.touch()
                    test_file.unlink()
                except (OSError, PermissionError):
                    # Try to fix permissions
                    try:
                        os.chmod(self.workspace_root, 0o755)
                        # Test again
                        test_file.touch()
                        test_file.unlink()
                    except (OSError, PermissionError) as e:
                        raise PermissionError(
                            f"Workspace directory {self.workspace_root} is not writable. "
                            f"Please run: sudo chmod 755 {self.workspace_root} && sudo chown $(whoami) {self.workspace_root}"
                        ) from e
        except PermissionError:
            raise
        except Exception as e:
            raise OSError(
                f"Could not create or access workspace directory {self.workspace_root}: {e}"
            ) from e
    
    def _get_github_app_jwt(self) -> str | None:
        """Generate JWT token for GitHub App authentication.
        
        Returns:
            JWT token string or None if App credentials not configured
        """
        logger.debug(f"[GitHubService] _get_github_app_jwt called")
        if not settings.GITHUB_APP_ID or not settings.GITHUB_APP_PRIVATE_KEY:
            logger.debug(f"[GitHubService] Missing credentials: GITHUB_APP_ID={settings.GITHUB_APP_ID is not None}, GITHUB_APP_PRIVATE_KEY={settings.GITHUB_APP_PRIVATE_KEY is not None}")
            return None
        
        try:
            # Get private key (can be file path or PEM content)
            private_key = settings.GITHUB_APP_PRIVATE_KEY
            
            # If it's a file path, read it
            # Resolve relative paths relative to project root
            private_key_path = Path(private_key)
            if not private_key_path.is_absolute():
                # File is at: apps/api/src/optifiner_api/services/github_service.py
                # Project root is 6 levels up: services -> optifiner_api -> src -> api -> apps -> project_root
                project_root = Path(__file__).parent.parent.parent.parent.parent.parent
                private_key_path = project_root / private_key
            
            # Check if it's a file path (exists as a file)
            logger.debug(f"[GitHubService] Checking private key path: {private_key_path} (exists={private_key_path.exists()}, is_file={private_key_path.is_file() if private_key_path.exists() else False})")
            if private_key_path.exists() and private_key_path.is_file():
                try:
                    logger.debug(f"[GitHubService] Reading private key from file: {private_key_path}")
                    with open(private_key_path, "r") as f:
                        private_key = f.read()
                    logger.debug(f"[GitHubService] Private key read successfully (length={len(private_key)})")
                except Exception as e:
                    logger.error(f"[GitHubService] Error reading private key file {private_key_path}: {e}")
                    return None
            elif not private_key_path.exists():
                # If path doesn't exist, assume it's PEM content directly
                # (don't error here, let jwt.encode handle validation)
                logger.debug(f"[GitHubService] Private key path doesn't exist, treating as PEM content")
                pass
            
            # Validate that we have private key content
            if not private_key or not private_key.strip():
                logger.error(f"[GitHubService] Private key is empty. Path checked: {private_key_path}")
                return None
            
            # Generate JWT token
            logger.debug(f"[GitHubService] Generating JWT token with App ID: {settings.GITHUB_APP_ID}")
            now = int(time.time())
            payload = {
                "iat": now - 60,  # Issued at (1 minute ago to account for clock skew)
                "exp": now + (10 * 60),  # Expires in 10 minutes
                "iss": settings.GITHUB_APP_ID,  # Issuer (App ID)
            }
            
            token = jwt.encode(payload, private_key, algorithm="RS256")
            logger.debug(f"[GitHubService] JWT token generated successfully")
            return token
        except jwt.InvalidKeyError as e:
            logger.error(f"[GitHubService] Invalid private key format: {e}")
            logger.error(f"[GitHubService] Private key path checked: {private_key_path if 'private_key_path' in locals() else 'N/A'}")
            return None
        except Exception as e:
            logger.error(f"[GitHubService] Error generating GitHub App JWT: {e}")
            logger.error(f"[GitHubService] Private key path checked: {private_key_path if 'private_key_path' in locals() else 'N/A'}")
            return None
    
    def _get_installation_id(self) -> str | None:
        """Get installation ID for GitHub App using Client ID.
        
        Lists all installations and finds one that matches the Client ID,
        or uses the first available installation.
        
        Returns:
            Installation ID string or None if not found
        """
        # Return cached installation ID if available
        if self._cached_installation_id:
            return self._cached_installation_id
        
        if not settings.GITHUB_APP_CLIENT_ID:
            return None
        
        jwt_token = self._get_github_app_jwt()
        if not jwt_token:
            return None
        
        try:
            # List all installations for the app
            url = "https://api.github.com/app/installations"
            
            headers = {
                "Authorization": f"Bearer {jwt_token}",
                "Accept": "application/vnd.github.v3+json",
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            installations = response.json()
            
            if not installations:
                print("No installations found for GitHub App")
                return None
            
            # Use the first installation
            # All installations belong to the same app, so we can use any of them
            # If you have multiple installations and need a specific one,
            # you can filter by account (organization/user) here
            installation = installations[0]
            installation_id = str(installation.get("id"))
            
            if installation_id:
                self._cached_installation_id = installation_id
                return installation_id
                
        except Exception as e:
            print(f"Error getting installation ID: {e}")
            return None
        
        return None
    
    def _get_installation_token(self) -> str | None:
        """Get installation access token for GitHub App.
        
        Returns:
            Installation token string or None if not available
        """
        logger.debug(f"[GitHubService] _get_installation_token called")
        # Check if we have a cached valid token
        if self._github_app_token and time.time() < self._github_app_token_expires:
            logger.debug(f"[GitHubService] Using cached installation token")
            return self._github_app_token
        
        # Get installation ID using Client ID
        logger.debug(f"[GitHubService] Getting installation ID")
        installation_id = self._get_installation_id()
        if not installation_id:
            logger.debug(f"[GitHubService] Installation ID not found")
            return None
        logger.debug(f"[GitHubService] Installation ID: {installation_id}")
        
        jwt_token = self._get_github_app_jwt()
        if not jwt_token:
            logger.debug(f"[GitHubService] JWT token not available")
            return None
        logger.debug(f"[GitHubService] JWT token obtained")
        
        try:
            # Get installation token from GitHub API
            url = f"https://api.github.com/app/installations/{installation_id}/access_tokens"
            logger.debug(f"[GitHubService] Requesting installation token from: {url}")
            
            headers = {
                "Authorization": f"Bearer {jwt_token}",
                "Accept": "application/vnd.github.v3+json",
            }
            
            response = requests.post(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            token = data.get("token")
            expires_at = data.get("expires_at")
            logger.debug(f"[GitHubService] Installation token received, expires_at={expires_at}")
            
            if token:
                # Cache the token (expires in ~1 hour, cache for 50 minutes)
                self._github_app_token = token
                if expires_at:
                    # Parse ISO format timestamp
                    try:
                        # Handle both Z and +00:00 formats
                        exp_str = expires_at.replace("Z", "+00:00")
                        exp_time = datetime.fromisoformat(exp_str)
                        self._github_app_token_expires = exp_time.timestamp() - 600  # 10 min buffer
                    except Exception:
                        # Fallback if parsing fails
                        self._github_app_token_expires = time.time() + (50 * 60)  # 50 minutes
                else:
                    self._github_app_token_expires = time.time() + (50 * 60)  # 50 minutes
                
                logger.info(f"[GitHubService] Installation token obtained and cached")
                return token
        except Exception as e:
            logger.error(f"[GitHubService] Error getting installation token: {e}")
            return None
        
        return None
    
    def _get_github_client(self) -> Github | None:
        """Get GitHub client using GitHub App installation token.
        
        Returns:
            Github client instance or None if App not configured
        """
        installation_token = self._get_installation_token()
        if installation_token:
            return Github(installation_token)
        
        return None
    
    def _get_configuration_error(self) -> str:
        """Get detailed error message about missing GitHub App configuration.
        
        Returns:
            Error message describing what configuration is missing
        """
        missing = []
        
        if not settings.GITHUB_APP_ID:
            missing.append("GITHUB_APP_ID")
        
        if not settings.GITHUB_APP_PRIVATE_KEY:
            missing.append("GITHUB_APP_PRIVATE_KEY")
        
        if not settings.GITHUB_APP_CLIENT_ID:
            missing.append("GITHUB_APP_CLIENT_ID")
        
        if missing:
            return f"GitHub App not configured. Missing environment variables: {', '.join(missing)}. Please set these in your .env file or environment."
        
        # If all config is present but still failing, check JWT generation
        jwt_token = self._get_github_app_jwt()
        if not jwt_token:
            # Try to get more specific error info
            private_key = settings.GITHUB_APP_PRIVATE_KEY
            private_key_path = Path(private_key)
            if not private_key_path.is_absolute():
                project_root = Path(__file__).parent.parent.parent.parent.parent.parent
                private_key_path = project_root / private_key
            
            if private_key_path.exists() and private_key_path.is_file():
                return f"GitHub App configuration present but JWT token generation failed. Private key file found at {private_key_path} but could not be used. Check that the file contains valid PEM format private key."
            elif private_key_path.exists():
                return f"GitHub App configuration present but JWT token generation failed. Path {private_key_path} exists but is not a file."
            else:
                return f"GitHub App configuration present but JWT token generation failed. Private key path '{private_key}' (resolved to {private_key_path}) not found. Check that GITHUB_APP_PRIVATE_KEY is either a valid file path or contains PEM content directly."
        
        # Check installation ID
        installation_id = self._get_installation_id()
        if not installation_id:
            return "GitHub App JWT generated but installation ID not found. Check that GITHUB_APP_CLIENT_ID is correct and the app is installed."
        
        return "GitHub App configuration issue. Check logs for details."
    
    def _get_auth_token(self) -> str | None:
        """Get GitHub App installation token.
        
        Returns:
            Installation token string or None
        """
        return self._get_installation_token()

    def clone_repository(
        self,
        repo_url: str,
        branch: str | None = None,
        target_dir: str | None = None,
    ) -> dict[str, Any]:
        """Clone a GitHub repository (supports both public and private repos).

        For private repositories, authentication is handled via:
        - GitHub App: Uses installation token (required)
        - SSH: Uses SSH keys if configured

        Args:
            repo_url: GitHub repository URL (https or git format)
            branch: Branch to clone (default: default branch)
            target_dir: Target directory name (default: repo name)

        Returns:
            Dictionary with clone information
        """
        logger.debug(f"[GitHubService] clone_repository called: repo_url={repo_url}, branch={branch}, target_dir={target_dir}")
        try:
            # Extract repo name from URL (before modifying for auth)
            original_url = repo_url
            if repo_url.endswith(".git"):
                repo_url = repo_url[:-4]
            repo_name = repo_url.split("/")[-1]
            logger.debug(f"[GitHubService] Extracted repo_name: {repo_name}")

            # Determine target directory
            if target_dir is None:
                target_dir = repo_name

            target_path = self.workspace_root / target_dir
            logger.debug(f"[GitHubService] Target path: {target_path}")

            # Remove existing directory if it exists
            if target_path.exists():
                logger.debug(f"[GitHubService] Removing existing directory: {target_path}")
                shutil.rmtree(target_path)

            # Prepare authenticated URL for private repos
            clone_url = original_url
            
            # Check if URL is already authenticated or in SSH format
            is_ssh = clone_url.startswith("git@") or clone_url.startswith("ssh://")
            is_authenticated = "@github.com" in clone_url and not is_ssh
            logger.debug(f"[GitHubService] URL analysis: is_ssh={is_ssh}, is_authenticated={is_authenticated}")
            
            # For HTTPS URLs without authentication, add token if available
            # Use GitHub App installation token
            auth_token = self._get_auth_token()
            logger.debug(f"[GitHubService] Auth token available: {auth_token is not None}")
            if not is_ssh and not is_authenticated and "github.com" in clone_url and auth_token:
                # If it's an HTTPS URL and we have a token, add authentication
                if clone_url.startswith("https://"):
                    # Insert token into URL: https://github.com/owner/repo -> https://TOKEN@github.com/owner/repo
                    clone_url = clone_url.replace("https://", f"https://{auth_token}@")
                    logger.debug(f"[GitHubService] Added auth token to HTTPS URL")
                elif clone_url.startswith("http://"):
                    # Handle http:// URLs
                    clone_url = clone_url.replace("http://", f"http://{auth_token}@")
                    logger.debug(f"[GitHubService] Added auth token to HTTP URL")
            
            # Try cloning with authentication
            last_error = None
            repo = None
            logger.debug(f"[GitHubService] Attempting to clone: branch={branch}")
            
            try:
                if branch:
                    logger.debug(f"[GitHubService] Cloning with branch: {branch}")
                    repo = Repo.clone_from(clone_url, str(target_path), branch=branch)
                else:
                    logger.debug(f"[GitHubService] Cloning default branch")
                    repo = Repo.clone_from(clone_url, str(target_path))
                logger.debug(f"[GitHubService] Clone successful")
            except Exception as e:
                last_error = str(e)
                logger.warning(f"[GitHubService] Clone failed: {last_error}")
                
                # If HTTPS with token failed and URL was HTTPS, try SSH format as fallback
                if (clone_url.startswith("https://") or clone_url.startswith("http://")) and not is_ssh:
                    logger.debug(f"[GitHubService] Attempting SSH fallback")
                    # Convert to SSH format: https://github.com/owner/repo -> git@github.com:owner/repo.git
                    ssh_url = clone_url
                    
                    # Remove token if present: https://TOKEN@github.com/owner/repo -> github.com/owner/repo
                    if "@github.com" in ssh_url:
                        parts = ssh_url.split("@")
                        if len(parts) > 1:
                            ssh_url = parts[-1]  # Take everything after @
                    
                    # Remove protocol
                    ssh_url = ssh_url.replace("https://", "").replace("http://", "")
                    
                    # Convert to SSH format
                    if "github.com/" in ssh_url:
                        ssh_url = ssh_url.replace("github.com/", "github.com:")
                    elif "github.com:" not in ssh_url and "github.com" in ssh_url:
                        ssh_url = ssh_url.replace("github.com", "github.com:")
                    
                    ssh_url = f"git@{ssh_url}"
                    if not ssh_url.endswith(".git"):
                        ssh_url = f"{ssh_url}.git"
                    
                    logger.debug(f"[GitHubService] Converted to SSH URL: {ssh_url}")
                    
                    # Try SSH clone as fallback
                    try:
                        if branch:
                            repo = Repo.clone_from(ssh_url, str(target_path), branch=branch)
                        else:
                            repo = Repo.clone_from(ssh_url, str(target_path))
                        clone_url = ssh_url  # Update for logging
                        logger.debug(f"[GitHubService] SSH clone successful")
                    except Exception as ssh_error:
                        # SSH also failed, return combined error
                        last_error = f"HTTPS failed: {last_error}; SSH fallback failed: {str(ssh_error)}"
                        logger.error(f"[GitHubService] SSH fallback also failed: {ssh_error}")
                        raise Exception(last_error)
                else:
                    # Not an HTTPS URL or already SSH, just raise the original error
                    raise

            if repo is None:
                raise Exception(last_error or "Failed to clone repository")

            # Update remote URL to use GitHub App token to prevent password prompts
            try:
                self._update_remote_url_with_token(repo, target_path)
            except Exception as e:
                logger.warning(f"[GitHubService] Failed to update remote URL after clone: {e}")

            result = {
                "success": True,
                "path": str(target_path),
                "repo_name": repo_name,
                "branch": repo.active_branch.name if repo.active_branch else None,
                "commit": repo.head.commit.hexsha,
            }
            logger.info(f"[GitHubService] Clone completed successfully: {result}")
            return result
        except Exception as e:
            error_msg = str(e)
            logger.error(f"[GitHubService] Clone failed with error: {error_msg}")
            return {
                "success": False,
                "error": error_msg,
            }

    def create_branch(
        self,
        repo_dir: str,
        branch_name: str,
        from_branch: str | None = None,
    ) -> dict[str, Any]:
        """Create a new branch in the repository using GitHub API.

        Args:
            repo_dir: Directory name of the repository
            branch_name: Name of the new branch to create
            from_branch: Branch to create from (default: default branch)

        Returns:
            Dictionary with branch creation information
        """
        logger.debug(f"[GitHubService] create_branch called: repo_dir={repo_dir}, branch_name={branch_name}, from_branch={from_branch}")
        
        if not self.github:
            error = self._get_configuration_error()
            logger.error(f"[GitHubService] GitHub client not available: {error}")
            return {
                "success": False,
                "error": error,
            }

        try:
            repo_path = self.workspace_root / repo_dir
            logger.debug(f"[GitHubService] Repository path: {repo_path}")

            if not repo_path.exists():
                error = f"Repository directory not found: {repo_dir}"
                logger.error(f"[GitHubService] {error}")
                return {
                    "success": False,
                    "error": error,
                }

            # Get repository info from local git to find owner/repo
            local_repo = Repo(str(repo_path))
            
            # Update remote URL to use GitHub App token to prevent password prompts
            try:
                self._update_remote_url_with_token(local_repo, repo_path)
            except Exception as e:
                logger.warning(f"[GitHubService] Failed to update remote URL: {e}")
            
            remote_url = local_repo.remotes.origin.url
            logger.debug(f"[GitHubService] Remote URL: {remote_url}")
            
            # Parse remote URL to get owner and repo name
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
                    logger.debug(f"[GitHubService] Parsed owner={owner}, repo_name={repo_name}")
                else:
                    error = f"Could not parse repository owner/name from URL: {remote_url}"
                    logger.error(f"[GitHubService] {error}")
                    return {
                        "success": False,
                        "error": error,
                    }
            else:
                error = f"Repository remote URL is not a GitHub repository: {remote_url}"
                logger.error(f"[GitHubService] {error}")
                return {
                    "success": False,
                    "error": error,
                }

            # Get GitHub repository object
            logger.debug(f"[GitHubService] Getting GitHub repo: {owner}/{repo_name}")
            github_repo = self.github.get_repo(f"{owner}/{repo_name}")
            
            # Check if branch already exists on GitHub
            try:
                logger.debug(f"[GitHubService] Checking if branch {branch_name} already exists")
                existing_branch = github_repo.get_branch(branch_name)
                logger.debug(f"[GitHubService] Branch already exists, checking out locally")
                # Branch exists on GitHub, checkout locally and return
                try:
                    local_repo.git.checkout(branch_name)
                except Exception:
                    # Create local branch tracking remote
                    local_repo.git.checkout("-b", branch_name, f"origin/{branch_name}")
                
                result = {
                    "success": True,
                    "branch": branch_name,
                    "message": f"Branch already exists on GitHub: {branch_name}",
                    "commit": existing_branch.commit.sha,
                }
                logger.info(f"[GitHubService] Branch already exists: {result}")
                return result
            except Exception:
                # Branch doesn't exist, create it
                logger.debug(f"[GitHubService] Branch does not exist, will create it")
                pass

            # Get source branch SHA
            if from_branch:
                logger.debug(f"[GitHubService] Getting source branch: {from_branch}")
                try:
                    source_branch = github_repo.get_branch(from_branch)
                    source_sha = source_branch.commit.sha
                    logger.debug(f"[GitHubService] Source branch SHA: {source_sha}")
                except Exception as e:
                    error = f"Source branch '{from_branch}' not found on GitHub: {e}"
                    logger.error(f"[GitHubService] {error}")
                    return {
                        "success": False,
                        "error": error,
                    }
            else:
                # Use default branch
                default_branch = github_repo.default_branch
                logger.debug(f"[GitHubService] Using default branch: {default_branch}")
                source_branch = github_repo.get_branch(default_branch)
                source_sha = source_branch.commit.sha
                from_branch = default_branch
                logger.debug(f"[GitHubService] Default branch SHA: {source_sha}")

            # Create branch via GitHub API
            logger.debug(f"[GitHubService] Creating branch via GitHub API: refs/heads/{branch_name} from {source_sha}")
            ref = github_repo.create_git_ref(
                ref=f"refs/heads/{branch_name}",
                sha=source_sha
            )
            logger.debug(f"[GitHubService] Branch created successfully via API")

            # Update local repository to track the new branch
            try:
                logger.debug(f"[GitHubService] Updating local repository to track new branch")
                local_repo.git.fetch("origin")
                local_repo.git.checkout("-b", branch_name, f"origin/{branch_name}")
                logger.debug(f"[GitHubService] Local repository updated")
            except Exception as e:
                # If local checkout fails, that's okay - branch exists on GitHub
                logger.warning(f"[GitHubService] Local checkout failed (non-critical): {e}")

            result = {
                "success": True,
                "branch": branch_name,
                "from_branch": from_branch,
                "commit": source_sha,
            }
            logger.info(f"[GitHubService] Branch created successfully: {result}")
            return result
        except Exception as e:
            error_msg = str(e)
            logger.error(f"[GitHubService] create_branch failed: {error_msg}")
            return {
                "success": False,
                "error": error_msg,
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
                "error": self._get_configuration_error(),
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
        branch: str,
        files: list[str] | None = None,
    ) -> dict[str, Any]:
        """Commit changes to the repository on a specific branch using GitHub API.

        Commits will be attributed to the GitHub App automatically.

        Args:
            repo_dir: Directory name of the repository
            commit_message: Commit message
            branch: Branch name (required - must be a branch created by the service)
            files: List of specific files to commit (None = all changes)

        Returns:
            Dictionary with commit information
        """
        if not self.github:
            return {
                "success": False,
                "error": self._get_configuration_error(),
            }

        try:
            repo_path = self.workspace_root / repo_dir

            if not repo_path.exists():
                return {
                    "success": False,
                    "error": f"Repository directory not found: {repo_dir}",
                }

            # Get repository info from local git to find owner/repo
            local_repo = Repo(str(repo_path))
            
            # Update remote URL to use GitHub App token to prevent password prompts
            try:
                self._update_remote_url_with_token(local_repo, repo_path)
            except Exception as e:
                logger.warning(f"[GitHubService] Failed to update remote URL: {e}")
            
            remote_url = local_repo.remotes.origin.url
            
            # Parse remote URL to get owner and repo name
            # Handle both https://github.com/owner/repo.git and git@github.com:owner/repo.git
            if "github.com" in remote_url:
                if remote_url.startswith("git@"):
                    # SSH format: git@github.com:owner/repo.git
                    repo_path_part = remote_url.split(":")[-1].replace(".git", "")
                else:
                    # HTTPS format: https://github.com/owner/repo.git or https://TOKEN@github.com/owner/repo.git
                    repo_path_part = remote_url.split("github.com/")[-1].replace(".git", "")
                    # Remove token if present
                    if "@" in repo_path_part:
                        repo_path_part = repo_path_part.split("@")[-1]
                
                parts = repo_path_part.split("/")
                if len(parts) >= 2:
                    owner = parts[0]
                    repo_name = parts[1]
                else:
                    return {
                        "success": False,
                        "error": f"Could not parse repository owner/name from URL: {remote_url}",
                    }
            else:
                return {
                    "success": False,
                    "error": f"Repository remote URL is not a GitHub repository: {remote_url}",
                }

            # Get GitHub repository object
            github_repo = self.github.get_repo(f"{owner}/{repo_name}")
            
            # Get the branch reference - we'll reuse this object to update it later
            # Also store the ref path format we used so we can use it later
            branch_ref = None
            ref_path = None
            try:
                # Use full ref path: refs/heads/{branch}
                ref_path = f"refs/heads/{branch}"
                branch_ref = github_repo.get_git_ref(ref_path)
                base_sha = branch_ref.object.sha
            except Exception as e:
                # Try without refs/ prefix as fallback
                try:
                    ref_path = f"heads/{branch}"
                    branch_ref = github_repo.get_git_ref(ref_path)
                    base_sha = branch_ref.object.sha
                except Exception:
                    return {
                        "success": False,
                        "error": f"Branch '{branch}' not found on GitHub. Tried 'refs/heads/{branch}' and 'heads/{branch}'. Error: {e}",
                    }

            # Get the base commit to get its tree SHA and use it as parent
            try:
                base_commit = github_repo.get_git_commit(base_sha)
                base_tree_sha = base_commit.tree.sha
            except Exception as e:
                return {
                    "success": False,
                    "error": f"Failed to get base commit: {e}",
                }
            
            # Get the base tree using the tree SHA from the commit
            try:
                base_tree = github_repo.get_git_tree(base_tree_sha, recursive=True)
            except Exception as e:
                return {
                    "success": False,
                    "error": f"Failed to get base tree: {e}",
                }

            # Collect file changes
            file_changes = []
            deleted_files = set()
            
            if files:
                # Commit specific files - check if they exist or are deleted
                for file_path in files:
                    full_path = repo_path / file_path
                    if full_path.exists():
                        with open(full_path, "rb") as f:
                            content = f.read()
                        file_changes.append({
                            "path": file_path,
                            "content": content,
                            "mode": "100644",  # Regular file
                        })
                    else:
                        # File doesn't exist - check if it was deleted (exists in base tree)
                        # We'll track it as deleted
                        deleted_files.add(file_path)
            else:
                # Commit all changes - find modified/added/deleted files
                # Stage all changes (including untracked files) so we can detect them consistently
                local_repo.git.add("-A")
                
                # Check status to see what's staged
                # After git add -A, all changes should be staged
                status = local_repo.git.status("--porcelain", "--untracked-files=all")
                
                if not status.strip():
                    return {
                        "success": False,
                        "error": "No changes to commit",
                    }
                
                # Parse status to get changed files
                # Git status format: XY filename
                # X = status of index, Y = status of working tree
                # After git add -A, all changes are staged:
                #   A  = added (staged, not in working tree)
                #   M  = modified (staged)
                #   D  = deleted (staged)
                #   R  = renamed (staged)
                #   ?? = untracked (shouldn't happen after git add -A, but handle it)
                for line in status.strip().split("\n"):
                    if not line.strip():
                        continue
                    
                    # Status code is first 2 characters, rest is filename
                    status_code = line[:2]
                    # Handle renamed files (R100 old -> new)
                    if status_code[0] == "R":
                        # Format: "R100 old_file -> new_file"
                        parts = line[3:].strip().split(" -> ")
                        if len(parts) == 2:
                            file_path = parts[1].strip()
                        else:
                            continue
                    else:
                        file_path = line[3:].strip()
                    
                    # Remove quotes if present
                    if file_path.startswith('"') and file_path.endswith('"'):
                        file_path = file_path[1:-1]
                    
                    # Handle deleted files first (D = deleted from index/staged)
                    if status_code[0] == "D" or status_code == "DD":
                        deleted_files.add(file_path)
                    # Handle untracked files (??) - fallback in case git add -A didn't catch them
                    elif status_code == "??":
                        full_path = repo_path / file_path
                        if full_path.exists() and full_path.is_file():
                            with open(full_path, "rb") as f:
                                content = f.read()
                            file_changes.append({
                                "path": file_path,
                                "content": content,
                                "mode": "100644",  # Regular file
                            })
                    # Handle modified files (M = modified in index/staged)
                    elif status_code[0] == "M":
                        full_path = repo_path / file_path
                        if full_path.exists() and full_path.is_file():
                            with open(full_path, "rb") as f:
                                content = f.read()
                            file_changes.append({
                                "path": file_path,
                                "content": content,
                                "mode": "100644",  # Regular file
                            })
                    # Handle added files (A = added to index/staged)
                    elif status_code[0] == "A":
                        full_path = repo_path / file_path
                        if full_path.exists() and full_path.is_file():
                            with open(full_path, "rb") as f:
                                content = f.read()
                            file_changes.append({
                                "path": file_path,
                                "content": content,
                                "mode": "100644",  # Regular file
                            })

            if not file_changes and not deleted_files:
                return {
                    "success": False,
                    "error": "No file changes to commit",
                }

            # Create blobs only for changed files (new/modified)
            tree_entries = []
            
            for file_change in file_changes:
                blob = github_repo.create_git_blob(
                    base64.b64encode(file_change["content"]).decode("utf-8"),
                    "base64"
                )
                # Use InputGitTreeElement for proper format
                tree_entries.append(
                    InputGitTreeElement(
                        path=file_change["path"],
                        mode=file_change["mode"],
                        type="blob",
                        sha=blob.sha,
                    )
                )

            # For deleted files, we need to explicitly remove them from the tree
            # by not including them. When using base_tree.sha, files not in tree_entries
            # will be kept from the base tree. To delete, we need to rebuild the tree
            # without those files. However, PyGithub's create_git_tree with base_tree.sha
            # will keep files from base that aren't in our tree_entries.
            # So we need to explicitly include all unchanged files except deleted ones.
            try:
                if deleted_files:
                    # Get all files from base tree and exclude deleted ones
                    if hasattr(base_tree, 'tree') and base_tree.tree:
                        for item in base_tree.tree:
                            if item.path not in deleted_files:
                                # Only include if not already in tree_entries (not changed)
                                # Check if path already exists in tree_entries
                                if not any(
                                    (isinstance(te, InputGitTreeElement) and te.path == item.path) or
                                    (isinstance(te, dict) and te.get("path") == item.path)
                                    for te in tree_entries
                                ):
                                    tree_entries.append(
                                        InputGitTreeElement(
                                            path=item.path,
                                            mode=item.mode,
                                            type=item.type,
                                            sha=item.sha,
                                        )
                                    )
                    # Create tree without base_tree since we're explicitly including all files
                    if not tree_entries:
                        return {
                            "success": False,
                            "error": "No files to include in tree after processing deletions",
                        }
                    new_tree = github_repo.create_git_tree(tree_entries)
                    # Verify we got a GitTree object, not a list
                    if isinstance(new_tree, list):
                        return {
                            "success": False,
                            "error": f"create_git_tree returned a list instead of GitTree object. This should not happen.",
                        }
                    if not hasattr(new_tree, 'sha'):
                        return {
                            "success": False,
                            "error": f"Failed to create git tree: tree object missing SHA attribute. Type: {type(new_tree)}",
                        }
                else:
                    # No deletions - only changed files, use base_tree to include all others
                    # PyGithub will automatically include all files from base_tree
                    # and override with our tree_entries
                    if tree_entries:
                        # Pass base_tree as keyword argument - use the GitTree object directly
                        # PyGithub accepts either GitTree object or SHA string
                        try:
                            new_tree = github_repo.create_git_tree(tree_entries, base_tree=base_tree)
                        except Exception as e:
                            # If passing GitTree object fails, try with SHA string
                            try:
                                new_tree = github_repo.create_git_tree(tree_entries, base_tree=base_tree.sha)
                            except Exception as e2:
                                return {
                                    "success": False,
                                    "error": f"Failed to create git tree with base_tree: {e}. Also failed with SHA: {e2}",
                                }
                        # Verify we got a GitTree object, not a list
                        if isinstance(new_tree, list):
                            return {
                                "success": False,
                                "error": f"create_git_tree returned a list instead of GitTree object. This should not happen.",
                            }
                        if not hasattr(new_tree, 'sha'):
                            return {
                                "success": False,
                                "error": f"Failed to create git tree: tree object missing SHA attribute. Type: {type(new_tree)}",
                            }
                    else:
                        return {
                            "success": False,
                            "error": "No file changes to commit",
                        }
            except Exception as tree_error:
                # Get more details about the error
                error_msg = str(tree_error)
                error_type = type(tree_error).__name__
                return {
                    "success": False,
                    "error": f"Failed to create git tree ({error_type}): {error_msg}. Tree entries: {len(tree_entries)} files, Base tree SHA: {base_tree.sha if hasattr(base_tree, 'sha') else 'N/A'}",
                }

            # Create commit
            try:
                # Verify we have a valid tree object
                if not hasattr(new_tree, 'sha') or not new_tree.sha:
                    return {
                        "success": False,
                        "error": f"Invalid tree object: {type(new_tree)}. Expected tree with SHA attribute.",
                    }
                
                # Create the commit with proper error handling
                # parents must be a list of GitCommit objects, not SHA strings
                # tree must be a GitTree object
                # author and committer are omitted - GitHub will use the authenticated GitHub App's identity automatically
                try:
                    commit = github_repo.create_git_commit(
                        message=commit_message,
                        tree=new_tree,  # Pass GitTree object
                        parents=[base_commit],  # Use GitCommit object, not SHA string
                        # author and committer omitted - will use GitHub App identity automatically
                    )
                except Exception as commit_error:
                    # Get more details about the error
                    error_type = type(commit_error).__name__
                    error_msg = str(commit_error)
                    error_details = f"{error_type}: {error_msg}"
                    
                    # Check if it's a GitHub API error with more details
                    if hasattr(commit_error, 'data') and commit_error.data:
                        error_details += f" | API Data: {commit_error.data}"
                    if hasattr(commit_error, 'status') and commit_error.status:
                        error_details += f" | Status: {commit_error.status}"
                    
                    return {
                        "success": False,
                        "error": f"Failed to create commit: {error_details}. Tree SHA: {new_tree.sha}, Base SHA: {base_sha}, Files changed: {len(file_changes)}, Files deleted: {len(deleted_files)}",
                    }
                
                # Verify commit was created
                if not hasattr(commit, 'sha') or not commit.sha:
                    return {
                        "success": False,
                        "error": f"Commit created but missing SHA: {type(commit)}",
                    }
            except Exception as commit_error:
                # Fallback error handling
                error_type = type(commit_error).__name__
                error_msg = str(commit_error)
                return {
                    "success": False,
                    "error": f"Failed to create commit ({error_type}): {error_msg}. Tree SHA: {new_tree.sha if hasattr(new_tree, 'sha') else 'N/A'}, Base SHA: {base_sha}, Files changed: {len(file_changes)}, Files deleted: {len(deleted_files)}",
                }

            # Update branch reference to point to the new commit
            # Use the branch_ref we got earlier - it should still be valid
            try:
                # Update the reference to point to our new commit
                # Use force=False first (fast-forward update)
                branch_ref.edit(commit.sha, force=False)
                
                # Wait a moment for GitHub to process the update
                import time
                time.sleep(0.5)
                
                # Verify the update worked by refreshing the reference using the same path format
                verify_ref = github_repo.get_git_ref(ref_path)
                
                if verify_ref.object.sha != commit.sha:
                    # Update didn't work, try with force
                    branch_ref.edit(commit.sha, force=True)
                    time.sleep(0.5)
                    # Verify again using the same path format
                    verify_ref = github_repo.get_git_ref(ref_path)
                    
                    if verify_ref.object.sha != commit.sha:
                        return {
                            "success": False,
                            "error": f"Failed to update branch reference. Expected: {commit.sha}, Got: {verify_ref.object.sha}. Commit was created but branch not updated.",
                        }
            except Exception as ref_error:
                # If the original branch_ref.edit() fails, try to get a fresh ref and update it
                # This can happen if the ref object is stale or the branch was updated
                try:
                    # Try to get a fresh reference using the same path format we used before
                    fresh_ref = github_repo.get_git_ref(ref_path)
                    
                    # Try to update with force=True
                    fresh_ref.edit(commit.sha, force=True)
                    import time
                    time.sleep(0.5)
                    
                    # Verify using the same path format
                    verify_ref = github_repo.get_git_ref(ref_path)
                    
                    if verify_ref.object.sha != commit.sha:
                        return {
                            "success": False,
                            "error": f"Failed to update branch reference with force: {ref_error}. Commit created: {commit.sha}, Branch SHA: {verify_ref.object.sha}",
                        }
                except Exception as force_error:
                    # If we still can't update, return error with commit SHA so user knows commit was created
                    return {
                        "success": False,
                        "error": f"Failed to update branch reference: {force_error}. Commit was created successfully (SHA: {commit.sha}) but branch '{branch}' could not be updated. You may need to manually update the branch or check permissions.",
                    }

            # Final verification: check that the branch actually points to our commit
            try:
                # Use the same ref path format we used before
                final_ref = github_repo.get_git_ref(ref_path)
                
                if final_ref.object.sha != commit.sha:
                    return {
                        "success": False,
                        "error": f"Commit created ({commit.sha}) but branch reference not updated. Branch points to: {final_ref.object.sha}",
                    }
            except Exception as verify_error:
                # If verification fails, the commit was still created, so we'll return success
                # but include a warning that verification failed
                return {
                    "success": True,
                    "commit": commit.sha,
                    "commit_message": commit_message,
                    "branch": branch,
                    "files_committed": [fc["path"] for fc in file_changes],
                    "warning": f"Commit created but verification failed: {verify_error}",
                }
            
            return {
                "success": True,
                "commit": commit.sha,
                "commit_message": commit_message,
                "branch": branch,
                "files_committed": [fc["path"] for fc in file_changes],
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }

    def push_changes(
        self,
        repo_dir: str,
        branch: str,
        force: bool = False,
    ) -> dict[str, Any]:
        """Sync local repository with remote after GitHub API commits.

        Since commits are created via GitHub API, they're already on the remote.
        This method fetches the latest changes to sync the local repository.

        Args:
            repo_dir: Directory name of the repository
            branch: Branch name (required)
            force: Not used (kept for compatibility, commits via API can't be force-pushed)

        Returns:
            Dictionary with sync information
        """
        try:
            repo_path = self.workspace_root / repo_dir

            if not repo_path.exists():
                return {
                    "success": False,
                    "error": f"Repository directory not found: {repo_dir}",
                }

            repo = Repo(str(repo_path))

            # Update remote URL to use GitHub App token to prevent password prompts
            try:
                self._update_remote_url_with_token(repo, repo_path)
            except Exception as e:
                logger.warning(f"[GitHubService] Failed to update remote URL: {e}")

            # Checkout the branch if not already on it
            try:
                if repo.active_branch and repo.active_branch.name != branch:
                    repo.heads[branch].checkout()
                elif not repo.active_branch:
                    # In detached HEAD, checkout the branch
                    repo.heads[branch].checkout()
            except Exception:
                # Branch might not exist locally, fetch and checkout
                repo.git.fetch("origin")
                try:
                    repo.git.checkout("-b", branch, f"origin/{branch}")
                except Exception:
                    return {
                        "success": False,
                        "error": f"Branch '{branch}' not found locally or on remote",
                    }

            # Fetch latest from remote to sync with GitHub API commits
            try:
                origin = repo.remotes.origin
                origin.fetch()
                
                # Pull to update local branch with remote changes
                origin.pull(branch)
                
                return {
                    "success": True,
                    "branch": branch,
                    "message": "Local repository synced with remote (commits were already on GitHub via API)",
                }
            except Exception as e:
                return {
                    "success": False,
                    "error": f"Failed to sync local repository: {str(e)}",
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
                "error": self._get_configuration_error(),
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
