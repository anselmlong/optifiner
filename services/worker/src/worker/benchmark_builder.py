"""Benchmark Builder Agent - creates benchmark scripts for codebases.

This agent analyzes a target codebase and generates a benchmark script
(run_validator.py) that:
1. Returns a score (primary metric like FPS, throughput, etc.)
2. Contains tests to ensure the application works correctly
3. Exposes metrics that would otherwise be hidden (FPS, memory usage, etc.)

The agent can:
- Read and analyze the codebase
- Write the benchmark script
- Run commands to test the script
- Install dependencies
- Iterate until the script works correctly
"""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, ToolMessage
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from pydantic import BaseModel, Field

from worker.config import ModelConfig, WorkerConfig, get_llm
from worker.observability import AgentObserver, get_observer
from worker.state import AgentState
from worker.workspace import WorkspaceManager, set_workspace, get_workspace
from worker.tools import get_benchmark_builder_tools


# System prompt for the benchmark builder agent
BENCHMARK_BUILDER_PROMPT = '''You are an expert Benchmark Builder Agent. Your task is to analyze a codebase and create a comprehensive benchmark script.

## Your Goal
Create a benchmark script at `/app/run_validator.py` that:
1. **Returns a score** - The primary performance metric (FPS, throughput, latency inverse, etc.)
2. **Contains functional tests** - Verifies the application works correctly
3. **Exposes hidden metrics** - If necessary, MODIFY the codebase files to expose FPS, memory usage, or other metrics

## IMPORTANT: You CAN and SHOULD Edit Codebase Files
You have FULL permission to edit any file in the codebase at `/app`. This is critical because:
- Many applications don't expose performance metrics by default
- You need to add instrumentation code to measure FPS, timing, memory, etc.
- Your modifications become the BASELINE for optimization agents

### What You Should Edit:
- Add FPS counters to game loops
- Add timing instrumentation to performance-critical functions
- Add memory tracking code
- Create hooks that your benchmark script can call
- Add global variables or functions to expose metrics

### What NOT to Change:
- Don't "optimize" the code - that's for later agents
- Don't remove features or functionality
- Don't break the application - it must still work!

### Example: Adding FPS to a Pygame Game
If you find a game loop like:
```python
while running:
    handle_events()
    update()
    draw()
```

You should edit it to add FPS tracking:
```python
import time
_frame_count = 0
_fps_start_time = time.time()
_current_fps = 0.0

def get_fps():
    return _current_fps

while running:
    handle_events()
    update()
    draw()
    _frame_count += 1
    elapsed = time.time() - _fps_start_time
    if elapsed >= 1.0:
        _current_fps = _frame_count / elapsed
        _frame_count = 0
        _fps_start_time = time.time()
```

Then your benchmark script can import and call `get_fps()`.

## Output Format
Your benchmark script MUST output JSON to stdout with this format:
```json
{{
    "score": 60.5,
    "passed": true,
    "tests_passed": 5,
    "tests_total": 5,
    "metrics": {{
        "fps": 60.5,
        "memory_mb": 128.5,
        "load_time_ms": 150
    }},
    "message": "All tests passed. FPS: 60.5"
}}
```

Required fields:
- `score`: Primary benchmark score (higher is better)
- `passed`: Boolean - whether all tests passed

Optional but recommended:
- `tests_passed`, `tests_total`: Test statistics
- `metrics`: Additional metrics dict
- `message`: Human-readable summary

## Workflow
1. **Explore the codebase** using list_dir, read_file, grep, glob_search
2. **Understand the application** - What does it do? How is it run? What metrics matter?
3. **Identify what to measure** - FPS for games, throughput for servers, latency for APIs, etc.
4. **MODIFY THE CODEBASE** to expose metrics if they're not already available
5. **Write the benchmark script** at `/app/run_validator.py` that reads these metrics
6. **Test the script** by running it with run_bash or run_python_file
7. **Fix any errors** - Install dependencies, fix bugs, iterate until it works
8. **Verify baseline** - Ensure the script runs successfully and returns valid output

## Important: Your Changes Are The Baseline
After you're done, evolution agents will receive a COPY of this modified codebase.
They will try to improve performance while keeping all your instrumentation intact.
This is why your metric exposure code MUST work correctly - it's how we measure their improvements!

### Dependencies
Use run_bash to install any needed dependencies:
- `pip install ...` for Python packages
- `npm install ...` for Node.js packages
- etc.

### Script Requirements
The benchmark script should:
- Accept `--quiet` flag to output only JSON (no other stdout)
- Handle errors gracefully and return JSON even on failure
- Be runnable from the repository root (`/app`)
- Complete within reasonable time (usually under 60 seconds)

## Available Tools
- `list_dir`: List directory contents
- `read_file`: Read file contents
- `write_file`: Create or overwrite files
- `edit_file`: Make precise edits to files
- `multi_edit`: Multiple edits to one file
- `grep`: Search for patterns in files
- `glob_search`: Find files by pattern
- `run_bash`: Execute shell commands
- `run_python`: Execute Python code
- `run_python_file`: Run a Python file

## Example Benchmark Script Structure

```python
#!/usr/bin/env python3
"""Benchmark and test script for [Application Name]."""

import json
import sys
import time

def run_tests():
    """Run functional tests to verify the application works."""
    tests_passed = 0
    tests_total = 0
    
    # Test 1: Basic functionality
    tests_total += 1
    try:
        # ... test code ...
        tests_passed += 1
    except Exception as e:
        print(f"Test 1 failed: {{e}}", file=sys.stderr)
    
    return tests_passed, tests_total

def measure_performance():
    """Measure the primary performance metric."""
    # ... measurement code ...
    return score, metrics

def main():
    quiet = "--quiet" in sys.argv
    
    try:
        tests_passed, tests_total = run_tests()
        score, metrics = measure_performance()
        
        result = {{
            "score": score,
            "passed": tests_passed == tests_total,
            "tests_passed": tests_passed,
            "tests_total": tests_total,
            "metrics": metrics,
            "message": f"Score: {{score}}, Tests: {{tests_passed}}/{{tests_total}}"
        }}
        
        print(json.dumps(result))
        sys.exit(0 if result["passed"] else 1)
        
    except Exception as e:
        result = {{
            "score": 0,
            "passed": False,
            "error": str(e)
        }}
        print(json.dumps(result))
        sys.exit(1)

if __name__ == "__main__":
    main()
```

Now, explore the codebase at /app and create the benchmark script!
'''


