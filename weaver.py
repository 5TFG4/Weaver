"""Weaver Entry Point

Run with: uvicorn weaver:app --reload
Or: python -m weaver
"""

import uvicorn

from src.glados.app import create_app

# Create the FastAPI application
app = create_app()


def main() -> None:
    """Start the Weaver API server."""
    uvicorn.run(
        "weaver:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )


if __name__ == "__main__":
    main()
