"""
Unit tests for MemoryAgent.
Tests Sessions & Memory capability.
"""

import pytest
import os
import tempfile
from agents.memory_agent import MemoryAgent


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    yield path
    if os.path.exists(path):
        os.unlink(path)


@pytest.fixture
def memory_agent(temp_db):
    """Create a MemoryAgent instance with temp database."""
    return MemoryAgent(temp_db)


def test_memory_agent_initialization(memory_agent, temp_db):
    """Test MemoryAgent initializes correctly."""
    assert memory_agent.db_path == temp_db
    # Verify schema was created
    import sqlite3
    conn = sqlite3.connect(temp_db)
    cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='memories'")
    assert cursor.fetchone() is not None
    conn.close()


def test_store_insight(memory_agent):
    """Test storing an insight in memory."""
    memory_id = memory_agent.store_insight(
        entity="aspirin",
        insight_type="signal_pattern",
        insight_text="Aspirin consistently shows bleeding-related signals",
        confidence=0.9,
        metadata={"source": "test"}
    )
    
    assert isinstance(memory_id, int)
    assert memory_id > 0


def test_retrieve_relevant_memories(memory_agent):
    """Test retrieving memories for a drug."""
    # Store some test memories
    memory_agent.store_insight(
        entity="aspirin",
        insight_type="signal_pattern",
        insight_text="Bleeding events common",
        confidence=0.9
    )
    memory_agent.store_insight(
        entity="aspirin",
        insight_type="temporal",
        insight_text="Signals spike in March",
        confidence=0.7
    )
    memory_agent.store_insight(
        entity="ibuprofen",
        insight_type="signal_pattern",
        insight_text="Different drug",
        confidence=0.8
    )
    
    # Retrieve aspirin memories
    memories = memory_agent.retrieve_relevant("aspirin")
    
    assert len(memories) == 2
    assert all(m['entity'] == 'aspirin' for m in memories)
    assert memories[0]['confidence'] >= memories[1]['confidence']  # Sorted by confidence


def test_retrieve_by_type(memory_agent):
    """Test filtering memories by insight type."""
    memory_agent.store_insight("aspirin", "signal_pattern", "Pattern 1", 0.9)
    memory_agent.store_insight("aspirin", "temporal", "Temporal 1", 0.8)
    memory_agent.store_insight("aspirin", "signal_pattern", "Pattern 2", 0.7)
    
    pattern_memories = memory_agent.retrieve_relevant("aspirin", insight_type="signal_pattern")
    
    assert len(pattern_memories) == 2
    assert all(m['insight_type'] == 'signal_pattern' for m in pattern_memories)


def test_get_drug_history(memory_agent):
    """Test getting complete drug history."""
    # Store various insights
    memory_agent.store_insight("aspirin", "signal_pattern", "Pattern 1", 0.9)
    memory_agent.store_insight("aspirin", "temporal", "Temporal 1", 0.8)
    memory_agent.store_insight("aspirin", "novel", "Novel finding", 0.6)
    
    history = memory_agent.get_drug_history("aspirin")
    
    assert history['entity'] == 'aspirin'
    assert history['total_insights'] == 3
    assert 'signal_pattern' in history['by_type']
    assert 'temporal' in history['by_type']
    assert len(history['high_confidence']) == 2  # confidence > 0.7


def test_extract_insights_from_analysis(memory_agent, monkeypatch):
    """Test extracting insights from analysis results."""
    # Mock the LLM call
    def mock_call_gemini(prompt):
        return """TYPE: signal_pattern
INSIGHT: Bleeding events are consistently reported
CONFIDENCE: 0.9

TYPE: temporal
INSIGHT: Signals increase in spring months
CONFIDENCE: 0.7"""
    
    monkeypatch.setattr('agents.memory_agent.call_gemini', mock_call_gemini)
    
    analysis_info = {
        'signals': [
            {'reaction': 'Bleeding', 'current_count': 50, 'zscore': 5.0},
            {'reaction': 'Nausea', 'current_count': 30, 'zscore': 3.0}
        ]
    }
    
    insights = memory_agent.extract_insights_from_analysis("aspirin", analysis_info)
    
    assert len(insights) == 2
    assert insights[0]['type'] == 'signal_pattern'
    assert insights[1]['type'] == 'temporal'
    assert all('id' in i for i in insights)


def test_extract_insights_no_signals(memory_agent):
    """Test that no insights are extracted when there are no signals."""
    analysis_info = {'signals': []}
    
    insights = memory_agent.extract_insights_from_analysis("aspirin", analysis_info)
    
    assert len(insights) == 0


def test_memory_metadata(memory_agent):
    """Test that metadata is stored and retrieved correctly."""
    metadata = {
        'signals_count': 10,
        'analysis_date': '2024-01-01',
        'source': 'automated'
    }
    
    memory_id = memory_agent.store_insight(
        entity="aspirin",
        insight_type="signal_pattern",
        insight_text="Test insight",
        confidence=0.8,
        metadata=metadata
    )
    
    memories = memory_agent.retrieve_relevant("aspirin")
    
    assert len(memories) == 1
    assert memories[0]['metadata'] == metadata


def test_confidence_bounds(memory_agent):
    """Test that confidence values are handled correctly."""
    # Test various confidence values
    memory_agent.store_insight("drug1", "type1", "text1", 0.0)
    memory_agent.store_insight("drug1", "type1", "text2", 0.5)
    memory_agent.store_insight("drug1", "type1", "text3", 1.0)
    
    memories = memory_agent.retrieve_relevant("drug1")
    
    assert len(memories) == 3
    assert all(0.0 <= m['confidence'] <= 1.0 for m in memories)
