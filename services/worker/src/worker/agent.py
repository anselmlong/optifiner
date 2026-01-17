"""LangGraph-based evolution agent."""

import re
import time
from typing import Any, Literal

from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, ToolMessage
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode

from worker.config import AgentType, ModelConfig, WorkerConfig, get_llm
from worker.observability import AgentObserver, get_observer
from worker.prompts import get_system_prompt
from worker.state import AgentState
from worker.tools import get_all_tools
from worker.tools.evaluate import _get_evaluator_timeout


# Map of tool names to their argument aliases (alias -> canonical name)
TOOL_ARG_ALIASES = {
    "read_file": {"path": "file_path"},
    "write_file": {"path": "file_path"},
    "edit_file": {"path": "file_path"},
    "multi_edit": {"path": "file_path"},
    "run_python_file": {"path": "file_path"},
}


def normalize_tool_args(tool_name: str, args: dict) -> dict:
    """Normalize tool arguments by converting aliases to canonical names."""
    aliases = TOOL_ARG_ALIASES.get(tool_name, {})
    if not aliases:
        return args
    
    normalized = dict(args)
    for alias, canonical in aliases.items():
        if alias in normalized and canonical not in normalized:
            normalized[canonical] = normalized.pop(alias)
    return normalized


def create_evolution_agent(
    config: WorkerConfig | None = None,
    agent_type: AgentType | None = None,
    model_config: ModelConfig | None = None,
    observer: AgentObserver | None = None,
):
    """Create a LangGraph evolution agent with all tools bound.

    Args:
        config: Worker configuration. If None, loads from environment.
        agent_type: Override agent type from config.
        model_config: Override model configuration.
        observer: Optional observer for logging/tracing.

    Returns:
        Compiled LangGraph agent.
    """
    if config is None:
        config = WorkerConfig.from_env()

    if agent_type is not None:
        config.agent_type = agent_type

    if model_config is not None:
        config.model = model_config

    # Use provided observer or global one
    obs = observer or get_observer()

    # Get tools
    tools = get_all_tools()

    # Create LLM with tools bound
    llm = get_llm(config.model)
    llm_with_tools = llm.bind_tools(tools)

    # Track if we've logged the system prompt
    system_prompt_logged = False

    # Define the agent node
    def agent_node(state: AgentState) -> dict[str, Any]:
        """The main agent reasoning node."""
        nonlocal system_prompt_logged

        # Build system message with context
        system_prompt = get_system_prompt(
            agent_type=config.agent_type,
            task=state.task,
            workspace_root=state.workspace_root,
            generation=state.generation,
            baseline_score=state.baseline_score,
            baseline_data=state.baseline_data,
            benchmark_timeout=state.benchmark_timeout,
        )

        # Log system prompt (only once per agent run)
        if obs and not system_prompt_logged:
            obs.on_system_prompt(system_prompt)
            system_prompt_logged = True

        # Log iteration start
        if obs:
            obs.on_iteration_start(state.iteration + 1)

        # Prepare messages
        messages = [SystemMessage(content=system_prompt)] + list(state.messages)

        # Invoke the model with timing
        start_time = time.time()
        response = llm_with_tools.invoke(messages)
        duration = time.time() - start_time
        
        # Log model call timing
        if obs:
            obs.on_model_call_complete(duration)

        # Log agent response
        if obs:
            content = response.content if hasattr(response, "content") else ""
            if isinstance(content, list):
                # Handle multi-part content (some models return list)
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

        # Update iteration count
        return {
            "messages": [response],
            "iteration": state.iteration + 1,
        }

    # Create a wrapped tool node that logs tool calls and results
    base_tool_node = ToolNode(tools)

    def observed_tool_node(state: AgentState) -> dict[str, Any]:
        """Tool node with observability."""
        # Find the tool calls from the last AI message
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

        # Execute tools
        result = base_tool_node.invoke(state)

        # Log tool results
        if obs and "messages" in result:
            for msg in result["messages"]:
                if isinstance(msg, ToolMessage):
                    # Find matching tool call
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

    # Track retry attempts for when agent tries to give up without improvement
    retry_count = 0
    max_retries = 3  # Maximum times we'll prod the agent to keep trying

    def check_for_improvement(state: AgentState) -> bool:
        """Check if the agent has achieved an improvement by looking at messages."""
        # Look for successful evaluate results in messages
        for msg in reversed(state.messages):
            content = ""
            if hasattr(msg, "content"):
                content = msg.content if isinstance(msg.content, str) else str(msg.content)
            
            # Check for improvement indicators in evaluate output
            if "Score:" in content and state.baseline_score is not None:
                # Try to extract score
                import re
                match = re.search(r"Score:\s*([\d.]+)", content)
                if match:
                    try:
                        score = float(match.group(1))
                        if score > state.baseline_score:
                            return True
                    except ValueError:
                        pass
            
            # Also check for explicit improvement messages
            if "improved" in content.lower() and "score" in content.lower():
                return True
        
        return False

    # Define the routing function
    def should_continue(state: AgentState) -> Literal["tools", "retry", "end"]:
        """Determine whether to continue, retry, or end."""
        nonlocal retry_count
        
        # Check iteration limit
        if state.iteration >= state.max_iterations:
            if obs:
                obs.on_error(f"Max iterations ({state.max_iterations}) reached")
            return "end"

        # Check if the last message has tool calls
        messages = state.messages
        if not messages:
            return "end"

        last_message = messages[-1]

        # Check for tool calls - continue normally
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            retry_count = 0  # Reset retry count when agent is working
            return "tools"

        # Agent is trying to stop (no tool calls)
        # Check if we have achieved an improvement
        if check_for_improvement(state):
            # Great, agent improved and is done
            return "end"
        
        # No improvement - should we retry?
        if retry_count < max_retries:
            retry_count += 1
            if obs:
                obs.on_error(f"No improvement yet - prompting agent to retry (attempt {retry_count}/{max_retries})")
            return "retry"
        
        # Max retries reached, give up
        if obs:
            obs.on_error(f"Agent failed to improve after {max_retries} retry prompts")
        return "end"

    def retry_node(state: AgentState) -> dict[str, Any]:
        """Inject a message telling the agent to keep trying."""
        retry_message = HumanMessage(content="""Your optimization didn't improve the score. Let's try a different approach.

## What to Try Next

**If you tried algorithm changes**, try data structure changes instead:
- Replace lists with dicts/sets for O(1) lookups
- Use NumPy arrays instead of Python lists for numerical data

**If you tried caching**, try vectorization instead:
- Convert Python loops to NumPy operations
- Batch multiple operations into single calls

**If you tried small optimizations**, try architectural changes:
- Add spatial partitioning for collision detection
- Change from object-per-entity to arrays-of-components
- Pre-render complex visuals into cached sprites

**Common issues with failed optimizations**:
- The change was correct but too small to measure (try a bigger bottleneck)
- The change introduced a bug (check the evaluate error message)
- The bottleneck was elsewhere (profile a different part of the code)

Pick a DIFFERENT target and technique. You have iterations remaining.""")
        
        return {
            "messages": [retry_message],
        }

    # Build the graph
    workflow = StateGraph(AgentState)

    # Add nodes
    workflow.add_node("agent", agent_node)
    workflow.add_node("tools", observed_tool_node)
    workflow.add_node("retry", retry_node)

    # Set entry point
    workflow.set_entry_point("agent")

    # Add edges
    workflow.add_conditional_edges(
        "agent",
        should_continue,
        {
            "tools": "tools",
            "retry": "retry",
            "end": END,
        },
    )

    # Tools always return to agent
    workflow.add_edge("tools", "agent")
    
    # Retry goes back to agent
    workflow.add_edge("retry", "agent")

    # Compile the graph
    return workflow.compile()


