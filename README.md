# AGI-Sentinel: AI-Powered Drug Safety Intelligence

> **Agentic AI Capstone Project** - Multi-agent system for automated pharmacovigilance signal detection and analysis

[![Python](https://img.shields.io/badge/Python-3.11-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104-green.svg)](https://fastapi.tiangolo.com/)
[![Gemini](https://img.shields.io/badge/Gemini-2.0-orange.svg)](https://ai.google.dev/)

## 📋 Table of Contents
- [Problem Statement](#problem-statement)
- [Solution](#solution)
- [Why Agents?](#why-agents)
- [Architecture](#architecture)
- [Key Features](#key-features)
- [Setup & Installation](#setup--installation)
- [Usage](#usage)
- [Project Structure](#project-structure)
- [Technologies Used](#technologies-used)

---

## 🎯 Problem Statement

**Drug safety monitoring is critical but overwhelmed by data.**

Pharmaceutical companies and regulatory agencies receive millions of adverse event reports annually through systems like OpenFDA. Manually analyzing this data to detect safety signals (unusual patterns of adverse events) is:

- ⏰ **Time-consuming** - Analysts spend weeks reviewing reports
- 🔍 **Prone to missing patterns** - Subtle correlations go unnoticed
- 📊 **Lacks historical context** - No memory of past findings
- 🧠 **Requires expert knowledge** - Needs pharmacovigilance expertise

**The cost of missing a safety signal can be measured in lives.**

---

## 💡 Solution

**AGI-Sentinel** is an autonomous multi-agent system that:

1. **Automatically ingests** adverse event data from OpenFDA
2. **Detects safety signals** using statistical analysis (z-scores, relative ratios)
3. **Generates intelligence reports** using LLM-powered analysis
4. **Learns from past analyses** with long-term memory
5. **Presents insights** through a modern web interface

**Result:** What took analysts days now takes minutes, with AI-powered insights and historical context.

---

## 🤖 Why Agents?

Agents are uniquely suited for this problem because:

### 1. **Autonomous Operation**
Each agent operates independently, making decisions without human intervention:
- IngestAgent decides what data to fetch
- AnalyzerAgent determines which signals are significant
- ExplainAgent synthesizes findings into actionable intelligence
- MemoryAgent learns patterns over time

### 2. **Specialized Expertise**
Each agent has a specific role, like a team of specialists:
- **Data Engineer** (IngestAgent) - Handles API calls and storage
- **Statistician** (AnalyzerAgent) - Performs signal detection
- **Medical Writer** (ExplainAgent) - Generates reports
- **Knowledge Manager** (MemoryAgent) - Maintains institutional memory

### 3. **Collaborative Intelligence**
Agents work together in a pipeline, each building on the previous agent's work:
```
Memory → Ingest → Analyze → Explain → Memory
   ↑                                      ↓
   └──────────── Learning Loop ───────────┘
```

### 4. **Continuous Learning**
The MemoryAgent creates a feedback loop, making the system smarter with each analysis.

---

## 🏗️ Architecture

### Multi-Agent System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                      ORCHESTRATOR                           │
│              (Coordinates Agent Pipeline)                   │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
┌──────────────┐      ┌──────────────┐     ┌──────────────┐
│ MemoryAgent  │      │ IngestAgent  │     │AnalyzerAgent │
│              │      │              │     │              │
│ • Retrieve   │──────▶ • Fetch FDA  │────▶│ • Compute    │
│   memories   │      │   data       │     │   statistics │
│ • Store      │      │ • Store in   │     │ • Detect     │
│   insights   │      │   SQLite     │     │   signals    │
└──────────────┘      └──────────────┘     └──────────────┘
        ▲                                           │
        │                                           ▼
        │                                  ┌──────────────┐
        │                                  │ExplainAgent  │
        │                                  │              │
        └──────────────────────────────────│ • Generate   │
                                           │   LLM report │
                                           │ • Extract    │
                                           │   insights   │
                                           └──────────────┘
                                                   │
                                                   ▼
                                           ┌──────────────┐
                                           │   Gemini     │
                                           │   2.0 API    │
                                           └──────────────┘
```

### Data Flow

1. **User Request** → Web UI or API
2. **MemoryAgent** → Retrieves past insights for drug
3. **IngestAgent** → Fetches adverse events from OpenFDA
4. **AnalyzerAgent** → Detects statistical signals
5. **ExplainAgent** → Generates LLM-powered analysis
6. **MemoryAgent** → Stores new insights for future use
7. **Report Generation** → Markdown report with historical context

### Technology Stack

**Backend:**
- FastAPI (REST API)
- SQLite (Data storage)
- Pandas/NumPy (Statistical analysis)
- Google Gemini 2.0 (LLM)

**Frontend:**
- Vanilla JavaScript
- Tailwind CSS
- Marked.js (Markdown rendering)

---

## ✨ Key Features

### 🎯 Capstone Requirements (4/3 features implemented)

1. ✅ **Multi-agent System** - 4 sequential agents working collaboratively
2. ✅ **LLM-Powered Agents** - ExplainAgent and MemoryAgent use Gemini
3. ✅ **Custom Tools** - OpenFDA API, SQLite DB, Statistical analysis
4. ✅ **Sessions & Memory** - MemoryAgent with long-term learning

### 🚀 Additional Features

- **Statistical Signal Detection** - Z-scores and relative ratio analysis
- **Automated Insight Extraction** - LLM extracts structured knowledge
- **Historical Context** - Reports include past findings
- **Modern UI** - Accordion layout, gradient backgrounds, animations
- **Comprehensive Testing** - Unit tests for all agents
- **Error Handling** - Robust validation and logging
- **API Endpoints** - RESTful API for all operations

---

## 🛠️ Setup & Installation

### Prerequisites

- Python 3.11+
- Google Gemini API key ([Get one here](https://ai.google.dev/))

### Installation Steps

1. **Clone the repository**
```bash
git clone https://github.com/YOUR_USERNAME/agi-sentinel.git
cd agi-sentinel
```

2. **Create virtual environment**
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Configure environment**
```bash
# Copy the example environment file
cp .env.example .env

# Edit .env and add your GENAI_API_KEY
# Get your API key from: https://ai.google.dev/
nano .env  # or use your preferred editor
```

5. **Run the server**
```bash
uvicorn server:app --reload
```

6. **Access the UI**
Open browser to: `http://localhost:8000/ui/`

---

## 📖 Usage

### Web Interface

1. **Enter drug name** (e.g., "aspirin", "ibuprofen")
2. **Set limit** (number of reports to analyze, max 1000)
3. **Click "Run Analysis"**
4. **View results:**
   - Safety signals detected
   - Intelligence report with accordion sections
   - Historical context from past analyses

### API Endpoints

**Run Analysis:**
```bash
POST /api/run
{
  "drug": "aspirin",
  "limit": 1000
}
```

**Get Signals:**
```bash
GET /api/signals?drug=aspirin
```

**Get Memory:**
```bash
GET /api/memory/aspirin
GET /api/memory/aspirin/summary
```

**View Reports:**
```bash
GET /api/reports/latest?drug=aspirin
```

---

## 📁 Project Structure

```
agi_sentinel/
├── agents/                    # Agent implementations
│   ├── ingest_agent.py       # Fetches FDA data
│   ├── analyzer_agent.py     # Detects signals
│   ├── explain_agent.py      # Generates LLM reports
│   └── memory_agent.py       # Manages long-term memory
├── orchestrator/              # Agent coordination
│   └── orchestrator.py       # Pipeline orchestration
├── tools/                     # Shared utilities
│   ├── api_tools.py          # OpenFDA API client
│   ├── db.py                 # Database operations
│   ├── analysis_tools.py     # Statistical functions
│   └── llm_tools.py          # Gemini integration
├── utils/                     # Helper modules
│   ├── logger.py             # Logging system
│   └── validators.py         # Input validation
├── ui/                        # Web interface
│   ├── index.html            # Main page
│   └── app.js                # Frontend logic
├── tests/                     # Unit tests
│   ├── test_memory_agent.py
│   ├── test_db.py
│   └── ...
├── server.py                  # FastAPI application
├── config.py                  # Configuration
└── requirements.txt           # Dependencies
```

---

## 🔧 Technologies Used

### Core Technologies
- **Python 3.11** - Primary language
- **FastAPI** - Modern web framework
- **SQLite** - Embedded database
- **Google Gemini 2.0** - Large language model

### Data & Analysis
- **Pandas** - Data manipulation
- **NumPy** - Numerical computing
- **OpenFDA API** - Adverse event data source

### Frontend
- **Tailwind CSS** - Utility-first CSS
- **Marked.js** - Markdown rendering
- **Vanilla JavaScript** - No framework overhead

### Development
- **pytest** - Testing framework
- **uvicorn** - ASGI server
- **python-dotenv** - Environment management

---

## 🎓 Learning Outcomes

This project demonstrates:

1. **Multi-agent architecture** - Designing collaborative AI systems
2. **LLM integration** - Effective prompt engineering and response parsing
3. **State management** - Sessions and long-term memory
4. **API design** - RESTful endpoints with validation
5. **Statistical analysis** - Signal detection algorithms
6. **Full-stack development** - Backend + Frontend integration

---

## 📊 Example Output

### Safety Signal Detection
```
Drug: Aspirin
Signals Detected: 31

Top Signals:
- Epistaxis (Z-score: 37.0, Relative: 5.11x)
- Haemorrhagic diathesis (Z-score: 18.0, Relative: 4.60x)
- Hearing impaired (Z-score: 18.0, Relative: 4.60x)
```

### Intelligence Report Sections
- **Summary** - High-level overview
- **Key Evidence** - Statistical findings
- **Possible Causes** - Medical interpretation
- **Risk Assessment** - Clinical significance
- **Recommended Next Steps** - Action items
- **Confidence Score** - Analysis reliability

### Historical Context
```
Found 3 relevant past insights:
- [signal_pattern] Bleeding events consistently reported (0.90)
- [temporal] Signals spike in March-April timeframe (0.70)
- [novel] First detection of hearing impairment correlation (0.85)
```

---

## 🚀 Future Enhancements

- **Multi-drug comparison** - Analyze multiple drugs simultaneously
- **Trend visualization** - Charts showing signal evolution
- **Email alerts** - Notifications for critical signals
- **Cloud deployment** - Deploy to Google Cloud Run
- **Advanced memory** - Similarity search and pattern clustering

---

## 📝 License

This project was created as a capstone submission for the Agentic AI course.

---

## 🙏 Acknowledgments

- **OpenFDA** - For providing public adverse event data
- **Google Gemini** - For powering the LLM analysis
- **Agentic AI Course** - For the comprehensive agent framework training

---

## 📧 Contact

For questions or feedback about this capstone project, please reach out through the course submission portal.

---

**Built with ❤️ using Agentic AI principles**