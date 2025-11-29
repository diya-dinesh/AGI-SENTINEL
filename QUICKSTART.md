# Quick Start Guide - AGI-Sentinel

## Step 1: Activate Virtual Environment

```bash
cd /Users/diyadinesh/Documents/agi_sentinel
source venv/bin/activate
```

## Step 2: Install/Update Dependencies

```bash
pip install -r requirements.txt
```

This will install:
- Core dependencies (pandas, numpy, requests, etc.)
- Web framework (FastAPI, uvicorn)
- Testing tools (pytest, pytest-cov)
- Development tools (ruff, black, mypy)

## Step 3: Configure Environment (Optional)

Create or edit `.env` file:

```bash
# Optional: Enable Gemini LLM (requires API key)
USE_GEMINI=false
# GENAI_API_KEY=your_api_key_here

# Optional: Logging configuration
LOG_LEVEL=INFO
LOG_DIR=./logs

# Optional: API configuration
OPENFDA_TIMEOUT=20
OPENFDA_MAX_RETRIES=3
```

## Step 4: Run the Server

```bash
uvicorn server:app --reload
```

The server will start at: **http://localhost:8000**

## Step 5: Access the UI

Open your browser and go to:
```
http://localhost:8000/ui/
```

Or test the API directly:
```
http://localhost:8000/api/health
```

## Quick Test

### Test 1: Health Check
```bash
curl http://localhost:8000/api/health
```

### Test 2: Run Pipeline
```bash
curl -X POST http://localhost:8000/api/run \
  -H "Content-Type: application/json" \
  -d '{"drug": "aspirin", "limit": 50}'
```

### Test 3: View Signals
```bash
curl http://localhost:8000/api/signals?drug=aspirin
```

## Running Tests (Optional)

```bash
# Run all tests
pytest tests/ -v

# Run with coverage report
pytest tests/ -v --cov=. --cov-report=html

# View coverage report
open htmlcov/index.html
```

## Troubleshooting

### Issue: "Module not found"
**Solution:** Make sure virtual environment is activated and dependencies are installed:
```bash
source venv/bin/activate
pip install -r requirements.txt
```

### Issue: "Database locked"
**Solution:** The new retry logic handles this automatically. If it persists, delete the database:
```bash
rm data/adsio.db
# It will be recreated on next run
```

### Issue: "Port already in use"
**Solution:** Use a different port:
```bash
uvicorn server:app --reload --port 8001
```

## What to Expect

1. **Server starts** - You'll see logs indicating the server is running
2. **Open UI** - Navigate to http://localhost:8000/ui/
3. **Enter a drug name** - e.g., "aspirin"
4. **Set limit** - e.g., 50 or 100
5. **Click "Run Pipeline"** - The system will:
   - Fetch data from OpenFDA
   - Store in database
   - Analyze for signals
   - Generate LLM report (if enabled)
6. **View results** - Signals table and report will populate

## Next Steps

- Review the [walkthrough.md](file:///Users/diyadinesh/.gemini/antigravity/brain/ee32cc28-0e4b-4078-83a5-9cba35d44e05/walkthrough.md) for detailed improvements
- Check logs in `logs/` directory for debugging
- Run tests to verify everything works
- Explore the API at http://localhost:8000/docs (FastAPI auto-generated docs)
