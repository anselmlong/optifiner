# Contributing to Optifiner

Thanks for your interest in contributing! Here's how to get involved.

## Ways to Contribute

- **Bug reports** — open a GitHub issue with steps to reproduce
- **New examples** — add a project to `examples/` showing Optifiner improving real code
- **Agent improvements** — better prompts, new agent types, smarter evaluation
- **Documentation** — fix inaccuracies, add tutorials, improve examples
- **Bug fixes & features** — see open issues for ideas

## Development Setup

```bash
git clone https://github.com/anselmlong/optifiner.git
cd optifiner

# Worker (core CLI)
cd services/worker
pip install -e ".[dev]"

# Web UI (optional)
cd ../../apps/web
npm install
```

## Project Structure

```
optifiner/
├── services/worker/    # Core CLI + LangGraph evolution engine  ← start here
├── apps/web/           # React dashboard (connects to API)
├── apps/api/           # FastAPI backend (optional full-stack)
├── examples/           # Example projects for benchmarking
└── docs/               # Documentation
```

## Adding a New Example

The best way to contribute is a new example showing Optifiner improving a real-world codebase.

1. Create a folder under `examples/your-example/`
2. Add the code to be optimized
3. Add an `optifiner_benchmark.py` (or `evaluate.py`) that outputs JSON:

```python
import json

def evaluate():
    # run your code, measure something
    score = ...
    return score

if __name__ == "__main__":
    score = evaluate()
    print(json.dumps({
        "score": score,
        "metric_name": "your_metric",   # e.g. "FPS", "throughput", "latency_ms"
        "higher_is_better": True,        # False for latency/cycles
    }))
```

4. Add a `README.md` explaining:
   - What the code does
   - What metric is being optimized
   - Baseline score vs. evolved score (if you have results)

5. Open a PR — include your before/after results if possible.

## Pull Request Guidelines

- Keep PRs focused on one thing
- Add or update tests if you change core logic
- Run `ruff check .` in `services/worker/` before submitting
- PRs that include before/after benchmark results are much easier to review

## Running Tests

```bash
cd services/worker
pytest tests/
```

## Code Style

We use `ruff` for Python linting:
```bash
ruff check .
ruff format .
```

## Questions?

Open a [GitHub Discussion](https://github.com/anselmlong/optifiner/discussions) for anything that isn't a bug or PR.
