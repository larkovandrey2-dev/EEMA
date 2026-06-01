import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT_DIR / "backend"

for path in (ROOT_DIR, BACKEND_DIR):
    path_value = str(path)
    if path_value not in sys.path:
        sys.path.insert(0, path_value)

from app.main import app  # noqa: E402
