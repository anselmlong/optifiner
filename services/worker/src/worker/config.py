"""Configuration for the evolution worker."""

import os
import threading
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


# Thread-local storage for early stop event
# This allows the agent to check if it should stop early (another agent found improvement)
_thread_local = threading.local()


def set_stop_event(event: threading.Event | None):
    """Set the stop event for the current thread.
    
    When this event is set, the agent should stop as soon as possible.
    
    Args:
        event: A threading.Event that signals early stop, or None to clear.
    """
    _thread_local.stop_event = event


def get_stop_event() -> threading.Event | None:
    """Get the stop event for the current thread, if any."""
    return getattr(_thread_local, 'stop_event', None)


def should_stop_early() -> bool:
    """Check if the agent should stop early (another agent found improvement).
    
    Returns:
        True if the stop event is set and the agent should stop.
    """
    event = get_stop_event()
    return event is not None and event.is_set()


class ModelProvider(str, Enum):
    """Supported LLM providers."""

    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    OPENAI = "openai"


class ModelConfig(BaseModel):
    """Configuration for an LLM model."""

    provider: ModelProvider
    model_name: str
    temperature: float = 0.0
    timeout: float = 600.0  # seconds for model call timeout
    max_retries: int = 3  # number of retries on timeout/transient errors
    api_key: str | None = None  # API key for the provider (thread-safe, avoids env var races)

    @classmethod
    def opus(cls) -> "ModelConfig":
        """Claude Opus 4 configuration."""
        return cls(
            provider=ModelProvider.ANTHROPIC,
            model_name="claude-opus-4-20250514",
            temperature=0.0,
            timeout=600.0,  # Longer timeout for Opus
            max_retries=3,
        )

    @classmethod
    def sonnet(cls) -> "ModelConfig":
        """Claude Sonnet 4.5 configuration."""
        return cls(
            provider=ModelProvider.ANTHROPIC,
            model_name="claude-sonnet-4-5-20250514",
            temperature=0.0,
            timeout=600.0,
            max_retries=3,
        )

    @classmethod
    def haiku(cls) -> "ModelConfig":
        """Claude Haiku 4 configuration."""
        return cls(
            provider=ModelProvider.ANTHROPIC,
            model_name="claude-haiku-4-20250514",
            temperature=0.0,
            timeout=300.0,  # Longer timeout for reliability
            max_retries=3,
        )

    @classmethod
    def gemini_flash(cls) -> "ModelConfig":
        """Gemini 2.5 Flash configuration (stable)."""
        return cls(
            provider=ModelProvider.GOOGLE,
            model_name="gemini-3-flash-preview",
            temperature=0.0,
            timeout=120.0,
            max_retries=3,
        )

    @classmethod
    def gemini_3_flash(cls) -> "ModelConfig":
        """Gemini 3 Flash configuration (preview - may have issues)."""
        return cls(
            provider=ModelProvider.GOOGLE,
            model_name="gemini-3-flash-preview",
            temperature=0.0,
            timeout=120.0,
            max_retries=3,
        )

    @classmethod
    def gemini_pro(cls) -> "ModelConfig":
        """Gemini Pro configuration (slower but more capable)."""
        return cls(
            provider=ModelProvider.GOOGLE,
            model_name="gemini-3-pro-preview",
            temperature=0.0,
            timeout=600.0,  # Longer timeout for Pro model
            max_retries=3,
        )

    @classmethod
    def gpt4o(cls) -> "ModelConfig":
        """GPT-4o configuration."""
        return cls(
            provider=ModelProvider.OPENAI,
            model_name="gpt-4o",
            temperature=0.0,
            timeout=60.0,
            max_retries=3,
        )

    @classmethod
    def gpt5_nano(cls) -> "ModelConfig":
        """GPT-5 Nano configuration (fast, lightweight model)."""
        return cls(
            provider=ModelProvider.OPENAI,
            model_name="gpt-5-nano",
            temperature=0.0,
            timeout=50.0,  # Shorter timeout for faster model
            max_retries=3,
        )


class AgentType(str, Enum):
    """Types of evolution agents."""

    ANALYZER = "analyzer"
    REFACTORING = "refactoring"
    FEATURE = "feature"
    OPTIMIZER = "optimizer"
    GENERAL = "general"


