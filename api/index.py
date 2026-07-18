import sys
import os

root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from main import app

# This file is used by Vercel Serverless Functions to host the FastAPI app.
# The 'app' object imported from 'main.py' is what Vercel mounts.
