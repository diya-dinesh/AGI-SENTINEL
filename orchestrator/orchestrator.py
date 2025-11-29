"""
Orchestrator for AGI-Sentinel Multi-Agent System.

DESIGN PATTERN: Sequential Agent Pipeline
Coordinates 4 specialized agents to perform automated pharmacovigilance analysis.

AGENT PIPELINE:
1. MemoryAgent   → Retrieves past insights (learning from history)
2. IngestAgent   → Fetches adverse event data from OpenFDA
3. AnalyzerAgent → Detects statistical safety signals
4. ExplainAgent  → Generates LLM-powered intelligence report
5. MemoryAgent   → Stores new insights (creates learning loop)

This orchestrator demonstrates the "Multi-agent System" capstone requirement
by coordinating autonomous agents that collaborate to solve a complex problem.
"""

import os
import datetime
from agents.ingest_agent import IngestAgent
from agents.analyzer_agent import AnalyzerAgent
from agents.explain_agent import ExplainAgent
from agents.memory_agent import MemoryAgent
from tools.db import get_db_path, ensure_db
from dotenv import load_dotenv
load_dotenv()

class Orchestrator:
    """Coordinates the multi-agent pipeline for drug safety analysis."""
    
    def __init__(self):
        """Initialize all agents with shared database."""
        self.db_path = get_db_path()
        ensure_db(self.db_path)
        
        # Initialize 4 specialized agents
        self.ingest = IngestAgent(self.db_path)
        self.analyzer = AnalyzerAgent(self.db_path)
        self.explainer = ExplainAgent(self.db_path)
        self.memory = MemoryAgent(self.db_path)  # Implements Sessions & Memory

    def run(self, drug, limit=100):
        """
        Execute the multi-agent pipeline for drug safety analysis.
        
        PIPELINE FLOW (Sequential Agents):
        1. Retrieve historical insights (MemoryAgent)
        2. Ingest adverse event data (IngestAgent)
        3. Detect safety signals (AnalyzerAgent)
        4. Generate LLM analysis (ExplainAgent)
        5. Extract & store new insights (MemoryAgent) → Creates learning loop
        
        Args:
            drug: Drug name to analyze
            limit: Number of adverse event reports to fetch (max 1000)
            
        Returns:
            trace: Dictionary containing results from each agent
        """
        trace = {}
        trace['pipeline_start'] = datetime.datetime.utcnow().isoformat()
        
        # STEP 0: Retrieve past learnings (demonstrates memory/learning)
        past_memories = self.memory.retrieve_relevant(drug, limit=5)
        trace['past_memories'] = past_memories
        
        # STEP 1: Ingest data from OpenFDA (demonstrates custom tools)
        ing = self.ingest.ingest(drug, limit)
        trace['ingest'] = ing
        
        # STEP 2: Analyze signals using statistical methods
        analysis_info = self.analyzer.analyze(drug)
        trace['analysis'] = analysis_info
        
        # STEP 3: Generate LLM-powered explanation (demonstrates LLM agent)
        llm_result = self.explainer.explain(drug, analysis_info, sample_reports_limit=3)
        trace['llm'] = llm_result
        
        # STEP 4: Extract insights and store in memory (creates learning loop)
        if analysis_info.get('signals'):
            insights = self.memory.extract_insights_from_analysis(drug, analysis_info)
            trace['new_insights'] = insights
        
        # STEP 5: Generate report with historical context
        report_path = self._write_report(drug, ing, analysis_info, llm_result, past_memories)
        trace['report_path'] = report_path
        trace['pipeline_end'] = datetime.datetime.utcnow().isoformat()
        return trace

    def _write_report(self, drug, ingest_info, analysis_info, llm_result, past_memories=None):
        ts = datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%S")
        os.makedirs("reports", exist_ok=True)
        path = f"reports/{drug}_report_{ts}.md"
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(f"# ADSIO Report — {drug}\n")
            fh.write(f"Generated at: {datetime.datetime.utcnow().isoformat()} UTC\n\n")

            # Summary
            fh.write("## Summary\n")
            fh.write(f"- Fetched: {ingest_info.get('fetched')}\n")
            fh.write(f"- Stored: {ingest_info.get('stored')}\n")

            # Analyzer signals
            signals = []
            if isinstance(analysis_info, dict):
                signals = analysis_info.get("signals", []) or []
            elif isinstance(analysis_info, list):
                signals = analysis_info

            fh.write(f"- Signals found: {len(signals)}\n\n")
            
            # Memory context (if available)
            if past_memories:
                fh.write("## Historical Context\n")
                fh.write(f"Found {len(past_memories)} relevant past insights:\n\n")
                for mem in past_memories[:3]:  # Show top 3
                    fh.write(f"- **[{mem['insight_type']}]** {mem['insight_text']} "
                            f"(confidence: {mem['confidence']:.2f})\n")
                fh.write("\n")

            if signals:
                fh.write("## Detected Signals\n")
                # Table header
                fh.write("| Reaction | Count | z-score | Relative | Week | Reason |\n")
                fh.write("|---|---:|---:|---:|---|---|\n")
                # Rows
                for s in signals:
                    reaction = s.get("reaction", "?")
                    current = s.get("current_count", "?")
                    z_val = s.get("zscore")
                    rel_val = s.get("relative")
                    reason = s.get("reason") or ""
                    z = f"{float(z_val):.2f}" if isinstance(z_val, (int, float)) else ("—" if z_val is None else str(z_val))
                    rel = f"{float(rel_val):.2f}" if isinstance(rel_val, (int, float)) else ("—" if rel_val is None else str(rel_val))
                    week_raw = s.get("week", "?")
                    week = str(week_raw).split(" ")[0]
                    fh.write(f"| {reaction} | {current} | {z} | {rel} | {week} | {reason} |\n")
                fh.write("\n")
            else:
                fh.write("No signals detected using current thresholds.\n\n")

            # LLM section
            fh.write("## LLM Analysis\n")
            if isinstance(llm_result, dict) and llm_result.get("text"):
                fh.write(llm_result["text"] + "\n")
            else:
                fh.write("LLM analysis unavailable.\n")
        return path
