"""Repository and GitHub API endpoints."""

from fastapi import APIRouter, HTTPException

from optifiner_api.models import (
    PullRequestRequest,
    RepositoryCloneRequest,
    RepositoryCommitRequest,
    RepositoryPushRequest,
)
from optifiner_api.services.github_service import GitHubService

router = APIRouter()

# Initialize service
github_service = GitHubService()


@router.post("/repositories/clone")
async def clone_repository(request: RepositoryCloneRequest):
    """Clone a GitHub repository.

    Args:
        request: Repository clone request

    Returns:
        Clone result
    """
    result = github_service.clone_repository(
        repo_url=request.repo_url,
        branch=request.branch,
        target_dir=request.target_dir,
    )

    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Clone failed"))

    return result


@router.get("/repositories/info/{owner}/{repo_name}")
async def get_repository_info(owner: str, repo_name: str):
    """Get repository information from GitHub API.

    Args:
        owner: Repository owner
        repo_name: Repository name

    Returns:
        Repository information
    """
    result = github_service.get_repository_info(owner, repo_name)

    if not result.get("success"):
        raise HTTPException(
            status_code=400, detail=result.get("error", "Failed to get repository info")
        )

    return result


@router.post("/repositories/{repo_dir}/update")
async def update_repository(repo_dir: str):
    """Update (pull) an existing repository.

    Args:
        repo_dir: Directory name of the repository

    Returns:
        Update result
    """
    result = github_service.update_repository(repo_dir)

    if not result.get("success"):
        raise HTTPException(
            status_code=400, detail=result.get("error", "Update failed")
        )

    return result


@router.get("/repositories")
async def list_repositories():
    """List all cloned repositories.

    Returns:
        List of repositories
    """
    repos = github_service.list_repositories()
    return {"repositories": repos}


@router.get("/repositories/{repo_dir}/status")
async def get_repository_status(repo_dir: str):
    """Get repository status (changes, branch, etc.).

    Args:
        repo_dir: Directory name of the repository

    Returns:
        Repository status
    """
    result = github_service.get_repository_status(repo_dir)

    if not result.get("success"):
        raise HTTPException(
            status_code=404, detail=result.get("error", "Repository not found")
        )

    return result


@router.post("/repositories/{repo_dir}/commit")
async def commit_repository_changes(repo_dir: str, request: RepositoryCommitRequest):
    """Commit changes to the repository.

    Args:
        repo_dir: Directory name of the repository
        request: Commit request with message and options

    Returns:
        Commit result with commit information
    """
    result = github_service.commit_changes(
        repo_dir=repo_dir,
        commit_message=request.commit_message,
        branch=request.branch,
        files=request.files,
        author_name=request.author_name,
        author_email=request.author_email,
    )

    if not result.get("success"):
        raise HTTPException(
            status_code=400, detail=result.get("error", "Commit failed")
        )

    return result


@router.post("/repositories/{repo_dir}/push")
async def push_repository_changes(repo_dir: str, request: RepositoryPushRequest):
    """Push committed changes to GitHub repository.

    Args:
        repo_dir: Directory name of the repository
        request: Push request with options

    Returns:
        Push result
    """
    result = github_service.push_changes(
        repo_dir=repo_dir,
        branch=request.branch,
        force=request.force,
    )

    if not result.get("success"):
        raise HTTPException(
            status_code=400, detail=result.get("error", "Push failed")
        )

    return result


@router.post("/repositories/{repo_dir}/pull-request")
async def create_pull_request(repo_dir: str, request: PullRequestRequest):
    """Create a pull request for a pushed branch.

    Args:
        repo_dir: Directory name of the repository
        request: Pull request request with title, body, and branch info

    Returns:
        Pull request information
    """
    result = github_service.create_pull_request(
        repo_dir=repo_dir,
        branch=request.branch,
        title=request.title,
        body=request.body,
        base_branch=request.base_branch,
    )

    if not result.get("success"):
        raise HTTPException(
            status_code=400, detail=result.get("error", "Failed to create pull request")
        )

    return result