def run_evolution_agent(
    task: str,
    config: WorkerConfig | None = None,
    agent_id: str = "",
    generation: int = 0,
    baseline_score: float | None = None,
    baseline_data: dict | None = None,
    observer: AgentObserver | None = None,
    benchmark_timeout: int | None = None,
) -> AgentState:
    """Run an evolution agent to completion.

    Args:
        task: The task to accomplish.
        config: Worker configuration.
        agent_id: Unique identifier for this agent.
        generation: Current evolution generation.
        baseline_score: Baseline benchmark score.
        baseline_data: Optional dict with detailed baseline metrics (fps, tests, etc.)
        observer: Optional observer for logging/tracing.
        benchmark_timeout: Timeout in seconds for benchmark execution. If None, uses thread-local value.

    Returns:
        Final agent state after completion.
    """
    if config is None:
        config = WorkerConfig.from_env()

    # Use provided observer or global one
    obs = observer or get_observer()

    # Create the agent with observer
    agent = create_evolution_agent(config, observer=obs)

    # Log agent start
    if obs:
        obs.on_agent_start(
            agent_id=agent_id or "anonymous",
            task=task,
            config={
                "agent_type": config.agent_type.value,
                "model": f"{config.model.provider.value}/{config.model.model_name}",
                "max_iterations": config.max_iterations,
                "workspace": config.workspace_root,
            },
        )

    # Get benchmark timeout (use provided value, or fall back to thread-local)
    actual_timeout = benchmark_timeout if benchmark_timeout is not None else _get_evaluator_timeout()
    
    # Initialize state
    initial_state = AgentState(
        messages=[HumanMessage(content=task)],
        task=task,
        task_type=config.agent_type.value,
        workspace_root=config.workspace_root,
        agent_id=agent_id,
        generation=generation,
        baseline_score=baseline_score,
        baseline_data=baseline_data,
        max_iterations=config.max_iterations,
        benchmark_timeout=actual_timeout,
    )

    # Log initial user message
    if obs:
        obs.on_user_message(task)

    # Run the agent
    # Set recursion_limit high enough to handle max_iterations (each iteration = 2 steps: agent + tools)
    recursion_limit = max(100, config.max_iterations * 3)
    try:
        final_state = agent.invoke(initial_state, config={"recursion_limit": recursion_limit})
        result = AgentState(**final_state)
        
        # Log agent end
        if obs:
            obs.on_agent_end(
                agent_id=agent_id or "anonymous",
                success=result.success,
                summary=result.summary,
            )
        
        return result
    except Exception as e:
        if obs:
            obs.on_error(str(e))
            obs.on_agent_end(agent_id=agent_id or "anonymous", success=False, summary=str(e))
        raise


def extract_score_from_messages(messages) -> float | None:
    """Extract the latest score from agent messages."""
    for msg in reversed(messages):
        content = ""
        if hasattr(msg, "content"):
            content = msg.content if isinstance(msg.content, str) else str(msg.content)

        # Look for "Score: X" pattern
        match = re.search(r"Score:\s*([\d.]+)", content)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                pass

    return None


# Convenience functions for specific agent types


def create_analyzer_agent(config: WorkerConfig | None = None):
    """Create an analyzer agent."""
    return create_evolution_agent(config, agent_type=AgentType.ANALYZER)


def create_refactoring_agent(config: WorkerConfig | None = None):
    """Create a refactoring agent."""
    return create_evolution_agent(config, agent_type=AgentType.REFACTORING)


def create_feature_agent(config: WorkerConfig | None = None):
    """Create a feature agent."""
    return create_evolution_agent(config, agent_type=AgentType.FEATURE)


def create_optimizer_agent(config: WorkerConfig | None = None):
    """Create an optimizer agent."""
    return create_evolution_agent(config, agent_type=AgentType.OPTIMIZER)
