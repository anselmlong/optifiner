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
import time
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
    print("Test 1: Clone Private Repository (clone_repository)")
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
    
    # Test 2: Create branch (uses GitHub API to create remote branch, then checks out locally)
    print("\n" + "-" * 70)
    print("Test 2: Create Branch (create_branch)")
    print("-" * 70)
    # Use timestamp to create unique branch name for each test run
    branch_name = f"test-optifiner-branch-{int(time.time())}"
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
        commit = branch_result.get('commit', '')
        print(f"  Commit: {commit[:8] if commit else 'N/A'}")
        if branch_result.get("message"):
            print(f"  Message: {branch_result.get('message')}")
    else:
        print(f"✗ Branch creation failed: {branch_result.get('error')}")
        return
    
    # Test 3: Get repository status
    print("\n" + "-" * 70)
    print("Test 3: Get Repository Status (get_repository_status)")
    print("-" * 70)
    
    status_result = service.get_repository_status(repo_dir)
    
    if status_result.get("success"):
        print(f"✓ Successfully got status")
        print(f"  Repo dir: {status_result.get('repo_dir')}")
        print(f"  Branch: {status_result.get('branch')}")
        commit = status_result.get('commit', '')
        print(f"  Commit: {commit[:8] if commit else 'N/A'}")
        print(f"  Has changes: {status_result.get('has_changes', False)}")
        print(f"  Is dirty: {status_result.get('is_dirty', False)}")
        print(f"  Changed files: {status_result.get('changed_files', [])}")
        print(f"  Untracked files: {status_result.get('untracked_files', [])}")
    else:
        print(f"✗ Status check failed: {status_result.get('error')}")
    
    # Test 4: List repositories
    print("\n" + "-" * 70)
    print("Test 4: List Repositories (list_repositories)")
    print("-" * 70)
    
    repos = service.list_repositories()
    print(f"✓ Found {len(repos)} repositories")
    for repo in repos[:5]:  # Show first 5
        print(f"  - {repo.get('name')}: branch={repo.get('branch', 'unknown')}, commit={repo.get('commit', 'N/A')}")
    if len(repos) > 5:
        print(f"  ... and {len(repos) - 5} more")
    
    # Test 5: Commit changes (commit_changes now does git commit + push)
    print("\n" + "-" * 70)
    print("Test 5: Commit Changes (commit_changes)")
    print("-" * 70)
    print("Note: commit_changes uses git commit + git push (not GitHub API)")
    
    repo_path = service.workspace_root / repo_dir
    test_file = repo_path / f"test_optifiner_{int(time.time())}.txt"
    
    try:
        test_file.write_text(f"Test file created by Optifiner at {time.time()}")
        print(f"Created test file: {test_file.name}")
        
        commit_result = service.commit_changes(
            repo_dir=repo_dir,
            commit_message="Test commit from Optifiner GitHub service test",
            branch=branch_name,
            files=None,  # Stage all changes with -A
        )
        
        if commit_result.get("success"):
            print(f"✓ Successfully committed and pushed")
            commit_hash = commit_result.get('commit_hash', '')
            print(f"  Commit hash: {commit_hash[:8] if commit_hash else 'N/A'}")
            print(f"  Commit message: {commit_result.get('commit_message')}")
            print(f"  Branch: {commit_result.get('branch')}")
        else:
            error = commit_result.get('error', 'Unknown error')
            # Check if there's a commit_hash even on failure (push might have failed)
            commit_hash = commit_result.get('commit_hash')
            if commit_hash:
                print(f"⚠ Commit succeeded but push failed")
                print(f"  Commit hash: {commit_hash[:8]}")
                print(f"  Error: {error}")
            else:
                print(f"⚠ Commit result: {error}")
    except Exception as e:
        print(f"⚠ Could not test commit: {e}")
    
    # Test 6: Push changes (now a no-op since commit_changes handles push)
    print("\n" + "-" * 70)
    print("Test 6: Push Changes (push_changes)")
    print("-" * 70)
    print("Note: push_changes is now a no-op since commit_changes handles pushing")
    
    push_result = service.push_changes(
        repo_dir=repo_dir,
        branch=branch_name,
        force=False,
    )
    
    if push_result.get("success"):
        print(f"✓ Push changes returned success")
        print(f"  Branch: {push_result.get('branch')}")
        print(f"  Message: {push_result.get('message')}")
    else:
        print(f"⚠ Push result: {push_result.get('error', 'Unknown')}")
    
    # Test 7: Update repository (git pull)
    print("\n" + "-" * 70)
    print("Test 7: Update Repository (update_repository)")
    print("-" * 70)
    
    update_result = service.update_repository(repo_dir)
    
    if update_result.get("success"):
        print(f"✓ Successfully updated repository")
        print(f"  Path: {update_result.get('path')}")
        print(f"  Branch: {update_result.get('branch')}")
        commit = update_result.get('commit', '')
        print(f"  Commit: {commit[:8] if commit else 'N/A'}")
    else:
        print(f"⚠ Update failed: {update_result.get('error')}")
        print("  (This may be expected if there are local changes)")
    
    # Test 8: Get repository info from GitHub API
    print("\n" + "-" * 70)
    print("Test 8: Get Repository Info (get_repository_info)")
    print("-" * 70)
    
    # Extract owner and repo name from URL
    try:
        # Parse URL to get owner/repo
        repo_url_parts = test_repo.replace(".git", "").rstrip("/").split("/")
        repo_owner = repo_url_parts[-2]
        repo_name_parsed = repo_url_parts[-1]
        
        info_result = service.get_repository_info(repo_owner, repo_name_parsed)
        if info_result.get("success"):
            print(f"✓ Successfully got repository info")
            print(f"  Name: {info_result.get('name')}")
            print(f"  Full name: {info_result.get('full_name')}")
            print(f"  Description: {info_result.get('description')}")
            print(f"  Default branch: {info_result.get('default_branch')}")
            print(f"  Language: {info_result.get('language')}")
            print(f"  Stars: {info_result.get('stars')}")
            print(f"  Forks: {info_result.get('forks')}")
            print(f"  URL: {info_result.get('url')}")
        else:
            print(f"✗ Failed: {info_result.get('error')}")
    except Exception as e:
        print(f"⚠ Could not parse repository URL: {e}")
    
    # Test 9: Create Pull Request
    print("\n" + "-" * 70)
    print("Test 9: Create Pull Request (create_pull_request)")
    print("-" * 70)
    
    try:
        pr_result = service.create_pull_request(
            repo_dir=repo_dir,
            branch=branch_name,
            title=f"[Test] Optifiner test PR - {branch_name}",
            body="This is a test PR created by Optifiner GitHub service test.\n\nThis PR can be safely closed.",
            base_branch=None,  # Use default branch
        )
        
        if pr_result.get("success"):
            pr_info = pr_result.get("pull_request", {})
            print(f"✓ Successfully created pull request")
            print(f"  PR Number: #{pr_info.get('number')}")
            print(f"  Title: {pr_info.get('title')}")
            print(f"  URL: {pr_info.get('url')}")
            print(f"  State: {pr_info.get('state')}")
            print(f"  Head: {pr_info.get('head')} -> Base: {pr_info.get('base')}")
        else:
            error = pr_result.get("error", "Unknown error")
            # PR might already exist, which is fine
            if "A pull request already exists" in error:
                print(f"✓ PR already exists for this branch (expected on re-runs)")
            elif "Branch" in error and "not found" in error:
                print(f"⚠ Branch not found on remote: {error}")
                print("   This may happen if the commit/push in Test 5 failed")
            else:
                print(f"✗ PR creation failed: {error}")
    except Exception as e:
        print(f"⚠ Could not test PR creation: {e}")
    
    print("\n" + "=" * 70)
    print("All tests completed!")
    print("=" * 70)
    print("\nMethods tested:")
    print("  1. clone_repository - Clone a GitHub repository")
    print("  2. create_branch - Create a new branch (GitHub API + local checkout)")
    print("  3. get_repository_status - Get local repository status")
    print("  4. list_repositories - List cloned repositories in workspace")
    print("  5. commit_changes - Commit and push changes (git commit + push)")
    print("  6. push_changes - Push changes (no-op, handled by commit_changes)")
    print("  7. update_repository - Update repository (git pull)")
    print("  8. get_repository_info - Get repository info from GitHub API")
    print("  9. create_pull_request - Create a pull request")


if __name__ == "__main__":
    main()
