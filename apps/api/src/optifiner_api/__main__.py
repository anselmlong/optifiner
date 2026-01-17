"""Entry point for running the API server."""

import os

# Fix gRPC fork warning: "Other threads are currently calling into gRPC, skipping fork()"
# This must be set before any gRPC imports (langchain-google-genai uses gRPC internally)
os.environ.setdefault("GRPC_ENABLE_FORK_SUPPORT", "1")

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "optifiner_api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
