# Understanding the Phylogenetic Tree

The phylogenetic tree is a visual representation of how your code evolved across generations. It shows the "family tree" of code candidates—starting from your original code as the root, branching into variants as evolution explores different optimizations, and growing more complex as successive generations build on successful improvements. Understanding how to read this tree helps you see which optimizations worked best and why certain code paths were abandoned.

## The Phylogenetic Tree

In evolutionary algorithms, a phylogenetic tree maps the relationships between candidates. In Optifiner:

- **Root**: Your original code (generation 0)
- **Branches**: Different code variants explored by agents in each generation
- **Trunk**: The most successful lineage—the path from root to your best final code
- **Dead Branches**: Variants that performed worse and weren't selected for the next generation
- **Leaves**: Final candidates at the end of evolution

The tree grows downward, with each generation adding a new layer. Successful mutations branch into multiple candidates for the next generation. Unsuccessful mutations end (no further descendants).

## Reading the Visualization

**Color Coding**
- **Green branches**: Candidates that improved fitness (selected for next generation)
- **Red branches**: Candidates that declined in fitness (not selected)
- **Highlighted trunk**: The most successful lineage leading to your best code

**Node Information**
Each node represents a code candidate and shows:
- Generation number (how many steps from the original)
- Fitness score
- Number of mutations applied
- Brief description of what changed

**Hovering Over Nodes**
When you hover over a node in the visualization, you can see:
- Exact fitness value
- List of code changes made
- Why this candidate was selected or rejected

## Understanding Branches

**What Makes a Branch Split?**
After each generation, agents generate multiple candidate improvements. Optifiner evaluates all candidates, and the best ones are selected as the basis for the next generation. This creates branches:
- If a candidate is selected, it becomes the parent of next-generation variants
- If a candidate is rejected, its branch ends

**Main Trunk vs Side Branches**
- **Main Trunk**: The continuous line from root to your final best code. This represents the most successful continuous improvement path. Follow the trunk to see which optimizations progressively improved your code.
- **Side Branches**: Dead-end explorations that didn't lead to better code. These are informative—they show what agents tried but didn't work.

**Why Did Evolution Explore Different Paths?**
Agents use randomness to explore multiple optimization strategies simultaneously. Not all work, but this diversity helps evolution avoid getting stuck. The tree shows this exploration process.

## Analyzing Mutations

**What's a Mutation?**
Each branch represents one or more code mutations—changes agents made to the code. A single candidate may involve multiple mutations (e.g., loop optimization + variable renaming + better algorithm).

**Comparing Mutations**
The tree shows which mutations were most productive:
- Follow the trunk to see which specific changes led to steady improvement
- Compare side branches to the trunk to understand what changes didn't help
- Note repeated patterns—if certain mutation types appear frequently in successful branches, they're particularly effective for your code

**Learning from Mutations**
By analyzing the tree, you can see:
- Which optimization strategies work for your codebase
- Common patterns in high-fitness candidates
- What types of changes your code responds well to

This knowledge helps you guide future evolution runs or apply similar optimizations manually.

## Using Insights

**Spotting Patterns**
If you see the tree heavily favor certain types of mutations (e.g., loop unrolling, memoization), those patterns are particularly effective for your code. You could:
- Manually apply similar changes to other parts of the codebase
- Run future evolution with agents biased toward these optimization types
- Focus optimization efforts where evolution found success

**Understanding Plateaus**
If the tree shows high fitness early, then branches stop improving:
- Evolution has likely reached diminishing returns
- Fitness has plateaued (normal behavior)
- Running more generations may yield minimal additional gains
- Consider this point as your natural stopping point

**Identifying Dead Ends**
Side branches that quickly fail reveal what doesn't work for your code. This is valuable information:
- Avoid similar changes in manual optimization
- Understand why certain patterns don't apply to your codebase
- Help agents learn what to avoid in future runs

## Tips and Tricks

**Zoom Into Details**
Most visualizations let you zoom in on specific generations or branches. This helps you see mutations and fitness scores more clearly when the tree is complex.

**Compare Multiple Evolution Runs**
Run evolution multiple times on the same code. You'll get different trees due to randomness and different agent decisions. Comparing trees shows:
- Which optimizations consistently help (appear in multiple runs)
- Outlier mutations that only sometimes work
- Most reliable optimization paths

**Export and Share**
You can download tree visualizations and share them. They're great for understanding what your evolution process discovered and documenting which optimizations were most effective.

**Follow the Trunk**
To understand which specific changes made the biggest difference, follow the main trunk from root to best candidate and examine each node's mutations. This shows the progressive improvement path.

---

**Last updated:** [Add date]
**Author:** [Add name]
