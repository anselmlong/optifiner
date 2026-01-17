# In-App Documentation Setup

## Overview

Your in-app help documentation has been created as **placeholder files** in `docs/in-app/`. These are completely separate from the GitHub documentation and ready for you to customize.

## Location

All in-app documentation files are located in:
```
docs/in-app/
├── INDEX.md                    # Master index (reference)
├── GETTING_STARTED.md          # Quick link: Getting Started
├── AGENT_CONFIGURATION.md      # Quick link: Agent Configuration
├── UNDERSTANDING_FITNESS.md    # Quick link: Understanding Fitness
├── MODEL_SETTINGS.md           # Quick link: Model Settings
├── WRITING_BENCHMARKS.md       # Quick link: Writing Benchmarks
├── BEST_PRACTICES.md           # Quick link: Best Practices
├── FIRST_EVOLUTION_PROJECT.md  # Tutorial: Your First Evolution Project
├── PHYLOGENETIC_TREE.md        # Tutorial: Understanding the Phylogenetic Tree
├── OPTIMIZING_AGENTS.md        # Tutorial: Optimizing Agent Performance
└── COST_MANAGEMENT.md          # Tutorial: Cost Management Strategies
```

## Quick Links (Help Page)

These 6 topics appear as clickable cards on the Help page:

1. **Getting Started** → `docs/in-app/GETTING_STARTED.md`
2. **Agent Configuration** → `docs/in-app/AGENT_CONFIGURATION.md`
3. **Understanding Fitness** → `docs/in-app/UNDERSTANDING_FITNESS.md`
4. **Model Settings** → `docs/in-app/MODEL_SETTINGS.md`
5. **Writing Benchmarks** → `docs/in-app/WRITING_BENCHMARKS.md`
6. **Best Practices** → `docs/in-app/BEST_PRACTICES.md`

## Tutorials (Help Page)

These 4 topics appear as tutorial cards:

1. **Your First Evolution Project** → `docs/in-app/FIRST_EVOLUTION_PROJECT.md`
2. **Understanding the Phylogenetic Tree** → `docs/in-app/PHYLOGENETIC_TREE.md`
3. **Optimizing Agent Performance** → `docs/in-app/OPTIMIZING_AGENTS.md`
4. **Cost Management Strategies** → `docs/in-app/COST_MANAGEMENT.md`

## How to Customize

### Step 1: Open a File
```bash
# Example: Edit Getting Started guide
vi docs/in-app/GETTING_STARTED.md
```

### Step 2: Replace Placeholders
Each file contains these sections to customize:

```markdown
# Title

**[PLACEHOLDER - Edit this section with your custom guide]**

## Overview
[Add your content here]

## [Topic Name]
[Add your content here]

---

**Last updated:** [Add date]
**Author:** [Add name]
```

### Step 3: Edit Content
1. Keep the markdown structure
2. Replace `[PLACEHOLDER - Edit this section...]` with an actual description
3. Replace all `[Add your content here]` sections with your content
4. Update the "Last updated" date and "Author" field
5. Save the file

### Step 4: Update INDEX
Reference the `docs/in-app/INDEX.md` file to see all available documentation.

## Example Edit

### Before:
```markdown
# Getting Started

**[PLACEHOLDER - Edit this section with your custom getting started guide]**

## Prerequisites

[Add your content here]

## Installation

[Add your content here]
```

### After:
```markdown
# Getting Started

Learn how to set up Optifiner and run your first code evolution experiment.

## Prerequisites

- Python 3.10+
- Node.js 18+
- Your API key (Google, Anthropic, or OpenAI)

## Installation

First, clone the repository and install dependencies...

[Your detailed content here]
```

## Integration with Help Page

The Help page in the web app currently shows all these topics as buttons. You can:

1. **Edit the Help page** to point to these docs
2. **Create a docs viewer component** to display these markdown files
3. **Link them from the Sidebar** navigation

Once you finish editing these placeholder files, the next step would be to integrate them into the web app UI.

## Current Status

✅ Placeholder docs created
✅ All 10 topics covered (6 quick links + 4 tutorials)
✅ Consistent template structure
✅ Ready for customization
⏳ Waiting for you to add custom content

## Next Steps

1. Open each file in `docs/in-app/`
2. Replace the placeholder content with your custom documentation
3. Keep the markdown format (headers, lists, code blocks)
4. Update dates and author information
5. Test your documentation

## File Naming Reference

| File | Help Page Section | Type |
|------|-------------------|------|
| `GETTING_STARTED.md` | Getting Started | Quick Link |
| `AGENT_CONFIGURATION.md` | Agent Configuration | Quick Link |
| `UNDERSTANDING_FITNESS.md` | Understanding Fitness | Quick Link |
| `MODEL_SETTINGS.md` | Model Settings | Quick Link |
| `WRITING_BENCHMARKS.md` | Writing Benchmarks | Quick Link |
| `BEST_PRACTICES.md` | Best Practices | Quick Link |
| `FIRST_EVOLUTION_PROJECT.md` | Your First Evolution Project | Tutorial |
| `PHYLOGENETIC_TREE.md` | Understanding the Phylogenetic Tree | Tutorial |
| `OPTIMIZING_AGENTS.md` | Optimizing Agent Performance | Tutorial |
| `COST_MANAGEMENT.md` | Cost Management Strategies | Tutorial |

## Markdown Tips

Use standard markdown for formatting:

```markdown
# Heading 1
## Heading 2
### Heading 3

**Bold text**
*Italic text*

- Bullet point 1
- Bullet point 2
  - Nested point

1. Numbered item 1
2. Numbered item 2

\`\`\`bash
# Code block
python cli.py --help
\`\`\`

[Link text](https://url.com)

| Column 1 | Column 2 |
|----------|----------|
| Data 1   | Data 2   |
```

## Questions?

Refer to `docs/in-app/INDEX.md` for a complete index and instructions on how these files are used.

---

**Setup Date:** 2025-01-17
**Status:** Ready for customization