# Tools are imported from worker.tools.get_benchmark_builder_tools()


def create_benchmark_builder_agent(
    config: WorkerConfig | None = None,
    model_config: ModelConfig | None = None,
    observer: AgentObserver | None = None,
):
    """Create a LangGraph benchmark builder agent.
    
    Args:
        config: Worker configuration.
        model_config: Override model configuration.
        observer: Optional observer for logging/tracing.
        
    Returns:
        Compiled LangGraph agent.
    """
    if config is None:
        config = WorkerConfig.from_env()
    
    if model_config is not None:
        config.model = model_config
    
    obs = observer or get_observer()
    tools = get_benchmark_builder_tools()  # From worker.tools
    
    llm = get_llm(config.model)
    llm_with_tools = llm.bind_tools(tools)
    
    system_prompt_logged = False
    
    def agent_node(state: AgentState) -> dict[str, Any]:
        """The main agent reasoning node."""
        nonlocal system_prompt_logged
        
        system_prompt = BENCHMARK_BUILDER_PROMPT
        
        if obs and not system_prompt_logged:
            obs.on_system_prompt(system_prompt)
            system_prompt_logged = True
        
        if obs:
            obs.on_iteration_start(state.iteration + 1)
        
        messages = [SystemMessage(content=system_prompt)] + list(state.messages)
        response = llm_with_tools.invoke(messages)
        
        if obs:
            content = response.content if hasattr(response, "content") else ""
            if isinstance(content, list):
                content = " ".join(
                    part.get("text", "") if isinstance(part, dict) else str(part)
                    for part in content
                )
            
            tool_calls = None
            if hasattr(response, "tool_calls") and response.tool_calls:
                tool_calls = [
                    {"name": tc.get("name", ""), "args": tc.get("args", {}), "id": tc.get("id", "")}
                    for tc in response.tool_calls
                ]
            
            obs.on_agent_response(content, tool_calls)
        
        return {
            "messages": [response],
            "iteration": state.iteration + 1,
        }
    
    base_tool_node = ToolNode(tools)
    
    def observed_tool_node(state: AgentState) -> dict[str, Any]:
        """Tool node with observability."""
        last_message = state.messages[-1] if state.messages else None
        tool_calls_info = []
        
        if last_message and hasattr(last_message, "tool_calls"):
            for tc in last_message.tool_calls:
                tool_name = tc.get("name", "unknown")
                tool_args = tc.get("args", {})
                call_id = tc.get("id", "")
                
                tool_calls_info.append({
                    "name": tool_name,
                    "args": tool_args,
                    "id": call_id,
                })
                
                if obs:
                    obs.on_tool_call(tool_name, tool_args, call_id)
        
        result = base_tool_node.invoke(state)
        
        if obs and "messages" in result:
            for msg in result["messages"]:
                if isinstance(msg, ToolMessage):
                    tool_name = "unknown"
                    call_id = msg.tool_call_id if hasattr(msg, "tool_call_id") else ""
                    
                    for tc_info in tool_calls_info:
                        if tc_info["id"] == call_id:
                            tool_name = tc_info["name"]
                            break
                    
                    content = msg.content if hasattr(msg, "content") else str(msg)
                    error = None
                    if hasattr(msg, "status") and msg.status == "error":
                        error = content
                    
                    obs.on_tool_result(tool_name, content, call_id, error)
        
        return result
    
    def should_continue(state: AgentState) -> str:
        """Determine whether to continue or end."""
        if state.iteration >= state.max_iterations:
            if obs:
                obs.on_error(f"Max iterations ({state.max_iterations}) reached")
            return "end"
        
        messages = state.messages
        if not messages:
            return "end"
        
        last_message = messages[-1]
        
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "tools"
        
        return "end"
    
    workflow = StateGraph(AgentState)
    workflow.add_node("agent", agent_node)
    workflow.add_node("tools", observed_tool_node)
    workflow.set_entry_point("agent")
    workflow.add_conditional_edges(
        "agent",
        should_continue,
        {
            "tools": "tools",
            "end": END,
        },
    )
    workflow.add_edge("tools", "agent")
    
    return workflow.compile()


