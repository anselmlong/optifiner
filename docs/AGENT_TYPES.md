# Agent Types

Optifiner uses specialized agents, each focused on a specific type of code improvement. This document describes each agent type and when they're most effective.

## Overview

Agents are cycled through in a pool, with each generation including multiple agent types. The diversity of approaches increases the likelihood of finding improvements.

```
Generation 1:
├─ Agent 1: Analyzer (type="analyzer")
├─ Agent 2: Refactorer (type="refactoring")
├─ Agent 3: Optimizer (type="optimizer")
├─ Agent 4: Feature Engineer (type="feature")
└─ ...more agents from different types

Generation 2:
├─ Agent 6: Analyzer
├─ Agent 7: General
└─ ...
```

## Agent Types

### 1. Analyzer

**Purpose**: Understand the codebase and identify improvement opportunities

**Capabilities**:
- Analyzes code structure and dependencies
- Identifies performance bottlenecks
- Detects algorithmic inefficiencies
- Spots code quality issues
- Finds unused code or variables

**Typical Improvements**:
- Suggests algorithm changes
- Identifies inefficient data structures
- Points out unnecessary computations
- Finds N+1 query problems
- Detects redundant code

**Example Improvements**:
```python
# Before: O(n²) nested loop
for i in range(len(arr)):
    for j in range(len(arr)):
        if arr[i] == arr[j] and i != j:
            process(arr[i])

# Analyzer suggests: Use set for O(n)
seen = set()
for item in arr:
    if item in seen:
        process(item)
    seen.add(item)
```

**Best For**:
- Initial analysis passes
- Large codebases requiring understanding
- Finding the "low-hanging fruit"
- Understanding performance profiles

**Limitations**:
- Doesn't implement changes as deeply as specialists
- May miss domain-specific optimizations
- Relies on code readability

---

### 2. Refactorer

**Purpose**: Restructure code for clarity, maintainability, and performance

**Capabilities**:
- Refactors complex functions
- Reduces code duplication
- Consolidates similar operations
- Improves code organization
- Simplifies control flow

**Typical Improvements**:
- Extract methods to reduce complexity
- Consolidate similar code blocks
- Improve naming for clarity
- Remove dead code
- Simplify conditionals

**Example Improvements**:
```python
# Before: Complex nested function
def process_data(records, filters):
    results = []
    for r in records:
        if filters.get('active') and not r.get('active'):
            continue
        if filters.get('type') and r.get('type') != filters['type']:
            continue
        if filters.get('min_value') and r.get('value') < filters['min_value']:
            continue
        results.append(r)
    return results

# Refactorer suggests: Extract filter logic
def matches_filters(record, filters):
    return (
        (not filters.get('active') or record.get('active')) and
        (not filters.get('type') or record.get('type') == filters['type']) and
        (not filters.get('min_value') or record.get('value') >= filters['min_value'])
    )

def process_data(records, filters):
    return [r for r in records if matches_filters(r, filters)]
```

**Best For**:
- Improving code readability
- Reducing cyclomatic complexity
- Preparing code for optimization
- Eliminating duplication

**Limitations**:
- Refactoring alone may not improve performance
- Requires careful change validation
- Can break subtle logic if not careful

---

### 3. Optimizer

**Purpose**: Fine-tune code for performance at the micro level

**Capabilities**:
- Optimizes hot loops
- Tunes parameters (batch sizes, thresholds)
- Implements caching strategies
- Optimizes data structure usage
- Fine-tunes algorithm constants

**Typical Improvements**:
- Reduces algorithmic complexity
- Adds memoization/caching
- Optimizes database queries
- Tunes memory usage
- Improves cache locality

**Example Improvements**:
```python
# Before: Repeated computation
def calculate_scores(items):
    scores = []
    for item in items:
        score = expensive_calculation(item)
        scores.append(score * WEIGHT)
    return scores

# Optimizer suggests: Cache computation
def calculate_scores(items, cache=None):
    if cache is None:
        cache = {}

    scores = []
    for item in items:
        if item not in cache:
            cache[item] = expensive_calculation(item)
        scores.append(cache[item] * WEIGHT)
    return scores
```

**Best For**:
- Performance-critical sections
- Reducing API calls
- Memory optimization
- Latency reduction

