import sys
import os
import traceback

# This file is used by Vercel Serverless Functions to host the FastAPI app.
try:
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if root_dir not in sys.path:
        sys.path.insert(0, root_dir)

    from main import app

except Exception as e:
    # If ANYTHING fails during import (like missing modules, ValueError, etc.),
    # Vercel will normally crash and return a generic 500.
    # By catching it and creating a dummy FastAPI app, we can see the exact error!
    from fastapi import FastAPI
    from fastapi.responses import JSONResponse
    
    err_str = traceback.format_exc()
    app = FastAPI()
    
    @app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
    async def catch_all(path: str):
        return JSONResponse(
            status_code=500,
            content={"detail": f"Vercel Backend Crash on Boot:\n{err_str}"}
        )

