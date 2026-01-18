#!/usr/bin/env python3
"""CLI for testing the evolution agents.

This CLI runs multiple agents on a target repository, each trying to improve
the codebase. Improvements are measured by a benchmark script that returns
a score.

All execution happens on the host machine with workspace isolation
(/tmp/optifiner_workspaces/) to provide safe sandboxing without containers.

The benchmark script is always at: <workspace_root>/optifiner_benchmark.py
"""

import os

# Fix gRPC fork warning: "Other threads are currently calling into gRPC, skipping fork()"
# This must be set before any gRPC imports (langchain-google-genai uses gRPC internally)
os.environ.setdefault("GRPC_ENABLE_FORK_SUPPORT", "1")

import json
import os
import shutil
import subprocess
import sys
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed, Future
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import click
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

from worker.observability import AgentObserver, set_observer
from worker.workspace import WorkspaceManager, set_workspace, isolated_workspace, BENCHMARK_SCRIPT_NAME
from worker.evaluator import get_evaluator, evaluate as queue_evaluate
from worker.tools.evaluate import set_benchmark_dev_mode, BENCHMARK_TIMEOUT

# Set up console for rich output
console = Console()

# Global flag for early stopping
_stop_generation = threading.Event()


def is_significant_improvement(
    baseline_score: float,
    new_score: float,
    min_improvement_pct: float = 3.0
) -> tuple[bool, float]:
    """Check if an improvement is statistically significant (above noise threshold).
    
    Small improvements (e.g., 0.01%) are likely just benchmark instability/noise.
    This function filters out noise by requiring a minimum percentage improvement.
    
    Args:
        baseline_score: The original score to compare against.
        new_score: The new score after changes.
        min_improvement_pct: Minimum improvement percentage required (default 3%).
    
    Returns:
        Tuple of (is_significant, improvement_percent).
    """
    if baseline_score <= 0:
        # Can't calculate percentage improvement with zero/negative baseline
        return new_score > baseline_score, 0.0
    
    improvement_pct = ((new_score - baseline_score) / baseline_score) * 100
    is_significant = improvement_pct >= min_improvement_pct
    return is_significant, improvement_pct


@dataclass
class AgentResult:
    """Result from a single agent run."""
    agent_id: str
    agent_type: str
    success: bool
    baseline_score: float
    final_score: float
    improvement: float = 0.0
    error: str | None = None
    duration_seconds: float = 0.0
    files_modified: list[str] = field(default_factory=list)


@dataclass
class EvolutionState:
    """State of the evolution process."""
    generation: int = 0
    best_score: float = 0.0
    baseline_score: float = 0.0
    total_improvements: int = 0
    total_attempts: int = 0
    history: list[dict] = field(default_factory=list)
    step_count: int = 0  # Track total successful steps across all generations


def save_step_snapshot(
    source_path: Path,
    output_dir: Path,
    step_number: int,
    agent_id: str,
    baseline_score: float,
    final_score: float,
    improvement_pct: float,
    generation: int,
    console: Console | None = None,
) -> Path:
    """Save a snapshot of the codebase at a specific evolution step.
    
    Creates a folder like: output_dir/steps/step_001/
    With the codebase and a metadata.json file.
    
    Args:
        source_path: Path to the current codebase to snapshot.
        output_dir: Base output directory (the _optifinered folder).
        step_number: The step number (1-indexed).
        agent_id: ID of the agent that made this improvement.
        baseline_score: Score before this improvement.
        final_score: Score after this improvement.
        improvement_pct: Percentage improvement.
        generation: Current generation number.
        console: Rich console for output.
        
    Returns:
        Path to the created step folder.
    """
    # Create steps directory structure
    steps_dir = output_dir / "steps"
    steps_dir.mkdir(parents=True, exist_ok=True)
    
    # Create step folder with zero-padded number
    step_folder = steps_dir / f"step_{step_number:03d}"
    
    # Copy codebase to step folder
    if step_folder.exists():
        shutil.rmtree(step_folder)
    
    # Copy source (excluding .git and steps folder to avoid recursion)
    def ignore_patterns(directory, files):
        ignored = []
        if Path(directory) == source_path:
            if ".git" in files:
                ignored.append(".git")
            if "steps" in files:
                ignored.append("steps")
        elif ".git" in files:
            ignored.append(".git")
        return ignored
    
    shutil.copytree(source_path, step_folder, ignore=ignore_patterns)
    
    # Create metadata file
    metadata = {
        "step": step_number,
        "generation": generation,
        "agent_id": agent_id,
        "baseline_score": baseline_score,
        "final_score": final_score,
        "improvement": final_score - baseline_score,
        "improvement_percent": improvement_pct,
        "timestamp": datetime.now().isoformat(),
    }
    
    metadata_path = step_folder / "step_metadata.json"
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)
    
    if console:
        console.print(f"[dim]  Saved step {step_number} snapshot to: {step_folder.name}/[/dim]")
    
    return step_folder


