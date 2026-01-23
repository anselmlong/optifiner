"""State definitions for the evolution agent."""

from typing import Annotated, Any, Sequence
from operator import add

from langchain_core.messages import BaseMessage
from pydantic import BaseModel, Field
from langgraph.graph.message import add_messages


class AgentState(BaseModel):
    """State for the evolution agent graph.

    This state is passed between nodes in the LangGraph workflow.
    Messages are accumulated using the add_messages reducer.
    """

    # Conversation messages (accumulated with add_messages)
    messages: Annotated[Sequence[BaseMessage], add_messages] = Field(default_factory=list)

    # Task information
    task: str = Field(default="", description="The current task description")
    task_type: str = Field(default="general", description="Type of task: analyze, refactor, optimize, etc.")

    # Codebase context
    workspace_root: str = Field(default="", description="Root directory of the target codebase (real path)")
    current_file: str | None = Field(default=None, description="Currently focused file")
    files_read: list[str] = Field(default_factory=list, description="Files that have been read")
    files_modified: list[str] = Field(default_factory=list, description="Files that have been modified")

    # Evolution context
    generation: int = Field(default=0, description="Current evolution generation")
    baseline_score: float | None = Field(default=None, description="Baseline benchmark score")
    baseline_data: dict | None = Field(default=None, description="Detailed baseline metrics (fps, tests, etc.)")
    current_score: float | None = Field(default=None, description="Current benchmark score after changes")
    best_score: float | None = Field(default=None, description="Best score achieved during this agent's run (for tracking improvements)")
    higher_is_better: bool = Field(default=True, description="If True, higher scores are better (FPS). If False, lower is better (cycles).")
    metric_name: str = Field(default="score", description="Name of the metric being optimized")

    # Agent tracking
    agent_id: str = Field(default="", description="Unique identifier for this agent instance")
    iteration: int = Field(default=0, description="Current iteration within this agent's run")
    max_iterations: int = Field(default=10, description="Maximum iterations allowed")
    benchmark_timeout: int = Field(default=30, description="Timeout in seconds for benchmark execution")
    min_improvement_pct: float = Field(default=3.0, description="Minimum improvement percentage to consider significant")

    # Results
    success: bool = Field(default=False, description="Whether the agent completed successfully")
    error: str | None = Field(default=None, description="Error message if failed")
    summary: str = Field(default="", description="Summary of changes made")

    class Config:
        arbitrary_types_allowed = True


class BenchmarkResult(BaseModel):
    """Result from running benchmarks."""

    score: float = Field(description="Primary benchmark score")
    latency_ms: float | None = Field(default=None, description="Execution latency in milliseconds")
    memory_mb: float | None = Field(default=None, description="Peak memory usage in MB")
    passed_tests: int = Field(default=0, description="Number of tests passed")
    total_tests: int = Field(default=0, description="Total number of tests")
    output: str = Field(default="", description="Raw benchmark output")
    error: str | None = Field(default=None, description="Error message if benchmark failed")

    @property
    def test_pass_rate(self) -> float:
        """Calculate test pass rate."""
        if self.total_tests == 0:
            return 1.0
        return self.passed_tests / self.total_tests

    @property
    def fitness(self) -> float:
        """Calculate composite fitness score.

        Weighted combination of:
        - Score/correctness: 70%
        - Test pass rate: 20%
        - Speed bonus: 10%
        """
        score_component = self.score * 0.7
        test_component = self.test_pass_rate * 0.2 * 100  # Normalize to 0-20
        speed_component = 0.0
        if self.latency_ms is not None and self.latency_ms > 0:
            # Lower latency = higher speed bonus (capped at 10)
            speed_component = min(10.0, 1000.0 / self.latency_ms)

        return score_component + test_component + speed_component


class EvolutionResult(BaseModel):
    """Result from an evolution attempt."""

    agent_id: str
    generation: int
    success: bool
    baseline_score: float
    final_score: float
    improvement: float = Field(default=0.0)
    improvement_percent: float = Field(default=0.0)
    changes_summary: str = Field(default="")
    files_modified: list[str] = Field(default_factory=list)
    benchmark_result: BenchmarkResult | None = None
    error: str | None = None

    @classmethod
    def from_state(cls, state: AgentState, benchmark: BenchmarkResult | None = None) -> "EvolutionResult":
        """Create an EvolutionResult from agent state."""
        baseline = state.baseline_score or 0.0
        current = state.current_score or baseline

        improvement = current - baseline
        improvement_pct = (improvement / baseline * 100) if baseline > 0 else 0.0

        return cls(
            agent_id=state.agent_id,
            generation=state.generation,
            success=state.success and improvement > 0,
            baseline_score=baseline,
            final_score=current,
            improvement=improvement,
            improvement_percent=improvement_pct,
            changes_summary=state.summary,
            files_modified=state.files_modified,
            benchmark_result=benchmark,
            error=state.error,
        )
