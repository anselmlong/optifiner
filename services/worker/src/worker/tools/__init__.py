"""Tools for the evolution agent.

Note: run_bash and run_python are NOT available to evolution agents to prevent
them from tampering with benchmarks or running arbitrary code. However, these
tools ARE available to the Benchmark Builder Agent (see benchmark_builder.py)
which needs them to test and iterate on the benchmark script.
"""

from worker.tools.file_read import read_file
from worker.tools.file_write import write_file
from worker.tools.file_edit import edit_file
from worker.tools.multi_edit import multi_edit
from worker.tools.grep import grep
from worker.tools.glob import glob_search
from worker.tools.list_dir import list_dir
# Execution tools - NOT available to evolution agents (prevents benchmark tampering)
# Available to Benchmark Builder Agent via benchmark_builder.py
# from worker.tools.run_python import run_python, run_python_file
# from worker.tools.run_bash import run_bash
from worker.tools.evaluate import evaluate, set_evaluator, get_evaluator

__all__ = [
    "read_file",
    "write_file",
    "edit_file",
    "multi_edit",
    "grep",
    "glob_search",
    "list_dir",
    # Execution tools available via direct import for benchmark builder:
    # "run_python",
    # "run_python_file",
    # "run_bash",
    "evaluate",
    "set_evaluator",
    "get_evaluator",
]


def get_all_tools():
    """Return all available tools for evolution agents.
    
    Note: This does NOT include run_bash, run_python as those are restricted
    to prevent benchmark tampering. Evolution agents can only read/write files
    and call the evaluate() function.
    """
    return [
        read_file,
        write_file,
        edit_file,
        multi_edit,
        grep,
        glob_search,
        list_dir,
        # NOT included for evolution agents - prevents benchmark tampering:
        # run_python,
        # run_python_file,
        # run_bash,
        evaluate,
    ]


def get_benchmark_builder_tools():
    """Return all tools available to the Benchmark Builder Agent.
    
    This includes execution tools (run_bash, run_python) which are needed
    to test and iterate on the benchmark script.
    """
    from worker.tools.run_python import run_python, run_python_file
    from worker.tools.run_bash import run_bash
    
    return [
        read_file,
        write_file,
        edit_file,
        multi_edit,
        grep,
        glob_search,
        list_dir,
        run_python,
        run_python_file,
        run_bash,
        # Note: evaluate is NOT included - benchmark builder creates the evaluator
    ]
