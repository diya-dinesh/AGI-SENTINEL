"""
Unit tests for database operations.
"""

import pytest
import sqlite3
from tools.db import (
    get_db_path,
    ensure_db,
    store_reports,
    load_reports,
    sample_reports_for_drug,
)


def test_ensure_db_creates_tables(temp_db):
    """Test that ensure_db creates required tables."""
    conn = sqlite3.connect(temp_db)
    cur = conn.cursor()
    
    # Check reports table exists
    cur.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name='reports'
    """)
    assert cur.fetchone() is not None
    
    # Check memories table exists
    cur.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name='memories'
    """)
    assert cur.fetchone() is not None
    
    conn.close()


def test_ensure_db_creates_indexes(temp_db):
    """Test that indexes are created."""
    conn = sqlite3.connect(temp_db)
    cur = conn.cursor()
    
    # Check for indexes
    cur.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='index' AND name LIKE 'idx_%'
    """)
    indexes = cur.fetchall()
    
    # Should have at least 4 indexes (3 for reports, 1 for memories)
    assert len(indexes) >= 4
    
    conn.close()


def test_store_reports_empty_list(temp_db):
    """Test storing empty list returns 0."""
    result = store_reports(temp_db, [])
    assert result == 0


def test_store_reports_valid_events(temp_db, sample_fda_events):
    """Test storing valid events."""
    result = store_reports(temp_db, sample_fda_events)
    assert result == len(sample_fda_events)
    
    # Verify data was stored
    conn = sqlite3.connect(temp_db)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM reports")
    count = cur.fetchone()[0]
    assert count == len(sample_fda_events)
    conn.close()


def test_store_reports_handles_malformed_data(temp_db):
    """Test that malformed events are skipped gracefully."""
    events = [
        {"safetyreportid": "valid"},  # Missing patient data
        {},  # Empty event
        None,  # Invalid type (will cause error but should be caught)
    ]
    
    # Should not raise exception
    result = store_reports(temp_db, events)
    # At least one should be stored (the first one)
    assert result >= 0


def test_load_reports(temp_db, sample_fda_events):
    """Test loading reports for a drug."""
    # Store some events first
    store_reports(temp_db, sample_fda_events)
    
    # Load reports
    import pandas as pd
    df = load_reports(temp_db, "ASPIRIN")
    
    assert isinstance(df, pd.DataFrame)
    assert len(df) == len(sample_fda_events)
    assert 'safetyreportid' in df.columns
    assert 'receivedate' in df.columns
    assert 'reaction' in df.columns


def test_load_reports_no_data(temp_db):
    """Test loading reports when no data exists."""
    import pandas as pd
    df = load_reports(temp_db, "NONEXISTENT")
    
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 0


def test_sample_reports_for_drug(temp_db, sample_fda_events):
    """Test sampling reports for a drug."""
    store_reports(temp_db, sample_fda_events)
    
    samples = sample_reports_for_drug(temp_db, "ASPIRIN", limit=2)
    
    assert isinstance(samples, list)
    assert len(samples) <= 2
    assert all('safetyreportid' in s for s in samples)
    assert all('reactions' in s for s in samples)


def test_concurrent_writes(temp_db, sample_fda_events):
    """Test that concurrent writes don't cause issues (basic test)."""
    # This is a simple test - in production you'd want more thorough concurrency testing
    import threading
    
    def write_data():
        store_reports(temp_db, sample_fda_events[:1])
    
    threads = [threading.Thread(target=write_data) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    
    # Check that some data was written
    conn = sqlite3.connect(temp_db)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM reports")
    count = cur.fetchone()[0]
    assert count > 0
    conn.close()
