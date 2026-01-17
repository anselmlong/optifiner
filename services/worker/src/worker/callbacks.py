"""Callbacks for observability into agent execution."""

import time
from dataclasses import dataclass, field
from typing import Any, Callable
from datetime import datetime

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.text import Text
from rich.markdown import Markdown
from rich.table import Table


@dataclass
class AgentEvent:
    """A single event from agent execution."""
    timestamp: datetime
    event_type: str  # "prompt", "reasoning", "tool_call", "tool_result", "error"
    agent_id: str
    iteration: int
    content: Any
    metadata: dict = field(default_factory=dict)


@dataclass  
class AgentObserver:
    """Observer that collects and displays agent events."""
    
    console: Console = field(default_factory=Console)
    events: list[AgentEvent] = field(default_factory=list)
    verbose: int = 1  # 0=quiet, 1=normal, 2=verbose, 3=debug
    show_prompts: bool = False
    show_reasoning: bool = True
    show_tool_calls: bool = True
    show_tool_results: bool = True
    current_agent_id: str = ""
    
    def log_prompt(self, agent_id: str, iteration: int, system_prompt: str, messages: list) -> None:
        """Log the prompt being sent to the LLM."""
        event = AgentEvent(
            timestamp=datetime.now(),
            event_type="prompt",
            agent_id=agent_id,
            iteration=iteration,
            content={"system": system_prompt, "messages": messages},
        )
        self.events.append(event)
        
        if self.verbose >= 3 or self.show_prompts:
            self.console.print()
            self.console.print(Panel(
                Text(system_prompt[:1500] + ("..." if len(system_prompt) > 1500 else ""), style="dim"),
                title=f"[bold blue]System Prompt[/bold blue] │ {agent_id} iter={iteration}",
                border_style="blue",
                padding=(0, 1),
            ))
            
            if messages:
                for i, msg in enumerate(messages[-3:]):  # Show last 3 messages
                    msg_type = type(msg).__name__
                    content = getattr(msg, 'content', str(msg))
                    if isinstance(content, str) and len(content) > 500:
                        content = content[:500] + "..."
                    self.console.print(f"  [dim]{msg_type}:[/dim] {content}")
    
    def log_reasoning(self, agent_id: str, iteration: int, response: Any) -> None:
        """Log the LLM's reasoning response."""
        content = ""
        tool_calls = []
        
        if hasattr(response, 'content'):
            content = response.content if isinstance(response.content, str) else str(response.content)
        
        if hasattr(response, 'tool_calls') and response.tool_calls:
            tool_calls = response.tool_calls
        
        event = AgentEvent(
            timestamp=datetime.now(),
            event_type="reasoning",
            agent_id=agent_id,
            iteration=iteration,
            content=content,
            metadata={"tool_calls": len(tool_calls)},
        )
        self.events.append(event)
        
        if self.verbose >= 1 and self.show_reasoning:
            self.console.print()
            
            # Show reasoning content
            if content and content.strip():
                # Truncate long reasoning
                display_content = content
                if len(display_content) > 2000 and self.verbose < 3:
                    display_content = display_content[:2000] + "\n\n[dim]... (truncated)[/dim]"
                
                self.console.print(Panel(
                    Markdown(display_content),
                    title=f"[bold cyan]💭 Agent Reasoning[/bold cyan] │ {agent_id} iter={iteration}",
                    border_style="cyan",
                    padding=(0, 1),
                ))
            
            # Show tool calls summary
            if tool_calls:
                self._display_tool_calls(agent_id, iteration, tool_calls)
    
    def _display_tool_calls(self, agent_id: str, iteration: int, tool_calls: list) -> None:
        """Display tool calls in a nice format."""
        if not self.show_tool_calls:
            return
            
        table = Table(title=f"🔧 Tool Calls", show_header=True, border_style="yellow")
        table.add_column("Tool", style="bold yellow")
        table.add_column("Arguments", style="dim")
        
        for tc in tool_calls:
            tool_name = tc.get('name', 'unknown') if isinstance(tc, dict) else getattr(tc, 'name', 'unknown')
            args = tc.get('args', {}) if isinstance(tc, dict) else getattr(tc, 'args', {})
            
            # Format args nicely
            args_str = ""
            if isinstance(args, dict):
                for k, v in args.items():
                    v_str = str(v)
                    if len(v_str) > 100:
                        v_str = v_str[:100] + "..."
                    args_str += f"{k}={v_str}\n"
            else:
                args_str = str(args)[:200]
            
            table.add_row(tool_name, args_str.strip())
        
        self.console.print(table)
    
    def log_tool_call(self, agent_id: str, iteration: int, tool_name: str, args: dict) -> None:
        """Log a tool being called."""
        event = AgentEvent(
            timestamp=datetime.now(),
            event_type="tool_call",
            agent_id=agent_id,
            iteration=iteration,
            content={"tool": tool_name, "args": args},
        )
        self.events.append(event)
        
        if self.verbose >= 2 and self.show_tool_calls:
            args_preview = str(args)[:150] + "..." if len(str(args)) > 150 else str(args)
            self.console.print(f"  [yellow]→ {tool_name}[/yellow]: {args_preview}")
    
    def log_tool_result(self, agent_id: str, iteration: int, tool_name: str, result: Any) -> None:
        """Log a tool result."""
        result_str = str(result) if result else ""
        
        event = AgentEvent(
            timestamp=datetime.now(),
            event_type="tool_result", 
            agent_id=agent_id,
            iteration=iteration,
            content={"tool": tool_name, "result": result_str[:5000]},
        )
        self.events.append(event)
        
        if self.verbose >= 2 and self.show_tool_results:
            # Show truncated result
            preview = result_str[:300] + "..." if len(result_str) > 300 else result_str
            preview = preview.replace('\n', ' ')
            self.console.print(f"  [green]← {tool_name}[/green]: {preview}")
    
    def log_error(self, agent_id: str, iteration: int, error: str) -> None:
        """Log an error."""
        event = AgentEvent(
            timestamp=datetime.now(),
            event_type="error",
            agent_id=agent_id,
            iteration=iteration,
            content=error,
        )
        self.events.append(event)
        
        if self.verbose >= 1:
            self.console.print(f"[red bold]✗ Error:[/red bold] {error}")
    
    def log_iteration_start(self, agent_id: str, iteration: int, max_iterations: int) -> None:
        """Log the start of an iteration."""
        if self.verbose >= 1:
            self.console.print()
            self.console.rule(
                f"[bold]Iteration {iteration}/{max_iterations}[/bold] │ {agent_id}",
                style="dim"
            )
    
    def log_agent_start(self, agent_id: str, agent_type: str, task_preview: str) -> None:
        """Log the start of an agent run."""
        self.current_agent_id = agent_id
        
        if self.verbose >= 1:
            self.console.print()
            self.console.print(Panel(
                f"[bold]Agent:[/bold] {agent_id}\n"
                f"[bold]Type:[/bold] {agent_type}\n"
                f"[bold]Task:[/bold] {task_preview[:200]}{'...' if len(task_preview) > 200 else ''}",
                title="[bold green]🚀 Agent Started[/bold green]",
                border_style="green",
            ))
    
    def log_agent_complete(self, agent_id: str, success: bool, score: float | None, duration: float) -> None:
        """Log agent completion."""
        if self.verbose >= 1:
            status = "[green]✓ Success[/green]" if success else "[red]✗ Failed[/red]"
            score_str = f"{score:.2f}" if score is not None else "N/A"
            
            self.console.print()
            self.console.print(Panel(
                f"{status}\n"
                f"[bold]Score:[/bold] {score_str}\n"
                f"[bold]Duration:[/bold] {duration:.1f}s\n"
                f"[bold]Iterations:[/bold] {len([e for e in self.events if e.agent_id == agent_id and e.event_type == 'reasoning'])}",
                title=f"[bold]Agent Complete[/bold] │ {agent_id}",
                border_style="green" if success else "red",
            ))
    
    def get_summary(self) -> dict:
        """Get a summary of all events."""
        return {
            "total_events": len(self.events),
            "by_type": {
                etype: len([e for e in self.events if e.event_type == etype])
                for etype in ["prompt", "reasoning", "tool_call", "tool_result", "error"]
            },
            "by_agent": {
                aid: len([e for e in self.events if e.agent_id == aid])
                for aid in set(e.agent_id for e in self.events)
            },
        }


# Global observer instance (can be replaced per-run)
_observer: AgentObserver | None = None


def get_observer() -> AgentObserver:
    """Get the global observer, creating one if needed."""
    global _observer
    if _observer is None:
        _observer = AgentObserver()
    return _observer


def set_observer(observer: AgentObserver) -> None:
    """Set the global observer."""
    global _observer
    _observer = observer


def create_observer(
    verbose: int = 1,
    show_prompts: bool = False,
    show_reasoning: bool = True,
    show_tool_calls: bool = True,
    show_tool_results: bool = True,
    console: Console | None = None,
) -> AgentObserver:
    """Create and set a new observer with the given settings."""
    observer = AgentObserver(
        console=console or Console(),
        verbose=verbose,
        show_prompts=show_prompts,
        show_reasoning=show_reasoning,
        show_tool_calls=show_tool_calls,
        show_tool_results=show_tool_results,
    )
    set_observer(observer)
    return observer
