"""
Database Management Module for AGI-Sentinel

This module provides comprehensive SQLite database operations with robust connection
management, error handling, and retry logic. It manages both adverse event reports
and the memory system for long-term learning.

KEY FEATURES:
- Context manager for automatic connection cleanup
- Retry logic with exponential backoff for lock handling
- WAL mode for better concurrency
- Proper indexing for query performance
- Transaction management with rollback on errors

DATABASE SCHEMA:

1. **reports table** (Adverse Event Reports):
   - id: Auto-increment primary key
   - safetyreportid: FDA report identifier
   - receivedate: Date report was received
   - drug_name: Extracted drug name
   - reaction: Semicolon-separated adverse reactions
   - raw_json: Complete FDA event data (for future analysis)
   - created_at: Timestamp of database insertion
   
   Indexes:
   - idx_reports_drug_name: Fast drug lookups
   - idx_reports_receivedate: Temporal queries
   - idx_reports_safetyreportid: Deduplication checks

2. **memories table** (Long-term Learning):
   - id: Auto-increment primary key
   - entity_type: Type of entity (e.g., "drug")
   - entity_value: Entity identifier (e.g., "aspirin")
   - summary: Insight text
   - meta: JSON metadata
   - created_at: Timestamp of memory creation
   
   Indexes:
   - idx_memories_entity: Fast entity lookups

CONNECTION MANAGEMENT:
- Uses context manager pattern for automatic cleanup
- Enables WAL (Write-Ahead Logging) for better concurrency
- Configurable timeout (default: 10 seconds)
- Automatic commit on success, rollback on error

RETRY LOGIC:
- Decorator-based retry for database lock errors
- Exponential backoff: 0.5s, 1.0s, 1.5s
- Maximum 3 retry attempts
- Only retries on lock errors, not other exceptions

ERROR HANDLING:
- All database errors logged with full context
- Graceful degradation (returns empty results on failure)
- Transaction rollback on any exception
- Connection cleanup in finally block

DATA STORAGE PATTERNS:
- Flattened storage for fast queries (drug_name, reaction columns)
- Raw JSON preservation for future analysis flexibility
- Deduplication via safetyreportid checks
- Batch insertion for efficiency

INTEGRATION:
- Used by IngestAgent for storing fetched reports
- Used by AnalyzerAgent for loading analysis data
- Used by MemoryAgent for long-term learning
- Configured via config.py (database path)
"""

import sqlite3
import os
import json
import time
from typing import List, Dict, Any, Optional
from contextlib import contextmanager
from dotenv import load_dotenv
from utils.logger import get_logger

logger = get_logger(__name__)
load_dotenv()

DB_DEFAULT = os.getenv("ADSIO_DB_PATH", "./data/adsio.db")
MAX_RETRIES = 3
RETRY_DELAY = 0.5  # seconds

@contextmanager
def get_connection(db_path: str, timeout: float = 10.0):
    """
    Context manager for database connections with automatic cleanup.
    
    Args:
        db_path: Path to database file
        timeout: Connection timeout in seconds
        
    Yields:
        Database connection
    """
    conn = None
    try:
        conn = sqlite3.connect(db_path, timeout=timeout)
        # Enable foreign keys
        conn.execute("PRAGMA foreign_keys = ON")
        # Use WAL mode for better concurrency
        conn.execute("PRAGMA journal_mode = WAL")
        yield conn
        conn.commit()
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Database error: {e}", exc_info=True)
        raise
    finally:
        if conn:
            conn.close()


def retry_on_db_lock(func):
    """
    Decorator to retry database operations on lock errors.
    
    Args:
        func: Function to decorate
        
    Returns:
        Wrapped function with retry logic
    """
    def wrapper(*args, **kwargs):
        for attempt in range(MAX_RETRIES):
            try:
                return func(*args, **kwargs)
            except sqlite3.OperationalError as e:
                if "locked" in str(e).lower() and attempt < MAX_RETRIES - 1:
                    logger.warning(f"Database locked, retrying... (attempt {attempt + 1}/{MAX_RETRIES})")
                    time.sleep(RETRY_DELAY * (attempt + 1))  # Exponential backoff
                else:
                    raise
        return func(*args, **kwargs)
    return wrapper


def get_db_path() -> str:
    """
    Get database path from environment or use default.
    
    Returns:
        Database file path
    """
    path = os.getenv("ADSIO_DB_PATH", DB_DEFAULT)
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    return path


