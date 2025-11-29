"""
IngestAgent: Data Ingestion Agent for AGI-Sentinel

AGENT ROLE: Fetches adverse event data from OpenFDA API and stores it in SQLite database.
This agent is the first step in the multi-agent pipeline, responsible for gathering
raw data that will be analyzed by downstream agents.

RESPONSIBILITIES:
- Query OpenFDA API for drug adverse event reports
- Handle API errors and rate limiting gracefully
- Store fetched reports in normalized database format
- Track ingestion metrics (fetched count, stored count, duration)

INTEGRATION:
- Uses tools.api_tools.get_fda_events for API interaction
- Uses tools.db.store_reports for database storage
- Called by orchestrator as first step in analysis pipeline
"""

import time
from typing import Dict, Any
from tools.api_tools import get_fda_events
from tools.db import store_reports
import logging

logger = logging.getLogger("IngestAgent")
logging.basicConfig(level=logging.INFO, format="[%(name)s] %(message)s")


class IngestAgent:
    """
    Agent responsible for ingesting adverse event data from OpenFDA.
    
    This agent implements the data collection phase of the pharmacovigilance
    pipeline, fetching structured adverse event reports and storing them for
    subsequent analysis.
    
    Attributes:
        db_path (str): Path to SQLite database for storing reports
        name (str): Agent identifier for logging and tracking
    """
    
    def __init__(self, db_path: str):
        """
        Initialize IngestAgent with database configuration.
        
        Args:
            db_path: Path to SQLite database file where reports will be stored
        """
        self.db_path = db_path
        self.name = "IngestAgent"

    def ingest(self, drug_name: str, limit: int = 100) -> Dict[str, Any]:
        """
        Fetch adverse event reports for a drug and store them in the database.
        
        This method performs the complete ingestion workflow:
        1. Query OpenFDA API for adverse events related to the drug
        2. Store fetched reports in SQLite database
        3. Track and return performance metrics
        
        Args:
            drug_name: Name of the drug to fetch adverse events for
            limit: Maximum number of reports to fetch (default: 100, max: 1000)
        
        Returns:
            Dictionary containing ingestion results:
                - agent: Agent name ("IngestAgent")
                - action: Action performed ("ingest")
                - drug: Drug name that was queried
                - fetched: Number of reports fetched from API
                - stored: Number of reports successfully stored in DB
                - duration: Time taken for ingestion in seconds
        
        Example:
            >>> agent = IngestAgent("data/adsio.db")
            >>> result = agent.ingest("aspirin", limit=100)
            >>> print(f"Stored {result['stored']} reports in {result['duration']}s")
        """
        start = time.time()
        logger.info(f"fetching events for '{drug_name}' (limit={limit})...")
        
        # Fetch adverse event reports from OpenFDA API
        events = get_fda_events(drug_name, limit)
        fetched = len(events)
        
        # Store reports in database (handles deduplication internally)
        stored = store_reports(self.db_path, events)
        
        duration = time.time() - start
        logger.info(f"done: fetched={fetched}, stored={stored}, duration={round(duration,1)}s")
        
        return {
            "agent": self.name,
            "action": "ingest",
            "drug": drug_name,
            "fetched": fetched,
            "stored": stored,
            "duration": duration
        }
