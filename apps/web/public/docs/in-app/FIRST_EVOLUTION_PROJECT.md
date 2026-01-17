# Your First Evolution Project

This tutorial walks you through running your first code evolution project with Optifiner, from setup to reviewing results. You'll complete a full optimization cycle and see how evolutionary algorithms improve your code.

## Step 1: Project Setup

**Create a New Project**
1. In Optifiner, click "Create New Project"
2. Give your project a name (e.g., "My First Evolution")
3. Select or upload your codebase (can be a single file or entire directory)
4. Choose your preferred LLM model—Gemini is the default and a good choice for your first run

**Choose Your Code**
For your first project, pick code that:
- Is relatively small and self-contained (100-1000 lines is ideal)
- Has clear performance characteristics you can measure
- Doesn't depend on external APIs or services you can't easily mock
- Examples: a sorting algorithm, image processing function, game loop, data parser

**Set Your Optimization Goal**
Decide what you want to improve:
- Speed (execution time)
- Memory usage
- Throughput (requests/operations per second)
- Code efficiency or structure

## Step 2: Benchmark Creation

Optifiner automatically creates benchmarks for your project. When you upload your code, Optifiner's agents analyze it and generate benchmarks that measure the performance metrics most relevant to your code.

**What Happens Behind the Scenes**
- Optifiner identifies what your code does
- It measures current performance (FPS for games, throughput for servers, latency for APIs, etc.)
- It creates benchmarks that will track improvements during evolution
- It validates the benchmarks work correctly

You can review the benchmarks Optifiner created, but you don't need to modify them for your first run. The system is optimized to find meaningful improvements automatically.

## Step 3: Configure Evolution

**Set Evolution Parameters**
- **Generations**: How many evolution cycles to run (start with 20-30 for your first run)
- **Population Size**: How many code candidates to evaluate per generation (default is usually good)
- **Agent Types**: Which optimization strategies to use (default settings are recommended for beginners)

**Set Your Budget**
- Decide how much you want to spend on API calls
- More generations = more optimization potential but higher cost
- Start conservative—you can always run more generations later

**Review Your Settings**
Before running, check:
- Your code was uploaded correctly
- Your optimization goal is clear
- Your model choice is set appropriately

## Step 4: Run Evolution

**Start the Evolution Run**
1. Click "Start Evolution"
2. Optifiner will begin generating and evaluating candidate code improvements
3. You'll see progress in real-time as each generation completes

**What's Happening**
Each generation:
1. Agents suggest code modifications
2. Benchmarks evaluate each modification
3. Successful improvements are kept, unsuccessful ones are discarded
4. The next generation builds on what worked

This continues for the number of generations you specified.

**Typical Timeline**
- Small projects: 5-15 minutes for 20-30 generations
- Larger projects: 30-60 minutes
- Total cost: typically $1-10 depending on model and project size

## Step 5: Review Results

**Check Your Fitness Progress**
Once evolution completes, you'll see:
- **Overall Improvement**: The total fitness gain from start to end (e.g., "15% improvement")
- **Fitness Graph**: How scores improved over generations—typically you'll see rapid improvement early, then plateau
- **Best Generation**: Which generation produced the best code

**Review the Evolved Code**
- Download the best evolved code version
- Compare it side-by-side with your original code
- Read the changes agents made—you'll learn what optimizations helped
- Test the evolved code to verify it works correctly

**Understand the Changes**
Optifiner shows you:
- What code was modified
- Which optimizations were most effective
- How much each change contributed to overall improvement

## Next Steps

**If Results Are Good**
- Integrate the evolved code into your project
- Run evolution again on other parts of your codebase
- Share your results—you've successfully used AI-driven optimization!

**If Results Are Marginal**
- This is normal for first runs—optimization potential varies by code
- Try running more generations (experiment costs less than you might think)
- Switch to a different model (Claude is more capable but pricier)
- Review your optimization goal—make sure it's clearly measurable

**To Explore Further**
- Try optimizing different code—different code has different optimization potential
- Experiment with multiple runs and compare results
- Read the Best Practices guide for advanced strategies
- Review the Advanced Agent Tuning guide for more control over evolution

**Common Next Questions**
- "Can I optimize multiple metrics?" Yes—configure benchmarks to measure multiple values
- "Should I run evolution again?" Yes—each run is independent and may find different improvements
- "Can I combine evolved versions?" You can manually merge good changes, or run a new evolution with combined code as input

---

**Last updated:** [Add date]
**Author:** [Add name]
