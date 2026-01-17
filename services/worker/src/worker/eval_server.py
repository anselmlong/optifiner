"""Evaluation server that runs on the host.

This server receives evaluation requests from Docker containers and runs
the evaluator locally on the host machine.
"""

import json
import os
import shutil
import subprocess
import sys
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from typing import Any


# Global state
_evaluator_path: str | None = None
_evaluator_timeout: int = 120
_workspace_root: str | None = None
_server: HTTPServer | None = None
_server_thread: threading.Thread | None = None


def _get_python_executable() -> str:
    """Get the Python executable to use for running scripts."""
    if sys.executable:
        return sys.executable
    if shutil.which("python3"):
        return "python3"
    if shutil.which("python"):
        return "python"
    return "python3"


class EvalRequestHandler(BaseHTTPRequestHandler):
    """Handle evaluation requests from Docker containers."""

    def log_message(self, format: str, *args) -> None:
        """Suppress default logging."""
        pass

    def _send_json(self, data: dict, status: int = 200):
        """Send JSON response."""
        response = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(response)))
        self.end_headers()
        self.wfile.write(response)

    def do_POST(self):
        """Handle POST request to /evaluate."""
        if self.path != "/evaluate":
            self._send_json({"error": "Not found"}, 404)
            return

        # Read request body
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode("utf-8")

        try:
            request_data = json.loads(body) if body else {}
        except json.JSONDecodeError:
            self._send_json({"error": "Invalid JSON"}, 400)
            return

        # Get workspace from request (container passes which workspace to evaluate)
        workspace = request_data.get("workspace", _workspace_root)
        if not workspace:
            self._send_json({"error": "No workspace specified"}, 400)
            return

        # Run the evaluator
        result = run_evaluator_local(workspace)
        self._send_json(result)

    def do_GET(self):
        """Handle GET request for health check."""
        if self.path == "/health":
            self._send_json({"status": "ok", "evaluator": _evaluator_path})
        else:
            self._send_json({"error": "Not found"}, 404)


def run_evaluator_local(workspace: str) -> dict[str, Any]:
    """Run the evaluator on the host machine.

    Args:
        workspace: Path to the workspace to evaluate.

    Returns:
        Dict with evaluation result including score, metrics, error.
    """
    global _evaluator_path, _evaluator_timeout

    if not _evaluator_path:
        return {"error": "No evaluator configured", "score": None}

    evaluator = Path(_evaluator_path)
    if not evaluator.exists():
        return {"error": f"Evaluator not found: {evaluator}", "score": None}

    # Determine how to run the evaluator
    if evaluator.suffix == ".py":
        cmd = [_get_python_executable(), str(evaluator), "--quiet"]
    elif evaluator.suffix == ".sh":
        cmd = ["bash", str(evaluator)]
    elif evaluator.suffix in (".js", ".mjs"):
        cmd = ["node", str(evaluator)]
    else:
        cmd = [str(evaluator)]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=_evaluator_timeout,
            cwd=workspace,
            env={**os.environ, "WORKSPACE_ROOT": workspace},
        )

        if result.returncode != 0:
            error_output = result.stderr.strip() if result.stderr else result.stdout.strip()
            return {
                "error": f"Evaluator failed (exit {result.returncode}): {error_output[:500]}",
                "score": None,
            }

        output = result.stdout.strip()

        # Try to parse as JSON
        try:
            data = json.loads(output)
            return data
        except json.JSONDecodeError:
            pass

        # Try to find JSON in output (may have prefix garbage like pygame welcome)
        json_start = output.find("{")
        if json_start >= 0:
            try:
                data = json.loads(output[json_start:])
                return data
            except json.JSONDecodeError:
                pass

        # Try to extract a number
        import re
        numbers = re.findall(r"[-+]?\d*\.?\d+", output)
        if numbers:
            return {"score": float(numbers[0]), "raw": output}

        return {"error": f"Could not parse evaluator output: {output[:200]}", "score": None}

    except subprocess.TimeoutExpired:
        return {"error": f"Evaluator timed out after {_evaluator_timeout} seconds", "score": None}
    except Exception as e:
        return {"error": f"Error running evaluator: {e}", "score": None}


def start_eval_server(
    evaluator_path: str,
    workspace_root: str,
    port: int = 9876,
    timeout: int = 120,
) -> tuple[HTTPServer, threading.Thread]:
    """Start the evaluation server on the host.

    Args:
        evaluator_path: Path to the evaluator script.
        workspace_root: Default workspace root.
        port: Port to listen on.
        timeout: Evaluator timeout in seconds.

    Returns:
        Tuple of (server, thread).
    """
    global _evaluator_path, _evaluator_timeout, _workspace_root, _server, _server_thread

    _evaluator_path = evaluator_path
    _evaluator_timeout = timeout
    _workspace_root = workspace_root

    server = HTTPServer(("0.0.0.0", port), EvalRequestHandler)
    _server = server

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    _server_thread = thread

    return server, thread


def stop_eval_server():
    """Stop the evaluation server."""
    global _server, _server_thread

    if _server:
        _server.shutdown()
        _server = None

    if _server_thread:
        _server_thread.join(timeout=2)
        _server_thread = None


def get_eval_server_url(port: int = 9876) -> str:
    """Get the URL for the evaluation server.

    Returns the host.docker.internal URL for use inside Docker containers.
    """
    return f"http://host.docker.internal:{port}/evaluate"
