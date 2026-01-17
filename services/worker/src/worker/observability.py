"""Observability module for agent execution.

Provides detailed logging and tracing of:
- System prompts sent to LLMs
- Agent reasoning and responses
- Tool calls and their results
- Iteration progress
"""

import json
import sys
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text
from rich.markdown import Markdown
from rich.tree import Tree


class EventType(str, Enum):
    """Types of observable events."""
    
    SYSTEM_PROMPT = "system_prompt"
    USER_MESSAGE = "user_message"
    AGENT_RESPONSE = "agent_response"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    ITERATION_START = "iteration_start"
    ITERATION_END = "iteration_end"
    AGENT_START = "agent_start"
    AGENT_END = "agent_end"
    ERROR = "error"


@dataclass
class ObservabilityEvent:
    """A single observable event."""
    
    event_type: EventType
    timestamp: datetime = field(default_factory=datetime.now)
    iteration: int = 0
    data: dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return {
            "event_type": self.event_type.value,
            "timestamp": self.timestamp.isoformat(),
            "iteration": self.iteration,
            "data": self.data,
        }


class AgentObserver:
    """Observer for agent execution with rich console output.
    
    Provides detailed visibility into agent reasoning, prompts, and tool usage.
    """
    
    def __init__(
        self,
        verbosity: int = 1,
        console: Console | None = None,
        log_file: str | None = None,
    ):
        """Initialize the observer.
        
        Args:
            verbosity: Level of detail (0=quiet, 1=normal, 2=verbose, 3=debug)
            console: Rich console for output. Creates one if not provided.
            log_file: Optional file path to write events as JSON lines.
        """
        self.verbosity = verbosity
        self.console = console or Console()
        self.log_file = log_file
        self.events: list[ObservabilityEvent] = []
        self.current_iteration = 0
        self._log_handle = None
        
        if self.log_file:
            self._log_handle = open(self.log_file, "w")
    
    def close(self):
        """Close any open resources."""
        if self._log_handle:
            self._log_handle.close()
            self._log_handle = None
    
    def _record_event(self, event: ObservabilityEvent):
        """Record an event to memory and optionally to file."""
        self.events.append(event)
        if self._log_handle:
            self._log_handle.write(json.dumps(event.to_dict()) + "\n")
            self._log_handle.flush()
    
    def _truncate(self, text: str, max_len: int = 500) -> str:
        """Truncate text with ellipsis if too long."""
        if len(text) <= max_len:
            return text
        return text[:max_len] + "..."
    
    def on_agent_start(self, agent_id: str, task: str, config: dict[str, Any] | None = None):
        """Called when an agent starts execution."""
        event = ObservabilityEvent(
            event_type=EventType.AGENT_START,
            data={"agent_id": agent_id, "task": task, "config": config or {}},
        )
        self._record_event(event)
        
        if self.verbosity >= 1:
            self.console.print()
            self.console.print(Panel(
                f"[bold cyan]Agent Starting[/bold cyan]\n\n"
                f"[dim]ID:[/dim] {agent_id}\n"
                f"[dim]Task:[/dim] {self._truncate(task, 200)}",
                title="🚀 Agent Execution",
                border_style="cyan",
            ))
    
    def on_agent_end(self, agent_id: str, success: bool, summary: str = ""):
        """Called when an agent finishes execution."""
        event = ObservabilityEvent(
            event_type=EventType.AGENT_END,
            iteration=self.current_iteration,
            data={"agent_id": agent_id, "success": success, "summary": summary},
        )
        self._record_event(event)
        
        if self.verbosity >= 1:
            status = "[green]✓ Success[/green]" if success else "[red]✗ Failed[/red]"
            self.console.print()
            self.console.print(Panel(
                f"{status}\n\n"
                f"[dim]Iterations:[/dim] {self.current_iteration}\n"
                f"[dim]Summary:[/dim] {summary or 'No summary'}",
                title="🏁 Agent Complete",
                border_style="green" if success else "red",
            ))
    
    def on_system_prompt(self, prompt: str):
        """Called when a system prompt is sent to the LLM."""
        event = ObservabilityEvent(
            event_type=EventType.SYSTEM_PROMPT,
            iteration=self.current_iteration,
            data={"prompt": prompt},
        )
        self._record_event(event)
        
        if self.verbosity >= 3:
            self.console.print()
            self.console.print(Panel(
                Syntax(prompt, "markdown", theme="monokai", word_wrap=True),
                title="📜 System Prompt",
                border_style="blue",
                subtitle=f"[dim]{len(prompt)} chars[/dim]",
            ))
        elif self.verbosity >= 2:
            # Show truncated version
            self.console.print()
            self.console.print(f"[blue]📜 System Prompt[/blue] [dim]({len(prompt)} chars)[/dim]")
            preview = self._truncate(prompt, 300)
            self.console.print(f"[dim]{preview}[/dim]")
    
    def on_user_message(self, message: str):
        """Called when a user message is sent."""
        event = ObservabilityEvent(
            event_type=EventType.USER_MESSAGE,
            iteration=self.current_iteration,
            data={"message": message},
        )
        self._record_event(event)
        
        if self.verbosity >= 2:
            self.console.print()
            self.console.print(Panel(
                self._truncate(message, 500),
                title="👤 User Message",
                border_style="green",
            ))
    
    def on_iteration_start(self, iteration: int):
        """Called at the start of each agent iteration."""
        self.current_iteration = iteration
        event = ObservabilityEvent(
            event_type=EventType.ITERATION_START,
            iteration=iteration,
        )
        self._record_event(event)
        
        if self.verbosity >= 1:
            self.console.print()
            self.console.print(f"[bold yellow]━━━ Iteration {iteration} ━━━[/bold yellow]")
    
    def on_model_call_complete(self, duration_seconds: float):
        """Called when a model API call completes."""
        if self.verbosity >= 1:
            self.console.print(f"[dim]  ⏱ Model call: {duration_seconds:.2f}s[/dim]")
    
    def on_iteration_end(self, iteration: int):
        """Called at the end of each agent iteration."""
        event = ObservabilityEvent(
            event_type=EventType.ITERATION_END,
            iteration=iteration,
        )
        self._record_event(event)
    
    def on_agent_response(self, content: str, tool_calls: list[dict] | None = None):
        """Called when the agent produces a response.
        
        Args:
            content: The text content of the response (reasoning).
            tool_calls: List of tool calls if any.
        """
        event = ObservabilityEvent(
            event_type=EventType.AGENT_RESPONSE,
            iteration=self.current_iteration,
            data={"content": content, "tool_calls": tool_calls},
        )
        self._record_event(event)
        
        if self.verbosity >= 2:
            self.console.print()
            
            # Show reasoning if present
            if content:
                self.console.print(Panel(
                    Markdown(self._truncate(content, 1000) if self.verbosity < 3 else content),
                    title="🧠 Agent Reasoning",
                    border_style="magenta",
                ))
            
            # Show tool calls summary
            if tool_calls:
                tools_text = ", ".join(tc.get("name", "unknown") for tc in tool_calls)
                self.console.print(f"[cyan]🔧 Tool calls:[/cyan] {tools_text}")
        
        elif self.verbosity >= 1 and content:
            # Minimal output - just show there was reasoning
            preview = content[:100].replace("\n", " ")
            if len(content) > 100:
                preview += "..."
            self.console.print(f"[magenta]🧠[/magenta] [dim]{preview}[/dim]")
    
    def on_tool_call(self, tool_name: str, tool_input: dict[str, Any], call_id: str = ""):
        """Called when a tool is being invoked."""
        event = ObservabilityEvent(
            event_type=EventType.TOOL_CALL,
            iteration=self.current_iteration,
            data={"tool_name": tool_name, "tool_input": tool_input, "call_id": call_id},
        )
        self._record_event(event)
        
        if self.verbosity >= 2:
            self.console.print()
            
            # Format tool input nicely
            input_str = json.dumps(tool_input, indent=2, default=str)
            if self.verbosity < 3:
                input_str = self._truncate(input_str, 500)
            
            self.console.print(Panel(
                Syntax(input_str, "json", theme="monokai", word_wrap=True),
                title=f"🔧 Tool: [bold]{tool_name}[/bold]",
                border_style="cyan",
            ))
        elif self.verbosity >= 1:
            # Compact tool call display
            args_preview = self._format_tool_args_compact(tool_name, tool_input)
            self.console.print(f"[cyan]🔧 {tool_name}[/cyan]({args_preview})")
    
    def _format_tool_args_compact(self, tool_name: str, tool_input: dict) -> str:
        """Format tool arguments compactly for display."""
        if not tool_input:
            return ""
        
        # Special formatting for common tools
        if tool_name == "read_file" and "path" in tool_input:
            return f"[dim]{tool_input['path']}[/dim]"
        elif tool_name in ("write_file", "edit_file") and "path" in tool_input:
            return f"[dim]{tool_input['path']}[/dim]"
        elif tool_name == "grep" and "pattern" in tool_input:
            path = tool_input.get("path", ".")
            return f"[dim]{tool_input['pattern']}[/dim] in {path}"
        elif tool_name == "run_bash" and "command" in tool_input:
            cmd = tool_input["command"][:50]
            if len(tool_input["command"]) > 50:
                cmd += "..."
            return f"[dim]{cmd}[/dim]"
        elif tool_name == "list_dir" and "path" in tool_input:
            return f"[dim]{tool_input['path']}[/dim]"
        elif tool_name == "evaluate":
            return ""
        
        # Generic compact format
        parts = []
        for k, v in list(tool_input.items())[:2]:
            v_str = str(v)[:30]
            if len(str(v)) > 30:
                v_str += "..."
            parts.append(f"{k}={v_str}")
        return ", ".join(parts)
    
    def on_tool_result(self, tool_name: str, result: Any, call_id: str = "", error: str | None = None):
        """Called when a tool returns a result."""
        # Serialize result for storage
        result_str = str(result) if not isinstance(result, str) else result
        
        event = ObservabilityEvent(
            event_type=EventType.TOOL_RESULT,
            iteration=self.current_iteration,
            data={
                "tool_name": tool_name,
                "result": result_str[:5000],  # Limit stored result size
                "call_id": call_id,
                "error": error,
            },
        )
        self._record_event(event)
        
        if error:
            if self.verbosity >= 1:
                self.console.print(f"[red]  ✗ Error: {error[:200]}[/red]")
        elif self.verbosity >= 2:
            result_preview = self._truncate(result_str, 500 if self.verbosity < 3 else 2000)
            self.console.print(Panel(
                result_preview,
                title=f"📤 Result: {tool_name}",
                border_style="dim",
            ))
        elif self.verbosity >= 1:
            # Show compact result
            result_preview = result_str[:100].replace("\n", " ")
            if len(result_str) > 100:
                result_preview += "..."
            self.console.print(f"[dim]  → {result_preview}[/dim]")
    
    def on_error(self, error: str, context: dict[str, Any] | None = None):
        """Called when an error occurs."""
        event = ObservabilityEvent(
            event_type=EventType.ERROR,
            iteration=self.current_iteration,
            data={"error": error, "context": context or {}},
        )
        self._record_event(event)
        
        if self.verbosity >= 1:
            self.console.print()
            self.console.print(Panel(
                f"[red]{error}[/red]",
                title="❌ Error",
                border_style="red",
            ))
    
    def get_summary(self) -> dict:
        """Get a summary of all observed events."""
        tool_calls = [e for e in self.events if e.event_type == EventType.TOOL_CALL]
        tool_counts = {}
        for tc in tool_calls:
            name = tc.data.get("tool_name", "unknown")
            tool_counts[name] = tool_counts.get(name, 0) + 1
        
        errors = [e for e in self.events if e.event_type == EventType.ERROR]
        
        return {
            "total_events": len(self.events),
            "iterations": self.current_iteration,
            "tool_calls": len(tool_calls),
            "tool_breakdown": tool_counts,
            "errors": len(errors),
        }
    
    def print_summary(self):
        """Print a summary of the agent execution."""
        summary = self.get_summary()
        
        self.console.print()
        table = Table(title="Execution Summary", show_header=False, box=None)
        table.add_column("Metric", style="dim")
        table.add_column("Value", style="cyan")
        
        table.add_row("Total Events", str(summary["total_events"]))
        table.add_row("Iterations", str(summary["iterations"]))
        table.add_row("Tool Calls", str(summary["tool_calls"]))
        table.add_row("Errors", str(summary["errors"]))
        
        self.console.print(table)
        
        if summary["tool_breakdown"]:
            self.console.print()
            self.console.print("[bold]Tool Usage:[/bold]")
            for tool, count in sorted(summary["tool_breakdown"].items(), key=lambda x: -x[1]):
                self.console.print(f"  [cyan]{tool}[/cyan]: {count}")


# Global observer instance (can be set by CLI or tests)
_global_observer: AgentObserver | None = None


def get_observer() -> AgentObserver | None:
    """Get the global observer instance."""
    return _global_observer


def set_observer(observer: AgentObserver | None):
    """Set the global observer instance."""
    global _global_observer
    _global_observer = observer


def create_observer(
    verbosity: int = 1,
    console: Console | None = None,
    log_file: str | None = None,
) -> AgentObserver:
    """Create and set a global observer.
    
    Args:
        verbosity: Level of detail (0=quiet, 1=normal, 2=verbose, 3=debug)
        console: Rich console for output.
        log_file: Optional file to write events.
    
    Returns:
        The created observer.
    """
    observer = AgentObserver(verbosity=verbosity, console=console, log_file=log_file)
    set_observer(observer)
    return observer
