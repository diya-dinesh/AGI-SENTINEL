"""
AnalyzerAgent: Statistical Signal Detection Agent for AGI-Sentinel

AGENT ROLE: Performs statistical analysis on adverse event data to detect safety signals.
This agent implements pharmacovigilance signal detection using z-score and relative
increase algorithms to identify unusual patterns in adverse event reporting.

RESPONSIBILITIES:
- Load adverse event reports from database
- Compute weekly reaction counts and baseline statistics
- Detect statistical signals using dual-threshold approach:
  * Z-score threshold (default: 2.0) - identifies statistical outliers
  * Relative increase threshold (default: 1.5x) - identifies meaningful increases
- Return ranked list of detected safety signals

ALGORITHM:
The signal detection uses a baseline comparison approach:
1. Calculate mean and std dev of weekly reaction counts (baseline period)
2. Compare recent week counts against baseline
3. Flag signals where: (count - mean) / std > z_threshold AND count/mean > relative_threshold

INTEGRATION:
- Uses tools.analysis_tools.load_reports to fetch data
- Uses tools.analysis_tools.detect_spikes for signal detection
- Called by orchestrator after IngestAgent completes
"""

from typing import Dict, Any, List
from tools.analysis_tools import load_reports, detect_spikes
import logging
import datetime

logger = logging.getLogger("AnalyzerAgent")
logging.basicConfig(level=logging.INFO, format="[%(name)s] %(message)s")


class AnalyzerAgent:
    """
    Agent responsible for statistical signal detection in adverse event data.
    
    This agent implements the core pharmacovigilance analysis, using statistical
    methods to identify adverse events that occur at higher-than-expected rates
    for a given drug.
    
    Attributes:
        db_path (str): Path to SQLite database containing adverse event reports
        name (str): Agent identifier for logging and tracking
    """
    
    def __init__(self, db_path: str):
        """
        Initialize AnalyzerAgent with database configuration.
        
        Args:
            db_path: Path to SQLite database file containing adverse event reports
        """
        self.db_path = db_path
        self.name = "AnalyzerAgent"

    def analyze(self, drug_name: str) -> Dict[str, Any]:
        """
        Analyze adverse event reports for a drug to detect safety signals.
        
        This method performs the complete signal detection workflow:
        1. Load all adverse event reports for the drug from database
        2. Compute weekly reaction counts and statistical baselines
        3. Detect signals using z-score and relative increase thresholds
        4. Return ranked list of detected signals
        
        The signal detection algorithm identifies reactions that show both:
        - Statistical significance (z-score > threshold)
        - Clinical significance (relative increase > threshold)
        
        Args:
            drug_name: Name of the drug to analyze
        
        Returns:
            Dictionary containing analysis results:
                - agent: Agent name ("AnalyzerAgent")
                - drug: Drug name that was analyzed
                - signals: List of detected signals, each containing:
                    * reaction: Adverse event name
                    * z_score: Statistical z-score
                    * relative_increase: Ratio vs baseline
                    * recent_count: Count in recent period
                    * baseline_mean: Average count in baseline period
                - stored_reports: Total number of reports analyzed
        
        Example:
            >>> agent = AnalyzerAgent("data/adsio.db")
            >>> result = agent.analyze("aspirin")
            >>> print(f"Detected {len(result['signals'])} signals from {result['stored_reports']} reports")
        """
        logger.info(f"analyzing reports for '{drug_name}'...")
        
        # Load all adverse event reports for this drug from database
        df = load_reports(self.db_path, drug_name)
        
        if df.empty:
            logger.info("no reports found for analysis")
            return {
                "agent": self.name,
                "drug": drug_name,
                "signals": [],
                "stored_reports": 0
            }
        
        # Perform statistical signal detection
        # detect_spikes computes z-scores and relative increases for each reaction
        signals = detect_spikes(df)
        
        logger.info(f"analysis complete. signals={len(signals)}")
        return {
            "agent": self.name,
            "drug": drug_name,
            "signals": signals,
            "stored_reports": len(df)
        }
