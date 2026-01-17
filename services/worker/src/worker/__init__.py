"""Evolution Worker - LangGraph-based agent workers for code evolution."""

import os

# Fix gRPC fork warning: "Other threads are currently calling into gRPC, skipping fork()"
# This must be set before any gRPC imports (langchain-google-genai uses gRPC internally)
os.environ.setdefault("GRPC_ENABLE_FORK_SUPPORT", "1")

from worker.agent import (
    create_evolution_agent,
    create_analyzer_agent,
    create_refactoring_agent,
    create_feature_agent,
    create_optimizer_agent,
    run_evolution_agent,
)
from worker.config import AgentType, ModelConfig, WorkerConfig
from worker.state import AgentState, BenchmarkResult, EvolutionResult
from worker.tools import get_all_tools
from worker.callbacks import (
    AgentObserver,
    AgentEvent,
    create_observer,
    get_observer,
    set_observer,
)

__all__ = [
    # Agent creation
    "create_evolution_agent",
    "create_analyzer_agent",
    "create_refactoring_agent",
    "create_feature_agent",
    "create_optimizer_agent",
    "run_evolution_agent",
    # Configuration
    "AgentType",
    "ModelConfig",
    "WorkerConfig",
    # State
    "AgentState",
    "BenchmarkResult",
    "EvolutionResult",
    # Tools
    "get_all_tools",
    # Observability
    "AgentObserver",
    "AgentEvent",
    "create_observer",
    "get_observer",
    "set_observer",
]