**Limitations**:
- May add complexity
- Cache invalidation challenges
- Tuning can be hardware-specific

---

### 4. Feature Engineer

**Purpose**: Add high-level features and improvements (caching, parallelization, etc.)

**Capabilities**:
- Adds caching layers
- Implements parallelization
- Introduces data structure improvements
- Adds preprocessing steps
- Implements batching strategies

**Typical Improvements**:
- LRU cache for function results
- Thread/async parallelization
- Batch processing instead of per-item
- Index data structures for O(1) lookup
- Lazy evaluation

**Example Improvements**:
```python
# Before: Sequential processing
def process_users(users):
    results = []
    for user in users:
        data = fetch_profile(user)
        processed = transform(data)
        results.append(processed)
    return results

# Feature Engineer suggests: Parallel processing
from concurrent.futures import ThreadPoolExecutor

def process_users(users):
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [
            executor.submit(process_user, user)
            for user in users
        ]
        return [f.result() for f in futures]

def process_user(user):
    data = fetch_profile(user)
    return transform(data)
```

**Best For**:
- Bottlenecks in I/O-bound operations
- Embarrassingly parallel workloads
- Adding infrastructure improvements
- Multi-dimensional optimization

**Limitations**:
- Concurrency adds complexity
- Thread safety concerns
- Not suitable for all problems

---

### 5. General

**Purpose**: All-purpose improvements without specialization

**Capabilities**:
- Any type of improvement
- Cross-cutting optimizations
- Holistic analysis
- Multi-dimensional improvements

**Typical Improvements**:
- Combination of refactoring and optimization
- Framework-specific improvements
- Domain-specific optimizations
- Algorithmic breakthroughs

**Example Improvements**:
- Rewrite function using different library
- Apply design patterns
- Multi-level optimization (code + data structure + algorithm)

**Best For**:
- Later generations (after specialists narrow down)
- Diverse codebases
- Finding unexpected improvements
- Polish passes

**Limitations**:
- Less focused than specialists
- May duplicate specialist improvements
- Harder to predict outcomes

---

## Agent Selection Strategy

### Per Generation

The system cycles through agent types to ensure diversity:

```
Generation 1: [Analyzer, Refactorer, Optimizer, Feature, General, ...]
Generation 2: [Refactorer, Optimizer, Feature, General, Analyzer, ...]
Generation 3: [Optimizer, Feature, General, Analyzer, Refactorer, ...]
```

### Agent Pool Configuration

```python
# Configuration in config.py
AGENT_TYPES = [
    "analyzer",
    "refactoring",
    "optimizer",
    "feature",
    "general"
]

def get_agent_type_for_pool(generation: int, agent_index: int) -> str:
    """Cycle through agent types."""
    types_count = len(AGENT_TYPES)
    pool_offset = generation * num_agents
    index = (pool_offset + agent_index) % types_count
    return AGENT_TYPES[index]
```

## System Prompts

Each agent type receives a specialized system prompt to guide its behavior.

### Analyzer Prompt (Excerpt)

```
You are an expert code analyzer specializing in performance and quality analysis.

Your task is to:
1. Read and understand the codebase
2. Identify performance bottlenecks
3. Find algorithmic inefficiencies
4. Suggest concrete improvements

Focus on:
- Time complexity (O(n²) → O(n log n))
- Space complexity
- Unnecessary computations
- Inefficient data structures

Use the tools:
- read_file, grep, list_dir to explore
- Only suggest changes, don't make them

Output a detailed analysis with specific improvement suggestions.
```

### Optimizer Prompt (Excerpt)

```
You are an expert performance optimizer with deep knowledge of system design.

Your task is to:
1. Identify hot paths and bottlenecks
2. Profile performance characteristics
3. Apply targeted optimizations
4. Verify improvements don't break functionality

Focus on:
- Reducing function call overhead
- Optimizing memory access patterns
- Caching frequently computed values
- Tuning algorithm parameters

Use the tools to:
- read_file to understand current implementation
- evaluate to measure improvement
- edit_file to apply optimizations

Make incremental changes and validate each one.
```

## Success Metrics Per Agent Type

