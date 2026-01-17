# Cost Management Strategies

Code evolution with Optifiner uses AI model APIs, which means your optimization runs incur costs. This guide helps you understand those costs, plan your budget, and optimize your spending while getting maximum improvement results.

## Understanding Costs

**What You Pay For**
You pay for API calls to large language models. Each evolution run involves:
- Agents analyzing your code
- Generating code candidates
- Running benchmarks to evaluate improvements
- Iterating on promising candidates

**Cost Breakdown Per Run**
Typical costs depend on three factors:

1. **Model Choice**
   - Claude Sonnet: ~$0.003 per 1K input tokens (most expensive, highest quality)
   - Gemini Flash: ~$0.000075 per 1K tokens (cheapest, good quality)
   - GPT-4o: ~$0.005 per 1K tokens (moderate)
   - GPT-5-nano: ~$0.00005 per 1K tokens (ultra-cheap, lower quality)

2. **Codebase Size**
   - Smaller codebases (< 1K lines): $1-5 per run
   - Medium codebases (1K-10K lines): $5-20 per run
   - Large codebases (> 10K lines): $20-100 per run

3. **Evolution Configuration**
   - More generations = more cost (roughly linear)
   - More agents per generation = more cost (roughly linear)
   - More iterations per agent = more cost (roughly linear)

**Cost Estimation Formula**
Estimated Cost = (Codebase Size in KB) × (Generations) × (Agents per Generation) × (Model Cost per 1K tokens) × (Token multiplier: typically 5-10)

Example for medium codebase (5K lines) with 10 generations, 10 agents, Gemini: approximately $18.80

## Budgeting

**Plan Your Budget**
Before starting evolution, decide how much you can spend:

1. **Per-Project Budget**: How much can you spend optimizing this specific code?
2. **Monthly Budget**: How much monthly can you allocate to evolution?
3. **Cost per Unit of Improvement**: How much is a 1% improvement worth?

**Budget Categories**
- **Experimentation Budget**: Testing your setup, validating benchmarks (usually $10-50)
- **Main Evolution Budget**: Longer runs targeting meaningful improvements ($50-500+)
- **Refinement Budget**: Follow-up runs to push optimization further (variable)

**Setting Reasonable Budgets**
- **Startup/Hobby Projects**: $20-50 per project (quick experiments)
- **Production Services**: $200-1000 per optimization cycle (longer, deeper runs)
- **Complex Systems**: $1000+ per cycle (large codebases, many iterations)

## Cost Optimization

**Strategy 1: Use Cheaper Models for Experiments**

Start with GPT-5-nano or Gemini Flash to test your setup. Once your benchmark is validated, switch to Claude for higher-quality improvements.

**Savings**: 50-80% reduction in experimentation costs while still validating your approach.

**Strategy 2: Reduce Generation Count**

Instead of running 30 generations, try 5 generations to validate approach, 10 generations for real optimization, or 20+ generations only if results are promising.

Each additional generation has diminishing returns—often you get 80% of possible improvements in the first half of generations.

**Strategy 3: Reduce Code Size**

Optimize smaller modules or functions instead of entire projects:
- Focus on performance hotspots (use profilers first)
- Optimize one file or function at a time
- Run multiple small optimizations instead of one massive run

**Savings**: Smaller codebase = exponentially lower costs (1K lines costs ~10x less than 10K lines).

**Strategy 4: Reduce Agents Per Generation**

Default is 10 agents. Try fewer agents for quick experiments, or more agents if you want greater diversity in exploration.

Fewer agents mean less diversity in exploration but lower cost.

**Strategy 5: Use Early Stopping**

Early stopping starts a new generation immediately when an improvement is found (rather than waiting for all agents to finish). This typically reduces total runs needed by 20-30%.

**Strategy 6: Validate Benchmarks First**

Before running expensive evolution, make sure your benchmark is correct and stable:
- Run your benchmark manually 5-10 times
- Verify fitness scores are consistent
- Check that improvements actually matter

Bad benchmarks waste money on optimization of the wrong thing.

## Monitoring Expenses

**Track Your Spending**
Most API providers give you usage dashboards:
- **Anthropic**: Check API usage in your dashboard
- **Google**: Cloud Console > Billing
- **OpenAI**: Usage page shows cost over time

**Per-Run Cost Analysis**
After each run, calculate actual cost:
1. Check your API provider's dashboard for tokens used
2. Calculate: (tokens / 1000) × (cost per 1K tokens)
3. Compare actual vs. estimated cost
4. Adjust future estimates

**Set Alerts**
Configure spending alerts at key thresholds:
- Alert at 50% of monthly budget
- Alert at 80% of monthly budget
- Hard limit at 100% of budget

Most API providers let you set alerts or spending caps.

## ROI Analysis: Is Evolution Worth It?

**Calculate the Value**
Is the improvement worth the cost?

Example calculation:
- Improvement: 20% faster code
- Cost: $100
- Time saved per day: 1 hour (for operations team)
- Annual value: 1 hour × 250 work days × $50/hour = $12,500
- **ROI: 12,500 ÷ 100 = 125x return**

Another example:
- Improvement: 15% throughput increase
- Cost: $50
- Additional customers served: 1000
- Annual revenue gained: $50,000
- **ROI: 50,000 ÷ 50 = 1000x return**

**Break-Even Analysis**
How much improvement justifies the cost?

For a $100 evolution run to break even:
- Service downtime cost: ~$1/min → need 100 minutes = 1.7 hours saved annually
- SaaS business with 10K users: need $100,000 annual revenue increase = 1% increase in throughput
- Internal tool: need 40 hours saved annually = 5 minutes per business day

Most optimizations easily pay for themselves.

## Cost Reduction Tips

1. **Profile First**: Use traditional profilers to identify bottlenecks before evolution. This focuses optimization where it matters most.

2. **Incremental Approach**: Optimize one hot spot at a time rather than entire systems. Smaller codebase = faster and cheaper.

3. **Batch Evolution**: If you have multiple optimizations to make, bundle them. Running multiple separate evolutions costs more than one evolution on all targets.

4. **Version Control**: Keep the best evolved versions. Don't re-optimize the same code multiple times.

5. **Reuse Benchmarks**: If you optimize multiple similar modules, reuse benchmarks where possible.

6. **Parallel Runs**: Run evolution on multiple modules in parallel if your budget allows. Parallel runs cost the same per run but find improvements faster overall.

7. **Off-Peak Timing**: No cost difference, but run evolution during off-peak hours to avoid impacting production systems.

---

**Last updated:** [Add date]
**Author:** [Add name]
