"""Pydantic models for API requests and responses.

This module provides complete feature parity with the CLI options from
worker/src/worker/cli.py.

CLI Option Mapping:
    --agents (-n)         -> agents_per_generation
    --parallel (-p)       -> parallel
    --generations (-g)    -> generations
    --max-iterations (-i) -> max_iterations_per_agent
    --task (-t)          -> user_prompt
    --model-provider     -> models[].provider
    --model-name         -> models[].model_name
    --verbose (-v)       -> verbosity (0=quiet, 1=normal, 2=verbose, 3=debug)
    --quiet (-q)         -> verbosity = 0
    --log-dir (-l)       -> log_dir
    --early-stop         -> early_stop
    --build-benchmark    -> build_benchmark
    --min-improvement    -> min_improvement_pct
"""

from pydantic import BaseModel, Field, field_validator


# =============================================================================
# Model Configuration
# =============================================================================

class ModelConfig(BaseModel):
    """Model configuration for optimization workflow.
    
    Equivalent to CLI: --model-provider and --model-name
    """
    model_config = {"protected_namespaces": ()}

    provider: str = Field(
        ..., 
        description="Model provider: 'anthropic', 'google', or 'openai'"
    )
    model_name: str = Field(
        ..., 
        description="Model name (e.g., 'gemini-2.0-flash-exp', 'claude-3-sonnet-20240229')"
    )
    api_key: str = Field(
        ..., 
        description="API key for the model provider"
    )
    instances: int = Field(
        1, 
        description="Number of agent instances using this model. "
                    "Overrides agents_per_generation when set > 0."
    )


# =============================================================================
# Optimization Workflow Request
# =============================================================================

