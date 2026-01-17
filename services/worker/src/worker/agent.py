"""LangGraph-based evolution agent."""

import re
from typing import Any, Literal

from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode

from worker.config import AgentType, ModelConfig, WorkerConfig, get_llm
from worker.prompts import get_system_prompt
from worker.state import AgentState
from worker.tools import get_all_tools


def create_evolution_agent(
    config: WorkerConfig | None = None,
    agent_type: AgentType | None = None,
    model_config: ModelConfig | None = None,
):
    """Create a LangGraph evolution agent with all tools bound.

    Args:
        config: Worker configuration. If None, loads from environment.
        agent_type: Override agent type from config.
        model_config: Override model configuration.

    Returns:
        Compiled LangGraph agent.
    """
    if config is None:
        config = WorkerConfig.from_env()

    if agent_type is not None:
        config.agent_type = agent_type

    if model_config is not None:
        config.model = model_config

    # Get tools
    tools = get_all_tools()

    # Create LLM with tools bound
    llm = get_llm(config.model)
    llm_with_tools = llm.bind_tools(tools)

    # Define the agent node
    def agent_node(state: AgentState) -> dict[str, Any]:
        """The main agent reasoning node."""
        # Build system message with context
        system_prompt = get_system_prompt(
            agent_type=config.agent_type,
            task=state.task,
            workspace_root=state.workspace_root,
            generation=state.generation,
            baseline_score=state.baseline_score,
        )

        # Prepare messages
        messages = [SystemMessage(content=system_prompt)] + list(state.messages)

        # Invoke the model
        response = llm_with_tools.invoke(messages)

        # Update iteration count
        return {
            "messages": [response],
            "iteration": state.iteration + 1,
        }

    # Define the tool execution node
    tool_node = ToolNode(tools)

    # Define the routing function
    def should_continue(state: AgentState) -> Literal["tools", "end"]:
        """Determine whether to continue or end."""
        # Check iteration limit
        if state.iteration >= state.max_iterations:
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
    workflow.add_node("tools", tool_node)

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
) -> AgentState:
    """Run an evolution agent to completion.

    Args:
        task: The task to accomplish.
        config: Worker configuration.
        agent_id: Unique identifier for this agent.
        generation: Current evolution generation.
        baseline_score: Baseline benchmark score.

    Returns:
        Final agent state after completion.
    """
    if config is None:
        config = WorkerConfig.from_env()

    # Create the agent
    agent = create_evolution_agent(config)

    # Initialize state
    initial_state = AgentState(
        messages=[HumanMessage(content=task)],
        task=task,
        task_type=config.agent_type.value,
        workspace_root=config.workspace_root,
        agent_id=agent_id,
        generation=generation,
        baseline_score=baseline_score,
        max_iterations=config.max_iterations,
    )

    # Run the agent
    final_state = agent.invoke(initial_state)

    return AgentState(**final_state)


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
