"""
backend/main.py
===============
Entry point exposing the unified TraceVeil FastAPI application.
"""

from .app.main import app

__all__ = ["app"]

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8000, reload=True)