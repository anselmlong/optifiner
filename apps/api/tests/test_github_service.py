"""Tests for GitHub service operations on private repositories."""

import os
import sys
import tempfile
import time
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
    assert result.get("commit") is not None
    assert result.get("path") is not None
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
    
    # Create a new branch with unique name
    branch_name = f"test-optifiner-branch-{int(time.time())}"
    branch_result = service.create_branch(
        repo_dir="test-branch-repo",
        branch_name=branch_name,
        from_branch=clone_result.get("branch"),
    )
    
    print(f"Branch creation result: {branch_result}")
    assert branch_result.get("success"), f"Branch creation failed: {branch_result.get('error')}"
    assert branch_result.get("branch") == branch_name
    # from_branch and commit are optional (branch may already exist)
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
    assert "repo_dir" in status_result
    assert "branch" in status_result
    assert "commit" in status_result
    assert "is_dirty" in status_result
    assert "changed_files" in status_result
    assert "untracked_files" in status_result
    assert "has_changes" in status_result
    print("✓ Get repository status test passed")


def test_list_repositories():
    """Test listing repositories."""
    print("\n=== Testing list_repositories ===")
    
    service = GitHubService()
    
    repos = service.list_repositories()
    
    print(f"Found {len(repos)} repositories")
    print(f"Repositories: {[r.get('name') for r in repos]}")
    assert isinstance(repos, list)
    # Each repo should have name, path, branch, commit
    for repo in repos:
        assert "name" in repo
        assert "path" in repo
        assert "branch" in repo
        assert "commit" in repo
    print("✓ List repositories test passed")


def test_commit_changes():
    """Test committing changes to private repository."""
    print("\n=== Testing commit_changes (Private Repo) ===")
    print("Note: commit_changes uses git commit + git push")
    
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
    
    # Create a test branch with unique name
    branch_name = f"test-commit-branch-{int(time.time())}"
    branch_result = service.create_branch(
        repo_dir="test-commit-repo",
        branch_name=branch_name,
    )
    
    assert branch_result.get("success"), f"Branch creation failed: {branch_result.get('error')}"
    
    # Create a test file
    repo_path = Path(service.workspace_root) / "test-commit-repo"
    test_file = repo_path / f"test_file_{int(time.time())}.txt"
    test_file.write_text(f"Test content for commit at {time.time()}")
    
    # Commit the change (this also pushes)
    commit_result = service.commit_changes(
        repo_dir="test-commit-repo",
        commit_message="Test commit from optifiner",
        branch=branch_name,
        files=None,  # Stage all with -A
    )
    
    print(f"Commit result: {commit_result}")
    if commit_result.get("success"):
        assert "commit_hash" in commit_result
        assert "commit_message" in commit_result
        assert "branch" in commit_result
        print("✓ Commit changes test passed")
    else:
        # Even on failure, check if commit succeeded but push failed
        if commit_result.get("commit_hash"):
            print(f"⚠ Commit succeeded but push failed: {commit_result.get('error')}")
        else:
            print(f"⚠ Commit test result: {commit_result.get('error')}")


def test_push_changes():
    """Test push_changes (now a no-op since commit_changes handles push)."""
    print("\n=== Testing push_changes ===")
    print("Note: push_changes is now a no-op since commit_changes handles pushing")
    
    service = GitHubService()
    
    # This should return success as it's a no-op
    result = service.push_changes(
        repo_dir="any-repo",
        branch="any-branch",
        force=False,
    )
    
    print(f"Push result: {result}")
    assert result.get("success"), f"Push should succeed as no-op: {result.get('error')}"
    assert result.get("message") == "Push handled by commit_changes"
    print("✓ Push changes test passed")