def save_initial_snapshot(
    source_path: Path,
    output_dir: Path,
    baseline_score: float,
    console: Console | None = None,
) -> Path:
    """Save the initial (step 0) snapshot before any evolution.
    
    Args:
        source_path: Path to the initial codebase.
        output_dir: Base output directory (the _optifinered folder).
        baseline_score: Initial baseline score.
        console: Rich console for output.
        
    Returns:
        Path to the created step_000 folder.
    """
    steps_dir = output_dir / "steps"
    steps_dir.mkdir(parents=True, exist_ok=True)
    
    step_folder = steps_dir / "step_000"
    
    if step_folder.exists():
        shutil.rmtree(step_folder)
    
    # Copy source (excluding .git and steps folder)
    def ignore_patterns(directory, files):
        ignored = []
        if Path(directory) == source_path:
            if ".git" in files:
                ignored.append(".git")
            if "steps" in files:
                ignored.append("steps")
        elif ".git" in files:
            ignored.append(".git")
        return ignored
    
    shutil.copytree(source_path, step_folder, ignore=ignore_patterns)
    
    # Create metadata file
    metadata = {
        "step": 0,
        "generation": 0,
        "agent_id": "initial",
        "baseline_score": baseline_score,
        "final_score": baseline_score,
        "improvement": 0.0,
        "improvement_percent": 0.0,
        "timestamp": datetime.now().isoformat(),
        "is_initial": True,
    }
    
    metadata_path = step_folder / "step_metadata.json"
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)
    
    if console:
        console.print(f"[dim]Saved initial snapshot to: {steps_dir.name}/step_000/[/dim]")
    
    return step_folder


def _get_python_executable() -> str:
    """Get the Python executable to use for running scripts."""
    if sys.executable:
        return sys.executable
    if shutil.which("python3"):
        return "python3"
    if shutil.which("python"):
        return "python"
    return "python3"


def get_optifinered_path(original_path: Path) -> Path:
    """Get the _optifinered output directory path.
    
    The original codebase is never modified. All changes (benchmark creation,
    optimizations) are made to a copy in a directory with the _optifinered suffix.
    
    Args:
        original_path: Path to the original repository.
        
    Returns:
        Path to the _optifinered output directory.
    """
    return original_path.parent / f"{original_path.name}_optifinered"


def create_optifinered_copy(original_path: Path, console: Console) -> Path:
    """Create or update the _optifinered output directory.
    
    Creates a fresh copy of the original repository in the _optifinered directory.
    If the directory already exists, it will be removed and recreated.
    
    Args:
        original_path: Path to the original repository.
        console: Rich console for output.
        
    Returns:
        Path to the created _optifinered directory.
    """
    optifinered_path = get_optifinered_path(original_path)
    
    if optifinered_path.exists():
        console.print(f"[dim]Removing existing {optifinered_path.name}...[/dim]")
        shutil.rmtree(optifinered_path)
    
    console.print(f"[dim]Creating {optifinered_path.name} from original...[/dim]")
    shutil.copytree(original_path, optifinered_path, symlinks=True)
    
    return optifinered_path


def run_evaluator(
    evaluator_path: str, 
    workspace: str, 
    timeout: int = 120,
    return_full_data: bool = False,
) -> tuple[float | None, str | None] | tuple[float | None, str | None, dict | None]:
    """Run the evaluator script using the queue-based evaluator.

    Args:
        evaluator_path: Path to the evaluator script.
        workspace: Path to the workspace to evaluate.
        timeout: Timeout in seconds.
        return_full_data: If True, return full evaluation data as third element.

    Returns:
        Tuple of (score, error) or (score, error, data).
    """
    # Use the queue-based evaluator to prevent simultaneous evaluations
    result = queue_evaluate(workspace, evaluator_path, timeout)
    
    if not result.get("success"):
        error = result.get("error", "Unknown error")
        if return_full_data:
            return None, error, None
        return None, error
    
    score = result.get("score")
    if score is None:
        error = "Evaluator returned no score"
        if return_full_data:
            return None, error, None
        return None, error
    
    if return_full_data:
        # Build data dict from result
        # Note: score IS the primary metric (FPS, throughput, etc.) 
        # Additional metrics are in the "metrics" dict
        data = {
            "score": score,
            "metric_name": result.get("metric_name"),
            "passed": result.get("passed"),
            "tests_passed": result.get("tests_passed"),
            "tests_total": result.get("tests_total"),
            "metrics": result.get("metrics"),
            "message": result.get("message"),
        }
        return float(score), None, data
    
    return float(score), None


def copy_workspace(source: str, dest: str) -> None:
    """Copy workspace to a new directory."""
    if os.path.exists(dest):
        shutil.rmtree(dest)
    shutil.copytree(source, dest, symlinks=True)


