"""CRUD operations for database models."""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from optifiner_api.db_models import (
    Project,
    Workflow,
    WorkflowStep,
    AgentInstance,
    LogEntry,
    WorkflowStatus,
    AgentStatus,
)


# =============================================================================
# Project CRUD
# =============================================================================

async def create_project(
    db: AsyncSession,
    name: str,
    description: str | None = None,
    repository_url: str | None = None,
    repository_branch: str | None = None,
    target_fitness: float = 0.95,
    cost_limit: float = 50.0,
) -> Project:
    """Create a new project."""
    project = Project(
        name=name,
        description=description,
        repository_url=repository_url,
        repository_branch=repository_branch,
        target_fitness=target_fitness,
        cost_limit=cost_limit,
    )
    db.add(project)
    await db.flush()
    await db.refresh(project)
    return project


async def get_project(db: AsyncSession, project_id: UUID) -> Project | None:
    """Get a project by ID."""
    result = await db.execute(
        select(Project)
        .where(Project.id == project_id)
        .options(selectinload(Project.workflows))
    )
    return result.scalar_one_or_none()


async def get_projects(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 100,
    status: str | None = None,
) -> list[Project]:
    """Get all projects with optional filtering."""
    query = select(Project)
    if status:
        query = query.where(Project.status == status)
    query = query.order_by(Project.updated_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())


async def update_project(
    db: AsyncSession,
    project_id: UUID,
    **kwargs: Any,
) -> Project | None:
    """Update a project."""
    kwargs["updated_at"] = datetime.utcnow()
    await db.execute(
        update(Project).where(Project.id == project_id).values(**kwargs)
    )
    await db.flush()
    return await get_project(db, project_id)


async def delete_project(db: AsyncSession, project_id: UUID) -> bool:
    """Delete a project."""
    result = await db.execute(
        delete(Project).where(Project.id == project_id)
    )
    await db.flush()
    return result.rowcount > 0


# =============================================================================
# Workflow CRUD
# =============================================================================

async def create_workflow(
    db: AsyncSession,
    repo_url: str,
    project_id: UUID | None = None,
    **kwargs: Any,
) -> Workflow:
    """Create a new workflow."""
    workflow = Workflow(
        repo_url=repo_url,
        project_id=project_id,
        **kwargs,
    )
    db.add(workflow)
    await db.flush()
    await db.refresh(workflow)
    return workflow


async def get_workflow(db: AsyncSession, workflow_id: UUID) -> Workflow | None:
    """Get a workflow by ID with all relationships."""
    result = await db.execute(
        select(Workflow)
        .where(Workflow.id == workflow_id)
        .options(
            selectinload(Workflow.steps),
            selectinload(Workflow.agents),
        )
    )
    return result.scalar_one_or_none()


async def get_workflows(
    db: AsyncSession,
    project_id: UUID | None = None,
    status: WorkflowStatus | None = None,
    skip: int = 0,
    limit: int = 100,
) -> list[Workflow]:
    """Get workflows with optional filtering."""
    query = select(Workflow)
    if project_id:
        query = query.where(Workflow.project_id == project_id)
    if status:
        query = query.where(Workflow.status == status)
    query = query.order_by(Workflow.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())


async def update_workflow(
    db: AsyncSession,
    workflow_id: UUID,
    **kwargs: Any,
) -> Workflow | None:
    """Update a workflow."""
    kwargs["updated_at"] = datetime.utcnow()
    await db.execute(
        update(Workflow).where(Workflow.id == workflow_id).values(**kwargs)
    )
    await db.flush()
    return await get_workflow(db, workflow_id)


async def update_workflow_status(
    db: AsyncSession,
    workflow_id: UUID,
    status: WorkflowStatus,
    **extra_fields: Any,
) -> Workflow | None:
    """Update workflow status with optional extra fields."""
    update_data = {"status": status, "updated_at": datetime.utcnow(), **extra_fields}
    
    # Set timestamps based on status
    if status == WorkflowStatus.RUNNING and "started_at" not in extra_fields:
        update_data["started_at"] = datetime.utcnow()
    elif status == WorkflowStatus.PAUSED:
        update_data["paused_at"] = datetime.utcnow()
    elif status in (WorkflowStatus.COMPLETED, WorkflowStatus.STOPPED, WorkflowStatus.FAILED):
        update_data["completed_at"] = datetime.utcnow()
    
    return await update_workflow(db, workflow_id, **update_data)


# =============================================================================
# WorkflowStep CRUD
# =============================================================================

async def create_workflow_step(
    db: AsyncSession,
    workflow_id: UUID,
    step_number: int,
    generation: int,
    baseline_score: float,
    final_score: float,
    agent_id: str | None = None,
    improvement: float = 0.0,
    improvement_percent: float = 0.0,
    is_initial: bool = False,
    commit_hash: str | None = None,
) -> WorkflowStep:
    """Create a new workflow step."""
    step = WorkflowStep(
        workflow_id=workflow_id,
        step_number=step_number,
        generation=generation,
        agent_id=agent_id,
        baseline_score=baseline_score,
        final_score=final_score,
        improvement=improvement,
        improvement_percent=improvement_percent,
        is_initial=is_initial,
        commit_hash=commit_hash,
    )
    db.add(step)
    await db.flush()
    await db.refresh(step)
    return step


async def get_workflow_steps(
    db: AsyncSession,
    workflow_id: UUID,
) -> list[WorkflowStep]:
    """Get all steps for a workflow."""
    result = await db.execute(
        select(WorkflowStep)
        .where(WorkflowStep.workflow_id == workflow_id)
        .order_by(WorkflowStep.step_number)
    )
    return list(result.scalars().all())


