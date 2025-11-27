#!/usr/bin/env python3
"""
Run script for the FastAPI server.
This script ensures the correct Python path is set before starting uvicorn.
"""
import sys
from pathlib import Path

# Add the server directory to Python path
server_dir = Path(__file__).parent
if str(server_dir) not in sys.path:
    sys.path.insert(0, str(server_dir))

import uvicorn

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)

