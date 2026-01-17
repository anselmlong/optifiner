"""Docker-based agent execution.

Runs agents in isolated Docker containers with workspace mounted as volume.
"""

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from rich.console import Console

# Default Docker image name
DOCKER_IMAGE_NAME = "optifiner-worker:latest"
DOCKERFILE_PATH = "infra/docker/Dockerfile.worker"


def get_project_root() -> Path:
    """Get the project root directory (containing infra/)."""
    # Walk up from this file to find the project root
    current = Path(__file__).resolve()
    for _ in range(10):  # Max 10 levels up
        if (current / "infra" / "docker" / "Dockerfile.worker").exists():
            return current
        current = current.parent
    raise RuntimeError("Could not find project root (looking for infra/docker/Dockerfile.worker)")


def image_exists(image_name: str = DOCKER_IMAGE_NAME) -> bool:
    """Check if the Docker image exists locally."""
    try:
        result = subprocess.run(
            ["docker", "image", "inspect", image_name],
            capture_output=True,
            text=True,
        )
        return result.returncode == 0
    except FileNotFoundError:
        raise RuntimeError("Docker is not installed or not in PATH")


def build_image(
    image_name: str = DOCKER_IMAGE_NAME,
    console: Console | None = None,
    force: bool = False,
) -> bool:
    """Build the Docker worker image if it doesn't exist.
    
    Args:
        image_name: Name for the Docker image.
        console: Optional Rich console for output.
        force: Force rebuild even if image exists.
    
    Returns:
        True if image was built or already exists, False on error.
    """
    if not force and image_exists(image_name):
        if console:
            console.print(f"[dim]Docker image {image_name} already exists[/dim]")
        return True
    
    try:
        project_root = get_project_root()
    except RuntimeError as e:
        if console:
            console.print(f"[red]Error: {e}[/red]")
        return False
    
    dockerfile = project_root / DOCKERFILE_PATH
    if not dockerfile.exists():
        if console:
            console.print(f"[red]Dockerfile not found: {dockerfile}[/red]")
        return False
    
    if console:
        console.print(f"[yellow]Building Docker image {image_name}...[/yellow]")
    
    try:
        result = subprocess.run(
            [
                "docker", "build",
                "-t", image_name,
                "-f", str(dockerfile),
                str(project_root),
            ],
            capture_output=True,
            text=True,
        )
        
        if result.returncode != 0:
            if console:
                console.print(f"[red]Docker build failed:[/red]\n{result.stderr}")
            return False
        
        if console:
            console.print(f"[green]Docker image {image_name} built successfully[/green]")
        return True
        
    except Exception as e:
        if console:
            console.print(f"[red]Docker build error: {e}[/red]")
        return False


