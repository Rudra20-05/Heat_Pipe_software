import sys, os
root = os.path.dirname(os.path.abspath(__file__))
backend = os.path.join(root, "backend")
if backend not in sys.path:
    sys.path.insert(0, backend)
from app.main import app
