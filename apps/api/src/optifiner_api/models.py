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
    evaluation_data: dict | None = None


class EvaluationData(BaseModel):
    """Evaluation data model."""

    score: float
    baseline_score: float | None = None
    improvement: float | None = None
    improvement_percent: float | None = None
    fps: float | None = None
    tests_passed: int | None = None
    tests_total: int | None = None
    test_results: dict | None = None
    metrics: dict | None = None
    raw_data: dict | None = None


class EvaluationDataStoreRequest(BaseModel):
    """Request model for storing evaluation data."""

    task_id: str = Field(..., description="Task identifier")
    evaluation_data: dict = Field(..., description="Full evaluation data dictionary")


class RepositoryCommitRequest(BaseModel):
    """Request model for committing changes."""

    commit_message: str = Field(..., description="Commit message")
    branch: str | None = Field(None, description="Branch name (default: current branch)")
    files: list[str] | None = Field(None, description="Specific files to commit (None = all changes)")
    author_name: str = Field("Optifiner", description="Git author name")
    author_email: str = Field("optifiner@example.com", description="Git author email")


class RepositoryPushRequest(BaseModel):
    """Request model for pushing changes to GitHub."""

    branch: str | None = Field(None, description="Branch name to push (default: current branch)")
    force: bool = Field(False, description="Whether to force push")


class PullRequestRequest(BaseModel):
    """Request model for creating a pull request."""

    branch: str = Field(..., description="Branch name (head branch for PR)")
    title: str = Field(..., description="Pull request title")
    body: str | None = Field(None, description="Pull request body/description")
    base_branch: str | None = Field(None, description="Base branch for PR (default: repository default branch)")


class TaskStatusResponse(BaseModel):
    """Task status response model."""

    task_id: str
    status: str
    repo_dir: str
    agent_type: str
    task_prompt: str
    result: EvolutionResult | None = None


class ModelConfig(BaseModel):
    """Model configuration for optimization workflow."""

    provider: str = Field(..., description="Model provider (anthropic, google, openai)")
    model_name: str = Field(..., description="Model name")
    api_key: str = Field(..., description="API key for the model")
    instances: int = Field(1, description="Number of instances to run for this model")


class OptimizationWorkflowRequest(BaseModel):
    """Request model for optimization workflow."""

    repo_url: str = Field(..., description="GitHub repository URL")
    branch: str | None = Field(None, description="Branch to clone (default: default branch)")
    total_cost_limit: float = Field(..., description="Total cost limit for the optimization")
    models: list[ModelConfig] = Field(..., description="List of models with their configurations")
    user_prompt: str = Field(..., description="User prompt describing the optimization goal")
    evaluator_path: str | None = Field(None, description="Path to evaluator script (if not in repo)")
    max_iterations_per_agent: int = Field(20, description="Maximum iterations per agent")
    time_limit_seconds: int = Field(300, description="Time limit per generation in seconds (default: 5 minutes)")


class GraphNode(BaseModel):
    """Node in the evolution graph."""

    id: str = Field(..., description="Node ID (instance_id or 'baseline')")
    type: str = Field(..., description="Node type: baseline, in_progress, accepted, or rejected")
    generation: int = Field(..., description="Generation number")
    score: float | None = Field(None, description="Evaluation score")
    instance_id: str | None = Field(None, description="Instance ID (None for baseline)")
    model_provider: str | None = Field(None, description="Model provider")
    model_name: str | None = Field(None, description="Model name")


class GraphEdge(BaseModel):
    """Edge in the evolution graph."""

    from_node: str = Field(..., description="Source node ID", alias="from")
    to_node: str = Field(..., description="Target node ID", alias="to")
    generation: int = Field(..., description="Generation when edge was created")

    class Config:
        populate_by_name = True
        allow_population_by_field_name = True


class GraphData(BaseModel):
    """Graph data structure for evolution tree."""

    nodes: list[GraphNode] = Field(default_factory=list, description="All nodes in the graph")
    edges: list[GraphEdge] = Field(default_factory=list, description="All edges in the graph")


class WorkerInstanceStatus(BaseModel):
    """Status of a worker instance."""

    instance_id: str
    model_provider: str
    model_name: str
    status: int = Field(..., description="Status: 0=accepted, 1=in_progress, 2=rejected")
    evaluation_score: float | None = None
    started_at: str | None = None
    completed_at: str | None = None
    error: str | None = None
    generation: int | None = Field(None, description="Generation when instance was created")
    parent_instance_id: str | None = Field(None, description="Parent instance ID that spawned this instance")
    accepted_at_generation: int | None = Field(None, description="Generation when instance was accepted")
    rejected_at_generation: int | None = Field(None, description="Generation when instance was rejected")


class OptimizationWorkflowStatus(BaseModel):
    """Status of optimization workflow."""

    workflow_id: str
    status: str = Field(..., description="Workflow status: pending, running, completed, failed")
    repo_dir: str
    baseline_score: float | None = None
    current_best_score: float | None = None
    generation: int = Field(0, description="Current generation number (loop level)")
    total_generations: int = Field(0, description="Total number of generations completed")
    last_improvement_generation: int | None = Field(None, description="Generation when last improvement occurred")
    final_generation: int | None = Field(None, description="Final generation when workflow completed")
    accepted_layers_count: int = Field(0, description="Number of accepted layers (generations with accepted improvements)")
    accepted_generations: list[int] = Field(default_factory=list, description="List of generation numbers that were accepted")
    graph_data: GraphData = Field(default_factory=lambda: GraphData(nodes=[], edges=[]), description="Graph/tree structure of evolution")
    parent_instance_id: str | None = Field(None, description="Current parent instance ID for next generation")
    worker_instances: list[WorkerInstanceStatus] = Field(default_factory=list)
    total_cost: float = Field(0.0, description="Total cost incurred so far")
    message: str | None = None
