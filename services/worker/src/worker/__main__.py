"""Entry point for running the evolution worker."""

import sys


def main():
    """Main entry point - delegates to CLI."""
    from worker.cli import main as cli_main
    cli_main()


if __name__ == "__main__":
    main()
