# Optifiner API

REST API for code optimization workflows. This API provides complete feature parity with the CLI (`services/worker/src/worker/cli.py`).

## Quick Start

### 1. Start the API server

```bash
cd apps/api
pip install -r requirements.txt
uvicorn optifiner_api.main:app --reload --host 0.0.0.0 --port 8000
```

### 2. Start an optimization workflow

The API accepts the same options as the CLI. Here's how CLI options map to API parameters:

| CLI Option | API Parameter | Default | Description |
|------------|---------------|---------|-------------|
| `--agents`, `-n` | `agents_per_generation` | 10 | Number of agents per generation |
| `--parallel`, `-p` | `parallel` | 1 | Agents to run in parallel |
| `--generations`, `-g` | `generations` | 1 | Max evolution generations |
| `--max-iterations`, `-i` | `max_iterations_per_agent` | 15 | Max iterations per agent |
| `--task`, `-t` | `user_prompt` | "Improve the code..." | Task description |
| `--min-improvement`, `-m` | `min_improvement_pct` | 6.0 | Min improvement % threshold |
| `--early-stop` | `early_stop` | true | Stop generation on improvement |
| `--verbose`, `-v` | `verbosity` | 1 | Log level (0-3) |
| `--quiet`, `-q` | `verbosity` = 0 | - | Minimal output |
| `--log-dir`, `-l` | `log_dir` | null | Agent logs directory |
| `--build-benchmark`, `-b` | `build_benchmark` | false | Auto-create benchmark |
| `--evaluator`, `-e` | `evaluator_path` | null | Path to evaluator script |

## Usage Examples

### CLI Example

```bash
python3 cli.py -p 5 -g 5 -m 10 \
    ../../examples/volumetric_particle_sim \
    --agents 5 \
    --max-iterations 25 \
    --task "Optimize this particle simulation for maximum FPS performance." \
    -vvv
```

### Equivalent API Request

```bash
curl -X POST http://localhost:8000/api/v1/optimization/start \
  -H "Content-Type: application/json" \
  -d '{
    "repo_url": "https://github.com/YOUR_USER/volumetric_particle_sim",
    "parallel": 5,
    "generations": 5,
    "min_improvement_pct": 10.0,
    "agents_per_generation": 5,
    "max_iterations_per_agent": 25,
    "user_prompt": "Optimize this particle simulation for maximum FPS performance.",
    "verbosity": 3,
    "total_cost_limit": 10.0,
    "models": [{
      "provider": "google",
      "model_name": "gemini-2.0-flash-exp",
      "api_key": "YOUR_GOOGLE_API_KEY"
    }]
  }'
```

### Using httpie

```bash
http POST localhost:8000/api/v1/optimization/start \
  repo_url="https://github.com/YOUR_USER/volumetric_particle_sim" \
  parallel:=5 \
  generations:=5 \
  min_improvement_pct:=10.0 \
  agents_per_generation:=5 \
  max_iterations_per_agent:=25 \
  user_prompt="Optimize this particle simulation for maximum FPS performance." \
  verbosity:=3 \
  total_cost_limit:=10.0 \
  models:='[{"provider": "google", "model_name": "gemini-2.0-flash-exp", "api_key": "YOUR_API_KEY"}]'
```

### Python Example

```python
import requests

response = requests.post(
    "http://localhost:8000/api/v1/optimization/start",
    json={
        "repo_url": "https://github.com/YOUR_USER/volumetric_particle_sim",
        "parallel": 5,
        "generations": 5,
        "min_improvement_pct": 10.0,
        "agents_per_generation": 5,
        "max_iterations_per_agent": 25,
        "user_prompt": "Optimize this particle simulation for maximum FPS performance.",
        "verbosity": 3,
        "total_cost_limit": 10.0,
        "models": [{
            "provider": "google",
            "model_name": "gemini-2.0-flash-exp",
            "api_key": "YOUR_GOOGLE_API_KEY"
        }]
    }
)

result = response.json()
workflow_id = result["workflow_id"]
print(f"Started workflow: {workflow_id}")
print(f"Branch: {result['branch']}")
print(f"Baseline score: {result['baseline_score']}")
```

## API Endpoints

### Start Optimization

```
POST /api/v1/optimization/start
```

**Request Body:**
```json
{
  "repo_url": "https://github.com/owner/repo",
  "branch": "main",
  "total_cost_limit": 10.0,
  "models": [
    {
      "provider": "google",
      "model_name": "gemini-2.0-flash-exp",
      "api_key": "YOUR_API_KEY",
      "instances": 5
    }
  ],
  "user_prompt": "Optimize for performance",
  "agents_per_generation": 10,
  "parallel": 5,
  "generations": 5,
  "max_iterations_per_agent": 15,
  "min_improvement_pct": 6.0,
  "early_stop": true,
  "verbosity": 1
}
```