### Analyzer
- **Success**: Identifies issues, suggests fixes (improves 20-30% of time)
- **Failure**: Misses obvious optimizations, suggests unprovable ideas

### Refactorer
- **Success**: Cleaner code that performs better (improves 15-25% of time)
- **Failure**: Breaks subtle logic, over-engineers

### Optimizer
- **Success**: Direct performance gains (improves 25-40% of time)
- **Failure**: Adds overhead, complicates code, breaks tests

### Feature Engineer
- **Success**: Structural improvements enabling parallelization (improves 20-35% of time)
- **Failure**: Adds unnecessary complexity, thread safety bugs

### General
- **Success**: Novel combinations of strategies (improves 10-20% of time)
- **Failure**: Unfocused attempts, misses opportunities

## Monitoring Agent Behavior

### Agent Metrics

```typescript
interface AgentMetrics {
  agent_id: string
  agent_type: string
  generation: number

  mutations_proposed: number
  mutations_successful: number
  success_rate: number  // successful / proposed

  improvements: {
    min: number
    max: number
    avg: number
  }

  tool_calls: {
    total: number
    by_tool: Record<string, number>
  }

  duration_seconds: number
  cost_usd: number
}
```

### Viewing Agent Performance

```bash
# JSON output includes agent metrics
cat results.json | jq '.agent_metrics[]'

# Filter by agent type
cat results.json | jq '.agent_metrics[] | select(.agent_type=="optimizer")'

# Calculate success rate
cat results.json | jq '.agent_metrics | map(.success_rate) | add / length'
```

## Customizing Agents

### Creating a Custom Agent Type

To add a new agent type:

1. **Define the agent type** in `config.py`:
```python
AGENT_TYPES = [
    "analyzer",
    "refactoring",
    "optimizer",
    "feature",
    "general",
    "custom",  # ← New type
]
```

2. **Create system prompt** in `prompts.py`:
```python
def get_system_prompt(agent_type: str) -> str:
    prompts = {
        # ... existing prompts ...
        "custom": """You are a custom optimization specialist...
        Your focus areas are:
        - ...
        - ...
        """,
    }
    return prompts.get(agent_type, prompts["general"])
```

3. **Update agent selection logic** if needed:
```python
def get_agent_type_for_pool(...):
    # Add custom logic to include your new agent
    pass
```

## Best Practices

### Combining Agent Types

1. **Early generations**: Use Analyzer for understanding
2. **Mid generations**: Use Optimizer and Refactorer for targeted improvements
3. **Late generations**: Use Feature Engineer and General for compound improvements

### Tuning Agent Behavior

```bash
# Increase analyzer weight (run more analyzer agents)
python cli.py /path/to/repo \
  --evaluator evaluate.py \
  --agents 12 \           # More agents = different mix
  --generations 5

# Increase iterations for deeper exploration
python cli.py /path/to/repo \
  --evaluator evaluate.py \
  --max-iterations 20     # Agents get more chances
```

### Monitoring Success

```python
# Track agent type success rates
results = json.load(open('results.json'))

success_by_type = {}
for metric in results['agent_metrics']:
    agent_type = metric['agent_type']
    if agent_type not in success_by_type:
        success_by_type[agent_type] = []
    success_by_type[agent_type].append(metric['success_rate'])

for agent_type, rates in success_by_type.items():
    avg_rate = sum(rates) / len(rates)
    print(f"{agent_type}: {avg_rate:.1%} success rate")
```

## Troubleshooting Agent Issues

### Problem: Low success rates (< 10%)

**Causes**:
- Evaluator too strict or noisy
- Codebase difficult to improve
- Agent confusion (poorly written code)

**Solutions**:
- Improve evaluator stability
- Increase `--max-iterations`
- Add more context in `--task` description
- Use Analyzer first to understand code

### Problem: Same improvements repeated

**Causes**:
- Too few agent types
- Agents not diverse enough

**Solutions**:
- Increase `--agents` count
- Add custom agent types
- Improve prompts to encourage diversity

### Problem: Agents making unrelated changes

**Causes**:
- Overly permissive LLM
- Unclear task description
- Agent confusion

**Solutions**:
- Clarify `--task` parameter
- Add constraints to system prompt
- Use `--model-name` with more focused model
- Lower model temperature (more deterministic)