def run_agent_in_docker(
    workspace: str,
    evaluator_path: str,
    agent_type: str,
    agent_id: str,
    baseline_score: float,
    task: str,
    max_iterations: int,
    model_provider: str,
    model_name: str,
    image_name: str = DOCKER_IMAGE_NAME,
    timeout: int = 600,
    console: Console | None = None,
    baseline_data: dict[str, Any] | None = None,
    verbosity: int = 0,
    stream_output: bool = True,
) -> dict[str, Any]:
    """Run an agent inside a Docker container.
    
    Args:
        workspace: Path to the workspace (will be mounted as volume).
        evaluator_path: Path to the evaluator script.
        agent_type: Type of agent to run.
        agent_id: Unique ID for this agent.
        baseline_score: Current baseline score.
        task: Task description.
        max_iterations: Maximum iterations.
        model_provider: LLM provider.
        model_name: Model name.
        image_name: Docker image to use.
        timeout: Container timeout in seconds.
        console: Optional Rich console for output.
        baseline_data: Optional dict with baseline evaluation data (fps, tests, etc.)
        verbosity: Verbosity level (0=quiet, 1=normal, 2=verbose, 3=debug).
        stream_output: If True, stream container output in real-time.
    
    Returns:
        Dict with agent result including success, score, error, etc.
    """
    workspace_path = Path(workspace).resolve()
    evaluator_abs = Path(evaluator_path).resolve()
    
    # Create a temp directory for the evaluator inside the container
    # We need to mount both workspace and evaluator
    evaluator_dir = evaluator_abs.parent
    evaluator_name = evaluator_abs.name
    
    # Prepare environment variables for the container
    env_vars = {
        "WORKSPACE_ROOT": "/workspace",
        "AGENT_TYPE": agent_type,
        "AGENT_ID": agent_id,
        "BASELINE_SCORE": str(baseline_score),
        "MAX_ITERATIONS": str(max_iterations),
        "MODEL_PROVIDER": model_provider,
        "MODEL_NAME": model_name,
        "TASK": task,
        "EVALUATOR_PATH": f"/evaluator/{evaluator_name}",
        "VERBOSITY": str(verbosity),
    }
    
    # Pass API keys from environment
    for key in ["ANTHROPIC_API_KEY", "GOOGLE_API_KEY", "OPENAI_API_KEY"]:
        if os.environ.get(key):
            env_vars[key] = os.environ[key]
    
    # Pass baseline data as JSON if provided
    if baseline_data:
        env_vars["BASELINE_DATA"] = json.dumps(baseline_data)
    
    # Build docker run command
    cmd = [
        "docker", "run",
        "--rm",  # Remove container after exit
        "--name", f"optifiner-{agent_id}",
    ]
    
    # Add environment variables
    for key, value in env_vars.items():
        cmd.extend(["-e", f"{key}={value}"])
    
    # Mount volumes
    cmd.extend([
        "-v", f"{workspace_path}:/workspace",
        "-v", f"{evaluator_dir}:/evaluator:ro",
    ])
    
    # Set resource limits
    cmd.extend([
        "--memory", "2g",
        "--cpus", "2",
    ])
    
    # Image and command
    cmd.extend([
        image_name,
        "python", "-u", "-m", "worker.docker_entrypoint",  # -u for unbuffered output
    ])
    
    if console:
        console.print(f"[dim]Running agent {agent_id} in Docker container...[/dim]")
    
    try:
        if stream_output and console:
            # Use Popen to stream output in real-time
            import threading
            import time as time_module
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,  # Line buffered
            )
            
            output_lines: list[str] = []
            
            def read_output():
                for line in iter(process.stdout.readline, ''):
                    if line:
                        output_lines.append(line)
                        # Print non-JSON lines (logs) directly - they already have ANSI colors
                        stripped = line.strip()
                        if stripped and not stripped.startswith('{"'):
                            # Use print() directly to preserve ANSI escape codes from container
                            print(f"  {stripped}", flush=True)
                process.stdout.close()
            
            # Start output reader thread
            reader = threading.Thread(target=read_output, daemon=True)
            reader.start()
            
            # Wait with timeout
            start_time = time_module.time()
            while process.poll() is None:
                if time_module.time() - start_time > timeout:
                    process.kill()
                    subprocess.run(["docker", "kill", f"optifiner-{agent_id}"], capture_output=True)
                    return {
                        "agent_id": agent_id,
                        "success": False,
                        "score": baseline_score,
                        "error": f"Container timed out after {timeout} seconds",
                    }
                time_module.sleep(0.1)
            
            reader.join(timeout=2)
            stdout = ''.join(output_lines)
            returncode = process.returncode
        else:
            # Non-streaming mode (for parallel execution or quiet mode)
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            stdout = result.stdout
            stderr = result.stderr
            returncode = result.returncode
            # In non-streaming, combine stderr with stdout for error reporting
            if stderr and returncode != 0:
                stdout = stdout + "\n" + stderr if stdout else stderr
        
        stdout = stdout.strip()
        
        # Find the JSON result in output (may have other logs before it)
        json_start = stdout.rfind('{"')
        if json_start >= 0:
            try:
                return json.loads(stdout[json_start:])
            except json.JSONDecodeError:
                pass
        
        # If no JSON, return based on exit code
        if returncode == 0:
            return {
                "agent_id": agent_id,
                "success": True,
                "score": baseline_score,
                "error": None,
                "output": stdout,
            }
        else:
            return {
                "agent_id": agent_id,
                "success": False,
                "score": baseline_score,
                "error": stdout or f"Container exited with code {returncode}",
            }
            
    except subprocess.TimeoutExpired:
        # Kill the container
        subprocess.run(["docker", "kill", f"optifiner-{agent_id}"], capture_output=True)
        return {
            "agent_id": agent_id,
            "success": False,
            "score": baseline_score,
            "error": f"Container timed out after {timeout} seconds",
        }
    except Exception as e:
        return {
            "agent_id": agent_id,
            "success": False,
            "score": baseline_score,
            "error": str(e),
        }


def stop_container(agent_id: str) -> bool:
    """Stop a running container by agent ID.
    
    Args:
        agent_id: The agent ID used to name the container.
    
    Returns:
        True if container was stopped, False otherwise.
    """
    try:
        result = subprocess.run(
            ["docker", "stop", f"optifiner-{agent_id}"],
            capture_output=True,
            timeout=10,
        )
        return result.returncode == 0
    except Exception:
        return False


def cleanup_containers(prefix: str = "optifiner-") -> int:
    """Stop and remove all containers with the given prefix.
    
    Args:
        prefix: Container name prefix to match.
    
    Returns:
        Number of containers stopped.
    """
    try:
        # List running containers
        result = subprocess.run(
            ["docker", "ps", "-q", "--filter", f"name={prefix}"],
            capture_output=True,
            text=True,
        )
        
        if result.returncode != 0 or not result.stdout.strip():
            return 0
        
        container_ids = result.stdout.strip().split("\n")
        
        # Stop them
        if container_ids:
            subprocess.run(
                ["docker", "stop"] + container_ids,
                capture_output=True,
            )
        
        return len(container_ids)
    except Exception:
        return 0
