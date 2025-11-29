"""
AGI-Sentinel FastAPI Server

REST API for multi-agent pharmacovigilance system.
Provides endpoints for running the agent pipeline, retrieving signals,
accessing reports, and querying the memory system.

ARCHITECTURE:
- FastAPI for modern async REST API
- CORS enabled for web UI integration
- Comprehensive error handling and validation
- Static file serving for web interface

KEY ENDPOINTS:
- POST /api/run          → Execute agent pipeline
- GET  /api/signals      → Retrieve detected signals
- GET  /api/memory/{drug} → Access agent memory
- GET  /api/reports      → List generated reports
"""

import os
import sys
import glob
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, List

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, Field, validator

from orchestrator.orchestrator import Orchestrator
from agents.analyzer_agent import AnalyzerAgent
from tools.db import get_db_path, ensure_db
from utils.logger import get_logger
from utils.validators import (
    validate_drug_name,
    validate_limit,
    validate_drug_list,
    ValidationError
)
from utils.logger import get_logger

# Initialize logger
logger = get_logger(__name__)

# Optional future agents (stubs). Import guarded inside endpoints if needed to avoid import errors when files are missing.

app = FastAPI(
    title="AGI-Sentinel API",
    version="0.1.0",
    description="Autonomous Drug Safety Intelligence & Oversight (ADSIO) System",
)

# CORS for local dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Custom exception handlers
@app.exception_handler(ValidationError)
async def validation_exception_handler(request: Request, exc: ValidationError):
    """Handle validation errors with standardized response."""
    logger.warning(f"Validation error: {exc}")
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "error": "Validation Error",
            "message": str(exc),
            "timestamp": datetime.utcnow().isoformat() + "Z",
        },
    )


@app.exception_handler(RequestValidationError)
async def request_validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle Pydantic validation errors."""
    logger.warning(f"Request validation error: {exc}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "Invalid Request",
            "message": "Request validation failed",
            "details": exc.errors(),
            "timestamp": datetime.utcnow().isoformat() + "Z",
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected errors gracefully."""
    logger.error(f"Unexpected error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal Server Error",
            "message": "An unexpected error occurred. Please try again later.",
            "timestamp": datetime.utcnow().isoformat() + "Z",
        },
    )

# Ensure DB exists
DB_PATH = get_db_path()
ensure_db(DB_PATH)

# Serve static UI under /ui
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
UI_DIR = os.path.join(PROJECT_ROOT, "ui")
if not os.path.isdir(UI_DIR):
    os.makedirs(UI_DIR, exist_ok=True)
# Custom static file handler with no-cache headers
from fastapi.responses import FileResponse
import mimetypes

@app.get("/ui/{file_path:path}")
async def serve_ui(file_path: str):
    """Serve UI files with no-cache headers to prevent caching issues."""
    if not file_path:
        file_path = "index.html"
    
    full_path = os.path.join(UI_DIR, file_path)
    
    if not os.path.exists(full_path):
        if file_path == "" or file_path.endswith("/"):
            full_path = os.path.join(UI_DIR, "index.html")
        else:
            raise HTTPException(status_code=404, detail="File not found")
    
    # Determine content type
    content_type, _ = mimetypes.guess_type(full_path)
    if content_type is None:
        content_type = "application/octet-stream"
    
    # Add no-cache headers for JavaScript and HTML files
    headers = {}
    if file_path.endswith(('.js', '.html', '.css')):
        headers = {
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0"
        }
    
    return FileResponse(
        full_path,
        media_type=content_type,
        headers=headers
    )

# Handle default browser favicon request to avoid 404 noise
@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    return Response(status_code=204)

# Redirect / -> /ui/
@app.get("/")
def root_redirect():
    return RedirectResponse(url="/ui/")

class RunRequest(BaseModel):
    """Request model for pipeline execution."""
    drug: str = Field(..., min_length=2, max_length=100, description="Drug name to analyze")
    limit: Optional[int] = Field(100, ge=1, le=1000, description="Number of reports to fetch")
    
    @validator('drug')
    def validate_drug(cls, v):
        """Validate drug name."""
        return validate_drug_name(v)
    
    @validator('limit')
    def validate_limit_value(cls, v):
        """Validate limit."""
        return validate_limit(v)


class CorrelateRequest(BaseModel):
    """Request model for drug correlation."""
    drugs: List[str] = Field(..., min_items=2, max_items=10, description="List of drugs to compare")
    limit: Optional[int] = Field(200, ge=1, le=1000, description="Number of reports per drug")
    
    @validator('drugs')
    def validate_drugs(cls, v):
        """Validate drug list."""
        return validate_drug_list(v)
    
    @validator('limit')
    def validate_limit_value(cls, v):
        """Validate limit."""
        return validate_limit(v)


class MemoryNote(BaseModel):
    """Request model for memory notes."""
    key: str = Field(..., min_length=1, max_length=100)
    text: str = Field(..., min_length=1, max_length=10000)

@app.get("/api/health")
def health():
    """Enhanced health check with dependency status."""
    try:
        # Check database connectivity
        db_status = "connected"
        try:
            import sqlite3
            conn = sqlite3.connect(DB_PATH)
            conn.execute("SELECT 1")
            conn.close()
        except Exception as e:
            db_status = f"error: {str(e)}"
            logger.error(f"Database health check failed: {e}")
        
        # Check LLM availability
        llm_status = "configured" if Config.USE_GEMINI and Config.GENAI_API_KEY else "disabled"
        
        health_data = {
            "status": "ok" if db_status == "connected" else "degraded",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "version": "0.1.0",
            "dependencies": {
                "database": db_status,
                "llm": llm_status,
            },
            "config": Config.get_summary(),
        }
        
        return health_data
    except Exception as e:
        logger.error(f"Health check failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service health check failed"
        )

