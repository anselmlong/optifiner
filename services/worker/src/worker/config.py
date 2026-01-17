"""Configuration for the evolution worker."""

import os
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


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
    max_tokens: int = 4096
    timeout: float = 60.0  # seconds for model call timeout
    max_retries: int = 3  # number of retries on timeout/transient errors

    @classmethod
    def sonnet(cls) -> "ModelConfig":
        """Claude Sonnet 4.5 configuration."""
        return cls(
            provider=ModelProvider.ANTHROPIC,
            model_name="claude-sonnet-4-20250514",
            temperature=0.0,
            max_tokens=8192,
            timeout=60.0,
            max_retries=3,
        )

    @classmethod
    def gemini_flash(cls) -> "ModelConfig":
        """Gemini 3 Flash configuration."""
        return cls(
            provider=ModelProvider.GOOGLE,
            model_name="gemini-3-flash-preview",
            temperature=0.0,
            max_tokens=8192,
            timeout=20.0,  # Shorter timeout for faster model
            max_retries=3,
        )

    @classmethod
    def gpt4o(cls) -> "ModelConfig":
        """GPT-4o configuration."""
        return cls(
            provider=ModelProvider.OPENAI,
            model_name="gpt-4o",
            temperature=0.0,
            max_tokens=4096,
            timeout=60.0,
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
        max_tokens = int(os.getenv("MODEL_MAX_TOKENS", "8192"))

        # Workspace root comes from WORKSPACE_ROOT env or will be set dynamically
        workspace_root = os.getenv("WORKSPACE_ROOT", "")

        # Default timeout based on model
        default_timeout = 20.0 if "gemini" in model_name.lower() and "flash" in model_name.lower() else 60.0
        timeout = float(os.getenv("MODEL_TIMEOUT", str(default_timeout)))
        max_retries = int(os.getenv("MODEL_MAX_RETRIES", "3"))

        return cls(
            model=ModelConfig(
                provider=ModelProvider(provider),
                model_name=model_name,
                temperature=temperature,
                max_tokens=max_tokens,
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
    """
    if config.provider == ModelProvider.ANTHROPIC:
        from langchain_anthropic import ChatAnthropic

        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY environment variable is required. "
                "Please set it with: export ANTHROPIC_API_KEY='your-api-key'"
            )

        return ChatAnthropic(
            model=config.model_name,
            api_key=api_key,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
            timeout=config.timeout,
            max_retries=config.max_retries,
        )
    elif config.provider == ModelProvider.GOOGLE:
        from langchain_google_genai import ChatGoogleGenerativeAI

        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError(
                "GOOGLE_API_KEY environment variable is required. "
                "Please set it with: export GOOGLE_API_KEY='your-api-key'"
            )

        return ChatGoogleGenerativeAI(
            model=config.model_name,
            google_api_key=api_key,
            temperature=config.temperature,
            max_output_tokens=config.max_tokens,
            timeout=config.timeout,
            max_retries=config.max_retries,
        )
    elif config.provider == ModelProvider.OPENAI:
        from langchain_openai import ChatOpenAI

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError(
                "OPENAI_API_KEY environment variable is required. "
                "Please set it with: export OPENAI_API_KEY='your-api-key'"
            )

        return ChatOpenAI(
            model=config.model_name,
            api_key=api_key,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
            timeout=config.timeout,
            max_retries=config.max_retries,
        )
    else:
        raise ValueError(f"Unsupported provider: {config.provider}")