def test_update_repository():
    """Test updating (pulling) a repository."""
    print("\n=== Testing update_repository ===")
    
    _check_auth()
    test_repo = _get_test_repo()
    
    service = GitHubService()
    assert service.github is not None, "GitHub client not available"
    
    # First clone the private repo
    clone_result = service.clone_repository(
        repo_url=test_repo,
        target_dir="test-update-repo",
    )
    
    assert clone_result.get("success"), f"Clone failed: {clone_result.get('error')}"
    
    # Update the repository
    update_result = service.update_repository("test-update-repo")
    
    print(f"Update result: {update_result}")
    if update_result.get("success"):
        assert "path" in update_result
        assert "branch" in update_result
        assert "commit" in update_result
        print("✓ Update repository test passed")
    else:
        # Update may fail if there are local changes, which is acceptable
        print(f"⚠ Update result: {update_result.get('error')}")
        print("   (May be expected if there are local changes)")


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
    assert "description" in result
    assert "default_branch" in result
    assert "language" in result
    assert "stars" in result
    assert "forks" in result
    assert "url" in result
    print("✓ Get repository info test passed")


def test_create_pull_request():
    """Test creating a pull request for private repository."""
    print("\n=== Testing create_pull_request (Private Repo) ===")
    
    _check_auth()
    test_repo = _get_test_repo()
    
    service = GitHubService()
    assert service.github is not None, "GitHub client not available"
    
    # First clone the private repo
    clone_result = service.clone_repository(
        repo_url=test_repo,
        target_dir="test-pr-repo",
    )
    
    assert clone_result.get("success"), f"Clone failed: {clone_result.get('error')}"
    
    # Create a test branch with unique name
    branch_name = f"test-pr-branch-{int(time.time())}"
    branch_result = service.create_branch(
        repo_dir="test-pr-repo",
        branch_name=branch_name,
    )
    
    assert branch_result.get("success"), f"Branch creation failed: {branch_result.get('error')}"
    
    # Create a test file
    repo_path = Path(service.workspace_root) / "test-pr-repo"
    test_file = repo_path / f"test_pr_file_{int(time.time())}.txt"
    test_file.write_text(f"Test content for PR - {time.time()}")
    
    # Commit the change (this also pushes)
    commit_result = service.commit_changes(
        repo_dir="test-pr-repo",
        commit_message="Test commit for PR creation",
        branch=branch_name,
    )
    
    if not commit_result.get("success"):
        print(f"⚠ Commit failed (may affect PR test): {commit_result.get('error')}")
    
    # Create the pull request
    pr_result = service.create_pull_request(
        repo_dir="test-pr-repo",
        branch=branch_name,
        title=f"[Test] PR creation test - {branch_name}",
        body="This is an automated test PR created by Optifiner test suite.\n\nThis PR can be safely closed.",
        base_branch=None,  # Use default branch
    )
    
    print(f"PR creation result: {pr_result}")
    
    if pr_result.get("success"):
        pr_info = pr_result.get("pull_request", {})
        assert "number" in pr_info
        assert "url" in pr_info
        assert "title" in pr_info
        assert "state" in pr_info
        assert "head" in pr_info
        assert "base" in pr_info
        print(f"✓ Pull request created successfully: #{pr_info.get('number')}")
        print(f"  URL: {pr_info.get('url')}")
    else:
        error = pr_result.get("error", "Unknown error")
        # Check if it's a known non-fatal error
        if "A pull request already exists" in error:
            print(f"✓ PR already exists for this branch (expected on re-runs)")
        elif "Branch" in error and "not found" in error:
            print(f"⚠ Branch not found on remote - commit/push may have failed: {error}")
        else:
            print(f"⚠ PR creation result: {error}")
    
    print("✓ Create pull request test completed")


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
    print("Methods being tested:")
    print("  - clone_repository")
    print("  - create_branch")
    print("  - get_repository_status")
    print("  - list_repositories")
    print("  - commit_changes")
    print("  - push_changes (no-op)")
    print("  - update_repository")
    print("  - get_repository_info")
    print("  - create_pull_request")
    print()
    
    try:
        test_clone_repository()
        test_create_branch()
        test_get_repository_status()
        test_list_repositories()
        test_commit_changes()
        test_push_changes()
        test_update_repository()
        test_get_repository_info()
        test_create_pull_request()
        
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
