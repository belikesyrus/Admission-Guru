"""
Admission Guru — Server entry point.
Run:   python start_server.py
Then open:  http://localhost:5000
"""
import sys
import os

# Add backend to Python path
BACKEND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend")
sys.path.insert(0, BACKEND_DIR)

# Import the Flask app (this registers all routes including /api/health)
from app import app

print("=" * 55)
print("  🎓  ADMISSION GURU — Starting Server")
print("=" * 55)
print("  URL  : http://localhost:5000")
print("  Health: http://localhost:5000/api/health")
print("  Press Ctrl+C to stop")
print("=" * 55)

# Run directly (not via app.py's __main__ block, to avoid double-init)
app.run(
    host="0.0.0.0",
    port=5000,
    debug=True,
    use_reloader=False
)
