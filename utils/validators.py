"""
Validation utilities for AGI-Sentinel.
Provides input validation and sanitization functions.
"""

import re
from typing import Optional
from datetime import datetime


class ValidationError(Exception):
    """Custom exception for validation errors."""
    pass


def validate_drug_name(drug_name: str) -> str:
    """
    Validate and sanitize drug name input.
    
    Args:
        drug_name: Drug name to validate
        
    Returns:
        Sanitized drug name
        
    Raises:
        ValidationError: If drug name is invalid
    """
    if not drug_name or not isinstance(drug_name, str):
        raise ValidationError("Drug name must be a non-empty string")
    
    # Strip whitespace
    drug_name = drug_name.strip()
    
    # Check length
    if len(drug_name) < 2:
        raise ValidationError("Drug name must be at least 2 characters long")
    
    if len(drug_name) > 100:
        raise ValidationError("Drug name must be less than 100 characters")
    
    # Allow letters, numbers, spaces, hyphens, and parentheses
    if not re.match(r'^[a-zA-Z0-9\s\-()]+$', drug_name):
        raise ValidationError(
            "Drug name can only contain letters, numbers, spaces, hyphens, and parentheses"
        )
    
    return drug_name


def validate_limit(limit: Optional[int], min_val: int = 1, max_val: int = 1000) -> int:
    """
    Validate limit parameter for API requests.
    
    Args:
        limit: Limit value to validate
        min_val: Minimum allowed value
        max_val: Maximum allowed value
        
    Returns:
        Validated limit value
        
    Raises:
        ValidationError: If limit is invalid
    """
    if limit is None:
        return 100  # Default value
    
    try:
        limit = int(limit)
    except (TypeError, ValueError):
        raise ValidationError(f"Limit must be an integer, got {type(limit).__name__}")
    
    if limit < min_val:
        raise ValidationError(f"Limit must be at least {min_val}")
    
    if limit > max_val:
        raise ValidationError(f"Limit must be at most {max_val}")
    
    return limit


def validate_date(date_str: Optional[str]) -> Optional[datetime]:
    """
    Validate and parse date string.
    
    Args:
        date_str: Date string in YYYYMMDD or YYYY-MM-DD format
        
    Returns:
        Parsed datetime object or None
        
    Raises:
        ValidationError: If date format is invalid
    """
    if not date_str:
        return None
    
    # Try multiple formats
    formats = ["%Y%m%d", "%Y-%m-%d", "%Y/%m/%d"]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    
    raise ValidationError(
        f"Invalid date format: {date_str}. Expected YYYYMMDD or YYYY-MM-DD"
    )


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename to prevent path traversal attacks.
    
    Args:
        filename: Filename to sanitize
        
    Returns:
        Sanitized filename
    """
    # Remove path separators and null bytes
    filename = filename.replace('/', '').replace('\\', '').replace('\0', '')
    
    # Remove leading dots
    filename = filename.lstrip('.')
    
    # Replace spaces with underscores
    filename = filename.replace(' ', '_')
    
    # Keep only alphanumeric, underscore, hyphen, and dot
    filename = re.sub(r'[^a-zA-Z0-9_\-.]', '', filename)
    
    # Limit length
    if len(filename) > 255:
        filename = filename[:255]
    
    return filename or "unnamed"


def validate_drug_list(drugs: list) -> list:
    """
    Validate a list of drug names.
    
    Args:
        drugs: List of drug names
        
    Returns:
        List of validated drug names
        
    Raises:
        ValidationError: If list is invalid or contains invalid drug names
    """
    if not isinstance(drugs, list):
        raise ValidationError("Drugs must be provided as a list")
    
    if not drugs:
        raise ValidationError("Drug list cannot be empty")
    
    if len(drugs) > 10:
        raise ValidationError("Cannot compare more than 10 drugs at once")
    
    validated = []
    for drug in drugs:
        validated.append(validate_drug_name(drug))
    
    return validated
