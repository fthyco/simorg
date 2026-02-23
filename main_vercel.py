import os
import sys

# Ensure repo root is on sys.path
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)

# Import the actual FastAPI app from the main backend module
from backend.main import app
