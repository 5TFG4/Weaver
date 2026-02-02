"""Weaver Entry Point

Run with: uvicorn weaver:app --reload
Or: python -m weaver
"""

import os

import uvicorn

from src.glados.app import create_app

# Create the FastAPI application
app = create_app()


def main() -> None:
    """Start the Weaver API server."""
    uvicorn.run(
        "weaver:app",
        host=os.getenv("WEAVER_HOST", "127.0.0.1"),
        port=int(os.getenv("WEAVER_PORT", "8000")),
        reload=os.getenv("WEAVER_RELOAD", "true").lower() == "true",
    )


if __name__ == "__main__":
    main()
