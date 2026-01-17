"""Docker container entrypoint for running agents.

This module is executed inside the Docker container. It reads configuration
from environment variables and runs the agent, outputting results as JSON.
"""

import json
import os
import sys
import time

from worker.config import AgentType, ModelConfig, ModelProvider, WorkerConfig
from worker.agent import run_evolution_agent, extract_score_from_messages
from worker.tools.evaluate import set_evaluator
from worker.observability import AgentObserver, set_observer


def main():
    """Main entrypoint for Docker-based agent execution."""
    start_time = time.time()
    
    # Read configuration from environment
    workspace = os.environ.get("WORKSPACE_ROOT", "/workspace")
    agent_type = os.environ.get("AGENT_TYPE", "general")
    agent_id = os.environ.get("AGENT_ID", "docker-agent")
    baseline_score = float(os.environ.get("BASELINE_SCORE", "0"))
    max_iterations = int(os.environ.get("MAX_ITERATIONS", "15"))
    model_provider = os.environ.get("MODEL_PROVIDER", "google")
    model_name = os.environ.get("MODEL_NAME", "gemini-3-flash-preview")
    task = os.environ.get("TASK", "Improve the code to get a higher benchmark score.")
    evaluator_path = os.environ.get("EVALUATOR_PATH", "")
    
    # Parse baseline data if provided
    baseline_data = None
    baseline_data_json = os.environ.get("BASELINE_DATA")
    if baseline_data_json:
        try:
            baseline_data = json.loads(baseline_data_json)
        except json.JSONDecodeError:
            pass
    
    # Set workspace root
    os.environ["WORKSPACE_ROOT"] = workspace
    
    # Configure evaluator
    if evaluator_path:
        set_evaluator(evaluator_path)
    
    # Create quiet observer (container output should be minimal)
    observer = AgentObserver(verbosity=0)
    set_observer(observer)
    
    # Build config
    try:
        config = WorkerConfig(
            model=ModelConfig(
                provider=ModelProvider(model_provider),
                model_name=model_name,
                temperature=0.0,
                max_tokens=8192,
            ),
            agent_type=AgentType(agent_type),
            max_iterations=max_iterations,
            workspace_root=workspace,
        )
    except Exception as e:
        result = {
            "agent_id": agent_id,
            "success": False,
            "baseline_score": baseline_score,
            "final_score": baseline_score,
            "error": f"Config error: {e}",
            "duration_seconds": time.time() - start_time,
        }
        print(json.dumps(result))
        sys.exit(1)
    
    # Build the task with baseline info
    baseline_info = f"Current baseline score: {baseline_score}"
    if baseline_data:
        baseline_info += f"\nBaseline details: FPS={baseline_data.get('fps', 'N/A')}, "
        baseline_info += f"Tests passed={baseline_data.get('tests_passed', 'N/A')}/{baseline_data.get('tests_total', 'N/A')}"
    
    final_task = f"""Your goal is to improve the codebase to increase its benchmark score.

{task}

{baseline_info}

IMPORTANT: The baseline score has already been measured - you do NOT need to run evaluate first.
Start by exploring the codebase and making improvements directly.

After making changes, use `evaluate` to test if your changes improved the score.
If score improved above {baseline_score}, you've succeeded!"""

    # Run the agent
    try:
        state = run_evolution_agent(
            task=final_task,
            config=config,
            agent_id=agent_id,
            generation=0,
            baseline_score=baseline_score,
            observer=observer,
        )
        
        # Extract final score
        final_score = extract_score_from_messages(state.messages)
        if final_score is None:
            final_score = baseline_score
        
        improvement = final_score - baseline_score
        success = improvement > 0
        
        result = {
            "agent_id": agent_id,
            "agent_type": agent_type,
            "success": success,
            "baseline_score": baseline_score,
            "final_score": final_score,
            "improvement": improvement,
            "duration_seconds": time.time() - start_time,
            "files_modified": state.files_modified if hasattr(state, 'files_modified') else [],
        }
        
        print(json.dumps(result))
        sys.exit(0 if success else 1)
        
    except Exception as e:
        result = {
            "agent_id": agent_id,
            "success": False,
            "baseline_score": baseline_score,
            "final_score": baseline_score,
            "error": str(e),
            "duration_seconds": time.time() - start_time,
        }
        print(json.dumps(result))
        sys.exit(1)


if __name__ == "__main__":
    main()
