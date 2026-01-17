"""Tests for GitHub service operations on private repositories."""

import os
import sys
import tempfile
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from optifiner_api.services.github_service import GitHubService
from optifiner_api.config import settings


def _get_test_repo():
    """Get test private repository URL from environment or use default."""
    test_repo = os.getenv("TEST_PRIVATE_REPO", "https://github.com/anselmlong/stuckincom1again")
    return test_repo


def _check_auth():
    """Check if GitHub App is configured."""
    has_app = bool(
        settings.GITHUB_APP_ID
        and settings.GITHUB_APP_PRIVATE_KEY
        and settings.GITHUB_APP_CLIENT_ID
    )
    if not has_app:
        raise ValueError(
            "GitHub App not configured. Required: "
            "GITHUB_APP_ID, GITHUB_APP_PRIVATE_KEY, GITHUB_APP_CLIENT_ID"
        )


def test_clone_repository():
    """Test cloning a private repository."""
    print("\n=== Testing clone_repository (Private Repo) ===")
    
    _check_auth()
    test_repo = _get_test_repo()
    
    service = GitHubService()
    assert service.github is not None, "GitHub client not available - check App configuration"
    
    result = service.clone_repository(
        repo_url=test_repo,
        branch=None,  # Use default branch
        target_dir=None,  # Use original repository name
    )
    
    print(f"Clone result: {result}")
    assert result.get("success"), f"Clone failed: {result.get('error')}"
    assert result.get("repo_name") is not None
    assert result.get("branch") is not None
    print("✓ Clone private repository test passed")


def test_create_branch():
    """Test creating a new branch in private repository."""
    print("\n=== Testing create_branch (Private Repo) ===")
    
    _check_auth()
    test_repo = _get_test_repo()
    
    service = GitHubService()
    assert service.github is not None, "GitHub client not available"
    
    # First clone the private repo
    clone_result = service.clone_repository(
        repo_url=test_repo,
        target_dir="test-branch-repo",
    )
    
    assert clone_result.get("success"), f"Clone failed: {clone_result.get('error')}"
    
    # Create a new branch
    branch_result = service.create_branch(
        repo_dir="test-branch-repo",
        branch_name="test-optifiner-branch",
        from_branch=clone_result.get("branch"),
    )
    
    print(f"Branch creation result: {branch_result}")
    assert branch_result.get("success"), f"Branch creation failed: {branch_result.get('error')}"
    assert branch_result.get("branch") == "test-optifiner-branch"
    print("✓ Create branch test passed")


def test_get_repository_status():
    """Test getting repository status for private repository."""
    print("\n=== Testing get_repository_status (Private Repo) ===")
    
    _check_auth()
    test_repo = _get_test_repo()
    
    service = GitHubService()
    assert service.github is not None, "GitHub client not available"
    
    # First clone the private repo
    clone_result = service.clone_repository(
        repo_url=test_repo,
        target_dir="test-status-repo",
    )
    
    assert clone_result.get("success"), f"Clone failed: {clone_result.get('error')}"
    
    # Get repository status
    status_result = service.get_repository_status("test-status-repo")
    
    print(f"Status result: {status_result}")
    assert status_result.get("success"), f"Status check failed: {status_result.get('error')}"
    assert "branch" in status_result
    assert "commit" in status_result
    print("✓ Get repository status test passed")


def test_list_repositories():
    """Test listing repositories."""
    print("\n=== Testing list_repositories ===")
    
    service = GitHubService()
    
    repos = service.list_repositories()
    
    print(f"Found {len(repos)} repositories")
    print(f"Repositories: {[r.get('name') for r in repos]}")
    assert isinstance(repos, list)
    print("✓ List repositories test passed")


def test_commit_changes():
    """Test committing changes to private repository."""
    print("\n=== Testing commit_changes (Private Repo) ===")
    
    _check_auth()
    test_repo = _get_test_repo()
    
    service = GitHubService()
    assert service.github is not None, "GitHub client not available"
    
    # First clone the private repo
    clone_result = service.clone_repository(
        repo_url=test_repo,
        target_dir="test-commit-repo",
    )
    
    assert clone_result.get("success"), f"Clone failed: {clone_result.get('error')}"
    
    # Create a test branch
    branch_result = service.create_branch(
        repo_dir="test-commit-repo",
        branch_name="test-commit-branch",
    )
    
    assert branch_result.get("success"), f"Branch creation failed: {branch_result.get('error')}"
    
    # Create a test file
    repo_path = Path(service.workspace_root) / "test-commit-repo"
    test_file = repo_path / "test_file.txt"
    test_file.write_text("Test content for commit")
    
    # Commit the change
    commit_result = service.commit_changes(
        repo_dir="test-commit-repo",
        commit_message="Test commit from optifiner",
        branch="test-commit-branch",
    )
    
    print(f"Commit result: {commit_result}")
    if commit_result.get("success"):
        print("✓ Commit changes test passed")
    else:
        print(f"⚠ Commit test result: {commit_result.get('error')}")


def test_get_repository_info():
    """Test getting repository info from GitHub API for private repository."""
    print("\n=== Testing get_repository_info (Private Repo) ===")
    
    _check_auth()
    test_repo = _get_test_repo()
    
    service = GitHubService()
    assert service.github is not None, "GitHub client not available"
    
    # Parse owner and repo from URL
    repo_url_parts = test_repo.replace(".git", "").rstrip("/").split("/")
    repo_owner = repo_url_parts[-2]
    repo_name = repo_url_parts[-1]
    
    result = service.get_repository_info(repo_owner, repo_name)
    
    print(f"Repository info result: {result}")
    assert result.get("success"), f"Failed to get repo info: {result.get('error')}"
    assert "name" in result
    assert "full_name" in result
    print("✓ Get repository info test passed")


def run_all_tests():
    """Run all GitHub service tests on private repository."""
    print("=" * 60)
    print("GitHub Service Tests (Private Repository)")
    print("=" * 60)
    print("\n⚠ These tests require:")
    print("   1. GitHub App configured (GITHUB_APP_ID, GITHUB_APP_PRIVATE_KEY, GITHUB_APP_CLIENT_ID)")
    print("   2. The GitHub App must have access to the private repository")
    print(f"\nDefault test repository: {_get_test_repo()}")
    print("   Override with: export TEST_PRIVATE_REPO=https://github.com/owner/repo")
    print()
    
    try:
        test_clone_repository()
        test_create_branch()
        test_get_repository_status()
        test_list_repositories()
        test_commit_changes()
        test_get_repository_info()
        
        print("\n" + "=" * 60)
        print("All tests completed!")
        print("=" * 60)
    except ValueError as e:
        print(f"\n❌ Configuration error: {e}")
        print("\nPlease ensure:")
        print("  - TEST_PRIVATE_REPO is set to a private repository URL")
        print("  - GitHub App is fully configured in .env file")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    run_all_tests()
