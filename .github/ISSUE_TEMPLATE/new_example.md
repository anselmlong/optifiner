---
name: New example submission
about: Share a new use case or example project for Optifiner
title: 'Example: <your-example-name>'
labels: example
assignees: ''
---

**What does this example optimize?**
Describe the code being evolved and the metric being improved.

**Baseline score**
What score does the unmodified code achieve?

**Best evolved score**
What score did Optifiner achieve after evolution? How many generations/agents?

**Command used**
```bash
python cli.py /path/to/example \
  --evaluator evaluate.py \
  --agents 5 \
  --generations 3 \
  --model-provider google \
  --model-name gemini-2.5-flash
```

**Interesting improvements made**
What did the agents actually change? Any surprising optimizations?

**PR**
Link to the PR adding this to `examples/` (if you have one).