**Response:**
```json
{
  "success": true,
  "workflow_id": "abc12345-...",
  "baseline_score": 45.2,
  "repo_dir": "volumetric_particle_sim",
  "branch": "optifiner-abc12345",
  "status": "running"
}
```

### Get Workflow Status

```
GET /api/v1/optimization/{workflow_id}/status
```

**Response:**
```json
{
  "workflow_id": "abc12345-...",
  "status": "running",
  "baseline_score": 45.2,
  "current_best_score": 62.8,
  "generation": 3,
  "max_generations": 5,
  "total_improvements": 2,
  "total_attempts": 15,
  "step_count": 2,
  "steps": [
    {
      "step": 0,
      "generation": 0,
      "agent_id": "initial",
      "baseline_score": 45.2,
      "final_score": 45.2,
      "is_initial": true
    },
    {
      "step": 1,
      "generation": 1,
      "agent_id": "abc12345-gen1-optimizer-3",
      "baseline_score": 45.2,
      "final_score": 52.1,
      "improvement_percent": 15.3
    }
  ],
  "improvement": 17.6,
  "improvement_percent": 38.9
}
```

### Pause Workflow

```
POST /api/v1/optimization/{workflow_id}/pause
```

### Resume Workflow

```
POST /api/v1/optimization/{workflow_id}/resume
```

### Stop Workflow

```
POST /api/v1/optimization/{workflow_id}/stop
```

## Git Operations

The API performs all git operations on the user's repository:

1. **Clone**: Clones the specified repository to workspace
2. **Branch**: Creates optimization branch `optifiner-{workflow_id[:8]}`
3. **Commit**: Commits each improvement with message like:
   ```
   Gen 3 | abc12345-gen3-optimizer-2: +15.3% (45.20 → 52.10)
   ```
4. **Push**: Pushes commits to the remote repository

### GitHub App Authentication

For private repositories, configure GitHub App credentials in `.env`:

```bash
GITHUB_APP_ID=123456
GITHUB_APP_PRIVATE_KEY=path/to/private-key.pem
GITHUB_APP_CLIENT_ID=Iv1.abcdef123456
```

## Model Providers

Supported model providers:

| Provider | Environment Variable | Example Models |
|----------|---------------------|----------------|
| Google | `GOOGLE_API_KEY` | `gemini-2.0-flash-exp`, `gemini-1.5-pro` |
| Anthropic | `ANTHROPIC_API_KEY` | `claude-3-sonnet-20240229`, `claude-3-opus-20240229` |
| OpenAI | `OPENAI_API_KEY` | `gpt-4`, `gpt-4-turbo` |

## Verbosity Levels

| Level | CLI | Description |
|-------|-----|-------------|
| 0 | `-q` | Quiet - minimal output |
| 1 | (default) | Normal - progress and results |
| 2 | `-vv` | Verbose - full tool calls |
| 3 | `-vvv` | Debug - everything including prompts |

## Step Snapshots

The API saves step snapshots in the repository, just like the CLI:

```
repo/
├── steps/
│   ├── step_000/           # Initial state
│   │   ├── step_metadata.json
│   │   └── ... (code files)
│   ├── step_001/           # First improvement
│   │   ├── step_metadata.json
│   │   └── ... (code files)
│   └── step_002/           # Second improvement
│       ├── step_metadata.json
│       └── ... (code files)
└── optifiner_benchmark.py  # Benchmark script
```

## Local Testing with Examples

To test with local examples (like the CLI):

1. Push your example to a GitHub repository
2. Use the API to optimize it:

```bash
# First, push volumetric_particle_sim to your GitHub
cd examples/volumetric_particle_sim
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/YOUR_USER/volumetric_particle_sim
git push -u origin main

# Then use the API
curl -X POST http://localhost:8000/api/v1/optimization/start \
  -H "Content-Type: application/json" \
  -d '{
    "repo_url": "https://github.com/YOUR_USER/volumetric_particle_sim",
    "parallel": 5,
    "generations": 5,
    "min_improvement_pct": 10.0,
    "agents_per_generation": 5,
    "max_iterations_per_agent": 25,
    "user_prompt": "Optimize this particle simulation for maximum FPS performance.",
    "verbosity": 3,
    "total_cost_limit": 10.0,
    "models": [{
      "provider": "google",
      "model_name": "gemini-2.0-flash-exp",
      "api_key": "YOUR_API_KEY"
    }]
  }'
```

## Health Check

```bash
curl http://localhost:8000/health
# {"status": "healthy"}
```

## API Documentation

Interactive API documentation is available at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
