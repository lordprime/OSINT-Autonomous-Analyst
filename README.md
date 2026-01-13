# OSINT Autonomous Analyst

**Production-ready OSINT intelligence platform** with AI-powered investigation, multi-source data collection, and knowledge graph analysis.

![Status](https://img.shields.io/badge/status-production--ready-green)
![Docker](https://img.shields.io/badge/docker-required-blue)
![Python](https://img.shields.io/badge/python-3.11-blue)
![Next.js](https://img.shields.io/badge/next.js-14-black)

---

## 🚀 Quick Start (5 Minutes)

### Prerequisites
- Docker & Docker Compose
- Git
- 8GB RAM minimum

### Installation

```bash
# 1. Clone repository
git clone https://github.com/lordprime/OSINT-Autonomous-Analyst
cd OSINT-Autonomous-Analyst

# 2. Generate secrets
cd infrastructure
chmod +x setup_secrets.sh
./setup_secrets.sh

# 3. Start all services
docker-compose up -d

# 4. Initialize databases (wait 30 seconds for containers to be healthy)
docker exec oaa_neo4j cypher-shell -u neo4j -p osint_secure_password_change_me \
  -f /var/lib/neo4j/import/init.cypher

docker exec oaa_neo4j cypher-shell -u neo4j -p osint_secure_password_change_me \
  -f /var/lib/neo4j/import/init_extended.cypher

docker exec -i oaa_timescale psql -U osint -d osint_temporal \
  < ../database/timescale/schema.sql

docker exec -i oaa_timescale psql -U osint -d osint_temporal \
  < ../database/timescale/schema_extended.sql

# 5. Access the application
```

**Frontend:** http://localhost:3000  
**Backend API:** http://localhost:8000/api/docs

---

## 📖 Usage Guide

### 1. Create Investigation

**Via UI:**
1. Open http://localhost:3000
2. Enter target (e.g., "example.com")
3. Click "Create"
4. Watch automatic collection begin

**Via API:**
```bash
curl -X POST http://localhost:8000/api/v1/investigations/create \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Investigation",
    "target": "example.com",
    "goal": "Gather intelligence on target"
  }'
```

### 2. Start Data Collection

Collections automatically start or trigger manually:

```bash
curl -X POST http://localhost:8000/api/v1/collection/start \
  -H "Content-Type: application/json" \
  -d '{
    "investigation_id": "YOUR_ID",
    "agent_type": "duckduckgo",
    "query": "example.com",
    "max_results": 50
  }'
```

**Available Agents:**
- `duckduckgo` - Web search (no API key required)
- `telegram` - Public channels (requires API key)
- `instagram` - Public profiles (no API key)
- `linkedin` - Company pages (no API key)
- `facebook` - Public pages (no API key)

### 3. View Results

- **Dashboard:** Real-time graph updates
- **Detail Page:** Click investigation to see entities, jobs, hypotheses
- **API:** `GET /api/v1/investigations/{id}`

### 4. Generate Insights

**AI-powered analysis (requires Ollama or Groq):**

```bash
# Install Ollama (optional, for local LLM)
curl -fsSL https://ollama.com/install.sh | sh
ollama pull llama3:8b
ollama serve

# Generate hypotheses
curl -X POST http://localhost:8000/api/v1/reasoning/hypotheses \
  -H "Content-Type: application/json" \
  -d '{
    "investigation_id": "YOUR_ID",
    "text_context": "Investigation summary"
  }'
```

---

## 🏗️ Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│  Frontend   │────▶│   Backend    │────▶│  Databases  │
│  Next.js    │     │   FastAPI    │     │  Neo4j      │
│  (Port 3000)│     │  (Port 8000) │     │  TimescaleDB│
└─────────────┘     └──────────────┘     │  Elasticsearch
                            │             └─────────────┘
                            │
                    ┌───────▼────────┐
                    │  Collection    │
                    │    Agents      │
                    │ (5 sources)    │
                    └────────────────┘
```

**Tech Stack:**
- **Frontend:** Next.js 14, TypeScript, Tailwind CSS
- **Backend:** Python 3.11, FastAPI, Pydantic
- **Databases:** Neo4j (graph), TimescaleDB (time-series), Elasticsearch (search)
- **Cache:** Redis
- **Storage:** MinIO (S3-compatible)
- **AI:** Ollama, Groq, Claude, OpenAI

---

## 🔧 Configuration

### Environment Variables

Create `backend/.env` (copy from `.env.example`):

```bash
# Required
NEO4J_URI=bolt://neo4j:7687
TIMESCALE_HOST=timescale

# Optional - LLM Providers
OLLAMA_HOST=http://host.docker.internal:11434  # Local
GROQ_API_KEY=your_key_here                      # Cloud (free tier)
ANTHROPIC_API_KEY=your_key_here                 # Claude
OPENAI_API_KEY=your_key_here                    # GPT-4

# Optional - Collection Agents
TELEGRAM_API_ID=your_id
TELEGRAM_API_HASH=your_hash
```

### Rate Limits

Edit `backend/app/middleware/rate_limiter.py`:

```python
REQUESTS_PER_MINUTE = 60      # Per IP
REQUESTS_PER_HOUR = 1000      # Per IP
COLLECTION_PER_HOUR = 100     # Collection jobs
LLM_CALLS_PER_HOUR = 500      # AI reasoning
```

---

## 🧪 Testing

```bash
# Run E2E tests
cd backend
pytest tests/test_e2e.py -v

# Run agent tests
pytest tests/test_agents.py -v

# Check API health
curl http://localhost:8000/health
```

---

## 📊 API Reference

**Full documentation:** http://localhost:8000/api/docs

### Key Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/investigations/create` | POST | Create investigation |
| `/api/v1/investigations` | GET | List investigations |
| `/api/v1/collection/start` | POST | Start data collection |
| `/api/v1/collection/sources` | GET | Available sources |
| `/api/v1/entities/search` | POST | Search entities |
| `/api/v1/entities/graph/query` | POST | Query knowledge graph |
| `/api/v1/reasoning/plan` | POST | Generate investigation plan |
| `/api/v1/reasoning/hypotheses` | POST | Generate hypotheses |

---

## 🔒 Security

### Production Checklist

- [ ] Change default passwords in `infrastructure/secrets/*`
- [ ] Enable HTTPS (use nginx reverse proxy)
- [ ] Configure firewall (allow only 3000, 8000)
- [ ] Enable authentication (uncomment in `api/v1/__init__.py`)
- [ ] Rotate secrets monthly
- [ ] Monitor rate limiting logs
- [ ] Regular security updates

### Built-in Security

- ✅ Rate limiting (60 req/min per IP)
- ✅ Input validation (Pydantic schemas)
- ✅ SQL injection protection (parameterized queries)
- ✅ CORS configuration
- ✅ Secrets management (Docker secrets)

---

## 🐛 Troubleshooting

### Container won't start
```bash
# Clean rebuild
docker-compose down -v --remove-orphans
docker-compose up -d --build
```

### Database connection errors
```bash
# Check health
docker ps

# View logs
docker-compose logs backend
docker-compose logs neo4j
```

### Frontend shows "Failed to load"
```bash
# Check backend is running
curl http://localhost:8000/health

# Rebuild frontend
docker-compose up -d --build frontend
```

### Collection jobs stuck "pending"
```bash
# Check backend logs
docker logs oaa_backend | grep collection

# Verify agent is configured (API keys, etc.)
```

---

## 📁 Project Structure

```
OSINT-Autonomous-Analyst/
├── backend/
│   ├── app/
│   │   ├── api/v1/endpoints/      # API routes
│   │   ├── agents/                # Collection agents
│   │   ├── use_cases/             # Business logic
│   │   ├── schemas/               # Data models
│   │   └── middleware/            # Rate limiting, etc.
│   └── tests/                     # Test suites
├── frontend/
│   └── src/
│       ├── app/                   # Next.js pages
│       └── lib/                   # API client
├── database/
│   ├── neo4j/                     # Graph schemas
│   ├── timescale/                 # Time-series schemas
│   └── elasticsearch/             # Search mappings
└── infrastructure/
    ├── docker-compose.yml         # Service orchestration
    └── secrets/                   # Generated secrets
```

---

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

---

## 📄 License

This project is licensed under the MIT License - see LICENSE file for details.

---

## 🙏 Acknowledgments

- **Neo4j** for graph database
- **TimescaleDB** for time-series analytics
- **FastAPI** for backend framework
- **Next.js** for frontend
- **Ollama** for local LLM inference
- **Groq** for cloud LLM

---

## 📞 Support

- **Issues:** https://github.com/lordprime/OSINT-Autonomous-Analyst/issues
- **Discussions:** https://github.com/lordprime/OSINT-Autonomous-Analyst/discussions
- **Documentation:** See `/docs` folder

---

**Built with ❤️ for the OSINT community**
