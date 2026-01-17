# Model Settings

Optifiner supports large language models from three providers: Anthropic (Claude), Google (Gemini), and OpenAI (GPT). Each model offers different strengths in code quality, speed, and cost. This guide helps you understand each option and choose the right model for your optimization needs.

## Available Models

**Claude (Anthropic)**
- **claude-sonnet-4-20250514**: Premium quality for complex code analysis and transformation. Best for projects where code quality is the priority. Slightly higher cost but most capable.

**Gemini (Google)**
- **gemini-2.5-flash** (Default): Fast, cost-effective balance. Excellent for iterative evolution runs with many generations. Currently the default model in Optifiner.
- **gemini-3-flash-preview**: Experimental preview version. Use with caution as it may have stability issues.

**GPT (OpenAI)**
- **gpt-4o**: High-quality code transformations comparable to Claude. Good alternative if you prefer OpenAI's models.
- **gpt-5-nano**: Lightweight and fastest option. Lower cost but less capable. Best for quick iterations when speed matters more than quality.

## Choosing a Model

**Use Claude if:**
- Code quality is your top priority
- You're optimizing complex systems where understanding code intent matters
- You can afford slightly higher API costs

**Use Gemini (default) if:**
- You want a good balance of speed, quality, and cost
- You're running many evolution generations
- You want to stick with Optifiner's recommended default

**Use GPT-4o if:**
- You prefer OpenAI's models
- You need high-quality code transformations
- You're already invested in OpenAI infrastructure

**Use GPT-5-nano if:**
- You need the fastest inference times
- You're optimizing for cost
- You're running quick experimental runs

## Configuration Options

Configure your model via CLI arguments or environment variables:

```bash
--model-provider [anthropic|google|openai]  # Default: google
--model-name <string>                        # Default: gemini-2.5-flash
```

Set environment variables:
```bash
MODEL_PROVIDER=google
MODEL_NAME=gemini-2.5-flash
MODEL_TEMPERATURE=0.0
MODEL_TIMEOUT=50.0
MODEL_MAX_RETRIES=3
```

## Cost Analysis

Approximate API costs per 1K tokens:
- **Claude**: ~$0.003 input
- **Gemini**: ~$0.075 (very low cost)
- **GPT-4o**: ~$0.005 input
- **GPT-5-nano**: ~$0.00005 input (ultra-low cost)

Your total cost depends on: number of evolution generations, code size, model choice, and how many tokens each transformation requires.

## Performance Tips

- Start with Gemini (default) to understand your costs
- Use GPT-5-nano for experimental runs to validate your fitness functions before committing to expensive models
- Switch to Claude if evolution isn't producing quality improvements
- Monitor your API usage and adjust generation counts based on cost

---

**Last updated:** [Add date]
**Author:** [Add name]
