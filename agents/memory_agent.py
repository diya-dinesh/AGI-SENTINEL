"""
Memory Agent for AGI-Sentinel.

AGENT ROLE: Implements Sessions & Memory capability for the multi-agent system.
This agent creates a learning loop by storing insights from each analysis and
retrieving relevant historical patterns to improve future predictions.

KEY BEHAVIORS:
- Autonomous: Decides what insights to extract and store
- Collaborative: Provides historical context to other agents
- Stateful: Maintains long-term memory across sessions
- LLM-Powered: Uses Gemini to extract structured insights from raw analysis

CAPSTONE FEATURE: Sessions & Memory
"""

import json
import sqlite3
from datetime import datetime
from typing import List, Dict, Any, Optional
from utils.logger import get_logger
from tools.llm_tools import generate_analysis_text
import google.generativeai as genai
import os

logger = get_logger(__name__)


class MemoryAgent:
    """
    Agent that manages long-term memory and learning from past analyses.
    
    This agent implements the "Sessions & Memory" capstone requirement by:
    1. Storing insights from each drug analysis
    2. Retrieving relevant memories based on drug/pattern similarity
    3. Using LLM to extract structured knowledge from raw data
    4. Tracking patterns over time to improve future analyses
    """
    
    def __init__(self, db_path: str):
        """Initialize MemoryAgent with database path."""
        self.db_path = db_path
        self._ensure_memory_schema()
        logger.info("MemoryAgent initialized")
    
    def _ensure_memory_schema(self):
        """Create memories table if it doesn't exist."""
        conn = sqlite3.connect(self.db_path)
        try:
            # Check if table exists with old schema
            cursor = conn.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='memories'")
            existing = cursor.fetchone()
            
            # If table exists but has old schema, drop it
            if existing and 'insight_type' not in existing[0]:
                logger.info("Dropping old memories table to recreate with new schema")
                conn.execute("DROP TABLE IF EXISTS memories")
                conn.commit()
            
            # Create table with new schema
            conn.execute("""
                CREATE TABLE IF NOT EXISTS memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    entity TEXT NOT NULL,
                    insight_type TEXT NOT NULL,
                    insight_text TEXT NOT NULL,
                    confidence REAL DEFAULT 0.5,
                    metadata TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create indexes for efficient retrieval
            conn.execute("CREATE INDEX IF NOT EXISTS idx_memories_entity ON memories(entity)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_memories_type ON memories(insight_type)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_memories_created ON memories(created_at)")
            
            conn.commit()
            logger.info("Memory schema ensured")
        except Exception as e:
            logger.error(f"Failed to ensure memory schema: {e}")
            raise
        finally:
            conn.close()
    
    def store_insight(
        self,
        entity: str,
        insight_type: str,
        insight_text: str,
        confidence: float = 0.5,
        metadata: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Store an insight in memory.
        
        Args:
            entity: Drug name or entity the insight relates to
            insight_type: Type of insight ('signal_pattern', 'temporal', 'correlation', 'novel')
            insight_text: The actual insight text
            confidence: Confidence score 0-1
            metadata: Additional context as dict
            
        Returns:
            ID of stored memory
        """
        conn = sqlite3.connect(self.db_path)
        try:
            metadata_json = json.dumps(metadata) if metadata else None
            cursor = conn.execute(
                """
                INSERT INTO memories (entity, insight_type, insight_text, confidence, metadata)
                VALUES (?, ?, ?, ?, ?)
                """,
                (entity, insight_type, insight_text, confidence, metadata_json)
            )
            conn.commit()
            memory_id = cursor.lastrowid
            logger.info(f"Stored memory {memory_id} for {entity}: {insight_type}")
            return memory_id
        except Exception as e:
            logger.error(f"Failed to store insight: {e}")
            raise
        finally:
            conn.close()
    
    def retrieve_relevant(
        self,
        entity: str,
        insight_type: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant memories for an entity.
        
        Args:
            entity: Drug name to retrieve memories for
            insight_type: Optional filter by insight type
            limit: Maximum number of memories to return
            
        Returns:
            List of memory dictionaries
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            if insight_type:
                query = """
                    SELECT * FROM memories 
                    WHERE entity = ? AND insight_type = ?
                    ORDER BY created_at DESC, confidence DESC
                    LIMIT ?
                """
                cursor = conn.execute(query, (entity, insight_type, limit))
            else:
                query = """
                    SELECT * FROM memories 
                    WHERE entity = ?
                    ORDER BY created_at DESC, confidence DESC
                    LIMIT ?
                """
                cursor = conn.execute(query, (entity, limit))
            
            memories = []
            for row in cursor.fetchall():
                memory = dict(row)
                if memory['metadata']:
                    memory['metadata'] = json.loads(memory['metadata'])
                memories.append(memory)
            
            logger.info(f"Retrieved {len(memories)} memories for {entity}")
            return memories
        except Exception as e:
            logger.error(f"Failed to retrieve memories: {e}")
            return []
        finally:
            conn.close()
    
    def get_drug_history(self, entity: str) -> Dict[str, Any]:
        """
        Get complete history of insights for a drug.
        
        Args:
            entity: Drug name
            
        Returns:
            Dictionary with categorized insights
        """
        memories = self.retrieve_relevant(entity, limit=100)
        
        history = {
            'entity': entity,
            'total_insights': len(memories),
            'by_type': {},
            'recent': memories[:5],
            'high_confidence': [m for m in memories if m['confidence'] > 0.7]
        }
        
        # Group by type
        for memory in memories:
            insight_type = memory['insight_type']
            if insight_type not in history['by_type']:
                history['by_type'][insight_type] = []
            history['by_type'][insight_type].append(memory)
        
        return history
    
    def extract_insights_from_analysis(
        self,
        drug: str,
        analysis_info: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Extract and store insights from an analysis using LLM.
        
        Args:
            drug: Drug name
            analysis_info: Analysis results with signals
            
        Returns:
            List of extracted insights
        """
        signals = analysis_info.get('signals', [])
        
        if not signals:
            logger.info(f"No signals to extract insights from for {drug}")
            return []
        
        # Build prompt for LLM to extract insights
        signals_summary = "\n".join([
            f"- {s['reaction']}: count={s['current_count']}, z-score={s.get('zscore', 'N/A')}, "
            f"relative={s.get('relative', 'N/A')}, week={s.get('week', 'N/A')}"
            for s in signals[:10]  # Limit to top 10
        ])
        
        prompt = f"""Analyze these safety signals for {drug} and extract key insights:

{signals_summary}

Extract 2-3 concise insights in the following categories:
1. Signal Patterns: Recurring or notable adverse events
2. Temporal Patterns: Time-based trends
3. Novel Findings: Unexpected or first-time observations

Format each insight as:
TYPE: <category>
INSIGHT: <one sentence insight>
CONFIDENCE: <0.0-1.0>

Be specific and actionable."""

        try:
            # Call Gemini directly for insight extraction
            api_key = os.getenv("GENAI_API_KEY")
            if not api_key:
                logger.warning("No API key available for insight extraction")
                return []
            
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel(os.getenv("GOOGLE_MODEL", "gemini-2.0-flash-lite"))
            response = model.generate_content(prompt)
            llm_response = response.text
            
            insights = self._parse_llm_insights(llm_response)
            
            # Store each insight
            stored_insights = []
            for insight in insights:
                memory_id = self.store_insight(
                    entity=drug,
                    insight_type=insight['type'],
                    insight_text=insight['text'],
                    confidence=insight['confidence'],
                    metadata={'signals_count': len(signals)}
                )
                stored_insights.append({
                    'id': memory_id,
                    **insight
                })
            
            logger.info(f"Extracted and stored {len(stored_insights)} insights for {drug}")
            return stored_insights
            
        except Exception as e:
            logger.error(f"Failed to extract insights: {e}")
            return []
    
    def _parse_llm_insights(self, llm_text: str) -> List[Dict[str, Any]]:
        """Parse LLM response into structured insights."""
        insights = []
        lines = llm_text.strip().split('\n')
        
        current_insight = {}
        for line in lines:
            line = line.strip()
            if line.startswith('TYPE:'):
                if current_insight:
                    insights.append(current_insight)
                current_insight = {'type': line.replace('TYPE:', '').strip().lower().replace(' ', '_')}
            elif line.startswith('INSIGHT:'):
                current_insight['text'] = line.replace('INSIGHT:', '').strip()
            elif line.startswith('CONFIDENCE:'):
                try:
                    conf_str = line.replace('CONFIDENCE:', '').strip()
                    current_insight['confidence'] = float(conf_str)
                except:
                    current_insight['confidence'] = 0.5
        
        if current_insight and 'text' in current_insight:
            insights.append(current_insight)
        
        return insights
    
    def summarize_learnings(self, entity: str) -> str:
        """
        Generate LLM-powered summary of all learnings for a drug.
        
        Args:
            entity: Drug name
            
        Returns:
            Summary text
        """
        history = self.get_drug_history(entity)
        
        if history['total_insights'] == 0:
            return f"No historical insights available for {entity}."
        
        # Build context from memories
        insights_text = "\n".join([
            f"- [{m['insight_type']}] {m['insight_text']} (confidence: {m['confidence']:.2f})"
            for m in history['recent']
        ])
        
        prompt = f"""Summarize the key learnings about {entity} from these historical insights:

{insights_text}

Provide a concise 2-3 sentence summary highlighting:
1. Most consistent patterns
2. Notable trends
3. Areas of concern

Be specific and actionable."""

        try:
            # Call Gemini directly for summary generation
            api_key = os.getenv("GENAI_API_KEY")
            if not api_key:
                return "API key not available for summary generation"
            
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel(os.getenv("GOOGLE_MODEL", "gemini-2.0-flash-lite"))
            response = model.generate_content(prompt)
            summary = response.text
            
            logger.info(f"Generated learning summary for {entity}")
            return summary
        except Exception as e:
            logger.error(f"Failed to generate summary: {e}")
            return f"Error generating summary: {str(e)}"
