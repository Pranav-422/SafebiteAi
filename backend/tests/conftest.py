import importlib
import os
import sys

import pytest

BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@pytest.fixture(scope="session")
def appmod(tmp_path_factory):
    """Import app.py against a fresh temporary database (exactly like a fresh clone)."""
    db = tmp_path_factory.mktemp("db") / "safebite.db"
    os.environ.update({
        "JWT_SECRET": "test-secret-" + "x" * 40,
        "DATABASE_PATH": str(db),
        "CORS_ORIGINS": "http://localhost:3000",
        # generous limits so the suite itself isn't throttled; login-per-email stays strict
        "REGISTER_RATE_LIMIT": "10000 per hour",
        "LOGIN_IP_RATE_LIMIT": "10000 per minute",
        "ANALYZE_RATE_LIMIT": "10000 per minute",
        "OCR_RATE_LIMIT": "10000 per minute",
        "DEFAULT_RATE_LIMIT": "100000 per minute",
    })
    sys.path.insert(0, BACKEND)
    sys.modules.pop("app", None)
    mod = importlib.import_module("app")
    mod.app.testing = True
    return mod


@pytest.fixture(scope="session")
def client(appmod):
    return appmod.app.test_client()