@app.post("/api/run")
def run_pipeline(body: RunRequest):
    """Execute the full analysis pipeline for a drug."""
    logger.info(f"Pipeline execution requested for drug: {body.drug}, limit: {body.limit}")
    try:
        orch = Orchestrator()
        trace = orch.run(body.drug, body.limit or Config.DEFAULT_LIMIT)
        logger.info(f"Pipeline completed successfully for {body.drug}")
        return {
            "status": "success",
            "data": trace,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
    except ValidationError as e:
        logger.warning(f"Validation error in pipeline: {e}")
        raise
    except Exception as e:
        logger.error(f"Pipeline execution failed for {body.drug}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Pipeline execution failed: {str(e)}"
        )

@app.get("/api/signals")
def get_signals(drug: str):
    try:
        analyzer = AnalyzerAgent(DB_PATH)
        result = analyzer.analyze(drug)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/reports")
def list_reports(drug: Optional[str] = None):
    try:
        reports_dir = os.path.join(PROJECT_ROOT, "reports")
        os.makedirs(reports_dir, exist_ok=True)
        pattern = os.path.join(reports_dir, "*_report_*.md") if not drug else os.path.join(reports_dir, f"{drug}_report_*.md")
        files = sorted(glob.glob(pattern))
        names = [os.path.basename(f) for f in files]
        return {"reports": names}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/reports/latest")
def latest_report(drug: str):
    try:
        reports_dir = os.path.join(PROJECT_ROOT, "reports")
        pattern = os.path.join(reports_dir, f"{drug}_report_*.md")
        files = sorted(glob.glob(pattern))
        if not files:
            raise HTTPException(status_code=404, detail="No reports found for this drug")
        latest = files[-1]
        with open(latest, "r", encoding="utf-8") as fh:
            content = fh.read()
        return {"filename": os.path.basename(latest), "content": content}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/debug/weekly_counts")
def debug_weekly_counts(drug: str):
    """Return per-reaction weekly counts for debugging signal detection."""
    try:
        df = db_load_reports(DB_PATH, drug)
        if df.empty:
            return {"weeks": [], "counts": []}
        counts = compute_weekly_counts(df)
        # Convert to JSON-serializable structure
        counts['week'] = counts['week'].astype(str)
        data = counts.to_dict(orient='records')
        # Also include summary of weeks and reactions
        summary = {
            "unique_weeks": int(counts['week'].nunique()),
            "unique_reactions": int(counts['reaction'].nunique()),
            "total_rows": int(len(counts))
        }
        return {"summary": summary, "counts": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ----------------- CorrelationAgent (stub) -----------------
@app.post("/api/correlate")
def correlate(body: CorrelateRequest):
    """Stub for future correlation agent."""
    return {"status": "not_implemented", "message": "Correlation agent coming soon"}


# ============================================================================
# MEMORY AGENT ENDPOINTS (Sessions & Memory Feature)
# ============================================================================

@app.get("/api/memory/{drug}")
async def get_drug_memory(drug: str):
    """
    Get complete memory history for a drug.
    Demonstrates Sessions & Memory capability.
    """
    try:
        from agents.memory_agent import MemoryAgent
        
        drug = validate_drug_name(drug)
        db_path = get_db_path()
        memory_agent = MemoryAgent(db_path)
        
        history = memory_agent.get_drug_history(drug)
        
        logger.info(f"Retrieved memory history for '{drug}': {history['total_insights']} insights")
        
        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "drug": drug,
                "history": history,
                "timestamp": datetime.now().isoformat()
            }
        )
    except ValidationError as e:
        logger.warning(f"Validation error in memory retrieval: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error retrieving memory for '{drug}': {e}")
        raise HTTPException(status_code=500, detail=f"Memory retrieval failed: {str(e)}")


@app.get("/api/memory/{drug}/summary")
async def get_memory_summary(drug: str):
    """
    Get LLM-powered summary of learnings for a drug.
    Demonstrates LLM-powered memory synthesis.
    """
    try:
        from agents.memory_agent import MemoryAgent
        
        drug = validate_drug_name(drug)
        db_path = get_db_path()
        memory_agent = MemoryAgent(db_path)
        
        summary = memory_agent.summarize_learnings(drug)
        
        logger.info(f"Generated learning summary for '{drug}'")
        
        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "drug": drug,
                "summary": summary,
                "timestamp": datetime.now().isoformat()
            }
        )
    except ValidationError as e:
        logger.warning(f"Validation error in summary generation: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error generating summary for '{drug}': {e}")
        raise HTTPException(status_code=500, detail=f"Summary generation failed: {str(e)}")


# ============================================================================
# FUTURE AGENT STUBS (Correlation, etc.)
# ============================================================================

@app.get("/api/memory/trends")
@app.post("/api/memory/notes")
def memory_save(note: MemoryNote):
    try:
        try:
            from agents.memory_agent import MemoryAgent  # type: ignore
        except Exception:
            raise HTTPException(status_code=501, detail="MemoryAgent not implemented")
        agent = MemoryAgent(DB_PATH)
        agent.save_note(note.key, note.text)
        return {"status": "ok"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))