def run_benchmark_builder(
    workspace: WorkspaceManager,
    max_iterations: int = 30,
    model_config: ModelConfig | None = None,
    observer: AgentObserver | None = None,
) -> tuple[bool, str]:
    """Run the benchmark builder agent to create run_validator.py.
    
    Args:
        workspace: The workspace manager for the target codebase.
        max_iterations: Maximum iterations for the agent.
        model_config: Optional model configuration.
        observer: Optional observer for logging.
        
    Returns:
        Tuple of (success, message). Success is True if benchmark script was created
        and runs successfully.
    """
    # Set up workspace context
    set_workspace(workspace)
    
    config = WorkerConfig.from_env()
    if model_config:
        config.model = model_config
    config.max_iterations = max_iterations
    config.workspace_root = str(workspace.actual_root)
    
    obs = observer or get_observer()
    agent = create_benchmark_builder_agent(config, observer=obs)
    
    if obs:
        obs.on_agent_start(
            agent_id="benchmark-builder",
            task="Create benchmark script",
            config={
                "model": f"{config.model.provider.value}/{config.model.model_name}",
                "max_iterations": max_iterations,
                "workspace": config.workspace_root,
            },
        )
    
    task = """Analyze the codebase at /app and create a benchmark script at /app/run_validator.py.

The script should:
1. Run functional tests to verify the application works
2. Measure performance (FPS, throughput, etc.)
3. Output JSON with score, passed status, and metrics

After creating the script, run it to verify it works correctly. Fix any errors until it runs successfully.
"""
    
    initial_state = AgentState(
        messages=[HumanMessage(content=task)],
        task=task,
        task_type="benchmark_builder",
        workspace_root="/app",  # Virtual root
        agent_id="benchmark-builder",
        max_iterations=max_iterations,
    )
    
    if obs:
        obs.on_user_message(task)
    
    recursion_limit = max(100, max_iterations * 3)
    
    try:
        final_state = agent.invoke(initial_state, config={"recursion_limit": recursion_limit})
        
        # Check if benchmark script was created
        validator_path = workspace.actual_root / "run_validator.py"
        if not validator_path.exists():
            if obs:
                obs.on_agent_end(
                    agent_id="benchmark-builder",
                    success=False,
                    summary="Failed to create run_validator.py",
                )
            return False, "Benchmark script was not created"
        
        # Test the script
        result = subprocess.run(
            [sys.executable, str(validator_path), "--quiet"],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=str(workspace.actual_root),
            env={**os.environ, "WORKSPACE_ROOT": str(workspace.actual_root)},
        )
        
        if result.returncode != 0:
            error_msg = result.stderr or result.stdout
            if obs:
                obs.on_agent_end(
                    agent_id="benchmark-builder",
                    success=False,
                    summary=f"Benchmark script failed: {error_msg[:200]}",
                )
            return False, f"Benchmark script created but failed to run: {error_msg}"
        
        # Verify JSON output
        try:
            output = result.stdout.strip()
            # Handle pygame-style garbage prefix
            json_start = output.find("{")
            if json_start >= 0:
                data = json.loads(output[json_start:])
            else:
                data = json.loads(output)
            
            if "score" not in data:
                return False, "Benchmark output missing 'score' field"
            
            if obs:
                obs.on_agent_end(
                    agent_id="benchmark-builder",
                    success=True,
                    summary=f"Created benchmark script. Score: {data['score']}",
                )
            
            return True, f"Benchmark script created successfully. Score: {data['score']}"
            
        except json.JSONDecodeError as e:
            if obs:
                obs.on_agent_end(
                    agent_id="benchmark-builder",
                    success=False,
                    summary=f"Invalid JSON output: {e}",
                )
            return False, f"Benchmark script output is not valid JSON: {e}"
        
    except subprocess.TimeoutExpired:
        if obs:
            obs.on_agent_end(
                agent_id="benchmark-builder",
                success=False,
                summary="Benchmark script timed out",
            )
        return False, "Benchmark script timed out"
        
    except Exception as e:
        if obs:
            obs.on_error(str(e))
            obs.on_agent_end(
                agent_id="benchmark-builder",
                success=False,
                summary=str(e),
            )
        return False, f"Error running benchmark builder: {e}"