class OptimizationWorkflowRequest(BaseModel):
    """Request model for starting an optimization workflow.
    
    This model provides complete feature parity with the CLI.
    All CLI options from worker/src/worker/cli.py are supported.
    
    Example equivalent to:
        python3 cli.py -p 5 -g 5 -m 10 \\
            ../../examples/volumetric_particle_sim \\
            --agents 5 \\
            --max-iterations 25 \\
            --task "Optimize this particle simulation for maximum FPS performance." \\
            -vvv
    
    Would be:
        {
            "repo_url": "https://github.com/user/volumetric_particle_sim",
            "parallel": 5,
            "generations": 5,
            "min_improvement_pct": 10.0,
            "agents_per_generation": 5,
            "max_iterations_per_agent": 25,
            "user_prompt": "Optimize this particle simulation for maximum FPS performance.",
            "verbosity": 3,
            "models": [{"provider": "google", "model_name": "gemini-2.0-flash-exp", "api_key": "..."}],
            "total_cost_limit": 10.0
        }
    """

    # -------------------------------------------------------------------------
    # Repository Configuration
    # -------------------------------------------------------------------------
    repo_url: str = Field(
        ..., 
        description="GitHub repository URL (e.g., 'https://github.com/owner/repo')"
    )
    branch: str | None = Field(
        None, 
        description="Branch to clone. If not specified, uses repository's default branch."
    )
    
    # -------------------------------------------------------------------------
    # Cost Limit
    # -------------------------------------------------------------------------
    total_cost_limit: float = Field(
        ..., 
        description="Maximum total cost in USD for the optimization workflow"
    )
    
    # -------------------------------------------------------------------------
    # Model Configuration
    # -------------------------------------------------------------------------
    models: list[ModelConfig] = Field(
        ..., 
        description="List of models to use. Each model can have multiple instances."
    )
    
    # -------------------------------------------------------------------------
    # Task Configuration (CLI: --task, -t)
    # -------------------------------------------------------------------------
    user_prompt: str = Field(
        "Improve the code to get a higher benchmark score.",
        description="Task description for agents. "
                    "Equivalent to CLI: --task or -t"
    )
    
    # -------------------------------------------------------------------------
    # Agent Configuration (CLI options)
    # -------------------------------------------------------------------------
    agents_per_generation: int = Field(
        10,
        ge=1,
        description="Total agents per generation. Equivalent to CLI: --agents or -n. "
                    "Note: If models have 'instances' set, those values are used instead."
    )
    parallel: int = Field(
        1,
        ge=1,
        description="Number of agents to run in parallel. Equivalent to CLI: --parallel or -p. "
                    "Set to 1 for sequential execution."
    )
    generations: int = Field(
        1,
        ge=1,
        description="Maximum number of evolution generations. Equivalent to CLI: --generations or -g. "
                    "Each generation spawns agents and accepts the best improvement."
    )
    max_iterations_per_agent: int = Field(
        15,
        ge=1,
        description="Maximum iterations per agent. Equivalent to CLI: --max-iterations or -i"
    )
    agent_types: list[str] | None = Field(
        None,
        description="Agent types to cycle through. "
                    "Default: ['optimizer', 'refactoring', 'feature', 'analyzer', 'general']. "
                    "Agents are assigned types from this list cyclically."
    )
    
    # -------------------------------------------------------------------------
    # Optimization Settings (CLI options)
    # -------------------------------------------------------------------------
    min_improvement_pct: float = Field(
        6.0,
        ge=0.0,
        description="Minimum improvement percentage to accept a change. "
                    "Equivalent to CLI: --min-improvement or -m. "
                    "Default 6.0% filters benchmark noise. "
                    "Use higher values (10-20%) for noisy benchmarks."
    )
    early_stop: bool = Field(
        True,
        description="Stop generation early when improvement found. "
                    "Equivalent to CLI: --early-stop / --no-early-stop. "
                    "When enabled, starts new generation immediately upon finding improvement."
    )
    
    # -------------------------------------------------------------------------
    # Benchmark Configuration (CLI options)
    # -------------------------------------------------------------------------
    evaluator_path: str | None = Field(
        None,
        description="Path to evaluator script relative to repo root. "
                    "If not provided, looks for 'optifiner_benchmark.py' or 'run_validator.py'. "
                    "If not found, runs benchmark builder to create one."
    )
    build_benchmark: bool = Field(
        False,
        description="Force running benchmark builder even if evaluator exists. "
                    "Equivalent to CLI: --build-benchmark or -b"
    )
    
    # -------------------------------------------------------------------------
    # Logging Configuration (CLI options)
    # -------------------------------------------------------------------------
    verbosity: int = Field(
        1,
        ge=0,
        le=3,
        description="Logging verbosity level. Equivalent to CLI: -v count or -q. "
                    "0=quiet (minimal), 1=normal (default), 2=verbose (full tool calls), "
                    "3=debug (everything including prompts)"
    )
    log_dir: str | None = Field(
        None,
        description="Directory to save agent execution logs in JSONL format. "
                    "Equivalent to CLI: --log-dir or -l. "
                    "Each agent gets its own log file: {log_dir}/{agent_id}.jsonl"
    )
    
    # -------------------------------------------------------------------------
    # Time Limits
    # -------------------------------------------------------------------------
    time_limit_seconds: int = Field(
        300,
        ge=60,
        description="Time limit per generation in seconds. Default: 5 minutes (300s)"
    )


# =============================================================================
# Step Metadata
# =============================================================================

class StepMetadata(BaseModel):
    """Metadata for a single optimization step/snapshot.
    
    Steps are saved in the repository as:
        {repo}/steps/step_000/  (initial)
        {repo}/steps/step_001/  (first improvement)
        ...
    """
    
    step: int = Field(
        ..., 
        description="Step number. 0 = initial baseline, 1+ = improvements"
    )
    generation: int = Field(
        ..., 
        description="Generation when this step was created"
    )
    agent_id: str = Field(
        ..., 
        description="ID of the agent that made this improvement"
    )
    baseline_score: float = Field(
        ..., 
        description="Score before this improvement"
    )
    final_score: float = Field(
        ..., 
        description="Score after this improvement"
    )
    improvement: float = Field(
        ..., 
        description="Absolute improvement (final - baseline)"
    )
    improvement_percent: float = Field(
        ..., 
        description="Percentage improvement"
    )
    timestamp: str = Field(
        ..., 
        description="ISO format timestamp when step was created"
    )
    is_initial: bool = Field(
        False, 
        description="True if this is the initial snapshot (step 0)"
    )


# =============================================================================
# Workflow Status
# =============================================================================

