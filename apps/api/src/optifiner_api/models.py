"""Pydantic models for API requests and responses."""

from pydantic import BaseModel, Field


class RepositoryCloneRequest(BaseModel):
    """Request model for cloning a repository."""

    repo_url: str = Field(..., description="GitHub repository URL")
    branch: str | None = Field(None, description="Branch to clone")
    target_dir: str | None = Field(None, description="Target directory name")


class RepositoryInfo(BaseModel):
    """Repository information model."""

    name: str
    full_name: str
    description: str | None
    default_branch: str
    language: str | None
    stars: int
    forks: int
    url: str


class TaskSubmitRequest(BaseModel):
    """Request model for submitting a task."""

    repo_dir: str = Field(..., description="Directory name of the repository")
    agent_type: str = Field(..., description="Type of agent (analyzer, refactor, optimize, etc.)")
    task_prompt: str = Field(..., description="Task description/prompt")
    model: str | None = Field(None, description="LLM model to use")
    max_iterations: int = Field(20, description="Maximum iterations")
    metrics: str | None = Field(None, description="Metrics description")
    baseline: str | None = Field(None, description="Baseline description")
    analysis: str | None = Field(None, description="Analysis result (for improvement tasks)")


class EvolutionTask(BaseModel):
    """Evolution task model."""

    task_id: str
    repo_dir: str
    agent_type: str
    task_prompt: str
    model: str | None = None
    max_iterations: int = 20
    metrics: str | None = None
    baseline: str | None = None
    analysis: str | None = None


class EvolutionResult(BaseModel):
    """Evolution result model."""

    task_id: str
    success: bool
    result: str | None = None
    error: str | None = None
    iterations: int = 0
    messages_count: int = 0


class TaskStatusResponse(BaseModel):
    """Task status response model."""

    task_id: str
    status: str
    repo_dir: str
    agent_type: str
    task_prompt: str
    result: EvolutionResult | None = None
