# 🔍 OSINT Autonomous Analyst (OAA)

[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.11+-green.svg)](https://python.org)
[![Node.js](https://img.shields.io/badge/Node.js-18+-green.svg)](https://nodejs.org)
[![Docker](https://img.shields.io/badge/Docker-Required-blue.svg)](https://docker.com)

A **government-grade autonomous intelligence platform** for Open Source Intelligence (OSINT) analysis. This system combines multi-database architecture, AI-powered reasoning, and real-time data collection to provide comprehensive intelligence capabilities.

---

## 🚀 Quick Start

### Prerequisites

Before you begin, ensure you have the following installed:

| Requirement | Version | Check Command |
|-------------|---------|---------------|
| **Docker & Docker Compose** | Latest | `docker --version` |
| **Python** | 3.11+ | `python --version` |
| **Node.js** | 18+ | `node --version` |
| **Git** | Any | `git --version` |

### Installation

#### Step 1: Clone the Repository
```bash
git clone https://github.com/lordprime/OSINT-Autonomous-Analyst.git
cd OSINT-Autonomous-Analyst
```

#### Step 2: Configure Environment Variables
```bash
# Copy the example environment file
cd backend
cp .env.example .env   # Linux/Mac
copy .env.example .env # Windows

# Edit the .env file and add your API keys
```

**Required API Keys:**
- `ANTHROPIC_API_KEY` - For Claude AI reasoning (get from [Anthropic Console](https://console.anthropic.com/))
- `OPENAI_API_KEY` - For GPT reasoning (get from [OpenAI Platform](https://platform.openai.com/))

**Optional API Keys (for data collection):**
- `TWITTER_BEARER_TOKEN` - Twitter/X data collection
- `REDDIT_CLIENT_ID` / `REDDIT_CLIENT_SECRET` - Reddit data collection
- `SHODAN_API_KEY` - Infrastructure reconnaissance
- `CENSYS_API_ID` / `CENSYS_API_SECRET` - Certificate & host search

#### Step 3: Start All Services
```bash
# Navigate to infrastructure folder
cd ../infrastructure

# Start all Docker services (databases + backend + frontend)
docker-compose up -d
```

This will start:
- **Neo4j** (Graph Database) - For relationship mapping
- **TimescaleDB** (Time-Series Database) - For temporal data
- **Elasticsearch** - For full-text search
- **Redis** - For caching and rate limiting
- **MinIO** - For object storage (S3-compatible)
- **Backend API** (FastAPI) - Core application
- **Frontend** (Next.js) - User interface

#### Step 4: Verify Installation
```bash
# Check all containers are running
docker ps

# Check backend health
curl http://localhost:8000/health/detailed
# On Windows PowerShell: Invoke-RestMethod http://localhost:8000/health/detailed
```

---

## 📱 Accessing the Application

Once all services are running, access the application through:

| Service | URL | Credentials |
|---------|-----|-------------|
| **Frontend Dashboard** | http://localhost:3000 | - |
| **Backend API Docs** | http://localhost:8000/docs | - |
| **Neo4j Browser** | http://localhost:7474 | `neo4j` / `osint_secure_password_change_me` |
| **MinIO Console** | http://localhost:9001 | `osint_admin` / `osint_minio_password_change_me` |
| **Elasticsearch** | http://localhost:9200 | - |

---

## 🎯 How to Use

### 1. Chat-Based Investigation (Recommended)

The primary interface is a **chat console** where you can ask natural language questions:

```
Example queries:
- "Find all entities connected to Acme Corporation"
- "Show me the timeline of events related to John Doe"
- "Identify potential shell companies in the Panama region"
- "Map the organizational structure of XYZ Holdings"
```

### 2. Graph Exploration

Use the **interactive graph view** to:
- Visualize entity relationships
- Click nodes to drill down into details
- Filter by entity type (Person, Organization, Location, etc.)
- Export subgraphs for reports

### 3. Creating Investigations

1. Open the Dashboard at http://localhost:3000
2. Click "New Investigation"
3. Enter your investigation name and target entities
4. The AI will autonomously:
   - Plan collection tasks
   - Gather data from multiple sources
   - Build relationship graphs
   - Generate hypotheses and risk scores

---

## 🛠️ Development Setup

For local development without Docker:

### Backend
```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
./venv/Scripts/activate   # Windows
source venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Run development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend
```bash
cd frontend

# Install dependencies
npm install

# Run development server
npm run dev
```

---

## 📁 Project Structure

```
OSINT-Autonomous-Analyst/
├── backend/              # FastAPI application
│   ├── app/
│   │   ├── main.py       # Application entry point
│   │   ├── core/         # Configuration, database, audit
│   │   ├── api/v1/       # API routes
│   │   └── agents/       # Collection & reasoning agents
│   ├── requirements.txt
│   └── .env.example
├── frontend/             # Next.js application
│   ├── src/
│   │   ├── app/          # Pages and routes
│   │   ├── components/   # UI components
│   │   └── lib/          # Utilities and API client
│   └── package.json
├── infrastructure/       # Docker orchestration
│   └── docker-compose.yml
├── database/             # Database initialization scripts
│   ├── neo4j/            # Graph schema
│   └── timescale/        # Temporal schema
└── tests/                # Test suites
```

---

## 🔧 Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `ANTHROPIC_API_KEY` | Claude AI API key | Yes |
| `OPENAI_API_KEY` | OpenAI API key | Yes |
| `NEO4J_PASSWORD` | Neo4j database password | Auto-set |
| `TWITTER_BEARER_TOKEN` | Twitter API access | Optional |
| `SHODAN_API_KEY` | Shodan API access | Optional |
| `ENABLE_DARK_WEB_COLLECTION` | Enable Tor-based collection | Optional |

### Feature Flags

Control features in `.env`:
```bash
ENABLE_DENIED_ACTION_LOGGING=true    # Log blocked operations
ENABLE_HYPOTHESIS_GENERATION=true     # AI hypothesis generation
ENABLE_DARK_WEB_COLLECTION=false     # Dark web crawling (requires Tor)
ENABLE_GEOSPATIAL_ANALYTICS=true     # Map-based visualization
```

---

## 🧪 Testing

```bash
# Run all tests
cd backend
pytest

# Run with coverage
pytest --cov=app tests/

# Run specific test suite
pytest tests/unit/ -v
pytest tests/integration/ -v
pytest tests/security/red_team.py -v
```

---

## 🔐 Security Notes

- **Change all default passwords** in production
- Store API keys securely (never commit `.env` files)
- The system logs all queries for audit purposes
- Enable `ENABLE_DARK_WEB_COLLECTION` only in isolated environments

---

## 📊 API Reference

### Health Check
```bash
GET /health/detailed
```

### Create Investigation
```bash
POST /api/v1/investigations
Content-Type: application/json

{
  "name": "Investigation Name",
  "targets": ["Entity 1", "Entity 2"]
}
```

### Execute Query
```bash
POST /api/v1/investigations/{id}/query
Content-Type: application/json

{
  "query": "Find connections to Acme Corp"
}
```

Full API documentation available at: http://localhost:8000/docs

---

## 🆘 Troubleshooting

### Docker Issues
```bash
# Reset all containers
docker-compose down -v
docker-compose up -d --build

# View logs
docker-compose logs -f backend
docker-compose logs -f neo4j
```

### Port Conflicts
If ports are in use, modify `docker-compose.yml`:
```yaml
ports:
  - "3001:3000"  # Change frontend port
  - "8001:8000"  # Change backend port
```

### Database Connection Errors
Ensure all database containers are healthy:
```bash
docker ps --format "table {{.Names}}\t{{.Status}}"
```

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- Built with government-grade security from Day 1
- Powered by Neo4j, TimescaleDB, Elasticsearch, and AI reasoning engines

---

**⚠️ Disclaimer:** This tool is intended for lawful intelligence gathering and research purposes only. Users are responsible for ensuring compliance with all applicable laws and regulations in their jurisdiction.
