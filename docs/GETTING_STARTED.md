# Getting Started with Optifiner

This guide will walk you through setting up Optifiner and running your first code evolution experiment.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Installation](#installation)
3. [Configuration](#configuration)
4. [Creating Your First Evaluator](#creating-your-first-evaluator)
5. [Running Your First Evolution](#running-your-first-evolution)
6. [Using the Web Dashboard](#using-the-web-dashboard)
7. [Troubleshooting](#troubleshooting)

## Prerequisites

Ensure you have the following installed:

- **Python 3.10+** - For the evolution worker
- **Node.js 18+** - For the web dashboard
- **Git** - For version control
- **Docker** (optional) - For containerized deployment
- **API Key** - At least one from:
  - Anthropic (Claude)
  - Google (Gemini)
  - OpenAI (GPT)

### Check Your Installation

```bash
python --version          # Should be 3.10+
node --version           # Should be 18+
git --version            # Any recent version
```

## Installation

### Option 1: Local Development Setup

```bash
# 1. Clone the repository
git clone https://github.com/yourusername/optifiner.git
cd optifiner

# 2. Install Python dependencies for worker
cd services/worker
pip install -r requirements.txt

# 3. Install Node dependencies for web UI
cd ../../apps/web
npm install

# 4. Back to root for full project
cd ../..
```

### Option 2: Docker Setup

```bash
# Build and run everything with Docker Compose
docker-compose up --build

# Services will be available at:
# - Web UI: http://localhost:3000
# - API: http://localhost:8000
# - Redis: localhost:6379
# - PostgreSQL: localhost:5432
```

## Configuration

### Set Environment Variables

Create a `.env` file in the root directory:

```bash
# LLM Configuration
MODEL_PROVIDER=google              # Options: google, anthropic, openai
MODEL_NAME=gemini-2.5-flash        # Model identifier
GOOGLE_API_KEY=your-api-key-here   # If using Google
ANTHROPIC_API_KEY=your-key-here    # If using Anthropic
OPENAI_API_KEY=your-key-here       # If using OpenAI

# Evolution Parameters
AGENTS=10                          # Number of parallel agents
GENERATIONS=3                      # Number of evolution generations
MAX_ITERATIONS=15                  # Max LLM tool calls per agent
PARALLEL=4                         # Parallel execution workers

# Workspace
WORKSPACE_ROOT=/tmp/optifiner      # Where to create isolated workspaces

# Optional: Database (for full stack)
DATABASE_URL=postgresql://user:password@localhost/optifiner
REDIS_URL=redis://localhost:6379
```

### Verify Configuration

```bash
cd services/worker
python -c "from config import get_model_config; print(get_model_config())"
```

## Creating Your First Evaluator

An evaluator is a script that benchmarks your code and returns a numeric score. Higher scores indicate better performance.

### Example 1: Performance Benchmark

```python
# snake_game/evaluate.py
import subprocess
import json
import time

def evaluate():
    """Benchmark the snake game AI."""
    try:
        start = time.time()
        result = subprocess.run(
            ['python', 'game.py', '--headless', '--games', '10'],
            capture_output=True,
            timeout=30,
            text=True
        )
        elapsed = time.time() - start

        if result.returncode != 0:
            return 0.0

        # Parse game results
        output = json.loads(result.stdout)
        avg_score = output['average_score']

        # Score: higher average, faster execution
        return (avg_score / 1000) * (30 / elapsed)

    except Exception as e:
        print(f"Evaluation error: {e}")
        return 0.0

if __name__ == '__main__':
    score = evaluate()
    print(f"{score:.2f}")
```

### Example 2: Algorithm Optimization

```python
# job_shop/evaluate.py
import subprocess
import time

def evaluate():
    """Benchmark job shop scheduler."""
    try:
        start = time.time()
        result = subprocess.run(
            ['python', 'scheduler.py'],
            capture_output=True,
            timeout=60,
            text=True
        )
        elapsed = time.time() - start

        if result.returncode != 0:
            return 0.0

        # Parse makespan (lower is better)
        makespan = float(result.stdout.strip())

        # Invert: lower makespan = higher score
        return 1000 / makespan

    except Exception as e:
        print(f"Evaluation error: {e}")
        return 0.0

if __name__ == '__main__':
    score = evaluate()
    print(f"{score:.2f}")
```

### Requirements for Evaluators

Your evaluator script must:

1. **Accept no command-line arguments** - It receives config via environment variables
2. **Return quickly** - Typical evaluators run in 5-60 seconds
3. **Be deterministic or stable** - Same input should produce similar scores
4. **Print only the score** - Output should be a single number (float or int)
5. **Handle errors gracefully** - Return 0.0 on failures
6. **Be reproducible** - Results should be repeatable

## Running Your First Evolution

### Step 1: Prepare Your Repository

Ensure your target repository:

```
my_project/
├── src/
│   ├── main.py
│   ├── utils.py
│   └── ...
├── evaluate.py          # ← Your benchmark script
└── .git/                # ← Must be a git repo
```

```bash
cd my_project
git init
git add .
git commit -m "Initial commit"
```

### Step 2: Run Evolution

```bash
cd optifiner/services/worker

# Basic: Single generation, 5 agents
python cli.py /path/to/my_project \
  --evaluator /path/to/my_project/evaluate.py

# Full: Multiple generations, detailed config
python cli.py /path/to/my_project \
  --evaluator /path/to/my_project/evaluate.py \
  --agents 10 \
  --generations 3 \
  --parallel 4 \
  --max-iterations 15 \
  --model-provider google \
  --model-name gemini-2.5-flash \
  --output results.json \
  --verbose
```

### Step 3: Monitor Progress

```bash
# In another terminal, watch git commits
cd /path/to/my_project
git log --oneline -n 20

# View detailed results
cat results.json | jq '.'
```

### Command-Line Options

| Option | Default | Description |
|--------|---------|-------------|
| `--agents` | 10 | Number of parallel agents |
| `--generations` | 3 | Number of evolution generations |
| `--parallel` | 4 | Parallel execution workers |
| `--max-iterations` | 15 | Max LLM tool calls per agent |
| `--task` | Auto-detected | Description of improvement task |
| `--model-provider` | google | LLM provider (google, anthropic, openai) |
| `--model-name` | - | Model identifier |
| `--output` | Optional | JSON file for results |
| `--verbose` | False | Enable debug output |

## Using the Web Dashboard

### Start the Dashboard

```bash
cd apps/web
npm run dev
```

Open http://localhost:5173 in your browser.

### Dashboard Features

#### Home/Dashboard
- Overview of all projects
- Current fitness scores
- Agent activity
- Cost tracking

#### Projects
- Create new evolution runs
- View project history
- Configure evolution parameters
- Manage benchmark settings

#### Evolution Monitor
- Real-time agent activity
- Generation progress
- Fitness curve chart
- Code mutation details
- Git commit visualization

#### Analytics
- Historical metrics
- Convergence analysis
- Cost vs performance trade-offs
- Agent performance statistics

#### History
- Complete evolution timeline
- Revert to previous states
- Export results

#### Settings
- Model configuration
- Agent pool settings
- Workspace configuration
- Theme (light/dark)

## Interpreting Results

### Result JSON Structure

```json
{
  "repository": "/path/to/repo",
  "baseline_score": 42.5,
  "final_score": 56.3,
  "improvement": 32.5,
  "generations": 3,
  "total_agents": 30,
  "successful_mutations": 8,
  "total_mutations": 30,
  "success_rate": 0.267,
  "total_cost": 12.50,
  "duration_seconds": 1234,
  "commits": [
    {
      "hash": "abc123...",
      "agent_type": "optimizer",
      "description": "Optimized sorting algorithm",
      "score_before": 42.5,
      "score_after": 45.2,
      "improvement": 6.4
    }
  ]
}
```

### Success Metrics

- **Improvement %**: `(final_score - baseline_score) / baseline_score * 100`
- **Success Rate**: `successful_mutations / total_mutations`
- **Cost Efficiency**: `improvement / total_cost`

## Troubleshooting

### Common Issues

#### "API key not found"
```bash
export GOOGLE_API_KEY="your-api-key"
# Or in .env file
echo "GOOGLE_API_KEY=your-key" >> .env
```

#### "Evaluator timeout exceeded"
Your evaluator is taking too long. Increase timeout or optimize it:

```bash
# In cli.py, modify timeout
timeout=120  # Increase from 60
```

#### "Workspace already exists"
Remove the old workspace:

```bash
rm -rf /tmp/optifiner-workspace
```

#### "Git merge conflicts"
Optifiner will skip mutations that cause conflicts. Ensure your evaluator is deterministic.

#### "Low success rate (< 10%)"
- Evaluator may be too strict or noisy
- Improve evaluator stability
- Increase `--max-iterations` for more exploration
- Add more context in `--task` description

### Debug Mode

Enable verbose output:

```bash
python cli.py /path/to/repo \
  --evaluator /path/to/evaluate.py \
  --verbose
```

View detailed agent reasoning:

```bash
tail -f .optifiner/logs/agent_*.log
```

## Next Steps

- Read [Architecture](ARCHITECTURE.md) for system design details
- Learn about [Agent Types](AGENT_TYPES.md)
- Explore [Examples](EXAMPLES.md) with real projects
- Set up [Production Deployment](DEPLOYMENT.md)

## Support

- Check [troubleshooting](#troubleshooting) section above
- Review [FAQ](#troubleshooting)
- Open an issue on GitHub
- Join discussions in GitHub Discussions
