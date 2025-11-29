"""
Simple Memory Storage Module (Legacy)

NOTE: This module is a legacy implementation. The primary memory functionality
is now implemented in agents/memory_agent.py which provides more sophisticated
features including LLM-powered insight extraction and structured memory management.

This module provides basic memory storage and retrieval using SQLite.
It implements a simple key-value store with entity-based indexing.

KEY FEATURES:
- SQLite-based persistent storage
- Entity-type and entity-value indexing
- Naive substring search
- JSON metadata support

SCHEMA:
- id: UUID primary key
- entity_type: Type of entity (e.g., "drug")
- entity_value: Entity identifier (e.g., "aspirin")
- created_at: ISO timestamp
- summary: Memory text content
- meta: JSON metadata

INTEGRATION:
- Legacy module, prefer using agents/memory_agent.py for new code
- Kept for backward compatibility
"""
import sqlite3, os, uuid, json, datetime

MEM_DB = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "memory.db")
os.makedirs(os.path.dirname(MEM_DB), exist_ok=True)
_conn = None

def _get_conn():
    global _conn
    if _conn is None:
        _conn = sqlite3.connect(MEM_DB, check_same_thread=False)
        cur = _conn.cursor()
        cur.execute("""CREATE TABLE IF NOT EXISTS memories (
            id TEXT PRIMARY KEY,
            entity_type TEXT,
            entity_value TEXT,
            created_at TEXT,
            summary TEXT,
            meta TEXT
        )""")
        _conn.commit()
    return _conn

def write_memory(entity_type, entity_value, summary, meta=None):
    conn = _get_conn()
    cur = conn.cursor()
    id = str(uuid.uuid4())
    now = datetime.datetime.utcnow().isoformat()
    cur.execute("INSERT INTO memories (id, entity_type, entity_value, created_at, summary, meta) VALUES (?,?,?,?,?,?)",
                (id, entity_type, entity_value, now, summary, json.dumps(meta or {})))
    conn.commit()
    return id

def search_memory(query, top_k=5):
    # naive search: substring match on entity_value or summary
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, entity_type, entity_value, created_at, summary, meta FROM memories WHERE entity_value LIKE ? OR summary LIKE ? ORDER BY created_at DESC LIMIT ?",
                (f"%{query}%", f"%{query}%", top_k))
    rows = cur.fetchall()
    res = []
    for r in rows:
        res.append({"id": r[0], "entity_type": r[1], "entity_value": r[2], "created_at": r[3], "summary": r[4], "meta": json.loads(r[5] or "{}")})
    return res
