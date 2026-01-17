"""Benchmark Builder Agent - creates benchmark scripts for codebases.

This agent analyzes a target codebase and generates a benchmark script
(optifiner_benchmark.py) that:
1. Returns a score (primary metric like FPS, throughput, etc.)
2. Contains tests to ensure the application works correctly
3. Exposes metrics that would otherwise be hidden (FPS, memory usage, etc.)

The benchmark script is ALWAYS at: <workspace_root>/optifiner_benchmark.py

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

from worker.agent import normalize_tool_args

from worker.config import ModelConfig, WorkerConfig, get_llm
from worker.observability import AgentObserver, get_observer
from worker.state import AgentState
from worker.workspace import (
    WorkspaceManager,
    set_workspace,
    get_workspace,
    get_workspace_root,
    BENCHMARK_SCRIPT_NAME,
)
from worker.tools import get_benchmark_builder_tools
from worker.tools.evaluate import run_benchmark_for_validation, set_benchmark_dev_mode, BENCHMARK_TIMEOUT


# System prompt for the benchmark builder agent
BENCHMARK_BUILDER_PROMPT = '''You are an expert Benchmark Builder Agent. Your task is to analyze a codebase and create a comprehensive benchmark script.

## Your Goal
Create a benchmark script at `{workspace_root}/optifiner_benchmark.py` that:
1. **Returns a score** - The primary performance metric (FPS, throughput, latency inverse, etc.)
2. **Contains functional tests** - Verifies the application works correctly (test_gate)
3. **Exposes hidden metrics** - If necessary, MODIFY the codebase files to expose FPS, memory usage, or other metrics

## CRITICAL: Benchmark Script Location
The benchmark script MUST be written to this EXACT path:
    {benchmark_path}

This is a FIXED location. The evaluate tool will ONLY look for the script at this path.

## CRITICAL: Testing the Benchmark
- **DO NOT** run the benchmark script using `python` or `run_python_file` commands
- **DO NOT** run it with `bash` or `run_bash` commands
- **ALWAYS** use the `evaluate` tool to test your benchmark script
- The evaluate tool knows where the benchmark is and handles execution correctly

## IMPORTANT: You CAN and SHOULD Edit Codebase Files
You have FULL permission to edit any file in the codebase. This is critical because:
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

### For Browser/Web Applications:
- **Benchmarks must be Python scripts** - even for web apps, write the benchmark in Python
- **Use Playwright with Python** for testing browser-based apps (`pip install playwright && playwright install chromium` has already been run) (FORBIDDEN TO USE PLAYWRIGHT WITH NPM/NPX, only pip with python)
- **Headless mode**: Run browsers headlessly for faster benchmarking
- **Page load timing**: Measure DOMContentLoaded, load events, LCP, FCP
- **Network optimization**: Analyze and reduce request waterfalls, bundle sizes
- **Render performance**: Use Performance API to measure paint times, long tasks
- **Example setup**:
```python
from playwright.sync_api import sync_playwright

port = ... # [host static files on random port]

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.goto(f"http://localhost:{{port}}")
    # Start application (for games, press start, etc.)
    # Measure performance, interact with UI, etc.
```
CRITICAL: USING PYTHON AND NOT NODE/NPM WHATERVER. USE PYTHON FOR WEB STUFF, EVEN IF THE CODE IS IN JS
If you run npm, or check for puppeteer instead of playwright, you will be fired.

## REQUIRED Output Format
Your benchmark script MUST output JSON to stdout with this EXACT format:

```json
{{
    "score": 60.5,
    "metric_name": "FPS",
    "test_gate": true,
    "metrics": {{
        "memory_mb": 128.5,
        "load_time_ms": 150
    }},
    "message": "All tests passed. FPS: 60.5"
}}
```

### Required Fields (ALL THREE ARE MANDATORY):
- `score`: Primary benchmark score as a NUMBER (higher is better). Must NOT be null for success.
- `metric_name`: STRING naming what the score measures (e.g., "FPS", "throughput", "benchmark_score")
- `test_gate`: BOOLEAN - true if all tests pass, false otherwise. Must be true for success.

### Optional Fields:
- `metrics`: Object with additional metrics
- `message`: Human-readable summary

### SUCCESS CRITERIA:
The benchmark is considered SUCCESSFUL when BOTH conditions are met:
1. `test_gate` is `true`
2. `score` is NOT null

Once your benchmark passes both conditions, your job is complete and the code becomes the base for evolution agents.

## AUTOMATIC STOPPING:
When you call `evaluate` and it returns `[BENCHMARK PASSED]`, you will be automatically stopped.
You do NOT need to do anything else after seeing `[BENCHMARK PASSED]` - the system handles completion.
This means: once the evaluate tool shows your benchmark passes, your work is done!

## Workflow
1. **Explore the codebase** using list_dir, read_file, grep, glob_search
2. **Understand the application** - What does it do? How is it run? What metrics matter?
3. **Identify what to measure** - FPS for games, throughput for servers, latency for APIs, etc.
4. **MODIFY THE CODEBASE** to expose metrics if they're not already available
5. **Write the benchmark script** at `{benchmark_path}`
6. **Test with evaluate tool** - Use the `evaluate` tool to test your script (NOT python/bash!)
7. **Fix any errors** - Install dependencies, fix bugs, iterate until it works
8. **Verify success** - Ensure evaluate shows: test_gate=PASSED and score is not null

## Important: Your Changes Are The Baseline
After you're done, evolution agents will receive a COPY of this modified codebase.
They will try to improve performance while keeping all your instrumentation intact.
This is why your metric exposure code MUST work correctly - it's how we measure their improvements!

### Dependencies
Use run_bash to install any needed dependencies:
- `pip install ...` for Python packages
- etc.

### Script Requirements
The benchmark script should:
- Accept `--quiet` flag to output only JSON (no other stdout)
- Handle errors gracefully and return JSON even on failure
- Be runnable from the repository root

### ⚠️ CRITICAL: {timeout}-SECOND TIMEOUT ⚠️
**The benchmark script MUST exit (complete execution) within {timeout} seconds.**

If the Python script does not exit within {timeout} seconds:
- The evaluation will be FORCEFULLY TERMINATED
- The benchmark will be marked as FAILED with a timeout error
- Any partial output will be shown, but the benchmark does NOT pass

This means your script must:
- Measure performance quickly (a few seconds of measurement is usually enough)
- Call `sys.exit()` or simply return from `main()` after outputting JSON
- NOT have infinite loops or blocking operations that prevent exit
- NOT wait for user input or external events indefinitely

## Available Tools
- `list_dir`: List directory contents
- `read_file`: Read file contents
- `write_file`: Create or overwrite files
- `edit_file`: Make precise edits to files
- `multi_edit`: Multiple edits to one file
- `grep`: Search for patterns in files
- `glob_search`: Find files by pattern
- `run_bash`: Execute shell commands (for pip install, etc. - NOT for running benchmark!)
- `run_python`: Execute Python code (for testing pieces - NOT for running benchmark!)
- `run_python_file`: Run a Python file (NOT for running benchmark!)
- `evaluate`: Run the benchmark and get results (ALWAYS use this to test your benchmark!)

## Example Benchmark Script Structure

```python
#!/usr/bin/env python3
"""Benchmark script for [Application Name]."""

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
    return score, {{"additional_metric": value}}

def main():
    quiet = "--quiet" in sys.argv
    
    try:
        tests_passed, tests_total = run_tests()
        score, extra_metrics = measure_performance()
        
        result = {{
            "score": score,
            "metric_name": "FPS",  # or "throughput", "benchmark_score", etc.
            "test_gate": tests_passed == tests_total,
            "metrics": {{
                "tests_passed": tests_passed,
                "tests_total": tests_total,
                **extra_metrics
            }},
            "message": f"Score: {{score}}, Tests: {{tests_passed}}/{{tests_total}}"
        }}
        
        print(json.dumps(result))
        sys.exit(0 if result["test_gate"] else 1)
        
    except Exception as e:
        result = {{
            "score": None,
            "metric_name": "error",
            "test_gate": False,
            "message": str(e)
        }}
        print(json.dumps(result))
        sys.exit(1)

if __name__ == "__main__":
    main()
```

Now, explore the codebase and create the benchmark script at {benchmark_path}!
Remember: Use `evaluate` tool to test it, NOT python or bash commands!
'''


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
    
    # Get tools including evaluate for testing the benchmark
    tools = get_benchmark_builder_tools()
    
    # Also add evaluate tool so agent can test the benchmark
    from worker.tools.evaluate import evaluate
    tools = tools + [evaluate]
    
    llm = get_llm(config.model)
    llm_with_tools = llm.bind_tools(tools)
    
    system_prompt_logged = False
    
    def agent_node(state: AgentState) -> dict[str, Any]:
        """The main agent reasoning node."""
        nonlocal system_prompt_logged
        
        # Get workspace info for the prompt
        workspace_root = str(get_workspace_root())
        benchmark_path = f"{workspace_root}/{BENCHMARK_SCRIPT_NAME}"
        
        system_prompt = BENCHMARK_BUILDER_PROMPT.format(
            workspace_root=workspace_root,
            benchmark_path=benchmark_path,
            timeout=BENCHMARK_TIMEOUT,
        )
        
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
                
                # Normalize tool arguments (e.g., path -> file_path)
                tc["args"] = normalize_tool_args(tool_name, tool_args)
                
                tool_calls_info.append({
                    "name": tool_name,
                    "args": tc["args"],
                    "id": call_id,
                })
                
                if obs:
                    obs.on_tool_call(tool_name, tc["args"], call_id)
        
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
        """Determine whether to continue or end after agent response."""
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
        
        # Don't allow ending without a VALID benchmark
        # Check if benchmark exists AND passes validation
        workspace_root = get_workspace_root()
        benchmark_path = workspace_root / BENCHMARK_SCRIPT_NAME
        
        if not benchmark_path.exists():
            # Benchmark file not created yet - force agent to continue
            return "remind"
        
        # Benchmark exists - check if it's valid
        result = run_benchmark_for_validation(workspace_root)
        if not result.is_valid:
            # Benchmark exists but doesn't pass - force agent to fix it
            return "remind"
        
        return "end"
    
    def should_continue_after_tools(state: AgentState) -> str:
        """Determine whether to continue or end after tools run.
        
        Checks if evaluate() returned a passing benchmark - if so, stop early.
        """
        messages = state.messages
        if not messages:
            return "agent"
        
        # Check the most recent tool messages for benchmark passed
        for msg in reversed(messages):
            # Stop checking once we hit an AI message (tool results come after AI message)
            if isinstance(msg, AIMessage):
                break
            if isinstance(msg, ToolMessage):
                content = msg.content if hasattr(msg, "content") else ""
                if "[BENCHMARK PASSED]" in content:
                    if obs:
                        obs.on_agent_end(
                            agent_id="benchmark-builder",
                            success=True,
                            summary="Benchmark passed - stopping early",
                        )
                    return "end"
        
        return "agent"
    
    def remind_node(state: AgentState) -> dict[str, Any]:
        """Remind the agent to fix the benchmark script."""
        workspace_root = get_workspace_root()
        benchmark_path = workspace_root / BENCHMARK_SCRIPT_NAME
        
        # Check what's wrong with the benchmark
        if benchmark_path.exists():
            result = run_benchmark_for_validation(workspace_root)
            if result.error:
                reminder_text = (
                    f"BENCHMARK ERROR - Please fix and retry!\n\n"
                    f"The benchmark script at {benchmark_path} failed with error:\n"
                    f"{result.error}\n\n"
                    f"Please fix the benchmark script and use the `evaluate` tool to test it again."
                )
            elif result.score is None:
                reminder_text = (
                    f"BENCHMARK INVALID - Score is null!\n\n"
                    f"The benchmark script at {benchmark_path} returned a null score.\n"
                    f"Please fix the script to return a valid numeric score and use `evaluate` to test again."
                )
            elif result.score == 0:
                reminder_text = (
                    f"BENCHMARK INVALID - Score is 0!\n\n"
                    f"The benchmark script at {benchmark_path} returned a score of 0.\n"
                    f"A score of 0 indicates the benchmark is not measuring correctly.\n"
                    f"Please fix the FPS/performance measurement logic and use `evaluate` to test again.\n\n"
                    f"Common issues:\n"
                    f"- FPS calculation dividing by zero or wrong time interval\n"
                    f"- Frames not being counted correctly\n"
                    f"- Measurement running for 0 seconds\n"
                    f"- Game loop not actually running"
                )
            elif not result.test_gate:
                reminder_text = (
                    f"BENCHMARK FAILED - Tests did not pass!\n\n"
                    f"The benchmark script at {benchmark_path} has test_gate=false.\n"
                    f"Please fix the tests and use `evaluate` to test again."
                )
            else:
                reminder_text = (
                    f"BENCHMARK INCOMPLETE - Please fix and retry!\n\n"
                    f"The benchmark at {benchmark_path} is not valid yet.\n"
                    f"Please use the `evaluate` tool to check what's wrong and fix it."
                )
        else:
            reminder_text = (
                f"IMPORTANT: You have not created the benchmark script yet!\n\n"
                f"You MUST create the benchmark script at: {benchmark_path}\n\n"
                f"Use the write_file tool to create it NOW. The script must output JSON with:\n"
                f"- score: numeric value (the metric you're measuring)\n"
                f"- metric_name: string (e.g., 'FPS', 'throughput')\n"
                f"- test_gate: boolean (true if tests pass)\n\n"
                f"Do not stop until you have created and tested the benchmark script with the evaluate tool!"
            )
        
        reminder = HumanMessage(content=reminder_text)
        
        if obs:
            obs.on_user_message(reminder.content)
        
        return {"messages": [reminder]}
    
    workflow = StateGraph(AgentState)
    workflow.add_node("agent", agent_node)
    workflow.add_node("tools", observed_tool_node)
    workflow.add_node("remind", remind_node)
    workflow.set_entry_point("agent")
    workflow.add_conditional_edges(
        "agent",
        should_continue,
        {
            "tools": "tools",
            "remind": "remind",
            "end": END,
        },
    )
    workflow.add_conditional_edges(
        "tools",
        should_continue_after_tools,
        {
            "agent": "agent",
            "end": END,
        },
    )
    # After remind, always go back to agent
    workflow.add_edge("remind", "agent")
    
    return workflow.compile()


def run_benchmark_builder(
    workspace: WorkspaceManager,
    max_iterations: int = 30,
    model_config: ModelConfig | None = None,
    observer: AgentObserver | None = None,
) -> tuple[bool, str]:
    """Run the benchmark builder agent to create optifiner_benchmark.py.
    
    Args:
        workspace: The workspace manager for the target codebase.
        max_iterations: Maximum iterations for the agent.
        model_config: Optional model configuration.
        observer: Optional observer for logging.
        
    Returns:
        Tuple of (success, message). Success is True if benchmark script was created
        and passes validation (test_gate=True, score not null).
    """
    # Set benchmark dev mode - timeouts tell agent to retry (they can fix the benchmark)
    set_benchmark_dev_mode(True)
    
    # Set up workspace context using context var and thread-local
    # NOTE: We do NOT set os.environ["WORKSPACE_ROOT"] here to avoid race conditions
    # when multiple agents run in parallel. The workspace module handles isolation.
    set_workspace(workspace)
    
    config = WorkerConfig.from_env()
    if model_config:
        config.model = model_config
    config.max_iterations = max_iterations
    config.workspace_root = str(workspace.workspace_root)
    
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
                "benchmark_path": str(workspace.benchmark_path),
            },
        )
    
    task = f"""Analyze the codebase at {workspace.workspace_root} and create a benchmark script at {workspace.benchmark_path}.

