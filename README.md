# Optifiner

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Optifiner is a **self-evolving code framework** that automatically improves codebases through multi-agent AI-driven optimization. It spawns parallel AI agents that propose and test code improvements, keeping only changes that measurably improve performance against benchmark metrics.

## 🚀 Key Features

- **Multi-Agent Evolution**: Deploy 10+ parallel AI agents that autonomously improve your code
- **Benchmark-Driven**: All improvements are validated against your custom evaluation metrics
- **Git-Integrated**: Every improvement is tracked, version-controlled, and reversible
- **Real-Time Visualization**: Monitor evolution progress through an interactive web dashboard
- **Multi-Model Support**: Works with Claude, GPT-4, Gemini, and other LLMs
- **Generational Optimization**: Runs multiple generations with automatic convergence detection
- **Production-Ready**: Docker support, scalable architecture, comprehensive observability

## 🎯 Use Cases

- **Performance Optimization**: Automatically refactor slow code for better throughput/latency
- **Algorithm Improvement**: Evolve sorting, pathfinding, and scheduling algorithms
- **Game AI Enhancement**: Improve NPC behavior and game mechanics
- **Competitive Programming**: Auto-optimize solutions for algorithmic contests
- **ML Model Tuning**: Refine hyperparameters and training code

## 📋 Quick Start

### Prerequisites

- Python 3.10+
- Node.js 18+
- Docker & Docker Compose (for full stack)
- API keys for at least one LLM provider:
  - Anthropic (Claude)
  - Google (Gemini)
  - OpenAI (GPT)

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/optifiner.git
cd optifiner

# Install worker dependencies
cd services/worker
pip install -r requirements.txt

# Install web UI dependencies
cd ../../apps/web
npm install
```

### Basic Usage

#### 1. Create an Evaluator

Your codebase needs a benchmark script that returns a numeric score:

```python
# evaluate.py
import subprocess
import time

def evaluate():
    """Run benchmarks and return a score (higher is better)."""
    start = time.time()
    result = subprocess.run(['python', 'main.py'], capture_output=True)
    elapsed = time.time() - start

    # Parse results and calculate score
    if result.returncode == 0:
        return 100.0 / (elapsed + 1)  # Faster = higher score
    return 0.0

if __name__ == '__main__':
    print(evaluate())
```

#### 2. Run Evolution

```bash
cd services/worker

# Single generation with 5 agents
python cli.py /path/to/your/repo \
  --evaluator /path/to/evaluate.py \
  --agents 5 \
  --generations 1 \
  --model-provider google \
  --model-name gemini-2.5-flash

# Multiple generations with parallel execution
python cli.py /path/to/your/repo \
  --evaluator /path/to/evaluate.py \
  --agents 10 \
  --parallel 4 \
  --generations 5 \
  --output results.json
```

#### 3. View Results

```bash
# Results are committed to git
git log --oneline

# View detailed evolution metrics
cat results.json | jq '.'
```

### Web Dashboard

```bash
cd apps/web

# Development
npm run dev          # Runs on http://localhost:5173

# Production build
npm run build
npm run preview
```

## 🏗️ Architecture

Optifiner consists of three main components:

```
┌─────────────────────────────────────────────────────────────┐
│                     Web Dashboard (React)                    │
│         Real-time visualization of evolution progress        │
└──────────────────────────┬──────────────────────────────────┘
                           │ WebSocket
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                   API Backend (FastAPI)                      │
│              Project management & coordination               │
└──────────────────────────┬──────────────────────────────────┘
                           │
        ┌──────────────────┴──────────────────┐
        ▼                                      ▼
   ┌─────────────┐                   ┌─────────────────┐
   │   Redis     │                   │   PostgreSQL    │
   │  Task Queue │                   │   History DB    │
   └─────────────┘                   └─────────────────┘
        ▲
        │ Celery Tasks
        │
