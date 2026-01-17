"""Entry point for running the evolution worker."""

import os

# Fix gRPC fork warning: "Other threads are currently calling into gRPC, skipping fork()"
# This must be set before any gRPC imports (langchain-google-genai uses gRPC internally)
os.environ.setdefault("GRPC_ENABLE_FORK_SUPPORT", "1")


def main():
    """Main entry point - delegates to CLI."""
    from worker.cli import main as cli_main
    cli_main()


if __name__ == "__main__":
    main()
