"""Runtime entrypoint for container platforms such as Cloud Run."""

from __future__ import annotations

import os

import uvicorn


def run() -> None:
    """Start the ASGI server with Cloud Run-compatible defaults."""
    port = int(os.getenv("PORT", "8080"))
    uvicorn.run("tlvflow.api.app:app", host="0.0.0.0", port=port)


if __name__ == "__main__":
    run()
