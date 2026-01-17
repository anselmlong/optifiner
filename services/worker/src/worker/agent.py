"""LangGraph-based evolution agent."""

import re
from typing import Any, Literal

from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, ToolMessage
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode

from worker.config import AgentType, ModelConfig, WorkerConfig, get_llm
from worker.prompts import get_system_prompt
from worker.state import AgentState
from worker.tools import get_all_tools
from worker.callbacks import get_observer


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
        observer = get_observer()
        
        # Log iteration start
        observer.log_iteration_start(
            state.agent_id, 
            state.iteration + 1, 
            state.max_iterations
        )
        
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
        
        # Log the prompt
        observer.log_prompt(
            state.agent_id,
            state.iteration + 1,
            system_prompt,
            list(state.messages)[-5:],  # Last 5 messages for context
        )

        # Invoke the model
        response = llm_with_tools.invoke(messages)
        
        # Log the reasoning response
        observer.log_reasoning(state.agent_id, state.iteration + 1, response)

        # Update iteration count
        return {
            "messages": [response],
            "iteration": state.iteration + 1,
        }

    # Define the tool execution node with observability
    base_tool_node = ToolNode(tools)
    
    def tool_node_with_logging(state: AgentState) -> dict[str, Any]:
        """Tool node wrapper that logs tool execution."""
        observer = get_observer()
        
        # Get the last message to see what tools are being called
        if state.messages:
            last_msg = state.messages[-1]
            if hasattr(last_msg, 'tool_calls') and last_msg.tool_calls:
                for tc in last_msg.tool_calls:
                    tool_name = tc.get('name', 'unknown') if isinstance(tc, dict) else getattr(tc, 'name', 'unknown')
                    args = tc.get('args', {}) if isinstance(tc, dict) else getattr(tc, 'args', {})
                    observer.log_tool_call(state.agent_id, state.iteration, tool_name, args)
        
        # Execute tools
        result = base_tool_node.invoke(state)
        
        # Log tool results
        if 'messages' in result:
            for msg in result['messages']:
                if isinstance(msg, ToolMessage):
                    tool_name = getattr(msg, 'name', 'unknown')
                    content = msg.content if hasattr(msg, 'content') else str(msg)
                    observer.log_tool_result(state.agent_id, state.iteration, tool_name, content)
        
        return result
    
    tool_node = tool_node_with_logging

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
    import time
    
    if config is None:
        config = WorkerConfig.from_env()

    observer = get_observer()
    start_time = time.time()
    
    # Log agent start
    observer.log_agent_start(
        agent_id=agent_id,
        agent_type=config.agent_type.value,
        task_preview=task,
    )

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
    try:
        final_state = agent.invoke(initial_state)
        result_state = AgentState(**final_state)
        
        # Extract final score
        final_score = extract_score_from_messages(result_state.messages)
        
        # Log completion
        observer.log_agent_complete(
            agent_id=agent_id,
            success=final_score is not None and (baseline_score is None or final_score > baseline_score),
            score=final_score,
            duration=time.time() - start_time,
        )
        
        return result_state
        
    except Exception as e:
        observer.log_error(agent_id, 0, str(e))
        observer.log_agent_complete(
            agent_id=agent_id,
            success=False,
            score=None,
            duration=time.time() - start_time,
        )
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
