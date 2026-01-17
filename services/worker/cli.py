#!/usr/bin/env python3
"""Standalone CLI entry point - run directly without pip install.

Usage:
    python cli.py <repository> --evaluator <path_to_evaluator>
"""

# CRITICAL: Set gRPC environment variables BEFORE any other imports
# This fixes: "Other threads are currently calling into gRPC, skipping fork()"
import os
os.environ["GRPC_ENABLE_FORK_SUPPORT"] = "1"
os.environ["GRPC_POLL_STRATEGY"] = "poll"  # More compatible with fork()
os.environ["GRPC_VERBOSITY"] = "ERROR"  # Suppress INFO/WARNING messages

import sys
from pathlib import Path

# Add src to path so we can import worker module
_SCRIPT_DIR = Path(__file__).parent.resolve()
_SRC_DIR = _SCRIPT_DIR / "src"
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from worker.cli import main

if __name__ == "__main__":
    main()
