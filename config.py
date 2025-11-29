"""
Configuration management for AGI-Sentinel.
Centralized configuration with validation and type safety.
"""

import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Project root directory
ROOT = Path(__file__).parent.absolute()
ENV_PATH = ROOT / ".env"

# Load environment variables
load_dotenv(ENV_PATH)


class Config:
    """Application configuration with validation."""
    
    # Project paths
    PROJECT_ROOT: Path = ROOT
    DATA_DIR: Path = ROOT / "data"
    REPORTS_DIR: Path = ROOT / "reports"
    LOGS_DIR: Path = ROOT / "logs"
    UI_DIR: Path = ROOT / "ui"
    
    # Database
    DB_PATH: str = os.getenv("ADSIO_DB_PATH", str(DATA_DIR / "adsio.db"))
    
    # API Configuration
    OPENFDA_ENDPOINT: str = "https://api.fda.gov/drug/event.json"
    OPENFDA_TIMEOUT: int = int(os.getenv("OPENFDA_TIMEOUT", "20"))
    OPENFDA_MAX_RETRIES: int = int(os.getenv("OPENFDA_MAX_RETRIES", "3"))
    
    # LLM Configuration
    GENAI_API_KEY: Optional[str] = os.getenv("GENAI_API_KEY")
    USE_GEMINI: bool = os.getenv("USE_GEMINI", "false").lower() == "true"
    GOOGLE_MODEL: str = os.getenv("GOOGLE_MODEL", "gemini-2.0-flash-lite")
    LLM_TIMEOUT: int = int(os.getenv("LLM_TIMEOUT", "30"))
    LLM_MAX_RETRIES: int = int(os.getenv("LLM_MAX_RETRIES", "2"))
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_DIR: str = os.getenv("LOG_DIR", str(LOGS_DIR))
    LOG_JSON: bool = os.getenv("LOG_JSON", "false").lower() == "true"
    
    # Analysis parameters
    MIN_WEEKS_FOR_ANALYSIS: int = int(os.getenv("MIN_WEEKS_FOR_ANALYSIS", "2"))
    Z_SCORE_THRESHOLD: float = float(os.getenv("Z_SCORE_THRESHOLD", "2.0"))
    RELATIVE_THRESHOLD: float = float(os.getenv("RELATIVE_THRESHOLD", "1.5"))
    
    # API limits
    DEFAULT_LIMIT: int = 100
    MIN_LIMIT: int = 1
    MAX_LIMIT: int = 1000
    MAX_COMPARE_DRUGS: int = 10
    
    # Server configuration
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    RELOAD: bool = os.getenv("RELOAD", "false").lower() == "true"
    
    # Rate limiting
    RATE_LIMIT_ENABLED: bool = os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true"
    RATE_LIMIT_REQUESTS: int = int(os.getenv("RATE_LIMIT_REQUESTS", "100"))
    RATE_LIMIT_WINDOW: int = int(os.getenv("RATE_LIMIT_WINDOW", "60"))  # seconds
    
    @classmethod
    def ensure_directories(cls):
        """Ensure all required directories exist."""
        for dir_path in [cls.DATA_DIR, cls.REPORTS_DIR, cls.LOGS_DIR]:
            Path(dir_path).mkdir(parents=True, exist_ok=True)
    
    @classmethod
    def validate(cls) -> list[str]:
        """
        Validate configuration and return list of warnings.
        
        Returns:
            List of warning messages
        """
        warnings = []
        
        # Check LLM configuration
        if cls.USE_GEMINI and not cls.GENAI_API_KEY:
            warnings.append(
                "USE_GEMINI is enabled but GENAI_API_KEY is not set. "
                "LLM features will not work."
            )
        
        # Check thresholds
        if cls.Z_SCORE_THRESHOLD <= 0:
            warnings.append(f"Z_SCORE_THRESHOLD should be positive, got {cls.Z_SCORE_THRESHOLD}")
        
        if cls.RELATIVE_THRESHOLD <= 0:
            warnings.append(f"RELATIVE_THRESHOLD should be positive, got {cls.RELATIVE_THRESHOLD}")
        
        # Check limits
        if cls.MIN_LIMIT > cls.MAX_LIMIT:
            warnings.append(f"MIN_LIMIT ({cls.MIN_LIMIT}) > MAX_LIMIT ({cls.MAX_LIMIT})")
        
        return warnings
    
    @classmethod
    def get_summary(cls) -> dict:
        """Get configuration summary (excluding sensitive data)."""
        return {
            "database": cls.DB_PATH,
            "llm_enabled": cls.USE_GEMINI,
            "llm_model": cls.GOOGLE_MODEL if cls.USE_GEMINI else None,
            "log_level": cls.LOG_LEVEL,
            "analysis": {
                "min_weeks": cls.MIN_WEEKS_FOR_ANALYSIS,
                "z_threshold": cls.Z_SCORE_THRESHOLD,
                "relative_threshold": cls.RELATIVE_THRESHOLD,
            },
            "limits": {
                "default": cls.DEFAULT_LIMIT,
                "min": cls.MIN_LIMIT,
                "max": cls.MAX_LIMIT,
            }
        }


# Initialize directories on import
Config.ensure_directories()

# Validate configuration and log warnings
config_warnings = Config.validate()
if config_warnings:
    import logging
    logger = logging.getLogger(__name__)
    for warning in config_warnings:
        logger.warning(f"Configuration warning: {warning}")


def get_env(name: str, default=None):
    """
    Get environment variable value.
    
    Args:
        name: Environment variable name
        default: Default value if not found
        
    Returns:
        Environment variable value or default
    """
    return os.getenv(name, default)

