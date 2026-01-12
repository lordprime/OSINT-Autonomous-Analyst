# Collection Agents - README

## Overview

Agent 3 (Collection Developer) has built a comprehensive data collection infrastructure with government-grade OpSec features.

## Architecture

```
Collection Request
    ↓
BaseCollectionAgent (compliance check + audit logging)
    ↓
Rate Limiter (token bucket with Redis)
    ↓
Proxy Manager (residential IP rotation)
    ↓
OpSec Helper (user-agent randomization + timing delays)
    ↓
Specific Agent (Twitter/Reddit/Surface Web)
    ↓
Data Normalization → CollectedItem
    ↓
Audit Log (success or denied action)
```

## Implemented Agents

### 1. Twitter Agent (`twitter.py`)
- **API**: Twitter API v2 with bearer token
- **Rate Limit**: 15 requests/15min
- **Features**:
  - Tweet search with query syntax
  - User timeline collection
  - Entity extraction (mentions, hashtags, URLs)
  - Engagement metrics (retweets, likes, replies)

**Example**:
```python
from app.agents.collection.twitter import twitter_agent

result = await twitter_agent.collect_with_audit(
    investigation_id="inv_123",
    query='cybersecurity threat intelligence',
    user_id="analyst_001",
    justification="Monitoring threat landscape",
    max_results=100
)
```

### 2. Reddit Agent (`reddit.py`)
- **API**: PRAW (Python Reddit API Wrapper)
- **Rate Limit**: 60 requests/min
- **Features**:
  - Subreddit post collection
  - Global search across all subreddits
  - Comment thread extraction
  - User mention detection

**Example**:
```python
from app.agents.collection.reddit import reddit_agent

# Collect from subreddit
result = await reddit_agent.collect_with_audit(
    investigation_id="inv_123",
    query="r/cybersecurity",
    user_id="analyst_001",
    justification="Monitoring security discussions",
    max_results=50
)
```

### 3. Surface Web Agent (`surface_web.py`)
- **Method**: HTTP scraping with BeautifulSoup
- **Rate Limit**: 10 requests/min
- **Features**:
  - Google dorking (search operators)
  - Web page scraping
  - Entity extraction (emails, URLs, phone numbers)
  - Pre-built dork templates

**Example**:
```python
from app.agents.collection.surface_web import surface_web_agent, dork_templates

# Google dork
query = dork_templates.find_email("example.com")
result = await surface_web_agent.collect_with_audit(
    investigation_id="inv_123",
    query=query,
    user_id="analyst_001",
    justification="Finding contact information"
)

# Scrape specific URL
item = await surface_web_agent.scrape_url(
    url="https://example.com/about",
    investigation_id="inv_123",
    user_id="analyst_001",
    justification="Company background research"
)
```

## OpSec Features

### Rate Limiting
- **Implementation**: Token bucket algorithm with Redis backend
- **Per-Source Limits**:
  - Twitter: 15 req/min
  - Reddit: 60 req/min
  - Shodan: 1 req/min
  - Google: 10 req/min

### Proxy Rotation
- **Type**: Residential proxies (not datacenter IPs)
- **Health Checking**: Automatic failover after 3 failures
- **Random Selection**: Prevents usage patterns

### User-Agent Randomization
- **Pool**: Top 50 real browser user-agents
- **Rotation**: Random selection per request
- **Coverage**: Chrome, Firefox, Safari, Edge on Windows/macOS/Linux

### Timing Randomization
- **Delay**: 5-30 seconds between requests (configurable)
- **Purpose**: Avoid detection of automated tools

### Referer Stripping
- **Header**: `Referrer-Policy: no-referrer`
- **Purpose**: Prevent leaking investigation tool origin

## Compliance & Audit

### Denied Action Logging
Every blocked collection is logged:
```python
{
  "user_id": "analyst_002",
  "action_type": "collection",
  "target": "https://eu-citizen-data.example.com",
  "denial_reason": "PII collection in EU prohibited by GDPR",
  "denial_policy_id": "POLICY_GDPR_001",
  "justification_provided": "Attempted background check"
}
```

### Audit Trail
Every successful collection is logged:
```python
{
  "user_id": "analyst_001",
  "action_type": "collection",
  "target": "cybersecurity threat intelligence",
  "agent_type": "twitter",
  "items_collected": 87,
  "status": "completed"
}
```

## Data Normalization

All agents normalize data to `CollectedItem`:
```python
@dataclass
class CollectedItem:
    source: str              # "twitter", "reddit", "surface_web"
    source_id: str           # Platform-specific ID
    timestamp: int           # Unix timestamp
    content: str             # Main text content
    author_id: str           # Normalized author ID
    entities: Dict           # Extracted entities (URLs, mentions, etc.)
    metadata: Dict           # Platform-specific metadata
    confidence: float        # 0.0-1.0 confidence score
    jurisdiction: str        # Data jurisdiction (for compliance)
```

## Configuration

### Environment Variables
```bash
# Twitter
TWITTER_BEARER_TOKEN=your_token_here

# Reddit
REDDIT_CLIENT_ID=your_client_id
REDDIT_CLIENT_SECRET=your_secret

# Proxy (optional)
ENABLE_PROXY_ROTATION=true
PROXY_PROVIDER=brightdata
PROXY_ENDPOINT=proxy.example.com:8080
PROXY_USERNAME=user
PROXY_PASSWORD=pass

# OpSec
TIMING_RANDOMIZATION_MIN_SEC=5
TIMING_RANDOMIZATION_MAX_SEC=30
```

## Usage Example

```python
from app.agents.collection.twitter import twitter_agent
from app.agents.collection.reddit import reddit_agent
from app.agents.collection.surface_web import surface_web_agent

# Twitter collection
twitter_result = await twitter_agent.collect_with_audit(
    investigation_id="inv_123",
    query="APT threat actor",
    user_id="analyst_001",
    justification="Threat intelligence gathering"
)

# Reddit collection
reddit_result = await reddit_agent.collect_with_audit(
    investigation_id="inv_123",
    query="r/netsec",
    user_id="analyst_001",
    justification="Security community monitoring"
)

# Surface web collection
web_result = await surface_web_agent.collect_with_audit(
    investigation_id="inv_123",
    query='site:example.com filetype:pdf',
    user_id="analyst_001",
    justification="Document discovery"
)
```

## Next Steps (Agent 4 - Reasoning)

With collection infrastructure complete, Agent 4 will build:
- Multi-LLM reasoning abstraction
- Hypothesis generation and testing
- Entity resolution engine
- Risk scoring with narrative explanations

---

**Agent 3 Status**: ✅ Core collection infrastructure complete