class WorkerConfig(BaseModel):
    """Configuration for the evolution worker."""

    # Model settings
    model: ModelConfig = Field(default_factory=ModelConfig.gemini_flash)

    # Agent settings
    agent_type: AgentType = AgentType.GENERAL
    max_iterations: int = 10

    # Workspace settings - real path, no emulation
    # This will be set dynamically when a workspace is created
    workspace_root: str = ""

    # Execution settings
    execution_timeout: int = 60
    benchmark_timeout: int = 30

    @classmethod
    def from_env(cls) -> "WorkerConfig":
        """Create configuration from environment variables."""
        provider = os.getenv("MODEL_PROVIDER", "google")
        model_name = os.getenv("MODEL_NAME", "gemini-3-flash-preview")
        temperature = float(os.getenv("MODEL_TEMPERATURE", "0.0"))

        # Workspace root comes from WORKSPACE_ROOT env or will be set dynamically
        workspace_root = os.getenv("WORKSPACE_ROOT", "")

        # Default timeout based on model
        # Gemini Flash: 120s, Gemini Pro: 600s, others: 600s
        if "gemini" in model_name.lower():
            if "flash" in model_name.lower():
                default_timeout = 120.0
            else:
                # Gemini Pro needs longer timeout
                default_timeout = 600.0
        else:
            default_timeout = 600.0
        timeout = float(os.getenv("MODEL_TIMEOUT", str(default_timeout)))
        max_retries = int(os.getenv("MODEL_MAX_RETRIES", "3"))

        return cls(
            model=ModelConfig(
                provider=ModelProvider(provider),
                model_name=model_name,
                temperature=temperature,
                timeout=timeout,
                max_retries=max_retries,
            ),
            agent_type=AgentType(os.getenv("AGENT_TYPE", "general")),
            max_iterations=int(os.getenv("MAX_ITERATIONS", "10")),
            workspace_root=workspace_root,
            execution_timeout=int(os.getenv("EXECUTION_TIMEOUT", "60")),
            benchmark_timeout=int(os.getenv("BENCHMARK_TIMEOUT", "30")),
        )


def get_llm(config: ModelConfig):
    """Create an LLM instance based on configuration.
    
    Timeout and retries are configured per-model. The timeout applies to
    the model API call only (not tool execution).
    
    API key can be provided directly in config.api_key (thread-safe for parallel execution)
    or will fall back to environment variables if not provided.
    """
    if config.provider == ModelProvider.ANTHROPIC:
        from langchain_anthropic import ChatAnthropic

        # Use config.api_key if provided (thread-safe), otherwise fall back to env var
        api_key = config.api_key or os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY environment variable is required. "
                "Please set it with: export ANTHROPIC_API_KEY='your-api-key'"
            )

        return ChatAnthropic(
            model=config.model_name,
            api_key=api_key,
            temperature=config.temperature,
            timeout=config.timeout,
            max_retries=config.max_retries,
        )
    elif config.provider == ModelProvider.GOOGLE:
        from langchain_google_genai import ChatGoogleGenerativeAI

        # Use config.api_key if provided (thread-safe), otherwise fall back to env var
        api_key = config.api_key or os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError(
                "GOOGLE_API_KEY environment variable is required. "
                "Please set it with: export GOOGLE_API_KEY='your-api-key'"
            )

        return ChatGoogleGenerativeAI(
            model=config.model_name,
            google_api_key=api_key,
            temperature=config.temperature,
            timeout=config.timeout,
            max_retries=config.max_retries,
        )
    elif config.provider == ModelProvider.OPENAI:
        from langchain_openai import ChatOpenAI

        # Use config.api_key if provided (thread-safe), otherwise fall back to env var
        api_key = config.api_key or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError(
                "OPENAI_API_KEY environment variable is required. "
                "Please set it with: export OPENAI_API_KEY='your-api-key'"
            )

        return ChatOpenAI(
            model=config.model_name,
            api_key=api_key,
            temperature=config.temperature,
            timeout=config.timeout,
            max_retries=config.max_retries,
        )
    else:
        raise ValueError(f"Unsupported provider: {config.provider}")
