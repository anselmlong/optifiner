# Job Shop Scheduling Example

Optifiner evolving a Job Shop Scheduling Problem (JSSP) solver.

## What it optimizes

Job Shop Scheduling is a classic NP-hard combinatorial optimization problem. Given a set of jobs, each consisting of operations that must be executed on specific machines in order, find a schedule that minimizes the total completion time (makespan).

`evaluate.py` contains both the scheduler to be evolved and the evaluation harness. It tests against 15 instances of varying difficulty:
- **Easy** (3 instances): 5 jobs × 5 machines
- **Medium** (4 instances): 8–10 jobs × 5–8 machines
- **Hard** (4 instances): 15–20 jobs × 10 machines
- **Very Hard** (4 instances): 30–50 jobs × 15 machines

**Metric:** Average score across all instances (higher is better). Score for each instance is `(lower_bound / makespan)²` — closer to optimal makespan = higher score.

## Run it

```bash
cd services/worker

python cli.py ../../examples/job_shop \
  --evaluator ../../examples/job_shop/evaluate.py \
  --agents 5 \
  --generations 3 \
  --model-provider google \
  --model-name gemini-2.5-flash
```

## Files

- `evaluate.py` — contains the scheduler implementation AND the benchmark harness (both get evolved)
