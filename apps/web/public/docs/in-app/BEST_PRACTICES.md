# Best Practices

Get the most out of Optifiner by following these proven strategies for effective code evolution. These practices help you set up projects for success, guide optimization toward meaningful improvements, and avoid common mistakes that slow down or derail evolution runs.

## General Tips

**Start with Clear Goals**: Define what "better" means for your project before starting evolution. Is it faster execution? Lower memory usage? Better readability? More scalable architecture? Your goals shape which metrics matter most and guide agents toward relevant optimizations.

**Use Realistic Benchmarks**: Benchmarks should measure real-world usage patterns, not artificial scenarios. If your code serves web requests, benchmark with actual request patterns. If it's a game, measure during typical gameplay. Optifiner's agents optimize for what you measure.

**Keep Projects Focused**: Optimize one codebase or module at a time rather than mixing unrelated code. Evolution works better when the code has a clear purpose and the metrics directly relate to that purpose. A game engine and a data processing library need different optimization strategies.

**Monitor Evolution Progress**: Watch how your fitness scores change over generations. If scores plateau, evolution may have reached the limits of what agents can improve without manual guidance. If scores are erratic, your benchmark may have too much variance.

## Optimization Strategies

**Identify Bottlenecks First**: Before running evolution, profile your code to understand where time is spent. Optifiner's agents can improve any code, but focusing on real bottlenecks produces faster overall improvement. Tell agents where the slowness actually is.

**Incremental Evolution**: Run evolution in smaller batches rather than one massive run. After 20-30 generations, review results, adjust strategy if needed, and run again. This gives you feedback points and prevents getting stuck in local optima.

**Balance Multiple Metrics**: If you care about both speed and memory usage, define metrics for both. Optifiner can optimize toward multiple objectives—just make sure your benchmark measures them all.

**Experiment with Different Agents**: Optifiner offers different types of agents (performance-focused, refactoring-focused, etc.). Try different combinations to see which produces better results for your code. Some agent types excel at different optimization targets.

## Common Pitfalls

**Chasing Marginal Improvements**: Once you've achieved 10-20% improvement, additional generations often yield smaller gains. Know when to accept a good result rather than running evolution indefinitely hoping for 50% improvement.

**Unrealistic Benchmarks**: A benchmark that measures something artificial won't guide evolution toward real improvements. Your benchmark should closely reflect actual usage.

**Breaking Functionality**: While Optifiner aims to preserve correctness, always verify that evolved code still works properly. If evolution produces incorrect results, your fitness benchmark may not be catching bugs—add functional tests.

**Ignoring Code Readability**: Some optimizations make code harder to understand. While Optifiner doesn't optimize for readability by default, you can adjust benchmarks to penalize overly complex changes or review evolved code for clarity issues.

## Performance Tips

**Run Multiple Evolution Experiments**: Different random seeds and agent configurations may produce different results. Run several independent evolution experiments and keep the best results.

**Adjust Generation Count Based on Budget**: More generations = better optimization but higher API costs. Start with 20-30 generations, then increase if results look promising.

**Use Cheaper Models for Experimentation**: Start with GPT-5-nano or Gemini to test your setup and validate benchmarks. Once you're confident, switch to Claude for higher-quality improvements.

**Parallelize Where Possible**: If your infrastructure allows, run multiple evolution experiments in parallel. You'll discover good optimizations faster.

## Advanced Techniques

**Hybrid Optimization**: Combine Optifiner with traditional profiling and manual optimization. Use profilers to identify bottlenecks, then use Optifiner to improve those specific areas.

**Iterative Refinement**: After evolution produces improvements, review the evolved code. Often you can learn patterns from what agents found and apply those patterns manually to other parts of the codebase.

**Benchmark Evolution**: As your code evolves, its performance characteristics change. Optifiner automatically updates benchmarks, but review them periodically to ensure they still measure what matters.

---

**Last updated:** [Add date]
**Author:** [Add name]
