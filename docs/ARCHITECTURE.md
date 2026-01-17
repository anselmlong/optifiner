# Architecture

This document provides an in-depth look at Optifiner's system design, components, and workflows.

## Table of Contents

1. [System Overview](#system-overview)
2. [Component Architecture](#component-architecture)
3. [Evolution Workflow](#evolution-workflow)
4. [Agent Architecture](#agent-architecture)
5. [Data Models](#data-models)
6. [Tool System](#tool-system)
7. [State Management](#state-management)

## System Overview

Optifiner is a three-tier system:

```
┌─────────────────────────────────────┐
│        Frontend (React/D3)           │
│    Dashboard & Visualization         │
└──────────────┬──────────────────────┘
               │ HTTP/WebSocket
┌──────────────▼──────────────────────┐
│      Backend (FastAPI/Celery)       │
│ Project management & task queueing  │
└──────────────┬──────────────────────┘
               │ Task Queue
┌──────────────▼──────────────────────┐
│  Worker (LangGraph/Python)          │
│ Evolution engine & agent execution  │
└─────────────────────────────────────┘
```

## Component Architecture

### 1. Worker Service (`services/worker/`)

The heart of Optifiner - contains the evolution engine.

#### Core Modules

**`agent.py`** - Agent orchestration
- Creates LangGraph agent graphs
- Manages agent lifecycle
- Coordinates tool execution
- Handles state transitions

```python
def create_agent(agent_type: str, config: WorkerConfig) -> CompiledGraph:
    """Create and compile a LangGraph agent."""
    graph = StateGraph(AgentState)
    graph.add_node("analyze", analyze_step)
    graph.add_node("improve", improve_step)
    graph.add_node("validate", validate_step)
    # ... edges and compilation
    return graph.compile()
```

**`state.py`** - Agent state definitions
- `AgentState` - Agent execution state
- `MessageState` - LLM message tracking
- `WorkspaceState` - Repository state

**`config.py`** - Configuration management
- Model provider setup (Anthropic, Google, OpenAI)
- Worker parameters (agents, generations, iterations)
- LLM client initialization

**`cli.py`** - Command-line interface (~1100 lines)
- Entry point for evolution runs
- Parameter parsing
- Orchestrates the full evolution cycle

**`evaluator.py`** - Benchmark execution
- Runs user-provided evaluation scripts
- Parses benchmark results
- Tracks fitness scores
- Manages timeouts and errors

**`workspace.py`** - Workspace isolation
- Creates isolated repository copies
- Manages filesystem operations
- Handles git operations per agent
- Cleans up temporary workspaces

**`prompts.py`** - LLM prompts
- System prompts for each agent type
- Few-shot examples
- Context injection for code analysis

#### Tool System (`tools/`)

Tools are the interface between agents and the codebase:

- **`read_file`** - Read file contents
- **`write_file`** - Create/overwrite files
- **`edit_file`** - Find & replace operations
- **`multi_edit`** - Atomic multi-file edits
- **`grep`** - Regex search across files
- **`glob_search`** - File pattern matching
- **`list_dir`** - Directory listing
- **`evaluate`** - Run benchmarks (restricted)

### 2. Web UI (`apps/web/`)

React-based dashboard for real-time evolution monitoring.

#### Page Structure

```
/                     → Dashboard (overview)
/projects             → Projects list
/projects/new         → Create new project
/projects/:id         → Evolution monitor (detailed view)
/projects/:id/analysis/:nodeId → Code analysis
/analytics            → Metrics & statistics
/history              → Evolution history
/settings             → Configuration
/help                 → Documentation
```

#### Components

**Layout Components**
- `MainLayout` - Main page wrapper
- `Header` - Navigation bar
- `Sidebar` - Project/agent navigation

**UI Components**
- `Button`, `Card`, `Badge`, `Modal` - Basic UI
- `EvolutionTree` - D3-based visualization
- `MetricsChart` - Recharts for fitness plots
- `CodeViewer` - Syntax-highlighted code display

**State Management (Zustand)**
```typescript
interface Store {
  projects: Project[]
  agents: Agent[]
  theme: 'light' | 'dark'
  settings: UserSettings
  activeProjectId: string | null
  updateProject(id: string, updates: Partial<Project>): void
  // ...
}
```

### 3. API Backend (`apps/api/`)

FastAPI backend for project management and coordination.

**Endpoints**
- `POST /projects` - Create project
- `GET /projects` - List projects
- `GET /projects/:id` - Get project details
- `POST /projects/:id/start` - Start evolution run
- `WebSocket /projects/:id/stream` - Real-time updates

### 4. Shared Packages (`packages/shared/`)

Shared utilities and types across services.

## Evolution Workflow

The complete flow from start to finish:

```
┌─────────────────────────────────────────────────────────────┐
│ 1. INITIALIZATION                                           │
│   • Load target repository                                  │
│   • Create workspace (isolated copy)                        │
│   • Initialize git history                                 │
│   • Get baseline score from evaluator                       │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│ 2. GENERATION LOOP (repeat N times)                         │
│   for each generation:                                      │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│ 3. AGENT CREATION                                           │
│   • Create M agents (cycle through types)                   │
│   • Agent 1: Analyzer                                       │
│   • Agent 2: Refactorer                                     │
│   • Agent 3: Optimizer                                      │
│   • ... up to M agents                                      │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│ 4. AGENT EXECUTION (parallel)                               │
│                                                              │
│   For each agent:                                           │
│   ┌──────────────────────────────────────┐                 │
│   │ Agent Thinking Loop                  │                 │
│   │                                      │                 │
│   │ 1. Analyze codebase                  │                 │
│   │    • Use grep/glob to find files     │                 │
│   │    • Read relevant files             │                 │
│   │    • Identify bottlenecks            │                 │
│   │                                      │                 │
│   │ 2. LLM generates improvement         │                 │
│   │    • Based on analysis               │                 │
│   │    • Creates code changes            │                 │
│   │                                      │                 │
│   │ 3. Apply changes                     │                 │
│   │    • Edit files in workspace         │                 │
│   │    • Verify syntax                   │                 │
│   │                                      │                 │
│   │ 4. Evaluate (call evaluate tool)     │                 │
│   │    • Run benchmarks                  │                 │
│   │    • Get new fitness score           │                 │
│   │                                      │                 │
│   │ 5. Decision                          │                 │
│   │    if score > previous_score:        │                 │
│   │      ✓ Commit to git                 │                 │
│   │    else:                             │                 │
│   │      ✗ Revert changes                │                 │
│   │                                      │                 │
│   │ 6. Iteration                         │                 │
│   │    if iterations < max AND fitness   │                 │
│   │       not converged:                 │                 │
│   │      Go to step 1                    │                 │
│   │    else:                             │                 │
│   │      Agent done                      │                 │
│   └──────────────────────────────────────┘                 │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│ 5. GENERATION COMPLETE                                      │
│   • Collect results from all agents                         │
│   • Update metrics                                          │
│   • Log to database (if enabled)                            │
│   • Check convergence                                       │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ├─ Continue? ─→ Go to step 3
                     │
                     └─ Stop? ─→ Step 6
                     │
┌────────────────────▼────────────────────────────────────────┐
│ 6. RESULTS                                                  │
│   • Export JSON results                                     │
│   • Create summary report                                   │
│   • Repository ready with improvements                      │
└─────────────────────────────────────────────────────────────┘
```

## Agent Architecture

### Agent State Machine

```
START
  │
  ├─→ [ANALYZING] ─→ Analyze codebase, identify opportunities
  │       │
  │       ▼
  │   [IMPROVING] ─→ Generate and apply improvements
  │       │
  │       ▼
  │   [EVALUATING] ─→ Run benchmarks
  │       │
  │       ├─ Improved? ─→ [COMMITTING] ─→ Commit to git
  │       │                   │
  │       │                   └──→ [COMPLETED]
  │       │
  │       └─ Not improved? ─→ [REVERTING] ─→ Undo changes
  │                               │
  │                               └──→ [ANALYZING] (if iterations < max)
  │                                        │
  │                                        └──→ [COMPLETED]
  │
  └─→ [ERROR] ─→ Log error, cleanup
        │
        └──→ [COMPLETED]
```

### Agent Types

Each agent specializes in a specific improvement category:

**Analyzer**
- Identifies performance bottlenecks
- Finds inefficient algorithms
- Detects code smells
- Suggests refactoring opportunities

**Refactorer**
- Restructures code for clarity
- Reduces complexity
- Consolidates duplication
- Improves modularity

**Optimizer**
- Fine-tunes parameters
- Caches computed values
- Vectorizes operations
- Applies domain-specific optimizations

**Feature Engineer**
- Adds caching layers
- Implements parallelization
- Introduces data structure improvements
- Adds algorithmic optimizations

**General**
- All-purpose improvements
- Multi-dimensional optimization

## Data Models

### Project Model

```typescript
interface Project {
  id: string
  name: string
  description: string
  repositoryPath: string
  evaluatorPath: string
  status: 'idle' | 'running' | 'completed' | 'failed'

  // Evolution metrics
  generation: number
  baselineFitness: number
  currentFitness: number
  maxFitness: number
  improvementPercent: number

  // Agent state
  totalAgents: number
  activeAgents: number
  successfulMutations: number
  totalMutations: number

  // Cost tracking
  totalCost: number
  costCurrency: 'USD'

  // Metadata
  createdAt: Date
  updatedAt: Date
  completedAt?: Date
}
```

### EvolutionNode Model

```typescript
interface EvolutionNode {
  id: string
  projectId: string

  // Position in tree
  generation: number
  parentId?: string
  childrenIds: string[]

  // Mutation details
  agentType: string
  agentId: string
  description: string

  // Fitness metrics
  fitnessBefore: number
  fitnessAfter: number
  fitnessImprovement: number

  // Git tracking
  commitHash: string
  commitMessage: string

  // Files changed
  filesModified: string[]
  insertions: number
  deletions: number

  // Metadata
  timestamp: Date
  duration_ms: number
  success: boolean
}
```

### Agent State

```python
@dataclass
class AgentState:
    """LangGraph agent execution state."""

    # Identification
    agent_id: str
    agent_type: str
    generation: int

    # Code analysis
    files_analyzed: list[str]
    code_context: str
    bottlenecks: list[str]
    improvement_ideas: list[str]

    # Execution tracking
    iteration: int
    max_iterations: int
    messages: list[dict]

    # Metrics
    fitness_history: list[float]
    current_fitness: float
    best_fitness: float

    # Status
    status: str
    last_error: str | None
    tool_calls: int
```

## Tool System

### Tool Interface

```python
class Tool(BaseModel):
    name: str
    description: str
    parameters: dict

    async def execute(self, **kwargs) -> Any:
        """Execute the tool."""
        pass
```

### Available Tools

| Tool | Purpose | Restrictions |
|------|---------|--------------|
| `read_file` | Read code | None |
| `write_file` | Create files | Can't write outside workspace |
| `edit_file` | Modify code | Can't overwrite blindly |
| `multi_edit` | Atomic edits | Atomic guarantee |
| `grep` | Search code | Regex only |
| `glob_search` | Find files | Pattern matching |
| `list_dir` | Browse structure | Read-only |
| `evaluate` | Run benchmarks | Restricted to evaluator |

### Tool Execution Flow

```python
# Agent generates tool call
tool_call = {
    "name": "edit_file",
    "parameters": {
        "file": "src/main.py",
        "old_text": "for i in range(len(arr)):",
        "new_text": "for i, val in enumerate(arr):"
    }
}

# Tool manager executes
result = await tool_manager.execute(tool_call)

# Agent receives result
result = {
    "success": True,
    "message": "File edited successfully",
    "new_content": "..."
}
```

## State Management

### Frontend State (Zustand)

```typescript
// Store structure
const useStore = create<AppStore>((set, get) => ({
  // Projects
  projects: [],
  setProjects: (projects) => set({ projects }),
  updateProject: (id, updates) => {
    set((state) => ({
      projects: state.projects.map((p) =>
        p.id === id ? { ...p, ...updates } : p
      ),
    }))
  },

  // UI State
  theme: 'light',
  toggleTheme: () => set((s) => ({ theme: s.theme === 'light' ? 'dark' : 'light' })),

  sidebarOpen: true,
  toggleSidebar: () => set((s) => ({ sidebarOpen: !s.sidebarOpen })),

  // Settings
  settings: defaultSettings,
  updateSettings: (updates) =>
    set((s) => ({ settings: { ...s.settings, ...updates } })),
}))
```

### Backend State (Database)

**PostgreSQL Tables:**
- `projects` - Project metadata
- `evolution_nodes` - Mutation history
- `agents` - Agent execution records
- `benchmarks` - Evaluation results
- `costs` - API usage tracking

**Redis Keys:**
- `evolution:{project_id}:state` - Current execution state
- `evolution:{project_id}:queue` - Agent task queue
- `agent:{agent_id}:status` - Agent status updates

## Performance Considerations

### Parallelization

- Agents run in parallel using Python `asyncio`
- Each agent gets isolated workspace (prevents conflicts)
- Git prevents direct conflicts (agents commit sequentially)
- Max parallel: configurable, default 4

### Optimization Strategies

1. **Caching** - File contents cached in agent state
2. **Filtering** - Agents prioritize relevant files
3. **Timeout** - Evaluator timeouts prevent hangs
4. **Incremental** - Changes build on previous improvements

### Scalability

- **Horizontal**: Deploy multiple workers via Celery
- **Vertical**: Increase parallel workers per instance
- **Network**: API backend coordinates across workers
- **Database**: PostgreSQL for result persistence

## Security Considerations

### Sandboxing

- Each agent gets isolated workspace copy
- No direct filesystem access outside workspace
- Tool restrictions prevent arbitrary command execution
- Evaluator restricted to evaluation script

### API Key Protection

- Keys loaded from environment variables
- Not logged or exposed in messages
- Rate limiting on API calls
- Cost tracking to prevent abuse

## Integration Points

### External LLMs

- **Anthropic**: Direct API calls to Claude
- **Google**: REST API to Gemini
- **OpenAI**: REST API to GPT-4

### Version Control

- **Git**: Full integration for versioning
- Commits tracking all improvements
- Revert capability for rollback

### Monitoring

- Logs to filesystem and/or cloud
- Metrics exported to Prometheus
- Error tracking for debugging
