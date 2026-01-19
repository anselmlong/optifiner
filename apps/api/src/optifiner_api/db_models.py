"""SQLAlchemy database models for Optifiner API."""

import enum
from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    JSON,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from optifiner_api.database import Base


class WorkflowStatus(str, enum.Enum):
    """Status of an optimization workflow."""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    STOPPED = "stopped"
    FAILED = "failed"


class AgentStatus(str, enum.Enum):
    """Status of an agent instance."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Project(Base):
    """Project model - represents an optimization project."""
    __tablename__ = "projects"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    repository_url = Column(String(512), nullable=True)
    repository_branch = Column(String(255), nullable=True)
    
    # Configuration
    target_fitness = Column(Float, default=0.95)
    cost_limit = Column(Float, default=50.0)
    
    # Status tracking
    status = Column(String(50), default="active")
    current_fitness = Column(Float, default=0.0)
    total_cost_spent = Column(Float, default=0.0)
    current_generation = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    workflows = relationship("Workflow", back_populates="project", cascade="all, delete-orphan")

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "name": self.name,
            "description": self.description,
            "repository_url": self.repository_url,
            "repository_branch": self.repository_branch,
            "target_fitness": self.target_fitness,
            "cost_limit": self.cost_limit,
            "status": self.status,
            "current_fitness": self.current_fitness,
            "total_cost_spent": self.total_cost_spent,
            "current_generation": self.current_generation,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class Workflow(Base):
    """Workflow model - represents an optimization workflow run."""
    __tablename__ = "workflows"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=True)
    
    # Status
    status = Column(Enum(WorkflowStatus), default=WorkflowStatus.PENDING)
    
    # Repository info
    repo_url = Column(String(512), nullable=False)
    repo_dir = Column(String(255), nullable=True)
    branch = Column(String(255), nullable=True)  # Optimization branch name
    original_branch = Column(String(255), nullable=True)
    
    # Scores
    baseline_score = Column(Float, nullable=True)
    current_best_score = Column(Float, nullable=True)
    baseline_data = Column(JSON, nullable=True)
    
    # Configuration
    user_prompt = Column(Text, nullable=True)
    models_config = Column(JSON, nullable=True)  # List of model configs
    agents_per_generation = Column(Integer, default=10)
    parallel = Column(Integer, default=1)
    max_generations = Column(Integer, default=1)
    max_iterations_per_agent = Column(Integer, default=15)
    agent_types = Column(JSON, nullable=True)
    min_improvement_pct = Column(Float, default=6.0)
    early_stop = Column(Boolean, default=True)
    evaluator_path = Column(String(512), nullable=True)
    build_benchmark = Column(Boolean, default=False)
    verbosity = Column(Integer, default=1)
    log_dir = Column(String(512), nullable=True)
    total_cost_limit = Column(Float, default=10.0)
    time_limit_seconds = Column(Integer, default=300)
    
    # Progress tracking
    generation = Column(Integer, default=0)
    total_improvements = Column(Integer, default=0)
    total_attempts = Column(Integer, default=0)
    step_count = Column(Integer, default=0)
    total_cost = Column(Float, default=0.0)
    
    # Results
    improvement = Column(Float, nullable=True)
    improvement_percent = Column(Float, nullable=True)
    error = Column(Text, nullable=True)
    pr_url = Column(String(512), nullable=True)  # Pull request URL
    
    # Graph structure for visualization
    graph_data = Column(JSON, nullable=True)
    
    # Timestamps
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    paused_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    project = relationship("Project", back_populates="workflows")
    steps = relationship("WorkflowStep", back_populates="workflow", cascade="all, delete-orphan")
    agents = relationship("AgentInstance", back_populates="workflow", cascade="all, delete-orphan")

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "workflow_id": str(self.id),
            "project_id": str(self.project_id) if self.project_id else None,
            "status": self.status.value if self.status else None,
            "repo_url": self.repo_url,
            "repo_dir": self.repo_dir,
            "branch": self.branch,
            "original_branch": self.original_branch,
            "baseline_score": self.baseline_score,
            "current_best_score": self.current_best_score,
            "baseline_data": self.baseline_data,
            "user_prompt": self.user_prompt,
            "models": self.models_config,
            "agents_per_generation": self.agents_per_generation,
            "parallel": self.parallel,
            "max_generations": self.max_generations,
            "max_iterations_per_agent": self.max_iterations_per_agent,
            "agent_types": self.agent_types,
            "min_improvement_pct": self.min_improvement_pct,
            "early_stop": self.early_stop,
            "evaluator_path": self.evaluator_path,
            "verbosity": self.verbosity,
            "log_dir": self.log_dir,
            "total_cost_limit": self.total_cost_limit,
            "time_limit_seconds": self.time_limit_seconds,
            "generation": self.generation,
            "total_improvements": self.total_improvements,
            "total_attempts": self.total_attempts,
            "step_count": self.step_count,
            "total_cost": self.total_cost,
            "improvement": self.improvement,
            "improvement_percent": self.improvement_percent,
            "error": self.error,
            "pr_url": self.pr_url,
            "graph_data": self.graph_data,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "paused_at": self.paused_at.isoformat() if self.paused_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "steps": [s.to_dict() for s in self.steps] if self.steps else [],
        }


class WorkflowStep(Base):
    """WorkflowStep model - represents a step/snapshot in the evolution."""
    __tablename__ = "workflow_steps"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    workflow_id = Column(UUID(as_uuid=True), ForeignKey("workflows.id"), nullable=False)
    
    step_number = Column(Integer, nullable=False)
    generation = Column(Integer, nullable=False)
    agent_id = Column(String(255), nullable=True)  # String ID from agent execution
    
    # Scores
    baseline_score = Column(Float, nullable=False)
    final_score = Column(Float, nullable=False)
    improvement = Column(Float, default=0.0)
    improvement_percent = Column(Float, default=0.0)
    
    # Metadata
    is_initial = Column(Boolean, default=False)
    commit_hash = Column(String(64), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    workflow = relationship("Workflow", back_populates="steps")

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "step": self.step_number,
            "generation": self.generation,
            "agent_id": self.agent_id,
            "baseline_score": self.baseline_score,
            "final_score": self.final_score,
            "improvement": self.improvement,
            "improvement_percent": self.improvement_percent,
            "is_initial": self.is_initial,
            "commit_hash": self.commit_hash,
            "timestamp": self.created_at.isoformat() if self.created_at else None,
        }


class AgentInstance(Base):
    """AgentInstance model - represents an agent during workflow execution."""
    __tablename__ = "agent_instances"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    workflow_id = Column(UUID(as_uuid=True), ForeignKey("workflows.id"), nullable=False)
    
    instance_id = Column(String(255), nullable=False)  # e.g., "abc123-gen1-optimizer-1"
    generation = Column(Integer, nullable=False)
    agent_type = Column(String(50), nullable=False)
    
    # Model configuration
    model_provider = Column(String(50), nullable=False)
    model_name = Column(String(255), nullable=False)
    
    # Status
    status = Column(Enum(AgentStatus), default=AgentStatus.PENDING)
    
    # Results
    baseline_score = Column(Float, nullable=True)
    final_score = Column(Float, nullable=True)
    improvement = Column(Float, nullable=True)
    improvement_percent = Column(Float, nullable=True)
    success = Column(Boolean, default=False)
    error = Column(Text, nullable=True)
    
    # Current activity (for real-time display)
    current_task = Column(String(512), nullable=True)
    current_file = Column(String(512), nullable=True)
    iterations_completed = Column(Integer, default=0)
    
    # Cost tracking
    cost = Column(Float, default=0.0)
    
    # Timestamps
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    workflow = relationship("Workflow", back_populates="agents")

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "instance_id": self.instance_id,
            "generation": self.generation,
            "agent_type": self.agent_type,
            "model_provider": self.model_provider,
            "model_name": self.model_name,
            "status": self.status.value if self.status else None,
            "baseline_score": self.baseline_score,
            "final_score": self.final_score,
            "improvement": self.improvement,
            "improvement_percent": self.improvement_percent,
            "success": self.success,
            "error": self.error,
            "current_task": self.current_task,
            "current_file": self.current_file,
            "iterations_completed": self.iterations_completed,
            "cost": self.cost,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


class LogEntry(Base):
    """LogEntry model - stores logs for workflows."""
    __tablename__ = "log_entries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    workflow_id = Column(UUID(as_uuid=True), ForeignKey("workflows.id"), nullable=False)
    agent_instance_id = Column(UUID(as_uuid=True), ForeignKey("agent_instances.id"), nullable=True)

    level = Column(String(20), nullable=False)  # info, success, warning, error
    message = Column(Text, nullable=False)
    details = Column(Text, nullable=True)
    agent_name = Column(String(255), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "workflow_id": str(self.workflow_id),
            "level": self.level,
            "message": self.message,
            "details": self.details,
            "agent_name": self.agent_name,
            "timestamp": self.created_at.strftime("%H:%M:%S") if self.created_at else None,
        }


class EarlyAccessSignup(Base):
    """Early access email signup model."""
    __tablename__ = "early_access_signups"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    email = Column(String(255), nullable=False, unique=True, index=True)
    source = Column(String(50), default="landing_page")
    user_agent = Column(String(512), nullable=True)
    ip_address = Column(String(45), nullable=True)
    status = Column(String(50), default="pending")
    notified_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": str(self.id),
            "email": self.email,
            "source": self.source,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "notified_at": self.notified_at.isoformat() if self.notified_at else None,
        }