┌──────┴──────────────────────────────────────────────────────┐
│              LangGraph Evolution Worker                      │
│                                                              │
│  ┌────────────────────────────────────────────────────┐    │
│  │  Agent Pool (Analyzer, Refactorer, Optimizer, etc) │    │
│  │                                                    │    │
│  │  Each Agent:                                       │    │
│  │  • Analyzes code with LLM                         │    │
│  │  • Proposes improvements                          │    │
│  │  • Edits files in sandbox workspace              │    │
│  │  • Runs evaluator benchmarks                      │    │
│  │  • Commits improvements if score improves        │    │
│  └────────────────────────────────────────────────────┘    │
│                                                              │
│  Tools: read_file, write_file, edit_file, grep, eval...    │
└──────────────────────────────────────────────────────────────┘
```

## 📚 Documentation

- **[Getting Started](docs/GETTING_STARTED.md)** - Detailed setup and configuration guide
- **[Architecture](docs/ARCHITECTURE.md)** - System design, component details, and workflows
- **[Agent Types](docs/AGENT_TYPES.md)** - Description of each agent type and its capabilities
- **[API Reference](docs/API_REFERENCE.md)** - CLI commands, endpoints, and configuration options
- **[Examples](docs/EXAMPLES.md)** - Real-world example projects and use cases
- **[Deployment](docs/DEPLOYMENT.md)** - Production deployment with Docker Compose

## 🛠️ Configuration

### Environment Variables

```bash
# LLM Provider (google, anthropic, or openai)
MODEL_PROVIDER=google
MODEL_NAME=gemini-2.5-flash
GOOGLE_API_KEY=your-key-here

# Evolution parameters
AGENTS=10              # Number of parallel agents
GENERATIONS=5          # Number of evolution generations
MAX_ITERATIONS=15      # Max tool calls per agent
PARALLEL=4             # Parallel execution workers

# Workspace
WORKSPACE_ROOT=/tmp/optifiner-workspace

# Database (for full stack)
DATABASE_URL=postgresql://user:pass@localhost/optifiner
REDIS_URL=redis://localhost:6379
```

### Supported Models

| Provider | Models |
|----------|--------|
| Anthropic | `claude-sonnet-4-20250514` |
| Google | `gemini-2.5-flash`, `gemini-3-flash-preview` |
| OpenAI | `gpt-4o`, `gpt-4-turbo` |

## 📊 Example Workflow

```
1. Initialize Evolution
   └─ Create workspace (isolated copy of repo)
   └─ Get baseline score from evaluator

2. Generation 1 (10 agents in parallel)
   ├─ Agent 1 (analyzer): Identifies bottlenecks
   │  └─ Proposes refactoring → Tests → Score improves! ✓
   ├─ Agent 2 (optimizer): Tweaks parameters
   │  └─ Proposes changes → Tests → No improvement ✗
   ├─ Agent 3 (feature): Adds caching
   │  └─ Proposes changes → Tests → Score improves! ✓
   └─ ...more agents...

3. Generation 2
   └─ Builds on successful changes from Gen 1
   └─ Proposes additional improvements

4. Results
   └─ All improvements committed to git
   └─ Fitness curve plotted
   └─ Summary report generated
```

## 🔧 Development

### Project Structure

```
optifiner/
├── apps/
│   ├── web/              # React frontend UI
│   └── api/              # FastAPI backend
├── services/
│   └── worker/           # LangGraph evolution agent
├── packages/
│   └── shared/           # Shared utilities
├── examples/             # Example projects
├── infra/               # Docker & deployment
├── docs/                # Documentation
└── scripts/             # Utility scripts
```

### Building from Source

```bash
# Install all dependencies
npm install -ws

# Run linter
npm run lint -ws

# Run tests
npm run test -ws

# Build everything
npm run build -ws
```

### Docker

```bash
# Build all images
docker-compose build

# Start all services
docker-compose up

# View logs
docker-compose logs -f worker
```

## 🤝 Contributing

We welcome contributions! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/your-feature`)
3. Commit your changes (`git commit -am 'Add your feature'`)
4. Push to the branch (`git push origin feature/your-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- Built with [LangGraph](https://langchain-ai.github.io/langgraph/) for agent orchestration
- Powered by leading LLM providers: Anthropic, Google, and OpenAI
- UI inspired by modern DevOps dashboards

## 💬 Support & Community

- **Issues**: Report bugs on [GitHub Issues](https://github.com/yourusername/optifiner/issues)
- **Discussions**: Join our [GitHub Discussions](https://github.com/yourusername/optifiner/discussions)
- **Documentation**: See the [docs](docs/) folder for detailed guides

## 🚦 Status

- ✅ Core evolution engine working
- ✅ Multi-agent orchestration with LangGraph
- ✅ React web dashboard
- 🔄 Full API backend (in progress)
- 🔄 Distributed task queue (in progress)
- 📋 Production deployment guide

---

**Start evolving your code today!** 🧬
