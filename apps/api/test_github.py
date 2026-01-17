#!/usr/bin/env python3
"""Simple test script for GitHub service operations on private repositories.

Run with: python test_github.py

Requires:
  - GitHub App configured (GITHUB_APP_ID, GITHUB_APP_PRIVATE_KEY, GITHUB_APP_CLIENT_ID)
  - The GitHub App must have access to the private repository

Default test repository: https://github.com/anselmlong/stuckincom1again
You can override with: export TEST_PRIVATE_REPO=https://github.com/owner/private-repo
"""

import os
import sys
import tempfile
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from git import Repo
from optifiner_api.services.github_service import GitHubService
from optifiner_api.config import settings


def main():
    """Run GitHub service tests on a private repository."""
    print("=" * 70)
    print("GitHub Service Operations Test (Private Repository)")
    print("=" * 70)
    
    # Get private repository URL from environment variable or use default
    test_repo = os.getenv("TEST_PRIVATE_REPO", "https://github.com/anselmlong/stuckincom1again")
    print(f"\nUsing test repository: {test_repo}")
    
    # Set workspace path - use default or temp directory for testing
    import tempfile
    # Default workspace is now apps/workspace (relative to project root)
    # For testing, we'll let the service handle workspace creation
    # But we can override with a temp directory if needed
    test_workspace_env = os.getenv("WORKER_WORKSPACE_PATH")
    if not test_workspace_env:
        # Use temp directory for testing to avoid cluttering the project
        test_workspace = Path(tempfile.mkdtemp(prefix="optifiner_test_"))
        os.environ["WORKER_WORKSPACE_PATH"] = str(test_workspace)
        print(f"\n⚠ Using temp directory for testing: {test_workspace}")
        print("   Set WORKER_WORKSPACE_PATH environment variable to use a custom path")
    else:
        print(f"\nUsing workspace from environment: {test_workspace_env}")
    
    # Initialize service
    service = GitHubService()
    print(f"Workspace root: {service.workspace_root}")
    
    # Check authentication method - REQUIRED for private repos
    has_app = bool(settings.GITHUB_APP_ID and settings.GITHUB_APP_PRIVATE_KEY and settings.GITHUB_APP_CLIENT_ID)
    has_auth = bool(service.github)
    
    print(f"\nGitHub App configured: {has_app}")
    if has_app:
        print(f"  App ID: {settings.GITHUB_APP_ID}")
        print(f"  Client ID: {settings.GITHUB_APP_CLIENT_ID}")
    else:
        print("\n❌ ERROR: GitHub App not fully configured")
        print("   Required environment variables:")
        print("   - GITHUB_APP_ID")
        print("   - GITHUB_APP_PRIVATE_KEY")
        print("   - GITHUB_APP_CLIENT_ID")
        sys.exit(1)
    
    print(f"GitHub client available: {has_auth}")
    if not has_auth:
        print("\n❌ ERROR: GitHub client not available - cannot authenticate")
        print("   Check your GitHub App configuration")
        sys.exit(1)
    
    # Ensure workspace exists and is writable
    try:
        service.workspace_root.mkdir(parents=True, exist_ok=True)
    except (OSError, PermissionError) as e:
        print(f"\n❌ ERROR: Cannot create or write to workspace: {service.workspace_root}")
        print(f"   Error: {e}")
        print("   Please set WORKER_WORKSPACE_PATH to a writable directory")
        sys.exit(1)
    
    # Test 1: Clone private repository
    print("\n" + "-" * 70)
    print("Test 1: Clone Private Repository")
    print("-" * 70)
    print(f"Cloning: {test_repo}")
    print("  (This requires GitHub App authentication)")
    
    clone_result = service.clone_repository(
        repo_url=test_repo,
        branch=None,
        target_dir=None,  # Use original repository name
    )
    
    if clone_result.get("success"):
        print(f"✓ Successfully cloned private repository")
        print(f"  Repo name: {clone_result.get('repo_name')}")
        print(f"  Branch: {clone_result.get('branch')}")
        print(f"  Commit: {clone_result.get('commit')[:8]}")
        print(f"  Path: {clone_result.get('path')}")
    else:
        print(f"✗ Clone failed: {clone_result.get('error')}")
        print("\n⚠ Make sure:")
        print("   1. The repository URL is correct")
        print("   2. The GitHub App has access to the repository")
        print("   3. The repository is private (this test requires a private repo)")
        return
    
    repo_dir = clone_result.get("repo_name")
    
    # Test 2: Create branch
    print("\n" + "-" * 70)
    print("Test 2: Create Branch")
    print("-" * 70)
    branch_name = "test-optifiner-branch"
    print(f"Creating branch: {branch_name}")
    
    branch_result = service.create_branch(
        repo_dir=repo_dir,
        branch_name=branch_name,
        from_branch=clone_result.get("branch"),
    )
    
    if branch_result.get("success"):
        print(f"✓ Successfully created branch")
        print(f"  Branch: {branch_result.get('branch')}")
        print(f"  From: {branch_result.get('from_branch', 'current')}")
        print(f"  Commit: {branch_result.get('commit', '')[:8]}")
    else:
        print(f"✗ Branch creation failed: {branch_result.get('error')}")
        return
    
    # Test 3: Get repository status
    print("\n" + "-" * 70)
    print("Test 3: Get Repository Status")
    print("-" * 70)
    
    status_result = service.get_repository_status(repo_dir)
    
    if status_result.get("success"):
        print(f"✓ Successfully got status")
        print(f"  Branch: {status_result.get('branch')}")
        print(f"  Commit: {status_result.get('commit', '')[:8]}")
        print(f"  Has changes: {status_result.get('has_changes', False)}")
        print(f"  Is dirty: {status_result.get('is_dirty', False)}")
    else:
        print(f"✗ Status check failed: {status_result.get('error')}")
    
    # Test 4: List repositories
    print("\n" + "-" * 70)
    print("Test 4: List Repositories")
    print("-" * 70)
    
    repos = service.list_repositories()
    print(f"✓ Found {len(repos)} repositories")
    for repo in repos[:5]:  # Show first 5
        print(f"  - {repo.get('name')}: {repo.get('branch', 'unknown')}")
    if len(repos) > 5:
        print(f"  ... and {len(repos) - 5} more")
    
    # Test 5: Commit changes (if we can write)
    print("\n" + "-" * 70)
    print("Test 5: Commit Changes")
    print("-" * 70)
    
    repo_path = service.workspace_root / repo_dir
    test_file = repo_path / "test_optifiner.txt"
    
    try:
        test_file.write_text("Test file created by Optifiner")
        print(f"Created test file: {test_file.name}")
        
        commit_result = service.commit_changes(
            repo_dir=repo_dir,
            commit_message="Test commit from Optifiner GitHub service test",
            branch=branch_name,
        )
        
        if commit_result.get("success"):
            print(f"✓ Successfully committed")
            print(f"  Commit: {commit_result.get('commit', '')[:8]}")
            print(f"  Branch: {commit_result.get('branch')}")
            
            # Push changes after commit (syncs local with remote since commits are via API)
            print(f"\nPushing changes to remote...")
            push_result = service.push_changes(
                repo_dir=repo_dir,
                branch=branch_name,
            )
            
            if push_result.get("success"):
                print(f"✓ Successfully synced local repository with remote")
                print(f"  Branch: {push_result.get('branch')}")
            else:
                print(f"⚠ Push result: {push_result.get('error', 'Failed to sync')}")
        else:
            # Handle case where commit_result might not be a dict
            if isinstance(commit_result, dict):
                print(f"⚠ Commit result: {commit_result.get('error', 'No changes to commit')}")
            else:
                print(f"⚠ Commit result (unexpected type {type(commit_result)}): {commit_result}")
    except Exception as e:
        print(f"⚠ Could not test commit: {e}")
    
    # Test 6: Get repository info from private repo
    print("\n" + "-" * 70)
    print("Test 6: Get Repository Info (GitHub API)")
    print("-" * 70)
    
    # Extract owner and repo name from URL
    try:
        # Parse URL to get owner/repo
        repo_url_parts = test_repo.replace(".git", "").rstrip("/").split("/")
        repo_owner = repo_url_parts[-2]
        repo_name = repo_url_parts[-1]
        
        info_result = service.get_repository_info(repo_owner, repo_name)
        if info_result.get("success"):
            print(f"✓ Successfully got repository info")
            print(f"  Name: {info_result.get('name')}")
            print(f"  Full name: {info_result.get('full_name')}")
            print(f"  Default branch: {info_result.get('default_branch')}")
            print(f"  Stars: {info_result.get('stars')}")
        else:
            print(f"✗ Failed: {info_result.get('error')}")
    except Exception as e:
        print(f"⚠ Could not parse repository URL: {e}")
    
    print("\n" + "=" * 70)
    print("All tests completed!")
    print("=" * 70)


if __name__ == "__main__":
    main()