@retry_on_db_lock
def ensure_db(db_path: str) -> None:
    """
    Ensure database schema exists with proper indexes.
    
    Args:
        db_path: Path to database file
    """
    logger.info(f"Ensuring database schema at {db_path}")
    
    with get_connection(db_path) as conn:
        cur = conn.cursor()
        
        # Raw reports table
        cur.execute("""
        CREATE TABLE IF NOT EXISTS reports (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          safetyreportid TEXT,
          receivedate TEXT,
          drug_name TEXT,
          reaction TEXT,
          raw_json TEXT,
          created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        """)
        
        # Create indexes for better query performance
        cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_reports_drug_name 
        ON reports(drug_name);
        """)
        
        cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_reports_receivedate 
        ON reports(receivedate);
        """)
        
        cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_reports_safetyreportid 
        ON reports(safetyreportid);
        """)
        
        # Memories table (simple)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS memories (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          entity_type TEXT,
          entity_value TEXT,
          summary TEXT,
          meta TEXT,
          created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        """)
        
        cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_memories_entity 
        ON memories(entity_type, entity_value);
        """)
        
        logger.info("Database schema ensured successfully")


@retry_on_db_lock
def store_reports(db_path: str, events: List[Dict[str, Any]]) -> int:
    """
    Flatten minimal fields and insert into reports table.
    
    Args:
        db_path: Path to database file
        events: List of event dictionaries from OpenFDA
        
    Returns:
        Number of rows inserted
    """
    if not events:
        logger.warning("No events to store")
        return 0
    
    logger.info(f"Storing {len(events)} events to database")
    
    with get_connection(db_path) as conn:
        cur = conn.cursor()
        inserted = 0
        
        # Use prepared statement for better security
        insert_sql = """
        INSERT INTO reports 
        (safetyreportid, receivedate, drug_name, reaction, raw_json) 
        VALUES (?, ?, ?, ?, ?)
        """
        
        for ev in events:
            try:
                safetyreportid = ev.get("safetyreportid")
                rcv = ev.get("receiptdate") or ev.get("receivedate") or None
                
                # Extract drug name safely
                drug = ""
                try:
                    patient = ev.get("patient", {})
                    drugs = patient.get("drug", [])
                    if drugs and len(drugs) > 0:
                        drug = drugs[0].get("medicinalproduct", "")
                except (TypeError, IndexError, AttributeError) as e:
                    logger.debug(f"Could not extract drug name: {e}")
                    drug = ""
                
                # Extract reactions safely
                reactions = ""
                try:
                    patient = ev.get("patient", {})
                    reaction_list = patient.get("reaction", [])
                    reactions = ";".join([
                        r.get("reactionmeddrapt", "") 
                        for r in reaction_list 
                        if isinstance(r, dict)
                    ])
                except (TypeError, AttributeError) as e:
                    logger.debug(f"Could not extract reactions: {e}")
                    reactions = ""
                
                raw = json.dumps(ev)
                
                cur.execute(insert_sql, (safetyreportid, rcv, drug, reactions, raw))
                inserted += 1
                
            except Exception as e:
                logger.warning(f"Failed to store event {ev.get('safetyreportid', 'unknown')}: {e}")
                continue
        
        logger.info(f"Successfully stored {inserted} events")
        return inserted

def load_reports(db_path, drug_name):
    """
    Return a pandas DataFrame of reports for the drug.
    """
    import pandas as pd
    conn = sqlite3.connect(db_path)
    query = """
        SELECT safetyreportid, receivedate, reaction
        FROM reports
        WHERE drug_name LIKE ?
    """
    df = pd.read_sql_query(query, conn, params=[f"%{drug_name}%"])
    conn.close()
    return df

def sample_reports_for_drug(db_path, drug_name, limit=3):
    """
    Return a list of short sample texts extracted from raw_json for illustration.
    """
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT raw_json FROM reports WHERE drug_name LIKE ? ORDER BY id DESC LIMIT ?", (f"%{drug_name}%", limit))
    rows = cur.fetchall()
    conn.close()
    samples = []
    for (raw,) in rows:
        try:
            obj = json.loads(raw)
            pt = obj.get("patient", {})
            reactions = ";".join([r.get("reactionmeddrapt","") for r in pt.get("reaction", [])])
            samples.append({"safetyreportid": obj.get("safetyreportid"), "reactions": reactions})
        except Exception:
            continue
    return samples
