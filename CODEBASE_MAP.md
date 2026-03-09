# Optifiner Codebase Map

Optifiner is a self-evolving code framework that uses multi-agent AI systems (built on LangGraph) to automatically improve codebases through benchmark-driven optimization.

## 🏗️ Project Architecture

The codebase is organized into three primary layers, plus examples and infrastructure.

### 1. Core Evolution Engine (`services/worker/`)
The heart of the project where the AI agents reside.
- **`src/worker/agent.py`**: **Graph Orchestrator** - Defines the LangGraph nodes (`agent`, `tools`, `retry`) and conditional edges for the evolution loop.
- **`src/worker/state.py`**: **Persistence Layer** - Defines `AgentState` with conversation messages and evolution metrics (baseline vs. current score).
- **`src/worker/evaluator.py`**: **Execution Guard** - Queue-based evaluator that runs benchmarks on the host machine safely.
- **`src/worker/workspace.py`**: **Isolation Manager** - Manages isolated workspace copies in `/tmp/optifiner_workspaces/` for safe agent execution.
- **`src/worker/tools/`**: **Agent Capabilities** - A suite of tools the agents use:
  - `evaluate.py`: Runs the benchmark script and parses JSON output.
  - `file_edit.py`: Performs precise string replacements in files.
  - `grep.py`: Regex search tool using ripgrep.
  - `run_bash.py` / `run_python.py`: Execution environments for testing.
- **`src/worker/prompts.py`**: **Instruction Set** - System prompts for specialized agents (Analyzer, Optimizer, Refactorer).
- **`src/worker/cli.py`**: **Entry Point** - Main CLI interface for running multi-agent runs.

### 2. API Backend (`apps/api/`)
A FastAPI-based service that exposes the evolution engine to the web.
- **`src/optifiner_api/main.py`**: **Server Entry** - Configures FastAPI app, CORS, and WebSocket endpoints (`/ws/workflow/{id}`).
- **`src/optifiner_api/api/optimization.py`**: **Workflow Router** - REST endpoints for starting and managing optimization workflows.
- **`src/optifiner_api/services/optimization_service.py`**: **Bridge Service** - Orchestrates the worker logic and manages real-time updates.
- **`src/optifiner_api/websocket.py`**: **Real-time Hub** - Broadcasts agent status, logs, and score improvements.
- **`src/optifiner_api/github_service.py`**: **Git Manager** - Handles repo cloning and Pull Request creation.

### 3. Web Frontend (`apps/web/`)
A React-based dashboard for real-time monitoring.
- **`src/main.tsx`**: **App Entry** - React application entry point and routing setup.
- **`src/pages/EvolutionMonitor.tsx`**: **Visualizer** - Displays the interactive **Phylogenetic Tree** showing agent branching and improvements.
- **`src/store/index.ts`**: **State Management** - Zustand store coordinating WebSocket updates with the UI.
- **`src/components/ui/Button.tsx`**: **Standardized Component** - Unified button component supporting both dashboard and landing page variants.

### 4. Examples & Infrastructure
- **`examples/snake_game/`**: Demo optimizing a snake AI based on survival metrics.
- **`examples/volumetric_particle_sim/`**: Demo optimizing software rendering for FPS.
- **`infra/docker/Dockerfile`**: **Unified Dockerfile** - Multi-stage build for API, Worker, and Web services.
- **`infra/compose/docker-compose.yml`**: Orchestrates the full stack with shared volumes.

## 🔄 Request-to-Result Flow
1. **Frontend**: User initiates optimization in `EvolutionMonitor.tsx`.
2. **API**: `optimization_service.py` clones the repo and starts the **Evolution Loop**.
3. **Worker**: `cli.py` spawns parallel agents using `agent.py`.
4. **Agent**: Reads code, proposes changes, and validates them via `evaluate.py`.
5. **Real-time**: Improvements are broadcast via `websocket.py` and rendered as new nodes in the Phylogenetic Tree.
