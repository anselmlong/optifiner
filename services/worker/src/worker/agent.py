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
                
                tool_calls_info.append({
                    "name": tool_name,
                    "args": tool_args,
                    "id": call_id,
                })
                
                if obs:
                    obs.on_tool_call(tool_name, tool_args, call_id)

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

    # Define the routing function
    def should_continue(state: AgentState) -> Literal["tools", "end"]:
        """Determine whether to continue or end."""
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

        # Check for tool calls
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "tools"

        return "end"

    # Build the graph
    workflow = StateGraph(AgentState)

    # Add nodes
    workflow.add_node("agent", agent_node)
    workflow.add_node("tools", observed_tool_node)

    # Set entry point
    workflow.set_entry_point("agent")

    # Add edges
    workflow.add_conditional_edges(
        "agent",
        should_continue,
        {
            "tools": "tools",
            "end": END,
        },
    )

    # Tools always return to agent
    workflow.add_edge("tools", "agent")

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
