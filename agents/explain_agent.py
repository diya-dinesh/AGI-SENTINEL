"""
ExplainAgent: LLM-Powered Intelligence Report Generation Agent

AGENT ROLE: Generates human-readable pharmacovigilance intelligence reports using
Google Gemini LLM. This agent transforms statistical signals into actionable insights
with medical context, risk assessment, and recommended next steps.

RESPONSIBILITIES:
- Sample representative adverse event reports from database
- Construct context-rich prompts for LLM analysis
- Generate structured intelligence reports using Gemini 2.0
- Provide fallback analysis when LLM is unavailable
- Extract key insights in standardized format

LLM INTEGRATION:
- Uses Google Gemini 2.0 Flash Lite for fast, cost-effective analysis
- Prompt engineering includes: drug name, statistical signals, sample reports
- Structured output format: Summary, Evidence, Causes, Risk, Next Steps, Confidence

FALLBACK STRATEGY:
If LLM is unavailable (API error, no API key, timeout), returns a basic
fallback report indicating manual review is needed.

INTEGRATION:
- Uses tools.db.sample_reports_for_drug to fetch example reports
- Uses tools.llm_tools.generate_analysis_text for LLM interaction
- Called by orchestrator after AnalyzerAgent completes
"""

import logging
from typing import Dict, Any, List, Optional
from tools.db import sample_reports_for_drug
from tools.llm_tools import generate_analysis_text

logger = logging.getLogger("ExplainAgent")
logging.basicConfig(level=logging.INFO, format="[ExplainAgent] %(message)s")


class ExplainAgent:
    """
    Agent responsible for generating LLM-powered intelligence reports.
    
    This agent implements the "explanation" phase of the pipeline, using
    large language models to synthesize statistical findings into actionable
    pharmacovigilance intelligence with medical context.
    
    Attributes:
        db_path (Optional[str]): Path to SQLite database for sampling reports
    """
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize ExplainAgent with optional database configuration.
        
        Args:
            db_path: Path to SQLite database file (optional, needed for report sampling)
        """
        self.db_path = db_path

    def explain(
        self,
        drug_name: str,
        analysis_info: Dict[str, Any],
        sample_reports_limit: int = 3
    ) -> Dict[str, Any]:
        """
        Generate an LLM-powered intelligence report for detected safety signals.
        
        This method performs the complete report generation workflow:
        1. Sample representative adverse event reports from database
        2. Construct context-rich prompt with drug name, signals, and examples
        3. Call Gemini LLM to generate structured analysis
        4. Return formatted report or fallback if LLM unavailable
        
        The LLM is prompted to provide:
        - Executive summary of findings
        - Key evidence from statistical analysis
        - Possible medical causes and mechanisms
        - Risk assessment and clinical significance
        - Recommended next steps for investigation
        - Confidence score in the analysis
        
        Args:
            drug_name: Name of the drug being analyzed
            analysis_info: Results from AnalyzerAgent containing detected signals
            sample_reports_limit: Number of example reports to include in prompt (default: 3)
        
        Returns:
            Dictionary containing report generation results:
                - status: "ok" if LLM succeeded, "fallback" if LLM unavailable
                - text: Generated intelligence report (markdown format)
        
        Example:
            >>> agent = ExplainAgent("data/adsio.db")
            >>> analysis = {"signals": [...], "stored_reports": 100}
            >>> result = agent.explain("aspirin", analysis)
            >>> print(result["text"])  # Displays markdown report
        """
        # Sample representative reports to provide context to the LLM
        try:
            samples = sample_reports_for_drug(
                self.db_path,
                drug_name,
                limit=sample_reports_limit
            )
        except Exception:
            # If sampling fails, proceed without examples
            samples = []

        # Construct prompt context for LLM
        # This includes all information needed for comprehensive analysis
        prompt_context = {
            "drug": drug_name,
            "analysis": analysis_info,  # Contains signals, counts, statistics
            "examples": samples  # Sample reports for medical context
        }

        try:
            # Generate intelligence report using Gemini LLM
            text = generate_analysis_text(prompt_context)
            logger.info("LLM analysis generated successfully")
            return {"status": "ok", "text": text}

        except Exception as e:
            # Fallback when LLM is unavailable (no API key, timeout, error)
            logger.warning(f"LLM unavailable: {e}")
            fallback = (
                f"LLM unavailable.\n\n"
                f"Fallback pharmacovigilance summary for {drug_name}:\n"
                "- No LLM insights available.\n"
                "- Review stored reports manually.\n"
                "- No signals detected.\n"
            )
            return {"status": "fallback", "text": fallback}
