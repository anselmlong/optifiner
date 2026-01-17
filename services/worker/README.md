# Optifiner Worker

LangGraph-based agent service for the Self Evolving Code Framework. Workers are responsible for analyzing, refactoring, and optimizing code in the target codebase.

## Architecture

```
┌─────────────────────────────────────────────────┐
│              Worker Container                    │
│                                                  │
│  ┌──────────────────────────────────────────┐  │
│  │           LangGraph Agent                 │  │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  │  │
│  │  │Analyzer │  │Refactor │  │Optimizer│  │  │
│  │  └────┬────┘  └────┬────┘  └────┬────┘  │  │
│  │       │            │            │        │  │
│  │       └────────────┼────────────┘        │  │
│  │                    ▼                     │  │
│  │              Tool Layer                  │  │
│  │  ┌────┬────┬────┬────┬────┬────┬────┐  │  │
│  │  │Read│Edit│Grep│Glob│ LS │Bash│ Py │  │  │
│  │  └────┴────┴────┴────┴────┴────┴────┘  │  │
│  └───────────────────┬──────────────────────┘  │
│                      ▼                         │
│              /app (target codebase)            │
└─────────────────────────────────────────────────┘
```

## Agent Types

| Type | Purpose | Capabilities |
|------|---------|--------------|
| **Analyzer** | Understand codebase, identify opportunities | Profile performance, detect bottlenecks, suggest improvements |
| **Refactoring** | Improve code quality | Simplify functions, remove duplication, improve algorithms |
| **Feature** | Add new capabilities | Caching, parallelization, heuristics, optimizations |
| **Optimizer** | Fine-tune performance | Parameter tuning, data structure optimization, micro-optimizations |

## Tools

All tools operate within the `/app` workspace directory:

| Tool | Description |
|------|-------------|
| `read_tool` | Read file contents with line numbers |
| `write_tool` | Write/create files |
| `edit_tool` | Make targeted string replacements |
| `multi_edit_tool` | Multiple edits in one atomic operation |
| `glob_tool` | Find files by pattern (e.g., `**/*.py`) |
| `grep_tool` | Search file contents with regex |
| `ls_tool` | List directory contents |
| `bash_tool` | Execute shell commands |
| `python_tool` | Execute Python code directly |

## Configuration

Environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `OPTIFINER_ANTHROPIC_API_KEY` | Anthropic API key | - |
| `OPTIFINER_GOOGLE_API_KEY` | Google API key | - |
| `OPTIFINER_DEFAULT_MODEL` | Default LLM model | `claude-sonnet-4-20250514` |
| `OPTIFINER_WORKSPACE_PATH` | Target codebase path | `/app` |
| `OPTIFINER_REDIS_URL` | Redis connection URL | `redis://redis:6379/0` |
| `OPTIFINER_COMMAND_TIMEOUT` | Command timeout (seconds) | `30` |
| `OPTIFINER_MAX_FILE_LINES` | Max lines to read | `2000` |

## Usage

### Running with Docker

```bash
# Build the worker image
docker build -t optifiner-worker -f infra/docker/Dockerfile.worker .

# Run with a target codebase
docker run -v /path/to/codebase:/app \
  -e OPTIFINER_ANTHROPIC_API_KEY=your-key \
  optifiner-worker
```

### Running with Docker Compose

```bash
cd infra/compose
docker-compose up worker
```

### Local Development

```bash
cd services/worker
pip install -e ".[dev]"

# Set environment variables
export OPTIFINER_ANTHROPIC_API_KEY=your-key
export OPTIFINER_WORKSPACE_PATH=/path/to/test/codebase

# Run the worker
python -m optifiner_worker.worker
```

## API

### Creating and Running an Agent

```python
from optifiner_worker.agents import AgentType, create_agent
from optifiner_worker.agents.base import run_agent

# Run an analyzer agent
result = await run_agent(
    agent_type=AgentType.ANALYZER,
    task="Analyze the codebase and identify performance bottlenecks",
    model="claude-sonnet-4-20250514",
    max_iterations=20,
)

print(result["result"])
```

### Evolution Workflows

```python
from optifiner_worker.agents.evolution import (
    run_analysis_agent,
    run_improvement_agent,
)
from optifiner_worker.agents import AgentType

# Step 1: Analyze the codebase
analysis = await run_analysis_agent(
    metrics="Execution time, memory usage",
    baseline="Current: 5.2s avg, 150MB peak",
)

# Step 2: Run improvement agent
improvement = await run_improvement_agent(
    agent_type=AgentType.OPTIMIZER,
    metrics="Execution time, memory usage",
    baseline="Current: 5.2s avg, 150MB peak",
    analysis=analysis["result"],
)
```

## Testing

```bash
cd services/worker
pytest tests/
```

## File Structure

```
services/worker/
├── pyproject.toml
├── README.md
└── src/optifiner_worker/
    ├── __init__.py
    ├── config.py          # Settings and configuration
    ├── worker.py          # Main worker entry point
    ├── agents/
    │   ├── __init__.py
    │   ├── base.py        # LangGraph agent creation
    │   ├── types.py       # Agent types and prompts
    │   └── evolution.py   # Evolution-specific workflows
    └── tools/
        ├── __init__.py
        ├── read.py        # File reading
        ├── write.py       # File writing
        ├── edit.py        # String replacement
        ├── multi_edit.py  # Multiple edits
        ├── glob.py        # File pattern matching
        ├── grep.py        # Content search
        ├── ls.py          # Directory listing
        ├── bash.py        # Shell commands
        └── python.py      # Python execution
```
