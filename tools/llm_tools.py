"""
Google Gemini LLM Integration Module

This module provides integration with Google's Gemini 2.0 API for generating
pharmacovigilance intelligence reports. It implements prompt engineering best practices
and handles LLM configuration, error handling, and fallback strategies.

KEY FEATURES:
- Google Gemini 2.0 Flash Lite integration for fast, cost-effective analysis
- Runtime toggle support (can enable/disable LLM without code changes)
- Structured prompt engineering for consistent report format
- Comprehensive error handling with graceful degradation
- Environment-based configuration for security

LLM CONFIGURATION:
- Model: gemini-2.0-flash-lite (default, configurable via env)
- API Key: Loaded from GENAI_API_KEY environment variable
- Toggle: USE_GEMINI environment variable (true/false)

PROMPT ENGINEERING:
The module uses a structured prompt that includes:
- Drug name and context
- Statistical analysis results (signals, counts, z-scores)
- Sample adverse event reports for medical context
- Explicit output format requirements (Summary, Evidence, Causes, Risk, Next Steps, Confidence)

OUTPUT FORMAT:
Generated reports follow a standardized structure:
- Summary: High-level overview of findings
- Key Evidence: Statistical signals and patterns
- Possible Causes: Medical interpretation and mechanisms
- Risk Assessment: Clinical significance evaluation
- Recommended Next Steps: Action items for investigation
- Confidence Score: 0-100 reliability rating

ERROR HANDLING:
- Missing API key: Raises ValueError with clear message
- LLM disabled: Raises ValueError to trigger fallback
- API errors: Propagated to caller for fallback handling
- All errors logged for debugging

INTEGRATION:
- Used by ExplainAgent to generate intelligence reports
- Configured via config.py and .env file
- Supports runtime reconfiguration for testing
"""

import os
import logging
from typing import Dict, Any
from dotenv import load_dotenv
import google.generativeai as genai

logging.basicConfig(level=logging.INFO, format="[LLM] %(message)s")
logger = logging.getLogger("LLM")

# Load environment variables from .env file
load_dotenv()

# LLM Configuration
GENAI_API_KEY = os.getenv("GENAI_API_KEY")
USE_GEMINI = os.getenv("USE_GEMINI", "False").lower() == "true"
MODEL_NAME = os.getenv("GOOGLE_MODEL", "gemini-2.0-flash-lite")

# Configure Gemini client if API key is available
if GENAI_API_KEY:
    logger.info("GENAI_API_KEY loaded: True")
    try:
        genai.configure(api_key=GENAI_API_KEY)
        logger.info("Gemini client configured successfully.")
    except Exception as e:
        logger.error(f"Gemini configuration failed: {e}")
else:
    logger.warning("GENAI_API_KEY NOT FOUND — Gemini will not run.")

logger.info(f"USE_GEMINI: {USE_GEMINI}")
logger.info(f"MODEL_NAME: {MODEL_NAME}")


def generate_analysis_text(context: Dict[str, Any]) -> str:
    """
    Generate pharmacovigilance intelligence report using Gemini LLM.
    
    This function constructs a context-rich prompt and calls the Gemini API
    to generate a structured analysis of detected safety signals. The prompt
    engineering approach ensures consistent, actionable output.
    
    Args:
        context: Dictionary containing analysis context with keys:
            - drug (str): Drug name being analyzed
            - analysis (dict): Statistical analysis results from AnalyzerAgent
            - examples (list): Sample adverse event reports for context
    
    Returns:
        Generated intelligence report as markdown-formatted text
    
    Raises:
        ValueError: If LLM is disabled (USE_GEMINI=false) or API key is missing
        Exception: If Gemini API call fails (network error, rate limit, etc.)
    
    Example:
        >>> context = {
        ...     "drug": "aspirin",
        ...     "analysis": {"signals": [...], "stored_reports": 100},
        ...     "examples": [{"safetyreportid": "123", "reactions": "nausea"}]
        ... }
        >>> report = generate_analysis_text(context)
        >>> print(report)  # Displays structured markdown report
    
    Note:
        The function re-reads environment variables on each call to support
        runtime toggling of LLM features without code changes. This is useful
        for testing and cost management.
    """
    # Re-read environment variables to support runtime configuration changes
    use_gemini = os.getenv("USE_GEMINI", "False").lower() == "true"
    api_key = os.getenv("GENAI_API_KEY") or GENAI_API_KEY

    # Validate LLM is enabled and configured
    if not api_key or not use_gemini:
        raise ValueError("LLM disabled or API key missing — skipping Gemini.")

    # Ensure Gemini client is configured (idempotent operation)
    try:
        genai.configure(api_key=api_key)
    except Exception:
        pass  # Already configured, ignore

    # Initialize Gemini model
    model = genai.GenerativeModel(MODEL_NAME)

    # Construct structured prompt for pharmacovigilance analysis
    # The prompt engineering approach:
    # 1. Establishes expert persona for domain-appropriate responses
    # 2. Provides all relevant context (drug, signals, examples)
    # 3. Specifies exact output format for consistency
    # 4. Sets word count limits for conciseness
    prompt = f"""
You are an expert pharmacovigilance analyst.

Drug: {context['drug']}

Analysis Summary:
{context['analysis']}

Sample Reports:
{context['examples']}

Write a concise intelligence note (150–250 words) including:
- Summary
- Key Evidence
- Possible Causes
- Risk Assessment
- Recommended Next Steps
- Confidence Score (0–100)
"""

    # Call Gemini API to generate analysis
    response = model.generate_content(prompt)
    return response.text


# Manual test harness for development and debugging
if __name__ == "__main__":
    print("\n[LLM] --- TEST RUN ---")
    print("[LLM] GENAI_API_KEY loaded:", bool(GENAI_API_KEY))
    print("[LLM] USE_GEMINI:", USE_GEMINI)
    print("[LLM] MODEL_NAME:", MODEL_NAME)

    if GENAI_API_KEY and USE_GEMINI:
        try:
            model = genai.GenerativeModel(MODEL_NAME)
            r = model.generate_content("Say 'Gemini test successful'.")
            print("\n[LLM] Response:", r.text)
        except Exception as e:
            print("\n[LLM] Test failed:", e)
    else:
        print("\n[LLM] Gemini disabled — cannot run test.")

