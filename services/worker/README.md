# Evolution Worker

LangGraph-based agent workers for the Self Evolving Code Framework.

## Quick Start

```bash
# Install the package
cd services/worker
pip install -e .

# Run evolution on a target codebase
evolution-cli /path/to/repo --evaluator /path/to/evaluate.py --agents 10
```

## CLI Usage

The `evolution-cli` command runs multiple AI agents on a codebase, each trying to improve it based on a benchmark score.

```bash
evolution-cli REPOSITORY [OPTIONS]
```

### Required Arguments

- `REPOSITORY`: Path to the target repository to evolve

### Options

| Option | Short | Default | Description |
|--------|-------|---------|-------------|
| `--evaluator` | `-e` | (required) | Path to evaluator script |
| `--agents` | `-n` | 10 | Number of agents to run |
| `--parallel` | `-p` | 1 | Parallel agent count |
| `--generations` | `-g` | 1 | Evolution generations |
| `--max-iterations` | `-i` | 15 | Max tool calls per agent |
| `--task` | `-t` | "Improve..." | Task description |
| `--model-provider` | | google | LLM provider |
| `--model-name` | | gemini-3-flash-preview | Model name |
| `--output` | `-o` | | JSON output file |

### Example

```bash
# Run 10 agents on a snake game AI
evolution-cli ./examples/snake_game \
    --evaluator ./examples/snake_game/evaluate.py \
    --agents 10 \
    --task "Improve the snake AI to get higher scores"

# Run with parallel agents
evolution-cli ./my-project \
    --evaluator ./benchmark.py \
    --agents 20 \
    --parallel 4 \
    --generations 3

# Use different model (Claude Opus 4, Sonnet 4.5, or Haiku 4)
evolution-cli ./project \
    --evaluator ./eval.py \
    --model-provider anthropic \
    --model-name claude-sonnet-4-5-20250514  # or claude-opus-4-20250514
```

## Evaluator Script

The evaluator script should output a score. It can be a Python, Bash, or Node.js script.

### JSON Format (Recommended)

```python
#!/usr/bin/env python3
import json

def evaluate():
    # Run your benchmark
    score = run_benchmark()
    
    print(json.dumps({
        "score": score,
        "metrics": {"fps": 60, "memory": 128},
        "passed": True
    }))

if __name__ == "__main__":
    evaluate()
```

### Simple Format

The evaluator can also just print a number:

```bash
#!/bin/bash
python benchmark.py | grep "Score:" | awk '{print $2}'
```

## Agent Types

The CLI cycles through different agent types:

| Type | Specialization |
|------|----------------|
| `optimizer` | Fine-tuning, parameter adjustment |
| `refactoring` | Code restructuring, algorithm improvement |
| `feature` | Adding caching, parallelization |
| `analyzer` | Understanding code, finding bottlenecks |
| `general` | All-purpose improvements |

## How It Works

1. **Baseline**: Get initial score from evaluator
2. **Agent Run**: Each agent:
   - Explores the codebase
   - Makes improvements
   - Uses `evaluate` tool to test changes
   - If score improved, changes are kept
3. **Git Integration**: Successful improvements are committed
4. **Evolution**: Process repeats for multiple generations

## Available Tools

Agents have access to:

- `read_file` - Read files
- `write_file` - Write files  
- `edit_file` - Search & replace
- `multi_edit` - Multiple edits atomically
- `grep` - Search with regex
- `glob_search` - Find files by pattern
- `list_dir` - List directories
- `run_python` - Execute Python code
- `run_bash` - Execute shell commands
- `evaluate` - Run the benchmark

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | | Anthropic API key |
| `GOOGLE_API_KEY` | | Google AI API key |
| `OPENAI_API_KEY` | | OpenAI API key |
| `WORKSPACE_ROOT` | /app | Workspace path |

## Example: Snake Game

See `examples/snake_game/` for a complete example:

```bash
# The snake AI starts with random moves (score ~5-10)
# Evolution agents improve it to use pathfinding (score ~50-100+)

evolution-cli ./examples/snake_game \
    --evaluator ./examples/snake_game/evaluate.py \
    --agents 5 \
    --task "Improve the SnakeAI class to get higher scores. The AI currently makes mostly random moves."
```

## Output

The CLI provides:
- Real-time progress display
- Per-agent success/failure status
- Generation summaries
- Final improvement statistics
- Optional JSON output file
