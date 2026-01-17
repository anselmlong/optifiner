"""Tools for the evolution agent."""

from worker.tools.file_read import read_file
from worker.tools.file_write import write_file
from worker.tools.file_edit import edit_file
from worker.tools.multi_edit import multi_edit
from worker.tools.grep import grep
from worker.tools.glob import glob_search
from worker.tools.list_dir import list_dir
from worker.tools.run_python import run_python, run_python_file
from worker.tools.run_bash import run_bash
from worker.tools.evaluate import evaluate, set_evaluator, get_evaluator

__all__ = [
    "read_file",
    "write_file",
    "edit_file",
    "multi_edit",
    "grep",
    "glob_search",
    "list_dir",
    "run_python",
    "run_python_file",
    "run_bash",
    "evaluate",
    "set_evaluator",
    "get_evaluator",
]


def get_all_tools():
    """Return all available tools for the agent."""
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
        evaluate,
    ]
