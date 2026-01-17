# Examples

Real-world examples demonstrating Optifiner in action.

## Table of Contents

1. [Snake Game AI](#snake-game-ai)
2. [Job Shop Scheduler](#job-shop-scheduler)
3. [Particle Simulation](#particle-simulation)
4. [Your Custom Project](#your-custom-project)

## Snake Game AI

**Goal**: Evolve a better snake game AI strategy

**Project Location**: `examples/snake_game/`

### Project Structure

```
examples/snake_game/
├── main.py              # Main game loop with AI
├── ai.py                # AI decision logic
├── board.py             # Game state
├── evaluate.py          # Benchmark script
└── README.md
```

### The Challenge

The snake game AI uses a simple greedy algorithm:
- Move towards food
- Avoid walls and tail
- Current score: ~50 points average

Goal: Improve to > 150 points using AI-driven optimization

### The Evaluator

```python
# evaluate.py
import subprocess
import json
import time

def evaluate():
    """Run snake AI benchmark."""
    try:
        result = subprocess.run(
            ['python', 'main.py', '--headless', '--games', '20'],
            capture_output=True,
            timeout=120,
            text=True
        )

        if result.returncode != 0:
            print(f"Error: {result.stderr}")
            return 0.0

        output = json.loads(result.stdout)
        avg_score = output['average_score']
        win_rate = output['win_rate']

        # Score: weighted average + win bonus
        return avg_score * (1 + win_rate)

    except Exception as e:
        print(f"Evaluation error: {e}")
        return 0.0

if __name__ == '__main__':
    print(f"{evaluate():.1f}")
```

### Running Evolution

```bash
cd examples/snake_game

# Single generation
python ../../services/worker/cli.py . \
  --evaluator evaluate.py \
  --agents 5 \
  --generations 1 \
  --task "Improve snake AI pathfinding and decision making"

# Multiple generations
python ../../services/worker/cli.py . \
  --evaluator evaluate.py \
  --agents 10 \
  --generations 5 \
  --model-provider google \
  --model-name gemini-2.5-flash \
  --output results.json
```

### Expected Improvements

**Generation 1**:
- Analyzer identifies greedy-only behavior
- Optimizer tunes look-ahead distance
- Score: 55-65 (baseline 50)

**Generation 2-3**:
- Refactorer extracts pathfinding logic
- Feature Engineer adds path caching
- Score: 80-120

**Generation 4-5**:
- General agents find novel strategies
- Multi-feature optimization
- Score: 150+ ✓

### Viewing Results

```bash
# Check improvements
git log --oneline | head -20

# View detailed results
cat results.json | jq '.commits[] | {agent: .agent_type, improvement: .improvement}'

# Analyze success rate
cat results.json | jq '.success_rate'
```

---

## Job Shop Scheduler

**Goal**: Evolve a faster job shop scheduling algorithm

**Project Location**: `examples/job_shop/`

### Project Structure

```
examples/job_shop/
├── scheduler.py         # Main scheduling algorithm
├── problem.py           # Problem definition & benchmarks
├── evaluate.py          # Benchmark script
└── README.md
```

### The Challenge

Job shop scheduling: assign M jobs to N machines minimizing total time (makespan)

Current algorithm: Nearest Neighbor heuristic
- Makespan: ~500 time units
- Runs in O(n log n) time

Goal: Find better heuristic reducing makespan by > 20%

### The Evaluator

```python
# evaluate.py
from scheduler import JobShopScheduler
from problem import get_benchmark_problems
import time

def evaluate():
    """Evaluate scheduler on benchmark problems."""
    try:
        scheduler = JobShopScheduler()
        problems = get_benchmark_problems(num_problems=5)

        total_makespan = 0
        count = 0

        for problem in problems:
            start = time.time()
            schedule = scheduler.solve(problem)
            elapsed = time.time() - start

            makespan = schedule.makespan
            total_makespan += makespan
            count += 1

        avg_makespan = total_makespan / count if count > 0 else float('inf')

        # Score: lower makespan = higher score
        # Normalize to reference (500)
        score = 500 / avg_makespan if avg_makespan > 0 else 0

        return score

    except Exception as e:
        print(f"Evaluation error: {e}")
        return 0.0

if __name__ == '__main__':
    score = evaluate()
    print(f"{score:.2f}")
```

### Running Evolution

```bash
cd examples/job_shop

python ../../services/worker/cli.py . \
  --evaluator evaluate.py \
  --agents 10 \
  --generations 3 \
  --task "Improve job shop scheduling heuristic to reduce makespan"
```

### Expected Improvements

**Initial Score**: ~1.0 (baseline 500 makespan)

**Generation 1**:
- Analyzer finds inefficient ordering
- Optimizer tweaks priority rules
- Score: ~1.05 (475 makespan) ✓

**Generation 2-3**:
- Refactorer consolidates logic
- Feature Engineer adds lookahead
- Score: ~1.2 (420 makespan) ✓✓

---

## Particle Simulation

**Goal**: Optimize particle simulation performance

**Project Location**: `examples/volumetric_particle_sim/`

### Project Structure

```
examples/volumetric_particle_sim/
├── simulation.py        # Core particle simulation
├── renderer.py          # Visualization (optional)
├── evaluate.py          # Performance benchmark
└── README.md
```

### The Challenge

N-body particle simulation with physics
- 10,000 particles
- Current throughput: 500 frames/second
- Memory: 500MB per frame

Goal: Achieve 1000+ frames/second (2x speedup)

### The Evaluator

```python
# evaluate.py
import subprocess
import time
import re

def evaluate():
    """Benchmark particle simulation."""
    try:
        # Run simulation with performance profiling
        result = subprocess.run(
            ['python', 'simulation.py', '--frames', '100', '--particles', '10000'],
            capture_output=True,
            timeout=60,
            text=True
        )

        if result.returncode != 0:
            print(f"Error: {result.stderr}")
            return 0.0

        # Parse output for performance metrics
        output = result.stdout
        match = re.search(r'fps:\s*([\d.]+)', output)
        if not match:
            return 0.0

        fps = float(match.group(1))

        # Parse memory usage
        mem_match = re.search(r'memory_mb:\s*([\d.]+)', output)
        memory_mb = float(mem_match.group(1)) if mem_match else 500

        # Score: fps gain with memory penalty
        # Baseline: 500 fps, 500 MB
        fps_score = fps / 500
        memory_penalty = 1 - (memory_mb - 500) / 500
        memory_penalty = max(0, memory_penalty)

        return fps_score * memory_penalty

    except Exception as e:
        print(f"Evaluation error: {e}")
        return 0.0

if __name__ == '__main__':
    score = evaluate()
    print(f"{score:.2f}")
```

### Running Evolution

```bash
cd examples/volumetric_particle_sim

python ../../services/worker/cli.py . \
  --evaluator evaluate.py \
  --agents 10 \
  --generations 5 \
  --task "Optimize particle simulation performance for 10K particles"
```

### Expected Improvements

**Baseline**: 500 fps, 1.0 score

**Generation 1**:
- Analyzer identifies expensive distance calculations
- Optimizer implements spatial hashing
- Score: ~1.1 (550 fps) ✓

**Generation 2**:
- Feature Engineer adds vectorization
- NumPy SIMD acceleration
- Score: ~1.4 (700 fps) ✓

**Generation 3-4**:
- Refactorer optimizes memory layout
- Feature Engineer parallelizes
- Score: ~1.8+ (900+ fps) ✓✓

**Generation 5**:
- General agent fine-tunes remaining parameters
- Score: ~2.0+ (1000+ fps) ✓✓✓

---

## Your Custom Project

### Setup Checklist

- [ ] Create `evaluate.py` in your project root
- [ ] Make sure project is a git repository
- [ ] Set up API keys for at least one LLM provider
- [ ] Test evaluator manually

### Step 1: Create an Evaluator

```python
# evaluate.py - MUST output single number to stdout
import subprocess
import time

def evaluate():
    """Your custom benchmark."""
    try:
        # 1. Run your code/benchmarks
        start = time.time()
        result = subprocess.run(
            ['python', 'main.py'],  # Or your build/test command
            capture_output=True,
            timeout=30,
            text=True
        )
        elapsed = time.time() - start

        if result.returncode != 0:
            print(f"Execution failed")
            return 0.0

        # 2. Parse output and calculate score
        # Higher score = better
        # Could be:
        #   - Execution time (lower = score = 100/time)
        #   - Test pass rate
        #   - Performance metric
        #   - Accuracy score
        #   - Combined metric

        score = calculate_score(result.stdout, elapsed)
        return score

    except Exception as e:
        print(f"Error: {e}")
        return 0.0

def calculate_score(output, elapsed_time):
    """Calculate a score (0-100+)."""
    # Parse your specific metrics
    # Example: parse execution time
    try:
        lines = output.strip().split('\n')
        last_line = lines[-1]
        value = float(last_line)
        return value
    except:
        return 0.0

if __name__ == '__main__':
    print(f"{evaluate():.2f}")
```

### Step 2: Test Your Evaluator

```bash
python evaluate.py
# Should output a single number (e.g., "42.50")
```

### Step 3: Run Optifiner

```bash
cd /path/to/your/project

# Make sure it's a git repo
git init
git add .
git commit -m "Initial commit"

# Run evolution
python /path/to/optifiner/services/worker/cli.py . \
  --evaluator evaluate.py \
  --agents 5 \
  --generations 2 \
  --task "Improve performance and code quality"
```

### Step 4: Review Results

```bash
# See what improved
git log --oneline | head -10

# View commit details
git log -p | head -100

# Parse JSON results
cat results.json | jq '.improvement_percent'
```

---

## Common Patterns

### Pattern 1: Performance Optimization

Best for: Speed, throughput, latency

```python
def evaluate():
    """Measure execution speed."""
    import timeit
    time_taken = timeit.timeit(your_function, number=100)
    return 100 / time_taken  # Lower time = higher score
```

### Pattern 2: Algorithm Correctness

Best for: Puzzle solving, optimization problems

```python
def evaluate():
    """Measure solution quality."""
    solution = solver()
    optimal = 100  # Known optimum
    return solution / optimal  # Score: quality vs. optimal
```

### Pattern 3: Test Suite

Best for: Refactoring, debugging

```python
def evaluate():
    """Run test suite."""
    result = subprocess.run(['pytest', 'tests/'], capture_output=True)
    passed = result.stdout.count('passed')
    total = result.stdout.count('passed') + result.stdout.count('failed')
    return passed / total  # Score: test pass rate
```

### Pattern 4: Resource Constrained

Best for: Memory optimization, embedded systems

```python
def evaluate():
    """Measure memory efficiency."""
    import tracemalloc
    tracemalloc.start()
    result = your_function()
    current, peak = tracemalloc.get_traced_memory()
    return 1000 / peak  # Lower peak = higher score
```

### Pattern 5: Combined Metrics

Best for: Balanced optimization

```python
def evaluate():
    """Multi-objective optimization."""
    speed_score = measure_speed()
    quality_score = measure_quality()
    memory_score = measure_memory()

    # Weighted combination
    return (
        0.5 * speed_score +    # 50% speed
        0.3 * quality_score +  # 30% quality
        0.2 * memory_score     # 20% memory
    )
```

---

## Troubleshooting Examples

### Problem: Low Success Rate

**Symptom**: Only 1-2 improvements per generation

**Cause**: Evaluator too noisy or strict

**Solution**:
```python
# Add stability to evaluator
def evaluate():
    scores = []
    for _ in range(3):  # Multiple runs
        scores.append(run_benchmark())
    return sum(scores) / len(scores)  # Average = more stable
```

### Problem: Same Changes Each Generation

**Symptom**: Git shows repeated commits

**Cause**: Agents finding same local optimum

**Solution**:
```bash
# Increase exploration
python cli.py . \
  --evaluator evaluate.py \
  --agents 15 \           # More agents
  --max-iterations 20 \   # Deeper search
  --generations 5         # More generations
```

### Problem: Timeouts

**Symptom**: "Evaluator timeout exceeded"

**Cause**: Benchmark takes too long

**Solution**:
```bash
# Increase timeout
python cli.py . \
  --evaluator evaluate.py \
  --timeout 120  # Increase from 60 seconds
```

Or optimize your evaluator:
```python
# Reduce problem size
result = subprocess.run(
    ['python', 'main.py', '--small-dataset'],
    # faster than --full-dataset
)
```

---

## Next Steps

- Explore other [examples](../examples/)
- Learn about [Agent Types](AGENT_TYPES.md)
- Read the [Getting Started](GETTING_STARTED.md) guide
- Check [API Reference](API_REFERENCE.md) for advanced options