class OptimizationWorkflowStatus(BaseModel):
    """Status of an optimization workflow.
    
    This model mirrors all output fields from the CLI for complete status reporting.
    """

    # Core identification
    workflow_id: str
    status: str = Field(
        ..., 
        description="Workflow status: 'running', 'paused', 'completed', 'stopped', 'failed'"
    )
    
    # Repository info
    repo_dir: str = Field(
        ..., 
        description="Local repository directory name"
    )
    repo_url: str | None = Field(
        None, 
        description="Original repository URL"
    )
    branch: str | None = Field(
        None, 
        description="Optimization branch name (optifiner-{workflow_id[:8]})"
    )
    original_branch: str | None = Field(
        None, 
        description="Original branch that was cloned"
    )
    
    # Scores
    baseline_score: float | None = Field(
        None, 
        description="Initial baseline score before any optimization"
    )
    current_best_score: float | None = Field(
        None, 
        description="Current best score achieved"
    )
    
    # Progress tracking
    generation: int = Field(
        0, 
        description="Current generation number"
    )
    max_generations: int | None = Field(
        None, 
        description="Maximum generations configured"
    )
    total_improvements: int = Field(
        0, 
        description="Total number of successful improvements"
    )
    total_attempts: int = Field(
        0, 
        description="Total number of agent attempts"
    )
    step_count: int = Field(
        0, 
        description="Total number of successful steps (0 = initial only)"
    )
    
    # Step snapshots
    steps: list[StepMetadata] = Field(
        default_factory=list, 
        description="Metadata for each step snapshot"
    )
    
    # Cost tracking
    total_cost: float = Field(
        0.0, 
        description="Total cost incurred so far"
    )
    total_cost_limit: float | None = Field(
        None, 
        description="Configured cost limit"
    )
    
    # Timing
    started_at: str | None = Field(
        None, 
        description="ISO timestamp when workflow started"
    )
    completed_at: str | None = Field(
        None, 
        description="ISO timestamp when workflow completed"
    )
    paused_at: str | None = Field(
        None, 
        description="ISO timestamp when workflow was paused"
    )
    
    # Configuration echo
    min_improvement_pct: float | None = Field(
        None, 
        description="Configured minimum improvement threshold"
    )
    early_stop: bool | None = Field(
        None, 
        description="Whether early stopping is enabled"
    )
    
    # Results
    improvement: float | None = Field(
        None, 
        description="Total improvement (final - baseline)"
    )
    improvement_percent: float | None = Field(
        None, 
        description="Total percentage improvement"
    )
    
    # Error handling
    message: str | None = Field(
        None, 
        description="Status message"
    )
    error: str | None = Field(
        None, 
        description="Error message if workflow failed"
    )


# =============================================================================
# Repository Operations (for direct GitHub integration)
# =============================================================================

class RepositoryCloneRequest(BaseModel):
    """Request model for cloning a repository."""

    repo_url: str = Field(..., description="GitHub repository URL")
    branch: str | None = Field(None, description="Branch to clone")
    target_dir: str | None = Field(None, description="Target directory name")


class RepositoryCommitRequest(BaseModel):
    """Request model for committing changes."""

    commit_message: str = Field(..., description="Commit message")
    branch: str | None = Field(None, description="Branch name")
    files: list[str] | None = Field(None, description="Specific files to commit")


class RepositoryPushRequest(BaseModel):
    """Request model for pushing changes to GitHub."""

    branch: str | None = Field(None, description="Branch name to push")
    force: bool = Field(False, description="Whether to force push")


class PullRequestRequest(BaseModel):
    """Request model for creating a pull request."""

    branch: str = Field(..., description="Head branch for PR")
    title: str = Field(..., description="Pull request title")
    body: str | None = Field(None, description="Pull request body")
    base_branch: str | None = Field(None, description="Base branch for PR")


# =============================================================================
# Early Access Signup Models
# =============================================================================

class EarlyAccessSignupRequest(BaseModel):
    """Request model for early access signup."""

    email: str = Field(
        ...,
        description="Email address for early access notification"
    )
    source: str = Field(
        "landing_page",
        description="Source of the signup"
    )

    @field_validator('email')
    @classmethod
    def validate_email(cls, v: str) -> str:
        """Validate email format."""
        import re
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, v.strip()):
            raise ValueError('Invalid email format')
        return v.strip().lower()


class EarlyAccessSignupResponse(BaseModel):
    """Response model for early access signup."""

    success: bool
    message: str
    email: str | None = None
    already_registered: bool = False
