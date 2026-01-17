# Writing Benchmarks

Optifiner automatically creates and manages benchmarks for your project. You don't need to write or maintain benchmark scripts—Optifiner's agents analyze your codebase and automatically generate benchmarks that measure meaningful performance improvements.

When you create a new project, Optifiner analyzes your code to understand what it does and identifies key performance metrics to measure (FPS for games, throughput for servers, latency for APIs, etc.). These benchmarks are then used throughout all evolution runs to evaluate whether code changes are improvements.

The benchmark system works behind the scenes, continuously evaluating how well your code performs and guiding agents toward optimizations that matter. If you want to adjust what metrics Optifiner measures, you can configure this through your project settings.

---

**Last updated:** [Add date]
**Author:** [Add name]
