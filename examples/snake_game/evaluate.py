#!/usr/bin/env python3
"""Evaluator for the Snake AI.

This script runs the Snake AI benchmark and outputs the score.
It's designed to be used with the evolution CLI.

Output format: JSON with a "score" field.
"""

import json
import sys
import random

# Set fixed seed for reproducibility
random.seed(42)

# Import the snake AI from the same directory
from snake_ai import benchmark


def main():
    """Run the benchmark and output the score."""
    try:
        # Run benchmark with fixed parameters
        avg_score = benchmark(num_games=20, grid_size=20)

        # Output as JSON
        result = {
            "score": avg_score,
            "metrics": {
                "avg_score": avg_score,
                "num_games": 20,
                "grid_size": 20,
            },
            "passed": True,
        }
        print(json.dumps(result))

    except Exception as e:
        result = {
            "score": 0,
            "passed": False,
            "error": str(e),
        }
        print(json.dumps(result))
        sys.exit(1)


if __name__ == "__main__":
    main()