def git_commit(workspace: str, message: str) -> str | None:
    """Create a git commit in the workspace. Returns commit hash or None."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            cwd=workspace,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            subprocess.run(["git", "init"], cwd=workspace, capture_output=True)
            subprocess.run(["git", "config", "user.email", "evolution@agent.local"], cwd=workspace, capture_output=True)
            subprocess.run(["git", "config", "user.name", "Evolution Agent"], cwd=workspace, capture_output=True)

        subprocess.run(["git", "add", "-A"], cwd=workspace, capture_output=True)

        result = subprocess.run(
            ["git", "diff", "--cached", "--quiet"],
            cwd=workspace,
            capture_output=True,
        )
        if result.returncode == 0:
            return None

        subprocess.run(
            ["git", "commit", "-m", message],
            cwd=workspace,
            capture_output=True,
        )

        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=workspace,
            capture_output=True,
            text=True,
        )
        return result.stdout.strip()[:8]

    except Exception:
        return None


def git_reset(workspace: str) -> None:
    """Reset git workspace to last commit.
    
    Note: Excludes the 'steps/' directory from git clean to preserve
    step snapshots across evolution iterations.
    """
    try:
        subprocess.run(["git", "checkout", "--", "."], cwd=workspace, capture_output=True)
        subprocess.run(["git", "clean", "-fd", "-e", "steps/"], cwd=workspace, capture_output=True)
    except Exception:
        pass


def run_single_agent_isolated(
    source_workspace: str,
    evaluator_path: str,
    agent_type: str,
    agent_id: str,
    baseline_score: float,
    task: str,
    max_iterations: int,
    model_provider: str,
    model_name: str,
    verbosity: int = 1,
    log_dir: str | None = None,
    baseline_data: dict | None = None,
    stop_event: threading.Event | None = None,
    compact: bool = False,
    min_improvement_pct: float = 3.0,
) -> tuple[AgentResult, WorkspaceManager | None]:
    """Run a single evolution agent in an isolated workspace.

    Args:
        source_workspace: Path to the source workspace to copy.
        evaluator_path: Path to the evaluator script.
        agent_type: Type of agent to run.
        agent_id: Unique ID for this agent.
        baseline_score: Current baseline score to beat.
        task: Task description.
        max_iterations: Maximum iterations.
        model_provider: LLM provider.
        model_name: Model name.
        verbosity: Observability verbosity.
        log_dir: Optional directory to write agent logs.
        baseline_data: Optional dict with baseline evaluation data.
        stop_event: Optional threading.Event to check for early stopping.
        compact: Enable compact logging mode for parallel execution.
        min_improvement_pct: Minimum improvement percentage to consider significant.

    Returns:
        Tuple of (AgentResult, workspace_manager). Workspace is kept if successful
        so changes can be copied back.
    """
    from worker.config import AgentType, ModelConfig, ModelProvider, WorkerConfig
    from worker.agent import run_evolution_agent, extract_score_from_messages
    from worker.tools.evaluate import set_evaluator

    start_time = time.time()

    # Check if we should stop before even starting
    if stop_event and stop_event.is_set():
        return AgentResult(
            agent_id=agent_id,
            agent_type=agent_type,
            success=False,
            baseline_score=baseline_score,
            final_score=baseline_score,
            error="Stopped: another agent found improvement",
            duration_seconds=time.time() - start_time,
        ), None

    # Create isolated workspace - use full agent_id to ensure uniqueness
    # Previously used agent_id[:8] which caused all agents to share workspace!
    workspace = WorkspaceManager(workspace_id=agent_id.replace("-", "_")[:32])
    try:
        workspace.setup(source_workspace)
    except Exception as e:
        return AgentResult(
            agent_id=agent_id,
            agent_type=agent_type,
            success=False,
            baseline_score=baseline_score,
            final_score=baseline_score,
            error=f"Workspace setup failed: {e}",
            duration_seconds=time.time() - start_time,
        ), None

    # Set the workspace context for tools using context var and thread-local
    # NOTE: We do NOT set os.environ["WORKSPACE_ROOT"] here because that's shared
    # across all threads and causes race conditions in parallel execution.
    # The workspace module uses ContextVar and thread-local for isolation.
    set_workspace(workspace)

    # Configure evaluator for improver mode (timeouts are hard fails)
    set_benchmark_dev_mode(False)
    
    # Check if the evaluator is an in-workspace benchmark (optifiner_benchmark.py)
    # vs an external evaluator. For in-workspace benchmarks, DON'T set the override
    # so the evaluate tool uses the COPY in the isolated workspace (where agent made changes).
    # External evaluators (like volumetric_particle_evaluator.py) should use WORKSPACE_ROOT
    # env var to find the code to evaluate.
    evaluator_filename = os.path.basename(evaluator_path)
    if evaluator_filename == BENCHMARK_SCRIPT_NAME:
        # In-workspace benchmark: let evaluate tool use workspace_root/optifiner_benchmark.py
        # This ensures we evaluate the agent's changes, not the original code
        set_evaluator(None, timeout=BENCHMARK_TIMEOUT)
    else:
        # External evaluator: set the override path
        # The external evaluator should use WORKSPACE_ROOT env var to find code
        set_evaluator(evaluator_path, timeout=BENCHMARK_TIMEOUT)

    # Set up observer
    log_file = None
    if log_dir:
        Path(log_dir).mkdir(parents=True, exist_ok=True)
        log_file = str(Path(log_dir) / f"{agent_id}.jsonl")

    observer = AgentObserver(
        verbosity=verbosity,
        console=console,
        log_file=log_file,
        agent_id=agent_id,
        compact=compact,
    )
    set_observer(observer)

    # Build config
    # Timeout for gemini flash model
    model_timeout = 120.0 if "gemini" in model_name.lower() and "flash" in model_name.lower() else 60.0
    try:
        config = WorkerConfig(
            model=ModelConfig(
                provider=ModelProvider(model_provider),
                model_name=model_name,
                temperature=0.0,
                max_tokens=8192,
                timeout=model_timeout,
                max_retries=3,
            ),
            agent_type=AgentType(agent_type),
            max_iterations=max_iterations,
            workspace_root=str(workspace.actual_root),
        )
    except Exception as e:
        observer.close()
        workspace.cleanup()
        set_workspace(None)
        return AgentResult(
            agent_id=agent_id,
            agent_type=agent_type,
            success=False,
            baseline_score=baseline_score,
            final_score=baseline_score,
            error=f"Config error: {e}",
            duration_seconds=time.time() - start_time,
        ), None

    # Build baseline info string - use score as the primary metric
    # Score IS the metric (FPS, throughput, etc.) so don't show them separately
    baseline_info = f"Current baseline score: {baseline_score}"
    if baseline_data:
        if "tests_passed" in baseline_data and "tests_total" in baseline_data:
            baseline_info += f"\nBaseline tests: {baseline_data['tests_passed']}/{baseline_data['tests_total']} passed"
        if "metrics" in baseline_data:
            # Filter out the primary metric from additional metrics display to avoid confusion
            # The score already represents the primary metric
            additional_metrics = {k: v for k, v in baseline_data["metrics"].items()}
            if additional_metrics:
                metrics_str = ", ".join(f"{k}={v}" for k, v in additional_metrics.items())
                baseline_info += f"\nBaseline metrics: {metrics_str}"

    # Run the agent
    try:
        final_task = f"""Optimize this codebase to improve its benchmark score (currently {baseline_score}).

