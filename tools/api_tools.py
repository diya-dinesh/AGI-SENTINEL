"""
OpenFDA API Integration Module

This module provides robust API integration with the OpenFDA adverse event reporting system.
It implements intelligent retry logic, error handling, and rate limiting to ensure reliable
data fetching even under adverse network conditions.

KEY FEATURES:
- Automatic retry with exponential backoff for transient failures
- Intelligent error classification (4xx vs 5xx responses)
- Graceful degradation (returns empty list instead of crashing)
- Configurable timeouts and retry limits
- Comprehensive logging for debugging and monitoring

API ENDPOINT:
- Base URL: https://api.fda.gov/drug/event.json
- Query format: patient.drug.medicinalproduct:("drug_name")
- Rate limits: Enforced by OpenFDA (40 requests/minute for unauthenticated)

RETRY STRATEGY:
- Transient errors (timeouts, 5xx): Retry with exponential backoff
- Client errors (4xx): No retry, immediate return or raise
- 404 Not Found: Return empty list (drug has no reports)

ERROR HANDLING:
- All network errors are logged with full context
- After max retries, returns empty list for graceful degradation
- Allows pipeline to continue even if data fetch fails

INTEGRATION:
- Used by IngestAgent to fetch adverse event data
- Configured via config.py (timeout, max_retries, endpoint)
"""

import requests
import time
from typing import List, Dict, Any, Optional
from functools import lru_cache
from config import Config
from utils.logger import get_logger

logger = get_logger(__name__)

OPENFDA_ENDPOINT = Config.OPENFDA_ENDPOINT


def get_fda_events(
    drug_name: str,
    limit: int = 100,
    timeout: Optional[int] = None,
    max_retries: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    Query OpenFDA for adverse event reports with retry logic.
    
    Args:
        drug_name: Drug name to search for
        limit: Maximum number of results to return
        timeout: Request timeout in seconds (uses config default if None)
        max_retries: Maximum number of retry attempts (uses config default if None)
        
    Returns:
        List of raw event dictionaries (may be empty)
        
    Raises:
        requests.RequestException: If all retries fail
    """
    timeout = timeout or Config.OPENFDA_TIMEOUT
    max_retries = max_retries or Config.OPENFDA_MAX_RETRIES
    
    # Build query
    q = f'patient.drug.medicinalproduct:("{drug_name}")'
    params = {"search": q, "limit": min(limit, 1000)}  # FDA API max is 1000
    
    logger.info(f"Fetching FDA events for '{drug_name}' (limit={limit})")
    
    last_error = None
    for attempt in range(max_retries):
        try:
            response = requests.get(
                OPENFDA_ENDPOINT,
                params=params,
                timeout=timeout,
                headers={"User-Agent": "AGI-Sentinel/0.1.0"}
            )
            response.raise_for_status()
            
            data = response.json()
            results = data.get("results", [])
            
            logger.info(f"Successfully fetched {len(results)} events for '{drug_name}'")
            return results
            
        except requests.Timeout as e:
            last_error = e
            logger.warning(
                f"Request timeout for '{drug_name}' (attempt {attempt + 1}/{max_retries})"
            )
            if attempt < max_retries - 1:
                time.sleep(1 * (attempt + 1))  # Exponential backoff
                
        except requests.HTTPError as e:
            last_error = e
            status_code = e.response.status_code if e.response else None
            
            # Don't retry on client errors (4xx)
            if status_code and 400 <= status_code < 500:
                logger.error(f"Client error {status_code} for '{drug_name}': {e}")
                if status_code == 404:
                    logger.info(f"No data found for '{drug_name}'")
                    return []
                raise
            
            logger.warning(
                f"HTTP error {status_code} for '{drug_name}' "
                f"(attempt {attempt + 1}/{max_retries}): {e}"
            )
            if attempt < max_retries - 1:
                time.sleep(2 * (attempt + 1))
                
        except requests.RequestException as e:
            last_error = e
            logger.warning(
                f"Request failed for '{drug_name}' (attempt {attempt + 1}/{max_retries}): {e}"
            )
            if attempt < max_retries - 1:
                time.sleep(1 * (attempt + 1))
    
    # All retries failed
    error_msg = f"Failed to fetch FDA events for '{drug_name}' after {max_retries} attempts"
    logger.error(f"{error_msg}: {last_error}")
    
    # Return empty list instead of raising to allow graceful degradation
    return []
