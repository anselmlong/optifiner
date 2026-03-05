# Snake AI Example

Optifiner evolving a Snake game AI from random moves to intelligent pathfinding.

## What it optimizes

`snake_ai.py` starts as an intentionally bad AI — it uses BFS to find food but with no survival strategy. Agents are tasked with improving the average score over 20 games on a 20×20 grid.

**Metric:** Average score per game (higher is better). Score = food eaten × 10.

## Run it

```bash
cd services/worker

# Baseline (see what the unmodified AI scores)
python3 -c "
import sys; sys.path.insert(0, '../../examples/snake_game')
from snake_ai import benchmark
import random; random.seed(42)
print('Baseline:', benchmark(20, 20))
"

# Evolve it
python cli.py ../../examples/snake_game \
  --evaluator ../../examples/snake_game/evaluate.py \
  --agents 5 \
  --generations 3 \
  --model-provider google \
  --model-name gemini-2.5-flash
```

## Expected progression

| Generation | Strategy | Score |
|-----------|----------|-------|
| Baseline | BFS to food, random fallback | ~30–50 |
| Gen 1 | Improved pathfinding or survival | ~60–100 |
| Gen 2+ | Space-filling or lookahead heuristics | ~100+ |

Results vary by model and number of agents.

## Files

- `snake_ai.py` — the Snake game + AI (this is what gets evolved)
- `evaluate.py` — benchmark script (runs 20 games, outputs JSON score)
