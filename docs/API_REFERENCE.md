# API Reference

This document provides a complete reference for Optifiner's CLI, REST API, and configuration options.

## Table of Contents

1. [CLI Commands](#cli-commands)
2. [REST API](#rest-api)
3. [Configuration](#configuration)
4. [Environment Variables](#environment-variables)
5. [Error Codes](#error-codes)

## CLI Commands

### Main Command: Evolution Run

```bash
python cli.py <repository> --evaluator <path>
```

Runs a complete evolution experiment on a repository.

#### Arguments

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `repository` | string | Yes | Path to target repository (must be a git repo) |

#### Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--evaluator` | string | None | Path to evaluator script (Python file) |
| `--agents` | int | 10 | Number of parallel agents |
| `--generations` | int | 3 | Number of evolution generations |
| `--parallel` | int | 4 | Parallel execution workers |
| `--max-iterations` | int | 15 | Max LLM tool calls per agent |
| `--model-provider` | string | google | LLM provider (google, anthropic, openai) |
| `--model-name` | string | gemini-2.5-flash | Model identifier |
| `--task` | string | Auto-detected | Task description for agents |
| `--output` | string | None | JSON file path for results |
| `--verbose` | flag | False | Enable debug output |
| `--timeout` | int | 300 | Evaluator timeout in seconds |
| `--seed` | int | None | Random seed for reproducibility |
| `--temperature` | float | 0.0 | LLM temperature (0=deterministic, 1=creative) |
| `--max-cost` | float | None | Stop if cost exceeds this (USD) |

### Examples

#### Basic Run
```bash
python cli.py ~/my_project --evaluator ~/my_project/evaluate.py
```

#### Tuned Parameters
```bash
python cli.py ~/my_project \
  --evaluator ~/my_project/evaluate.py \
  --agents 20 \
  --generations 5 \
  --parallel 8 \
  --model-provider anthropic \
  --model-name claude-sonnet-4-20250514
```

#### Cost-Limited Run
```bash
python cli.py ~/my_project \
  --evaluator ~/my_project/evaluate.py \
  --max-cost 10.0 \
  --output results.json
```

#### Reproducible Run
```bash
python cli.py ~/my_project \
  --evaluator ~/my_project/evaluate.py \
  --seed 42 \
  --temperature 0.0
```

## REST API

The FastAPI backend provides the following endpoints (future implementation).

### Project Management

#### Create Project
```http
POST /api/projects
Content-Type: application/json

{
  "name": "My Project",
  "description": "Optimize my game AI",
  "repositoryPath": "/path/to/repo",
  "evaluatorPath": "/path/to/evaluate.py"
}
```

**Response (201 Created)**:
```json
{
  "id": "proj_abc123",
  "name": "My Project",
  "status": "idle",
  "createdAt": "2025-01-17T10:00:00Z"
}
```

#### List Projects
```http
GET /api/projects
```

**Response (200 OK)**:
```json
{
  "projects": [
    {
      "id": "proj_abc123",
      "name": "My Project",
      "status": "idle",
      "currentFitness": 42.5,
      "createdAt": "2025-01-17T10:00:00Z"
    }
  ]
}
```

#### Get Project Details
```http
GET /api/projects/:id
```

**Response (200 OK)**:
```json
{
  "id": "proj_abc123",
  "name": "My Project",
  "status": "running",
  "generation": 2,
  "baselineFitness": 42.5,
  "currentFitness": 48.2,
  "improvementPercent": 13.4,
  "totalAgents": 20,
  "activeAgents": 3,
  "successfulMutations": 4,
  "totalMutations": 20,
  "totalCost": 2.50
}
```

### Evolution Control

#### Start Evolution Run
```http
POST /api/projects/:id/start
Content-Type: application/json

{
  "agents": 10,
  "generations": 3,
  "modelProvider": "google",
  "modelName": "gemini-2.5-flash"
}
```

**Response (202 Accepted)**:
```json
{
  "runId": "run_xyz789",
  "status": "queued"
}
```

#### Stop Evolution Run
```http
POST /api/projects/:id/stop
```

**Response (200 OK)**:
```json
{
  "status": "stopped",
  "message": "Evolution run stopped"
}
```

### Results & Analytics

#### Get Evolution Results
```http
GET /api/projects/:id/results
```

**Response (200 OK)**:
```json
{
  "baselineScore": 42.5,
  "finalScore": 56.3,
  "improvement": 32.5,
  "generations": 3,
  "totalAgents": 30,
  "successfulMutations": 8,
  "totalMutations": 30,
  "successRate": 0.267,
  "totalCost": 12.50,
  "duration": 1234,
  "commits": [
    {
      "hash": "abc123...",
      "agentType": "optimizer",
      "description": "Optimized sorting algorithm",
      "scoreBefore": 42.5,
      "scoreAfter": 45.2,
      "improvement": 6.4
    }
  ]
}
```

#### Get Evolution Tree
```http
GET /api/projects/:id/tree
```

**Response (200 OK)**:
```json
{
  "nodes": [
    {
      "id": "node_1",
      "generation": 1,
      "agentType": "analyzer",
      "fitness": 45.2,
      "fitnessChange": 2.7,
      "description": "Identified O(n²) sorting",
      "children": ["node_2", "node_3"]
    }
  ],
  "edges": [
    {
      "from": "node_1",
      "to": "node_2"
    }
  ]
}
```

#### Get Metrics Timeline
```http
GET /api/projects/:id/metrics?interval=generation
```

**Response (200 OK)**:
```json
{
  "data": [
    {
      "timestamp": "2025-01-17T10:00:00Z",
      "generation": 1,
      "fitness": 45.2,
      "agents": 10,
      "cost": 2.50
    }
  ]
}
```

### WebSocket Streaming

#### Subscribe to Real-Time Updates
```javascript
const ws = new WebSocket('ws://localhost:8000/api/projects/:id/stream');

ws.onmessage = (event) => {
  const message = JSON.parse(event.data);
  console.log(message);
};
```

**Message Types**:
```json
{
  "type": "agent_status",
  "data": {
    "agentId": "agent_1",
    "status": "analyzing",
    "progress": 0.35
  }
}
```

```json
{
  "type": "fitness_update",
  "data": {
    "fitness": 48.2,
    "improvement": 5.7,
    "timestamp": "2025-01-17T10:05:00Z"
  }
}
```

```json
{
  "type": "generation_complete",
  "data": {
    "generation": 1,
    "successfulMutations": 3,
    "totalMutations": 10
  }
}
```

## Configuration

### Config File Format

Create `.optifiner.yaml` in project root:

```yaml
# Project Configuration
project:
  name: "My Project"
  description: "Optimize my application"

# Evolution Parameters
evolution:
  agents: 10
  generations: 5
  parallel: 4
  maxIterations: 15
  timeout: 300

# Model Configuration
model:
  provider: google
  name: gemini-2.5-flash
  temperature: 0.0

# Agent Configuration
agents:
  types:
    - analyzer
    - refactoring
    - optimizer
    - feature
  enabled:
    analyzer: true
    refactoring: true
    optimizer: true

# Evaluator Configuration
evaluator:
  path: ./evaluate.py
  timeout: 60
  retries: 1

# Workspace Configuration
workspace:
  root: /tmp/optifiner
  cleanup: true

# Logging Configuration
logging:
  level: INFO
  file: .optifiner/logs/evolution.log
```

### Loading Configuration

```python
from config import load_config

config = load_config('.optifiner.yaml')
```

## Environment Variables

### LLM Configuration

```bash
# Google Gemini
export MODEL_PROVIDER=google
export MODEL_NAME=gemini-2.5-flash
export GOOGLE_API_KEY=your-key-here

# Anthropic Claude
export MODEL_PROVIDER=anthropic
export MODEL_NAME=claude-sonnet-4-20250514
export ANTHROPIC_API_KEY=your-key-here

# OpenAI GPT
export MODEL_PROVIDER=openai
export MODEL_NAME=gpt-4o
export OPENAI_API_KEY=your-key-here
```

### Evolution Parameters

```bash
export AGENTS=10                      # Parallel agents
export GENERATIONS=3                  # Evolution generations
export MAX_ITERATIONS=15              # Max LLM iterations per agent
export PARALLEL=4                     # Parallel workers
export EVALUATOR_TIMEOUT=300          # Evaluator timeout (seconds)
export MAX_COST=50.0                  # Stop if cost exceeds (USD)
```

### Workspace Configuration

```bash
export WORKSPACE_ROOT=/tmp/optifiner  # Workspace directory
export WORKSPACE_CLEANUP=1            # Clean up after run
export WORKSPACE_MEMORY_LIMIT=4gb     # Per-workspace memory limit
```

### Logging & Debugging

```bash
export LOG_LEVEL=DEBUG                # Log level (DEBUG, INFO, WARNING)
export LOG_FILE=.optifiner/logs/evolution.log
export VERBOSE=1                      # Verbose output
export SEED=42                        # Reproducible runs
```

### Database (Optional)

```bash
export DATABASE_URL=postgresql://user:password@localhost/optifiner
export REDIS_URL=redis://localhost:6379
export DATABASE_ECHO=0                # SQL query logging
```

## Error Codes

### CLI Errors

| Code | Message | Cause | Solution |
|------|---------|-------|----------|
| 1 | Repository not found | Invalid repository path | Check path exists and is a git repo |
| 2 | Evaluator not found | Invalid evaluator path | Check path exists and is executable |
| 3 | Invalid model provider | Unknown provider name | Use: google, anthropic, openai |
| 4 | API key not set | Missing environment variable | Set MODEL_PROVIDER_API_KEY |
| 5 | Evaluator timeout | Benchmark takes too long | Increase --timeout or optimize evaluator |
| 6 | Evaluator error | Benchmark script crashed | Check evaluator logs |
| 7 | Invalid parameters | Bad CLI arguments | Check help: python cli.py --help |
| 8 | Git error | Git operation failed | Check repository state |

### API Errors

| Code | Message | Cause | Solution |
|------|---------|-------|----------|
| 400 | Bad Request | Invalid request body | Check JSON format |
| 401 | Unauthorized | Missing API key | Provide authentication token |
| 404 | Not Found | Resource doesn't exist | Check resource ID |
| 409 | Conflict | Evolution already running | Stop current run first |
| 429 | Too Many Requests | Rate limit exceeded | Wait and retry |
| 500 | Internal Server Error | Server error | Check server logs |
| 503 | Service Unavailable | Server maintenance | Wait and retry |

## Output Formats

### JSON Results

```json
{
  "repository": "/path/to/repo",
  "baseline_score": 42.5,
  "final_score": 56.3,
  "improvement": 32.5,
  "improvement_percent": 32.5,
  "generations": 3,
  "total_agents": 30,
  "successful_mutations": 8,
  "total_mutations": 30,
  "success_rate": 0.267,
  "total_cost_usd": 12.50,
  "duration_seconds": 1234,
  "agent_metrics": [
    {
      "agent_id": "agent_1",
      "agent_type": "optimizer",
      "generation": 1,
      "mutations_proposed": 3,
      "mutations_successful": 1,
      "success_rate": 0.333,
      "improvements": {
        "min": 1.2,
        "max": 5.7,
        "avg": 3.45
      },
      "tool_calls": {
        "total": 12,
        "read_file": 5,
        "edit_file": 4,
        "evaluate": 2,
        "grep": 1
      },
      "duration_seconds": 45,
      "cost_usd": 0.42
    }
  ],
  "commits": [
    {
      "hash": "abc123def456",
      "agent_id": "agent_1",
      "agent_type": "optimizer",
      "generation": 1,
      "description": "Optimized sorting algorithm with memoization",
      "score_before": 42.5,
      "score_after": 45.2,
      "improvement": 6.4,
      "files_changed": ["src/sort.py"],
      "insertions": 12,
      "deletions": 3,
      "timestamp": "2025-01-17T10:05:00Z"
    }
  ]
}
```

## Rate Limiting

### API Rate Limits

- 100 requests/minute per API key
- 1000 requests/hour per API key
- WebSocket connections: 10 concurrent per key

### LLM API Limits

Varies by provider:
- **Google Gemini**: Check quota at console.cloud.google.com
- **Anthropic Claude**: Check documentation
- **OpenAI GPT**: Check usage at platform.openai.com

## Pagination

### List Endpoints

Use query parameters for pagination:

```http
GET /api/projects?page=1&limit=20
```

Parameters:
- `page`: Page number (1-indexed, default: 1)
- `limit`: Results per page (default: 20, max: 100)

Response:
```json
{
  "data": [...],
  "pagination": {
    "page": 1,
    "limit": 20,
    "total": 45,
    "totalPages": 3
  }
}
```

## Versioning

Current API version: **v1**

Include in requests:
```http
GET /api/v1/projects
```

## Webhooks (Future)

Planned for v2:
```bash
POST /api/webhooks
{
  "url": "https://yourserver.com/webhook",
  "events": ["run_complete", "mutation_successful", "error"]
}
```