{task}

{baseline_info}

## Your Mission
Find and fix ONE performance bottleneck to beat the baseline score of {baseline_score}.

## Workflow
1. **READ** the main files to understand the code structure
2. **IDENTIFY** the biggest performance bottleneck (look for: nested loops, object creation in hot paths, redundant calculations, Python loops that could be vectorized)
3. **IMPLEMENT** your optimization
4. **VERIFY** with `evaluate` - if score > {baseline_score}, you've succeeded!

## Quick Wins to Look For
- Nested loops over collections → spatial partitioning or hash maps
- Python loops over numbers/arrays → NumPy vectorization  
- Same calculation repeated → caching/memoization
- Objects created every frame → pre-allocation or pooling
- Many individual draw calls → sprite caching or batching

Don't run `evaluate` until you've made changes - the baseline is already measured."""

        state = run_evolution_agent(
            task=final_task,
            config=config,
            agent_id=agent_id,
            generation=0,
            baseline_score=baseline_score,
            observer=observer,
            min_improvement_pct=min_improvement_pct,
        )

        # Extract the final score
        final_score = extract_score_from_messages(state.messages)

        # If we couldn't extract from messages, run evaluator directly
        if final_score is None:
            eval_result = run_evaluator(evaluator_path, str(workspace.actual_root))
            final_score, eval_error = eval_result[0], eval_result[1]
            if eval_error:
                observer.close()
                set_workspace(None)
                workspace.cleanup()
                return AgentResult(
                    agent_id=agent_id,
                    agent_type=agent_type,
                    success=False,
                    baseline_score=baseline_score,
                    final_score=baseline_score,
                    error=eval_error,
                    duration_seconds=time.time() - start_time,
                ), None

        if final_score is None:
            final_score = baseline_score

        improvement = final_score - baseline_score
        success = improvement > 0

        if verbosity >= 2:
            observer.print_summary()

        observer.close()
        set_workspace(None)

        # Keep workspace if successful for copying back
        if not success:
            workspace.cleanup()
            workspace = None

        return AgentResult(
            agent_id=agent_id,
            agent_type=agent_type,
            success=success,
            baseline_score=baseline_score,
            final_score=final_score,
            improvement=improvement,
            duration_seconds=time.time() - start_time,
            files_modified=state.files_modified if hasattr(state, 'files_modified') else [],
        ), workspace

    except Exception as e:
        observer.on_error(str(e))
        observer.close()
        set_workspace(None)
        workspace.cleanup()
        return AgentResult(
            agent_id=agent_id,
            agent_type=agent_type,
            success=False,
            baseline_score=baseline_score,
            final_score=baseline_score,
            error=str(e),
            duration_seconds=time.time() - start_time,
        ), None


def run_benchmark_builder_cli(
    repository_path: Path,
    output_path: Path,
    model_provider: str,
    model_name: str,
    max_iterations: int = 30,
    verbosity: int = 1,
) -> tuple[bool, str, Path | None]:
    """Run the benchmark builder agent to create optifiner_benchmark.py.
    
    The agent works in an isolated workspace copied from output_path (which is
    already a copy of the original). Changes are written back to output_path,
    never to the original repository.
    
    Args:
        repository_path: Path to the original repository (for reference only).
        output_path: Path to the _optifinered output directory where changes go.
        model_provider: LLM provider.
        model_name: Model name.
        max_iterations: Maximum iterations for the agent.
        verbosity: Verbosity level.
        
    Returns:
        Tuple of (success, message, benchmark_path).
    """
    from worker.benchmark_builder import run_benchmark_builder
    from worker.config import ModelConfig, ModelProvider
    
    console.print("\n[bold cyan]Running Benchmark Builder Agent...[/bold cyan]")
    console.print(f"[dim]This agent will:[/dim]")
    console.print(f"[dim]  1. Analyze the codebase[/dim]")
    console.print(f"[dim]  2. Modify files to expose metrics (FPS, timing, etc.) if needed[/dim]")
    console.print(f"[dim]  3. Create {BENCHMARK_SCRIPT_NAME} benchmark script[/dim]")
    console.print(f"[dim]  4. Test and iterate until it works[/dim]")
    console.print(f"[dim]All changes will be saved to: {output_path}[/dim]")
    
    # Create workspace for benchmark builder (from the output_path, not original)
    workspace = WorkspaceManager(workspace_id="benchmark-builder")
    workspace.setup(output_path)
    
    # Set up observer
    observer = AgentObserver(
        verbosity=verbosity,
        console=console,
    )
    set_observer(observer)
    
    try:
        # Timeout for gemini flash model
        model_timeout = 120.0 if "gemini" in model_name.lower() and "flash" in model_name.lower() else 60.0
        model_config = ModelConfig(
            provider=ModelProvider(model_provider),
            model_name=model_name,
            temperature=0.0,
            max_tokens=8192,
            timeout=model_timeout,
            max_retries=3,
        )
        
        success, message = run_benchmark_builder(
            workspace=workspace,
            max_iterations=max_iterations,
            model_config=model_config,
            observer=observer,
        )
        
        if success:
            # Copy ALL changes back to the output directory (not the original repo!)
            # The benchmark builder may have modified the codebase to expose metrics
            # These modifications become the baseline for evolution agents
            console.print(f"[dim]Copying all modifications to output directory...[/dim]")
            
            modified_files = []
            for item in workspace.actual_root.rglob("*"):
                if item.is_file():
                    rel_path = item.relative_to(workspace.actual_root)
                    
                    # Skip git internals
                    if ".git" in rel_path.parts:
                        continue
                    
                    dst_path = output_path / rel_path
                    src_path = item
                    
                    # Check if file is new or modified
                    is_new = not dst_path.exists()
                    is_modified = False
                    if dst_path.exists():
                        try:
                            is_modified = src_path.read_bytes() != dst_path.read_bytes()
                        except Exception:
                            pass
                    
                    if is_new or is_modified:
                        dst_path.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(src_path, dst_path)
                        modified_files.append(str(rel_path))
            
            if modified_files:
                console.print(f"[green]✓ Modified {len(modified_files)} file(s):[/green]")
                for f in modified_files[:10]:  # Show first 10
                    console.print(f"[dim]  - {f}[/dim]")
                if len(modified_files) > 10:
                    console.print(f"[dim]  ... and {len(modified_files) - 10} more[/dim]")
            
            benchmark_path = output_path / BENCHMARK_SCRIPT_NAME
            if benchmark_path.exists():
                console.print(f"[green]✓ Benchmark script ready at {benchmark_path}[/green]")
                return True, message, benchmark_path
            else:
                console.print(f"[red]✗ {BENCHMARK_SCRIPT_NAME} not created[/red]")
                return False, "Benchmark script was not created", None
        
        console.print(f"[red]✗ Benchmark builder failed: {message}[/red]")
        return False, message, None
        
    finally:
        workspace.cleanup()
        set_workspace(None)
        observer.close()


@click.command()
@click.argument("repository", type=click.Path(exists=True))
@click.option("--evaluator", "-e", type=click.Path(),
              help="Path to evaluator script. If not provided, will run benchmark builder to create one.")
@click.option("--agents", "-n", default=10, help="Number of agents to run (default: 10)")
@click.option("--parallel", "-p", default=1, help="Number of agents to run in parallel (default: 1)")
@click.option("--generations", "-g", default=1, help="Number of evolution generations (default: 1)")
@click.option("--max-iterations", "-i", default=15, help="Max iterations per agent (default: 15)")
@click.option("--task", "-t", default="Improve the code to get a higher benchmark score.",
              help="Task description for agents")
@click.option("--model-provider", default="google",
              type=click.Choice(["anthropic", "google", "openai"]),
              help="LLM provider (default: google)")
@click.option("--model-name", default="gemini-3-flash-preview",
              help="Model name (default: gemini-3-flash-preview)")
@click.option("--output", "-o", type=click.Path(), help="Output file for results (JSON)")
@click.option("--verbose", "-v", count=True, default=1,
              help="Increase verbosity (-v=normal, -vv=verbose, -vvv=debug, omit for quiet)")
@click.option("--quiet", "-q", is_flag=True, help="Quiet mode - minimal output (overrides -v)")
@click.option("--log-dir", "-l", type=click.Path(),
              help="Directory to save agent execution logs (JSONL format)")
@click.option("--early-stop/--no-early-stop", default=True,
              help="Stop generation early when improvement found (default: enabled)")
@click.option("--build-benchmark", "-b", is_flag=True,
              help="Run benchmark builder agent to create optifiner_benchmark.py")
@click.option("--min-improvement", "-m", default=6.0, type=float,
              help="Minimum improvement percentage to accept a change (default: 6.0%%, filters noise)")
def main(
    repository: str,
    evaluator: str | None,
    agents: int,
    parallel: int,
    generations: int,
    max_iterations: int,
    task: str,
    model_provider: str,
    model_name: str,
    output: str | None,
    verbose: int,
    quiet: bool,
    log_dir: str | None,
    early_stop: bool,
    build_benchmark: bool,
    min_improvement: float,
):
    """Run evolution agents on a repository to improve its benchmark score.

    REPOSITORY: Path to the target repository to evolve.

    The benchmark script must output JSON with these required fields:
        - score: Primary metric value (number, non-null)
        - metric_name: Name of the metric (e.g., "FPS", "throughput")
        - test_gate: Boolean, must be true for valid run

    Example output:
        {"score": 60.5, "metric_name": "FPS", "test_gate": true, "metrics": {...}}

    If no benchmark exists, use --build-benchmark to automatically
    create one using the Benchmark Builder Agent.

    VERBOSITY LEVELS:
        (no flags): quiet mode - only show progress and results
        -v: normal - show iteration progress, tool calls (compact)
        -vv: verbose - show agent reasoning, full tool calls/results
        -vvv: debug - show everything including full system prompts
    
    EARLY STOPPING:
        By default, when an agent finds an improvement, the current generation
        stops and a new generation begins with the improved codebase.
        Use --no-early-stop to disable this behavior.
    """
    global _stop_generation
    
    repository_path = Path(repository).resolve()
    
    # Determine verbosity level
    verbosity = 0 if quiet else verbose

    # Resolve log directory
    log_directory = str(Path(log_dir).resolve()) if log_dir else None

    # Create the _optifinered output directory - original codebase is never modified
    console.print(f"\n[bold cyan]Setting up output directory...[/bold cyan]")
    working_path = create_optifinered_copy(repository_path, console)
    console.print(f"[green]Output directory: {working_path}[/green]")
    console.print(f"[dim]Original repository will not be modified.[/dim]\n")

    # Handle evaluator
    evaluator_path: Path | None = None
    
    if evaluator:
        evaluator_path = Path(evaluator).resolve()
        if not evaluator_path.exists():
            console.print(f"[red]Error: Evaluator not found: {evaluator_path}[/red]")
            sys.exit(1)
    else:
        # Check for benchmark script in working_path - try new name first, then legacy name
        benchmark_path = working_path / BENCHMARK_SCRIPT_NAME
        legacy_path = working_path / "run_validator.py"
        
        if benchmark_path.exists():
            evaluator_path = benchmark_path
            console.print(f"[dim]Using existing benchmark: {evaluator_path}[/dim]")
        elif legacy_path.exists():
            evaluator_path = legacy_path
            console.print(f"[dim]Using legacy benchmark: {evaluator_path}[/dim]")
        elif build_benchmark:
            # Explicitly requested to build benchmark
            success, message, created_path = run_benchmark_builder_cli(
                repository_path,
                working_path,
                model_provider,
                model_name,
                max_iterations=50,
                verbosity=verbosity,
            )
            
            if not success:
                console.print(f"[red]Failed to create benchmark: {message}[/red]")
                sys.exit(1)
            
            evaluator_path = created_path
        else:
            # No benchmark found, need to build one
            console.print(f"[yellow]No benchmark found ({BENCHMARK_SCRIPT_NAME} or run_validator.py).[/yellow]")
            console.print("[yellow]Running benchmark builder agent to create one...[/yellow]")
            
            success, message, created_path = run_benchmark_builder_cli(
                repository_path,
                working_path,
                model_provider,
                model_name,
                max_iterations=50,
                verbosity=verbosity,
            )
            
            if not success:
                console.print(f"[red]Failed to create benchmark: {message}[/red]")
                sys.exit(1)
            
            evaluator_path = created_path

    if evaluator_path is None:
        console.print("[red]Error: No evaluator available[/red]")
        sys.exit(1)

    console.print(Panel.fit(
        f"[bold cyan]Self-Evolving Code Framework[/bold cyan]\n\n"
        f"Original: [dim]{repository_path}[/dim] [yellow](unchanged)[/yellow]\n"
        f"Output: [green]{working_path}[/green]\n"
        f"Evaluator: [green]{evaluator_path}[/green]\n"
        f"Agents: [yellow]{agents}[/yellow] (parallel: {parallel})\n"
        f"Generations: [yellow]{generations}[/yellow]\n"
        f"Model: [blue]{model_provider}/{model_name}[/blue]\n"
        f"Verbosity: [magenta]{['quiet', 'normal', 'verbose', 'debug'][min(verbosity, 3)]}[/magenta]\n"
        f"Early stop: [{'green' if early_stop else 'dim'}]{early_stop}[/{'green' if early_stop else 'dim'}]"
        + (f"\nLog dir: [dim]{log_directory}[/dim]" if log_directory else ""),
        title="Evolution Setup"
    ))

    # Get initial baseline score with full data (from the working copy)
    console.print("\n[bold]Getting baseline score...[/bold]")
    baseline_result = run_evaluator(str(evaluator_path), str(working_path), return_full_data=True)
    baseline_score, baseline_error, baseline_data = baseline_result

    if baseline_error:
        console.print(f"[red]Error getting baseline: {baseline_error}[/red]")
        console.print("[yellow]Tip: Make sure your evaluator script works correctly.[/yellow]")
        sys.exit(1)

    console.print(f"[green]Baseline score: {baseline_score}[/green]")
    console.print(f"[dim]Minimum improvement threshold: {min_improvement}% (filters noise)[/dim]")
    if baseline_data:
        if baseline_data.get("tests_passed") is not None and baseline_data.get("tests_total") is not None:
            console.print(f"[dim]  Tests: {baseline_data['tests_passed']}/{baseline_data['tests_total']}[/dim]")
        if baseline_data.get("metrics"):
            # Show all metrics - score already represents the primary metric
            for k, v in baseline_data["metrics"].items():
                console.print(f"[dim]  {k}: {v}[/dim]")
    console.print()

    # Initialize evolution state
    state = EvolutionState(
        baseline_score=baseline_score,
        best_score=baseline_score,
    )

    # Save initial snapshot (step 0)
    save_initial_snapshot(working_path, working_path, baseline_score, console)

    # Create initial git commit in the working copy
    commit_hash = git_commit(str(working_path), f"Initial state - Score: {baseline_score}")
    if commit_hash:
        console.print(f"[dim]Created initial commit: {commit_hash}[/dim]")

    # Agent types to cycle through
    agent_types = ["optimizer", "refactoring", "feature", "analyzer", "general"]

    # Track current baseline data for agents
    current_baseline_data = baseline_data

    # Run evolution generations
    gen = 0
    while gen < generations:
        gen += 1
        state.generation = gen
        _stop_generation.clear()
        
        console.print(f"\n[bold cyan]═══ Generation {state.generation} ═══[/bold cyan]")
        console.print(f"Current best score: [green]{state.best_score}[/green]")

        generation_results: list[AgentResult] = []
        generation_improved = False

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console,
        ) as progress:
            task_id = progress.add_task(f"[cyan]Running {agents} agents...", total=agents)

            if parallel == 1:
                # Sequential execution
                for i in range(agents):
                    if early_stop and _stop_generation.is_set():
                        console.print(f"[yellow]⚡ Early stop triggered - starting new generation[/yellow]")
                        break
                    
                    agent_type = agent_types[i % len(agent_types)]
                    agent_id = f"gen{state.generation}-{agent_type}-{i+1}"

                    progress.update(task_id, description=f"[cyan]Agent {i+1}/{agents} ({agent_type})...")

                    result, workspace = run_single_agent_isolated(
                        source_workspace=str(working_path),
                        evaluator_path=str(evaluator_path),
                        agent_type=agent_type,
                        agent_id=agent_id,
                        baseline_score=state.best_score,
                        task=task,
                        max_iterations=max_iterations,
                        model_provider=model_provider,
                        model_name=model_name,
                        verbosity=verbosity,
                        log_dir=log_directory,
                        baseline_data=current_baseline_data,
                        stop_event=_stop_generation if early_stop else None,
                        min_improvement_pct=min_improvement,
                    )

                    generation_results.append(result)
                    state.total_attempts += 1

                    # Check if improvement is statistically significant (above noise threshold)
                    is_significant, improvement_pct = is_significant_improvement(
                        state.best_score, result.final_score, min_improvement
                    )
                    if result.success and is_significant and workspace:
                        # Copy improved workspace back to working copy (not original!)
                        git_reset(str(working_path))
                        
                        # Remove files and copy improved version (preserve steps folder)
                        for item in working_path.iterdir():
                            if item.name != ".git" and item.name != "steps":
                                if item.is_dir():
                                    shutil.rmtree(item)
                                else:
                                    item.unlink()
                        
                        for item in workspace.actual_root.iterdir():
                            if item.name != ".git" and item.name != "steps":
                                if item.is_dir():
                                    shutil.copytree(item, working_path / item.name)
                                else:
                                    shutil.copy2(item, working_path / item.name)

                        previous_score = state.best_score
                        state.best_score = result.final_score
                        state.total_improvements += 1
                        state.step_count += 1
                        generation_improved = True

                        # Save step snapshot BEFORE git commit so it's included in the commit
                        # and survives subsequent git_reset calls (which run git clean -fd)
                        save_step_snapshot(
                            source_path=working_path,
                            output_dir=working_path,
                            step_number=state.step_count,
                            agent_id=agent_id,
                            baseline_score=previous_score,
                            final_score=result.final_score,
                            improvement_pct=improvement_pct,
                            generation=state.generation,
                            console=console,
                        )

                        commit_msg = (
                            f"Gen {state.generation} | Agent {agent_id}: +{improvement_pct:.1f}% "
                            f"({result.baseline_score:.2f} → {result.final_score:.2f})"
                        )
                        commit_hash = git_commit(str(working_path), commit_msg)

                        console.print(f"\n[green]✓ Agent {agent_id} improved! "
                                      f"Score: {result.baseline_score:.2f} → {result.final_score:.2f} "
                                      f"(+{improvement_pct:.1f}%)[/green]")
                        if commit_hash:
                            console.print(f"[dim]  Committed: {commit_hash}[/dim]")

                        # Update baseline data
                        new_result = run_evaluator(str(evaluator_path), str(working_path), return_full_data=True)
                        if new_result[0] is not None:
                            current_baseline_data = new_result[2]

                        if early_stop:
                            _stop_generation.set()
                    else:
                        if result.error:
                            status = f"error: {result.error[:50]}"
                        elif result.final_score > state.best_score:
                            # Improved but below threshold
                            status = f"improvement too small ({improvement_pct:.1f}% < {min_improvement}%)"
                        else:
                            status = "no improvement"
                        console.print(f"[dim]✗ Agent {agent_id}: {status}[/dim]")

                    # Clean up workspace if we kept it
                    if workspace:
                        workspace.cleanup()

                    progress.update(task_id, advance=1)

            else:
                # Parallel execution with compact logging
                console.print(f"[dim]Running {agents} agents in parallel ({parallel} at a time)...[/dim]")
                
                def run_agent_parallel(i: int) -> tuple[AgentResult, WorkspaceManager | None]:
                    agent_type = agent_types[i % len(agent_types)]
                    agent_id = f"gen{state.generation}-{agent_type}-{i+1}"
                    
                    return run_single_agent_isolated(
                        source_workspace=str(working_path),
                        evaluator_path=str(evaluator_path),
                        agent_type=agent_type,
                        agent_id=agent_id,
                        baseline_score=state.best_score,
                        task=task,
                        max_iterations=max_iterations,
                        model_provider=model_provider,
                        model_name=model_name,
                        verbosity=verbosity,  # Use actual verbosity setting
                        log_dir=log_directory,
                        baseline_data=current_baseline_data,
                        stop_event=_stop_generation if early_stop else None,
                        compact=True,  # Enable compact logging for parallel agents
                        min_improvement_pct=min_improvement,
                    )

                try:
                    with ThreadPoolExecutor(max_workers=parallel) as executor:
                        futures = {executor.submit(run_agent_parallel, i): i for i in range(agents)}
                        early_stop_triggered = False

                        for future in as_completed(futures):
                            # Check early stop AFTER getting result to not discard already-completed work
                            # We still process results that beat the current best score
                            try:
                                result, workspace = future.result()
                            except Exception:
                                progress.update(task_id, advance=1)
                                # Only break if early stop was already triggered and we got an error
                                if early_stop_triggered:
                                    continue
                                continue

                            generation_results.append(result)
                            state.total_attempts += 1

                            # Check if improvement is statistically significant
                            is_significant, improvement_pct = is_significant_improvement(
                                state.best_score, result.final_score, min_improvement
                            )
                            if result.success and is_significant and workspace:
                                git_reset(str(working_path))
                                
                                # Preserve steps folder when copying
                                for item in working_path.iterdir():
                                    if item.name != ".git" and item.name != "steps":
                                        if item.is_dir():
                                            shutil.rmtree(item)
                                        else:
                                            item.unlink()
                                
                                for item in workspace.actual_root.iterdir():
                                    if item.name != ".git" and item.name != "steps":
                                        if item.is_dir():
                                            shutil.copytree(item, working_path / item.name)
                                        else:
                                            shutil.copy2(item, working_path / item.name)

                                previous_score = state.best_score
                                state.best_score = result.final_score
                                state.total_improvements += 1
                                state.step_count += 1
                                generation_improved = True

                                # Save step snapshot BEFORE git commit so it's included in the commit
                                # and survives subsequent git_reset calls (which run git clean -fd)
                                save_step_snapshot(
                                    source_path=working_path,
                                    output_dir=working_path,
                                    step_number=state.step_count,
                                    agent_id=result.agent_id,
                                    baseline_score=previous_score,
                                    final_score=result.final_score,
                                    improvement_pct=improvement_pct,
                                    generation=state.generation,
                                    console=console,
                                )

                                commit_msg = f"Gen {state.generation} | Agent {result.agent_id}: +{improvement_pct:.1f}%"
                                git_commit(str(working_path), commit_msg)

                                console.print(f"\n[green]✓ {result.agent_id} improved! +{improvement_pct:.1f}%[/green]")

                                new_result = run_evaluator(str(evaluator_path), str(working_path), return_full_data=True)
                                if new_result[0] is not None:
                                    current_baseline_data = new_result[2]

                                if early_stop and not early_stop_triggered:
                                    _stop_generation.set()
                                    early_stop_triggered = True
                                    # Cancel remaining futures but continue processing completed ones
                                    for f in futures:
                                        f.cancel()
                                    console.print(f"[yellow]⚡ Early stop - cancelling remaining agents[/yellow]")

                            if workspace:
                                workspace.cleanup()

                            progress.update(task_id, advance=1)

                except Exception as e:
                    console.print(f"[red]Error in parallel execution: {e}[/red]")

        # Generation summary
        successful = [r for r in generation_results if r.success]
        console.print(f"\n[bold]Generation {state.generation} Summary:[/bold]")
        console.print(f"  Successful improvements: [green]{len(successful)}/{len(generation_results)}[/green]")
        console.print(f"  Best score: [cyan]{state.best_score}[/cyan]")

        state.history.append({
            "generation": state.generation,
            "best_score": state.best_score,
            "improvements": len(successful),
            "attempts": len(generation_results),
            "results": [
                {
                    "agent_id": r.agent_id,
                    "agent_type": r.agent_type,
                    "success": r.success,
                    "improvement": r.improvement,
                    "duration": r.duration_seconds,
                    "error": r.error,
                }
                for r in generation_results
            ],
        })

        if early_stop and generation_improved and gen < generations:
            console.print(f"[cyan]Starting new generation with improved codebase...[/cyan]")

    # Final summary
    console.print("\n" + "═" * 50)
    improvement_pct = ((state.best_score - state.baseline_score) / state.baseline_score * 100) if state.baseline_score > 0 else 0
    steps_info = f"\n[bold]Version history:[/bold] [green]{working_path / 'steps'}[/green] ({state.step_count + 1} snapshots)"
    console.print(Panel.fit(
        f"[bold]Evolution Complete![/bold]\n\n"
        f"Initial score: [yellow]{state.baseline_score}[/yellow]\n"
        f"Final score: [green]{state.best_score}[/green]\n"
        f"Total improvement: [cyan]+{state.best_score - state.baseline_score:.2f}[/cyan] "
        f"([cyan]+{improvement_pct:.1f}%[/cyan])\n\n"
        f"Successful improvements: {state.total_improvements}/{state.total_attempts}\n\n"
        f"[bold]Output location:[/bold] [green]{working_path}[/green]"
        f"{steps_info}\n"
        f"[dim]Original repository was not modified.[/dim]",
        title="Results"
    ))

    # Save results
    if output:
        # Collect step metadata
        steps_metadata = []
        steps_dir = working_path / "steps"
        if steps_dir.exists():
            for step_folder in sorted(steps_dir.iterdir()):
                metadata_file = step_folder / "step_metadata.json"
                if metadata_file.exists():
                    with open(metadata_file) as f:
                        steps_metadata.append(json.load(f))
        
        results_data = {
            "repository": str(repository_path),
            "output_directory": str(working_path),
            "steps_directory": str(steps_dir),
            "evaluator": str(evaluator_path),
            "baseline_score": state.baseline_score,
            "final_score": state.best_score,
            "improvement": state.best_score - state.baseline_score,
            "improvement_percent": improvement_pct,
            "total_improvements": state.total_improvements,
            "total_steps": state.step_count,
            "total_attempts": state.total_attempts,
            "generations": state.history,
            "steps": steps_metadata,
            "timestamp": datetime.now().isoformat(),
            "early_stop": early_stop,
        }
        with open(output, "w") as f:
            json.dump(results_data, f, indent=2)
        console.print(f"\n[dim]Results saved to: {output}[/dim]")


if __name__ == "__main__":
    main()
