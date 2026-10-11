"""Backend directory FastAPI entry-point for Bhumi Vikas Sahayak.

Enables Render to start the application when the Root Directory is set to `backend`:
  uvicorn main:app --host 0.0.0.0 --port $PORT
"""
import sys
from pathlib import Path

# Ensure repository root is on sys.path so `backend.app...` imports and data path resolve
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.app.main import app

__all__ = ["app"]

if __name__ == "__main__":
    import os
    import uvicorn

    port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "0.0.0.0")
    uvicorn.run("main:app", host=host, port=port)
