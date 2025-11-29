"""
Pytest configuration and shared fixtures for AGI-Sentinel tests.
"""

import pytest
import os
import tempfile
import sqlite3
from pathlib import Path


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.db', delete=False) as f:
        db_path = f.name
    
    # Initialize schema
    from tools.db import ensure_db
    ensure_db(db_path)
    
    yield db_path
    
    # Cleanup
    try:
        os.unlink(db_path)
        # Also remove WAL files if they exist
        for ext in ['-shm', '-wal']:
            wal_file = db_path + ext
            if os.path.exists(wal_file):
                os.unlink(wal_file)
    except Exception:
        pass


@pytest.fixture
def sample_fda_events():
    """Sample FDA event data for testing."""
    return [
        {
            "safetyreportid": "12345",
            "receivedate": "20230101",
            "patient": {
                "drug": [
                    {"medicinalproduct": "ASPIRIN"}
                ],
                "reaction": [
                    {"reactionmeddrapt": "HEADACHE"},
                    {"reactionmeddrapt": "NAUSEA"}
                ]
            }
        },
        {
            "safetyreportid": "12346",
            "receivedate": "20230108",
            "patient": {
                "drug": [
                    {"medicinalproduct": "ASPIRIN"}
                ],
                "reaction": [
                    {"reactionmeddrapt": "HEADACHE"}
                ]
            }
        },
        {
            "safetyreportid": "12347",
            "receivedate": "20230115",
            "patient": {
                "drug": [
                    {"medicinalproduct": "ASPIRIN"}
                ],
                "reaction": [
                    {"reactionmeddrapt": "DIZZINESS"}
                ]
            }
        }
    ]


@pytest.fixture
def mock_config(monkeypatch):
    """Mock configuration for testing."""
    monkeypatch.setenv("USE_GEMINI", "false")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("OPENFDA_TIMEOUT", "5")
    monkeypatch.setenv("OPENFDA_MAX_RETRIES", "2")
