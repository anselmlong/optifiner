"""Base agent implementation using LangGraph."""

from typing import Annotated, Any, Literal, TypedDict

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

from optifiner_worker.agents.types import AgentType, get_system_prompt
from optifiner_worker.config import settings
from optifiner_worker.tools import ALL_TOOLS


class AgentState(TypedDict):
    """State for the agent graph."""

    messages: Annotated[list[BaseMessage], add_messages]
    agent_type: AgentType
    task: str
    iteration: int
    max_iterations: int
    result: str | None


def get_llm(model: str | None = None):
    """Get the LLM instance based on model name."""
    model = model or settings.default_model

    if "claude" in model.lower() or "sonnet" in model.lower():
        return ChatAnthropic(
            model=model,
            api_key=settings.anthropic_api_key,
            max_tokens=8192,
        )
    elif "gemini" in model.lower():
        return ChatGoogleGenerativeAI(
            model=model,
            google_api_key=settings.google_api_key,
        )
    else:
        # Default to Anthropic
        return ChatAnthropic(
            model=settings.default_model,
            api_key=settings.anthropic_api_key,
            max_tokens=8192,
        )


def should_continue(state: AgentState) -> Literal["tools", "end"]:
    """Determine if the agent should continue or end."""
    messages = state["messages"]
    last_message = messages[-1]

    # Check iteration limit
    if state["iteration"] >= state["max_iterations"]:
        return "end"

    # If the last message has tool calls, continue to tools
    if isinstance(last_message, AIMessage) and last_message.tool_calls:
        return "tools"

    return "end"


def create_agent_node(model: str | None = None):
    """Create the agent node function."""
    llm = get_llm(model)
    llm_with_tools = llm.bind_tools(ALL_TOOLS)

    def agent_node(state: AgentState) -> dict[str, Any]:
        """Process the current state and generate a response."""
        messages = state["messages"]

        # Add system prompt if not present
        if not messages or not isinstance(messages[0], SystemMessage):
            system_prompt = get_system_prompt(state["agent_type"])
            messages = [SystemMessage(content=system_prompt)] + list(messages)

        response = llm_with_tools.invoke(messages)

        return {
            "messages": [response],
            "iteration": state["iteration"] + 1,
        }

    return agent_node


def create_agent(
    agent_type: AgentType,
    model: str | None = None,
    max_iterations: int = 20,
) -> StateGraph:
    """Create a LangGraph agent with the specified type.

    Args:
        agent_type: The type of agent to create
        model: LLM model to use (defaults to settings.default_model)
        max_iterations: Maximum number of tool call iterations

    Returns:
        Compiled LangGraph StateGraph
    """
    # Create the graph
    workflow = StateGraph(AgentState)

    # Add nodes
    agent_node = create_agent_node(model)
    tool_node = ToolNode(ALL_TOOLS)

    workflow.add_node("agent", agent_node)
    workflow.add_node("tools", tool_node)

    # Set entry point
    workflow.set_entry_point("agent")

    # Add conditional edges
    workflow.add_conditional_edges(
        "agent",
        should_continue,
        {
            "tools": "tools",
            "end": END,
        },
    )

    # Tools always go back to agent
    workflow.add_edge("tools", "agent")

    return workflow.compile()


async def run_agent(
    agent_type: AgentType,
    task: str,
    model: str | None = None,
    max_iterations: int = 20,
) -> dict[str, Any]:
    """Run an agent with the given task.

    Args:
        agent_type: Type of agent to run
        task: The task description/prompt
        model: LLM model to use
        max_iterations: Maximum iterations

    Returns:
        Final state with results
    """
    agent = create_agent(agent_type, model, max_iterations)

    initial_state: AgentState = {
        "messages": [HumanMessage(content=task)],
        "agent_type": agent_type,
        "task": task,
        "iteration": 0,
        "max_iterations": max_iterations,
        "result": None,
    }

    # Run the agent
    final_state = await agent.ainvoke(initial_state)

    # Extract final result from last AI message
    for message in reversed(final_state["messages"]):
        if isinstance(message, AIMessage) and message.content:
            final_state["result"] = message.content
            break

    return final_state