# =============================================================================
# AgentInstance CRUD
# =============================================================================

async def create_agent_instance(
    db: AsyncSession,
    workflow_id: UUID,
    instance_id: str,
    generation: int,
    agent_type: str,
    model_provider: str,
    model_name: str,
    baseline_score: float | None = None,
) -> AgentInstance:
    """Create a new agent instance."""
    agent = AgentInstance(
        workflow_id=workflow_id,
        instance_id=instance_id,
        generation=generation,
        agent_type=agent_type,
        model_provider=model_provider,
        model_name=model_name,
        baseline_score=baseline_score,
        status=AgentStatus.PENDING,
    )
    db.add(agent)
    await db.flush()
    await db.refresh(agent)
    return agent


async def get_agent_instance(db: AsyncSession, agent_id: UUID) -> AgentInstance | None:
    """Get an agent instance by ID."""
    result = await db.execute(
        select(AgentInstance).where(AgentInstance.id == agent_id)
    )
    return result.scalar_one_or_none()


async def get_workflow_agents(
    db: AsyncSession,
    workflow_id: UUID,
    generation: int | None = None,
    status: AgentStatus | None = None,
) -> list[AgentInstance]:
    """Get agents for a workflow."""
    query = select(AgentInstance).where(AgentInstance.workflow_id == workflow_id)
    if generation is not None:
        query = query.where(AgentInstance.generation == generation)
    if status:
        query = query.where(AgentInstance.status == status)
    query = query.order_by(AgentInstance.created_at)
    result = await db.execute(query)
    return list(result.scalars().all())


async def update_agent_instance(
    db: AsyncSession,
    agent_id: UUID,
    **kwargs: Any,
) -> AgentInstance | None:
    """Update an agent instance."""
    await db.execute(
        update(AgentInstance).where(AgentInstance.id == agent_id).values(**kwargs)
    )
    await db.flush()
    return await get_agent_instance(db, agent_id)


async def update_agent_status(
    db: AsyncSession,
    agent_id: UUID,
    status: AgentStatus,
    **extra_fields: Any,
) -> AgentInstance | None:
    """Update agent status with optional extra fields."""
    update_data = {"status": status, **extra_fields}
    
    if status == AgentStatus.RUNNING and "started_at" not in extra_fields:
        update_data["started_at"] = datetime.utcnow()
    elif status in (AgentStatus.COMPLETED, AgentStatus.FAILED, AgentStatus.CANCELLED):
        update_data["completed_at"] = datetime.utcnow()
    
    return await update_agent_instance(db, agent_id, **update_data)


# =============================================================================
# LogEntry CRUD
# =============================================================================

async def create_log_entry(
    db: AsyncSession,
    workflow_id: UUID,
    level: str,
    message: str,
    agent_instance_id: UUID | None = None,
    agent_name: str | None = None,
    details: str | None = None,
) -> LogEntry:
    """Create a new log entry."""
    log = LogEntry(
        workflow_id=workflow_id,
        agent_instance_id=agent_instance_id,
        level=level,
        message=message,
        agent_name=agent_name,
        details=details,
    )
    db.add(log)
    await db.flush()
    await db.refresh(log)
    return log


async def get_workflow_logs(
    db: AsyncSession,
    workflow_id: UUID,
    limit: int = 100,
    level: str | None = None,
) -> list[LogEntry]:
    """Get logs for a workflow."""
    query = select(LogEntry).where(LogEntry.workflow_id == workflow_id)
    if level:
        query = query.where(LogEntry.level == level)
    query = query.order_by(LogEntry.created_at.desc()).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())


# =============================================================================
# EarlyAccessSignup CRUD
# =============================================================================

async def create_early_access_signup(
    db: AsyncSession,
    email: str,
    source: str = "landing_page",
    user_agent: str | None = None,
    ip_address: str | None = None,
) -> "EarlyAccessSignup":
    """Create a new early access signup."""
    from optifiner_api.db_models import EarlyAccessSignup

    signup = EarlyAccessSignup(
        email=email.lower().strip(),
        source=source,
        user_agent=user_agent,
        ip_address=ip_address,
    )
    db.add(signup)
    await db.flush()
    await db.refresh(signup)
    return signup


async def get_early_access_signup_by_email(
    db: AsyncSession,
    email: str,
) -> "EarlyAccessSignup | None":
    """Get a signup by email."""
    from optifiner_api.db_models import EarlyAccessSignup

    result = await db.execute(
        select(EarlyAccessSignup).where(
            EarlyAccessSignup.email == email.lower().strip()
        )
    )
    return result.scalar_one_or_none()


async def get_early_access_signups(
    db: AsyncSession,
    status: str | None = None,
    skip: int = 0,
    limit: int = 100,
) -> list["EarlyAccessSignup"]:
    """Get all early access signups with optional filtering."""
    from optifiner_api.db_models import EarlyAccessSignup

    query = select(EarlyAccessSignup)
    if status:
        query = query.where(EarlyAccessSignup.status == status)
    query = query.order_by(EarlyAccessSignup.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())


async def count_early_access_signups(
    db: AsyncSession,
    status: str | None = None,
) -> int:
    """Count early access signups."""
    from optifiner_api.db_models import EarlyAccessSignup
    from sqlalchemy import func

    query = select(func.count(EarlyAccessSignup.id))
    if status:
        query = query.where(EarlyAccessSignup.status == status)
    result = await db.execute(query)
    return result.scalar_one()