The script MUST output JSON with these REQUIRED fields:
- score: The primary metric value (number, not null)
- metric_name: Name of what score measures (e.g., "FPS", "throughput")
- test_gate: Boolean, true if all tests pass

SUCCESS = test_gate is true AND score is not null.

IMPORTANT:
- Write the benchmark to: {workspace.benchmark_path}
- Test it using the `evaluate` tool, NOT python/bash commands!
- Keep iterating until evaluate shows: test_gate=PASSED and score is a number
"""
    
    initial_state = AgentState(
        messages=[HumanMessage(content=task)],
        task=task,
        task_type="benchmark_builder",
        workspace_root=str(workspace.workspace_root),
        agent_id="benchmark-builder",
        max_iterations=max_iterations,
    )
    
    if obs:
        obs.on_user_message(task)
    
    recursion_limit = max(100, max_iterations * 3)
    
    try:
        final_state = agent.invoke(initial_state, config={"recursion_limit": recursion_limit})
        
        # Verify the benchmark was created and passes
        result = run_benchmark_for_validation(workspace.workspace_root)
        
        if result.error:
            if obs:
                obs.on_agent_end(
                    agent_id="benchmark-builder",
                    success=False,
                    summary=f"Benchmark error: {result.error}",
                )
            return False, f"Benchmark failed: {result.error}"
        
        if not result.is_valid:
            reasons = []
            if not result.test_gate:
                reasons.append("test_gate is false")
            if result.score is None:
                reasons.append("score is null")
            elif result.score == 0:
                reasons.append("score is 0 (invalid benchmark)")
            
            if obs:
                obs.on_agent_end(
                    agent_id="benchmark-builder",
                    success=False,
                    summary=f"Benchmark incomplete: {', '.join(reasons)}",
                )
            return False, f"Benchmark did not pass: {', '.join(reasons)}"
        
        # Success!
        if obs:
            obs.on_agent_end(
                agent_id="benchmark-builder",
                success=True,
                summary=f"Benchmark created. {result.metric_name}: {result.score}",
            )
        
        return True, f"Benchmark script created successfully. {result.metric_name}: {result.score}"
        
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
