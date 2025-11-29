"""
Unit tests for validation utilities.
"""

import pytest
from utils.validators import (
    ValidationError,
    validate_drug_name,
    validate_limit,
    validate_date,
    sanitize_filename,
    validate_drug_list,
)
from datetime import datetime


class TestValidateDrugName:
    """Tests for drug name validation."""
    
    def test_valid_drug_names(self):
        """Test valid drug names pass validation."""
        assert validate_drug_name("aspirin") == "aspirin"
        assert validate_drug_name("IBUPROFEN") == "IBUPROFEN"
        assert validate_drug_name("Acetaminophen") == "Acetaminophen"
        assert validate_drug_name("Drug-Name") == "Drug-Name"
        assert validate_drug_name("Drug (Generic)") == "Drug (Generic)"
    
    def test_strips_whitespace(self):
        """Test that whitespace is stripped."""
        assert validate_drug_name("  aspirin  ") == "aspirin"
        assert validate_drug_name("\taspirin\n") == "aspirin"
    
    def test_empty_string_raises_error(self):
        """Test that empty string raises ValidationError."""
        with pytest.raises(ValidationError, match="non-empty string"):
            validate_drug_name("")
        
        with pytest.raises(ValidationError):
            validate_drug_name("   ")
    
    def test_too_short_raises_error(self):
        """Test that too short names raise ValidationError."""
        with pytest.raises(ValidationError, match="at least 2 characters"):
            validate_drug_name("a")
    
    def test_too_long_raises_error(self):
        """Test that too long names raise ValidationError."""
        with pytest.raises(ValidationError, match="less than 100 characters"):
            validate_drug_name("a" * 101)
    
    def test_invalid_characters_raise_error(self):
        """Test that invalid characters raise ValidationError."""
        with pytest.raises(ValidationError, match="can only contain"):
            validate_drug_name("aspirin@123")
        
        with pytest.raises(ValidationError):
            validate_drug_name("drug;name")
        
        with pytest.raises(ValidationError):
            validate_drug_name("drug/name")


class TestValidateLimit:
    """Tests for limit validation."""
    
    def test_valid_limits(self):
        """Test valid limits pass validation."""
        assert validate_limit(1) == 1
        assert validate_limit(100) == 100
        assert validate_limit(1000) == 1000
    
    def test_none_returns_default(self):
        """Test that None returns default value."""
        assert validate_limit(None) == 100
    
    def test_string_numbers_converted(self):
        """Test that string numbers are converted."""
        assert validate_limit("50") == 50
    
    def test_below_min_raises_error(self):
        """Test that values below min raise ValidationError."""
        with pytest.raises(ValidationError, match="at least"):
            validate_limit(0)
        
        with pytest.raises(ValidationError):
            validate_limit(-1)
    
    def test_above_max_raises_error(self):
        """Test that values above max raise ValidationError."""
        with pytest.raises(ValidationError, match="at most"):
            validate_limit(1001)
    
    def test_invalid_type_raises_error(self):
        """Test that invalid types raise ValidationError."""
        with pytest.raises(ValidationError, match="must be an integer"):
            validate_limit("invalid")
        
        with pytest.raises(ValidationError):
            validate_limit([])


class TestValidateDate:
    """Tests for date validation."""
    
    def test_valid_date_formats(self):
        """Test valid date formats are parsed."""
        result = validate_date("20230101")
        assert isinstance(result, datetime)
        assert result.year == 2023
        assert result.month == 1
        assert result.day == 1
        
        result = validate_date("2023-01-01")
        assert isinstance(result, datetime)
        
        result = validate_date("2023/01/01")
        assert isinstance(result, datetime)
    
    def test_none_returns_none(self):
        """Test that None returns None."""
        assert validate_date(None) is None
        assert validate_date("") is None
    
    def test_invalid_format_raises_error(self):
        """Test that invalid formats raise ValidationError."""
        with pytest.raises(ValidationError, match="Invalid date format"):
            validate_date("01-01-2023")
        
        with pytest.raises(ValidationError):
            validate_date("invalid")


class TestSanitizeFilename:
    """Tests for filename sanitization."""
    
    def test_removes_path_separators(self):
        """Test that path separators are removed."""
        assert sanitize_filename("path/to/file.txt") == "pathtofile.txt"
        assert sanitize_filename("path\\to\\file.txt") == "pathtofile.txt"
    
    def test_removes_leading_dots(self):
        """Test that leading dots are removed."""
        assert sanitize_filename("..file.txt") == "file.txt"
        assert sanitize_filename(".hidden") == "hidden"
    
    def test_replaces_spaces(self):
        """Test that spaces are replaced with underscores."""
        assert sanitize_filename("my file.txt") == "my_file.txt"
    
    def test_removes_special_characters(self):
        """Test that special characters are removed."""
        assert sanitize_filename("file@#$.txt") == "file.txt"
        assert sanitize_filename("file<>|?.txt") == "file.txt"
    
    def test_limits_length(self):
        """Test that filename length is limited."""
        long_name = "a" * 300 + ".txt"
        result = sanitize_filename(long_name)
        assert len(result) <= 255
    
    def test_empty_returns_unnamed(self):
        """Test that empty filename returns 'unnamed'."""
        assert sanitize_filename("") == "unnamed"
        assert sanitize_filename("@#$%") == "unnamed"


class TestValidateDrugList:
    """Tests for drug list validation."""
    
    def test_valid_drug_list(self):
        """Test valid drug lists pass validation."""
        result = validate_drug_list(["aspirin", "ibuprofen"])
        assert len(result) == 2
        assert "aspirin" in result
        assert "ibuprofen" in result
    
    def test_not_a_list_raises_error(self):
        """Test that non-list raises ValidationError."""
        with pytest.raises(ValidationError, match="must be provided as a list"):
            validate_drug_list("aspirin")
        
        with pytest.raises(ValidationError):
            validate_drug_list({"drug": "aspirin"})
    
    def test_empty_list_raises_error(self):
        """Test that empty list raises ValidationError."""
        with pytest.raises(ValidationError, match="cannot be empty"):
            validate_drug_list([])
    
    def test_too_many_drugs_raises_error(self):
        """Test that too many drugs raise ValidationError."""
        with pytest.raises(ValidationError, match="more than 10 drugs"):
            validate_drug_list(["drug" + str(i) for i in range(11)])
    
    def test_invalid_drug_in_list_raises_error(self):
        """Test that invalid drug names in list raise ValidationError."""
        with pytest.raises(ValidationError):
            validate_drug_list(["aspirin", ""])
        
        with pytest.raises(ValidationError):
            validate_drug_list(["aspirin", "a"])
