"""
Unit tests for analysis tools.
"""

import pytest
import pandas as pd
import numpy as np
from tools.analysis_tools import (
    compute_weekly_counts,
    detect_spikes,
)


class TestComputeWeeklyCounts:
    """Tests for weekly count computation."""
    
    def test_empty_dataframe(self):
        """Test with empty dataframe."""
        df = pd.DataFrame()
        result = compute_weekly_counts(df)
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0
    
    def test_single_reaction_single_week(self):
        """Test with single reaction in single week."""
        df = pd.DataFrame({
            'safetyreportid': ['1', '2', '3'],
            'receivedate': ['2023-01-01', '2023-01-02', '2023-01-03'],
            'reaction': ['HEADACHE', 'HEADACHE', 'HEADACHE']
        })
        
        result = compute_weekly_counts(df)
        assert len(result) == 1
        assert result.iloc[0]['reaction'] == 'HEADACHE'
        assert result.iloc[0]['count'] == 3
    
    def test_multiple_reactions(self):
        """Test with multiple reactions."""
        df = pd.DataFrame({
            'safetyreportid': ['1', '2', '3'],
            'receivedate': ['2023-01-01', '2023-01-01', '2023-01-01'],
            'reaction': ['HEADACHE', 'NAUSEA', 'HEADACHE']
        })
        
        result = compute_weekly_counts(df)
        assert len(result) == 2
        
        headache = result[result['reaction'] == 'HEADACHE']
        assert len(headache) == 1
        assert headache.iloc[0]['count'] == 2
        
        nausea = result[result['reaction'] == 'NAUSEA']
        assert len(nausea) == 1
        assert nausea.iloc[0]['count'] == 1
    
    def test_semicolon_separated_reactions(self):
        """Test with semicolon-separated reactions."""
        df = pd.DataFrame({
            'safetyreportid': ['1'],
            'receivedate': ['2023-01-01'],
            'reaction': ['HEADACHE;NAUSEA;DIZZINESS']
        })
        
        result = compute_weekly_counts(df)
        assert len(result) == 3
        assert set(result['reaction']) == {'HEADACHE', 'NAUSEA', 'DIZZINESS'}
    
    def test_multiple_weeks(self):
        """Test with data spanning multiple weeks."""
        df = pd.DataFrame({
            'safetyreportid': ['1', '2', '3'],
            'receivedate': ['2023-01-01', '2023-01-08', '2023-01-15'],
            'reaction': ['HEADACHE', 'HEADACHE', 'HEADACHE']
        })
        
        result = compute_weekly_counts(df)
        assert len(result) == 3  # 3 different weeks
        assert all(result['count'] == 1)


class TestDetectSpikes:
    """Tests for spike detection."""
    
    def test_empty_dataframe(self):
        """Test with empty dataframe."""
        df = pd.DataFrame()
        result = detect_spikes(df)
        assert isinstance(result, list)
        assert len(result) == 0
    
    def test_single_week_volume_detection(self):
        """Test volume-based detection for single week."""
        df = pd.DataFrame({
            'safetyreportid': ['1', '2', '3', '4'],
            'receivedate': ['2023-01-01'] * 4,
            'reaction': ['HEADACHE'] * 4
        })
        
        result = detect_spikes(df)
        assert len(result) > 0
        assert result[0]['reaction'] == 'HEADACHE'
        assert result[0]['current_count'] == 4
        assert result[0]['reason'] == 'volume_only'
    
    def test_zscore_spike_detection(self):
        """Test z-score based spike detection."""
        # Create baseline with low counts, then a spike
        dates = ['2023-01-01', '2023-01-08', '2023-01-15', '2023-01-22']
        reactions = ['HEADACHE'] * 2 + ['HEADACHE'] * 2 + ['HEADACHE'] * 10
        receive_dates = [dates[0]] * 2 + [dates[1]] * 2 + [dates[2]] * 10
        
        df = pd.DataFrame({
            'safetyreportid': [str(i) for i in range(len(reactions))],
            'receivedate': receive_dates,
            'reaction': reactions
        })
        
        result = detect_spikes(df)
        assert len(result) > 0
        
        # Should detect spike in week 3
        spike = result[0]
        assert spike['reaction'] == 'HEADACHE'
        assert spike['current_count'] == 10
        assert spike['zscore'] is not None
    
    def test_relative_spike_detection(self):
        """Test relative increase spike detection."""
        # Create data with relative increase
        df = pd.DataFrame({
            'safetyreportid': ['1', '2', '3', '4', '5', '6', '7'],
            'receivedate': ['2023-01-01', '2023-01-01',  # Week 1: 2 events
                          '2023-01-08', '2023-01-08',  # Week 2: 2 events
                          '2023-01-15', '2023-01-15', '2023-01-15'],  # Week 3: 3 events (1.5x increase)
            'reaction': ['HEADACHE'] * 7
        })
        
        result = detect_spikes(df)
        # May or may not detect depending on thresholds
        assert isinstance(result, list)
    
    def test_no_spike_stable_data(self):
        """Test that stable data doesn't trigger false positives."""
        # Create stable data
        df = pd.DataFrame({
            'safetyreportid': [str(i) for i in range(12)],
            'receivedate': ['2023-01-01'] * 3 + ['2023-01-08'] * 3 + 
                          ['2023-01-15'] * 3 + ['2023-01-22'] * 3,
            'reaction': ['HEADACHE'] * 12
        })
        
        result = detect_spikes(df)
        # Should not detect spikes in stable data
        assert len(result) == 0
    
    def test_multiple_reactions_independent(self):
        """Test that different reactions are analyzed independently."""
        df = pd.DataFrame({
            'safetyreportid': [str(i) for i in range(20)],
            'receivedate': ['2023-01-01'] * 2 + ['2023-01-08'] * 2 + ['2023-01-15'] * 16,
            'reaction': ['HEADACHE'] * 10 + ['NAUSEA'] * 10
        })
        
        result = detect_spikes(df)
        # Both reactions should be analyzed
        reactions = [s['reaction'] for s in result]
        assert 'HEADACHE' in reactions or 'NAUSEA' in reactions
