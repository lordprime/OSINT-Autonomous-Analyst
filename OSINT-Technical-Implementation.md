# OSINT Autonomous Analyst: Technical Implementation & Architecture Guide

## Quick Reference: System Architecture Diagram

```
┌────────────────────────────────────────────────────────────────────┐
│                     INVESTIGATOR INTERFACE                         │
│  Chat | Graph | Timeline | Map | Case Browser | Audit Trail       │
│                 (Next.js + FastAPI Backend)                        │
└────────────────┬─────────────────────────────────────────────────┘
                 │
        ┌────────▼───────────────────────────────────────────┐
        │    REASONING LAYER (LLM Agentic Orchestration)     │
        │  LangGraph / LlamaIndex + Claude 3.5 Sonnet        │
        │                                                     │
        │  • Investigative Planner Agent                      │
        │  • Hypothesis Generator & Tester                    │
        │  • Predictive Intelligence Agent                    │
        │  • Red-Team Devil's Advocate Agent                  │
        │  • Evidence Verifier Agent                          │
        └────┬──────────────────┬──────────────────────────┬─┘
             │                  │                          │
    ┌────────▼────────┐  ┌──────▼──────────┐  ┌──────────▼─────┐
    │  ANALYSIS       │  │   KNOWLEDGE     │  │  GOVERNANCE    │
    │  AGENTS         │  │   STORE         │  │  & AUDIT       │
    │                 │  │                 │  │                │
    │ • Entity        │  │ • Neo4j Graph   │  │ • Compliance   │
    │   Resolution    │  │ • Elasticsearch │  │   Checker      │
    │ • Sentiment &   │  │ • TimescaleDB   │  │ • Audit Logger │
    │   Intent        │  │ • Pinecone      │  │ • Legal Policy │
    │ • Risk Scoring  │  │   Vectors       │  │   Engine       │
    │ • Geospatial &  │  │ • S3 Archive    │  │ • Bias         │
    │   Temporal      │  │                 │  │   Detector     │
    └────┬────────────┘  └────────┬────────┘  └────────┬───────┘
         │                        │                    │
         └────────────┬───────────┴────────────────────┘
                      │
        ┌─────────────▼──────────────────────────────┐
        │   DATA PIPELINE (Rate Limit, Compliance)   │
        │  Kafka / Cloud Pub/Sub Message Bus         │
        └─────────────┬──────────────────────────────┘
                      │
     ┌────────────────┼────────────────┬──────────┬────────────┐
     │                │                │          │            │
┌────▼─────┐  ┌──────▼──────┐  ┌──────▼───┐  ┌─▼──────┐  ┌──▼──────┐
│ Surface  │  │ Social Media │  │ Dark Web │  │Tech &  │  │Corporate│
│ Web      │  │ Agents       │  │ Agent    │  │Infra   │  │Financial│
│ Agent    │  │ (Twitter,    │  │(Tor/I2P) │  │Agent   │  │Agent    │
│          │  │ Reddit,      │  │          │  │(Shodan,│  │(SEC,    │
│(Google,  │  │ Telegram,    │  │          │  │Censys) │  │OFAC)    │
│RSS,      │  │ YouTube,     │  │          │  │        │  │         │
│Scraping) │  │ LinkedIn)    │  │          │  │        │  │         │
└──────────┘  └───────────────┘  └──────────┘  └────────┘  └─────────┘

┌──────────────────────────────────────────────────────────────────┐
│           EXTERNAL DATA SOURCES (100+ APIs + Feeds)              │
└──────────────────────────────────────────────────────────────────┘
```

---

## Part 1: Detailed Agent Implementation Architecture

### 1.1 Agentic Orchestration Framework

**Core Components** (using LangGraph):

```python
from langgraph.graph import StateGraph, END
from langchain.agents import AgentExecutor, create_openai_tools_agent
from typing import TypedDict, Annotated
import operator

# Shared state across all agents
class InvestigationState(TypedDict):
    case_id: str
    user_query: str
    investigation_goal: str
    
    # Intermediate results
    entities_discovered: list
    hypotheses_generated: list
    evidence_collected: dict
    risk_scores: dict
    
    # Agent activity log
    agent_messages: Annotated[list, operator.add]
    audit_trail: list

# Agent definitions
class PlannerAgent:
    """Decomposes investigative goals into tasks"""
    def __init__(self, llm, tools):
        self.agent = create_openai_tools_agent(llm, tools, prompt)
        self.executor = AgentExecutor.from_agent_and_tools(self.agent, tools)
    
    def decompose(self, state: InvestigationState) -> InvestigationState:
        # Inputs: investigation_goal
        # Outputs: task_plan, assigned_agents, estimated_timeline
        goal_decomposition = self.executor.invoke({
            "input": f"Decompose this investigation: {state['investigation_goal']}",
            "conversation_history": state['agent_messages']
        })
        state['agent_messages'].append({
            'agent': 'planner',
            'action': 'decomposed_goal',
            'result': goal_decomposition
        })
        return state

class CollectionAgent:
    """Executes data collection from specific source"""
    def __init__(self, source_type: str, credentials: dict):
        self.source_type = source_type  # 'twitter', 'google', 'shodan', etc.
        self.credentials = credentials
        # Source-specific connectors initialized here
    
    def collect(self, state: InvestigationState, query: str) -> InvestigationState:
        # Call appropriate data source API
        raw_data = self._query_source(query)
        
        # Tag with metadata
        tagged_data = [{
            'source': self.source_type,
            'timestamp': datetime.now(),
            'query': query,
            'content': item,
            'confidence': 0.8,  # Source-dependent
            'jurisdiction': 'US'  # Source-dependent
        } for item in raw_data]
        
        # Log to audit trail
        state['audit_trail'].append({
            'action': 'data_collection',
            'agent': f'collection_{self.source_type}',
            'query': query,
            'result_count': len(tagged_data),
            'timestamp': datetime.now()
        })
        
        state['entities_discovered'].extend(tagged_data)
        return state

class HypothesisAgent:
    """Generates and tests hypotheses"""
    def __init__(self, llm, graph_db, vector_db):
        self.llm = llm
        self.graph_db = graph_db
        self.vector_db = vector_db
    
    def generate_hypotheses(self, state: InvestigationState) -> InvestigationState:
        # Prompt LLM with current graph + evidence
        current_entities = state['entities_discovered']
        current_graph = self._extract_graph_patterns()
        
        hypotheses = self.llm.invoke(f"""
        Given this entity set and knowledge graph patterns:
        Entities: {current_entities}
        Graph patterns: {current_graph}
        
        Generate 3-5 plausible, testable hypotheses that would advance the investigation.
        For each hypothesis, specify:
        1. Hypothesis statement
        2. Evidence that would support it
        3. Evidence that would refute it
        4. Collection tasks needed
        """)
        
        state['hypotheses_generated'] = hypotheses
        return state
    
    def test_hypothesis(self, state: InvestigationState, hypothesis: str) -> InvestigationState:
        # For each hypothesis:
        # 1. Identify what evidence is needed
        # 2. Check if we have it; if not, dispatch collection
        # 3. Perform Bayesian update: P(H | evidence)
        # 4. Score: confidence in hypothesis
        
        supporting_evidence = self._find_supporting_evidence(hypothesis)
        contradicting_evidence = self._find_contradicting_evidence(hypothesis)
        
        prior_prob = 0.5  # Start neutral
        likelihood_ratio = len(supporting_evidence) / (len(contradicting_evidence) + 1)
        posterior_prob = (likelihood_ratio * prior_prob) / (likelihood_ratio * prior_prob + (1 - prior_prob))
        
        state['hypotheses_generated'][hypothesis]['confidence'] = posterior_prob
        state['audit_trail'].append({
            'action': 'hypothesis_test',
            'hypothesis': hypothesis,
            'confidence': posterior_prob,
            'supporting_evidence': len(supporting_evidence),
            'contradicting_evidence': len(contradicting_evidence)
        })
        return state

# Orchestration workflow
def build_investigation_graph():
    graph = StateGraph(InvestigationState)
    
    # Add agents as nodes
    graph.add_node("planner", planner_agent.decompose)
    graph.add_node("twitter_collector", twitter_agent.collect)
    graph.add_node("graph_analyzer", entity_resolution.run)
    graph.add_node("hypothesis_gen", hypothesis_agent.generate_hypotheses)
    graph.add_node("risk_scorer", risk_scorer.score)
    
    # Define workflow edges
    graph.add_edge("START", "planner")
    graph.add_conditional_edges(
        "planner",
        lambda state: state['task_plan'][0]['agent_type'],  # Route to appropriate collector
        {
            "twitter": "twitter_collector",
            "google": "google_collector",
            "dark_web": "dark_web_collector"
        }
    )
    graph.add_edge("twitter_collector", "graph_analyzer")
    graph.add_edge("graph_analyzer", "hypothesis_gen")
    graph.add_edge("hypothesis_gen", "risk_scorer")
    graph.add_edge("risk_scorer", END)
    
    return graph.compile()

# Execution
investigation_graph = build_investigation_graph()
result = investigation_graph.invoke({
    'case_id': 'case_12345',
    'user_query': "Who is the hidden owner of Company X?",
    'investigation_goal': 'Identify beneficial owner chain for Company X',
    'entities_discovered': [],
    'hypotheses_generated': [],
    'evidence_collected': {},
    'risk_scores': {},
    'agent_messages': [],
    'audit_trail': []
})
```

---

## Part 2: Data Models & Schema (Neo4j Cypher)

### 2.1 Comprehensive Node & Relationship Schema

```cypher
-- ============ NODE TYPES ============

-- PERSON: Individual actor
CREATE CONSTRAINT person_id IF NOT EXISTS
  FOR (n:Person) REQUIRE n.id IS UNIQUE;

CREATE (p:Person {
  id: "person_uuid",
  name: "Full Name",
  aliases: ["alias1", "alias2"],
  email: ["email@domain.com"],
  phone: ["1-555-1234"],
  birth_date: "1980-01-15",
  nationality: ["US", "UK"],
  pep_status: false,
  sanctioned: false,
  social_handles: {
    twitter: "@handle",
    telegram: "@telegram_handle",
    reddit: "reddit_user",
    linkedin: "linkedin_profile"
  },
  crypto_addresses: ["1A1z7agoat2YLZW51Uxeqn2HHGsqy8mE3W"],
  addresses: ["123 Main St, New York, NY"],
  
  -- Metadata
  risk_score: 0.65,
  risk_score_confidence: 0.8,
  source_count: 15,  -- Number of sources mentioning this person
  last_updated: 1704067200000,
  created_date: 1704067200000,
  
  -- Investigation metadata
  investigation_relevant: true,
  investigator_notes: ""
})

-- ORGANIZATION: Company, NGO, government entity
CREATE CONSTRAINT org_id IF NOT EXISTS
  FOR (n:Organization) REQUIRE n.id IS UNIQUE;

CREATE (o:Organization {
  id: "org_uuid",
  name: "Company Name",
  legal_name: "Legal Entity Name Inc.",
  aliases: ["Company", "Company X"],
  
  -- Corporate structure
  registration_number: "EIN12345678",
  country: "US",
  state: "NY",
  city: "New York",
  headquarters: "123 Business Ave, New York, NY",
  subsidiaries: ["sub_org_id_1", "sub_org_id_2"],
  parent_org: "parent_org_id",
  
  -- Regulatory status
  sanctioned: false,
  sanctioned_by: ["OFAC"],
  pep: false,
  shell_company_score: 0.3,
  business_lines: ["Technology", "Consulting"],
  
  -- Financial
  annual_revenue: 10000000,
  employee_count: 500,
  founded_date: "2015-01-01",
  
  -- Risk
  risk_score: 0.4,
  risk_dimensions: {
    national_security: 0.2,
    criminal: 0.5,
    financial_crime: 0.3,
    cyber: 0.4,
    reputational: 0.35
  },
  
  -- Metadata
  last_updated: 1704067200000,
  source_count: 25
})

-- ASSET: IP, domain, email, phone, handle, crypto address
CREATE CONSTRAINT asset_id IF NOT EXISTS
  FOR (n:Asset) REQUIRE n.id IS UNIQUE;

CREATE (a:Asset {
  id: "asset_uuid",
  asset_type: "domain",  -- {domain, ip, email, phone, handle, crypto_address, hash}
  value: "example.com",
  
  -- Domain-specific
  ip_addresses: ["192.0.2.1"],  -- If domain
  dns_records: {A: "192.0.2.1", MX: "mail.example.com"},
  registrar: "GoDaddy",
  registration_date: "2020-01-15",
  expiration_date: "2025-01-15",
  
  -- Behavioral
  first_seen: 1704067200000,
  last_seen: 1704067200000,
  activity_pattern: "consistent",  -- {consistent, sporadic, dormant}
  
  -- Security/Risk
  malware_associated: false,
  c2_indicator: false,
  phishing_indicator: false,
  
  -- Metadata
  source_count: 5,
  confidence: 0.9
})

-- EVENT: Protest, meeting, transaction, arrest, etc.
CREATE CONSTRAINT event_id IF NOT EXISTS
  FOR (n:Event) REQUIRE n.id IS UNIQUE;

CREATE (e:Event {
  id: "event_uuid",
  event_type: "protest",  -- {protest, meeting, transaction, arrest, communication, etc.}
  title: "Event Title",
  description: "Detailed description",
  
  -- Temporal
  start_date: 1704067200000,
  end_date: 1704153600000,
  
  -- Spatial
  location: "New York, NY",
  coordinates: {latitude: 40.7128, longitude: -74.0060},
  location_type: "city",  -- {city, building, intersection, etc.}
  
  -- Participants
  participants: ["person_id_1", "person_id_2"],
  organizations_involved: ["org_id_1"],
  
  -- Analysis
  significance: 0.7,  -- 0-1 importance score
  clustered_with: ["event_id_2", "event_id_3"],  -- Related events
  
  -- Metadata
  source: "Twitter",
  source_url: "https://twitter.com/...",
  verified: false
})

-- CAMPAIGN_CLUSTER: Disinformation, recruitment, influence operations
CREATE CONSTRAINT campaign_id IF NOT EXISTS
  FOR (n:CampaignCluster) REQUIRE n.id IS UNIQUE;

CREATE (c:CampaignCluster {
  id: "campaign_uuid",
  campaign_type: "disinformation",  -- {disinformation, recruitment, influence, etc.}
  narrative: "Key narrative claim",
  description: "Multi-sentence campaign description",
  
  -- Temporal
  launch_date: 1704067200000,
  detected_date: 1704067200000,
  
  -- Reach & Coordination
  participant_accounts: ["account_id_1", "account_id_2"],
  participating_platforms: ["twitter", "telegram", "reddit"],
  estimated_impressions: 1000000,
  
  -- Behavioral Indicators
  coordinated_inauthentic_behavior_score: 0.85,
  timing_correlation: 0.9,
  phrase_similarity: 0.88,
  account_network_clustering: 0.92,
  
  -- Targets
  target_demographics: ["18-35", "US"],
  target_keywords: ["keyword1", "keyword2"],
  
  -- Risk
  risk_score: 0.8,
  
  -- Metadata
  last_updated: 1704067200000
})

-- ============ RELATIONSHIP TYPES ============

-- Person ─ owns ─→ Asset
CREATE (p:Person)-[r:OWNS {
  confidence: 0.9,
  source: "WHOIS",
  timestamp: 1704067200000
}]->(a:Asset)

-- Person ─ employed_by ─→ Organization
CREATE (p:Person)-[r:EMPLOYED_BY {
  confidence: 0.95,
  title: "Chief Technology Officer",
  start_date: "2020-01-15",
  end_date: "2024-12-31",
  source: "LinkedIn",
  timestamp: 1704067200000
}]->(o:Organization)

-- Person ─ owns ─→ Organization
CREATE (p:Person)-[r:OWNS {
  confidence: 0.85,
  share_percent: 51.0,
  source: "SEC_EDGAR",
  timestamp: 1704067200000
}]->(o:Organization)

-- Person ─ communicates_with ─→ Person
CREATE (p1:Person)-[r:COMMUNICATES_WITH {
  confidence: 0.75,
  communication_count: 125,
  last_communication: 1704067200000,
  platforms: ["telegram", "email"],
  source: "Telegram_Scrape",
  timestamp: 1704067200000
}]->(p2:Person)

-- Person ─ appears_with ─→ Person
CREATE (p1:Person)-[r:APPEARS_WITH {
  confidence: 0.8,
  co_appearance_count: 5,
  source: "News_Articles",
  locations: ["New York, NY"],
  timestamp: 1704067200000
}]->(p2:Person)

-- Person ─ co_travels_with ─→ Person
CREATE (p1:Person)-[r:CO_TRAVELS_WITH {
  confidence: 0.9,
  shared_locations: ["Dubai", "Moscow"],
  timeline_windows: [[start1, end1], [start2, end2]],
  source: "AIS_Data",
  timestamp: 1704067200000
}]->(p2:Person)

-- Organization ─ subsidiary_of ─→ Organization
CREATE (o1:Organization)-[r:SUBSIDIARY_OF {
  confidence: 0.99,
  ownership_percent: 100.0,
  source: "SEC_EDGAR",
  timestamp: 1704067200000
}]->(o2:Organization)

-- Organization ─ shares_infrastructure ─→ Organization
CREATE (o1:Organization)-[r:SHARES_INFRASTRUCTURE {
  confidence: 0.7,
  shared_ips: ["192.0.2.1"],
  shared_registrar: "GoDaddy",
  source: "Censys",
  timestamp: 1704067200000
}]->(o2:Organization)

-- Entity ─ mentioned_in ─→ Document
CREATE (e:Entity)-[r:MENTIONED_IN {
  confidence: 0.85,
  mention_context: "Text snippet around mention",
  source: "News_Article",
  document_id: "doc_123",
  timestamp: 1704067200000
}]->(d:Document)

-- Entity ─ part_of ─→ CampaignCluster
CREATE (e:Entity)-[r:PART_OF {
  confidence: 0.8,
  role: "amplifier",  -- {originator, amplifier, target, etc.}
  source: "Campaign_Analysis",
  timestamp: 1704067200000
}]->(c:CampaignCluster)

-- ============ COMPLEX QUERIES ============

-- Query: Find shell companies owned by Person X
MATCH (p:Person {name: "Person X"})-[owns:OWNS]->(o:Organization)
WHERE o.shell_company_score > 0.7
RETURN o, owns
ORDER BY o.shell_company_score DESC

-- Query: Find all 2-hop connections to high-risk actors
MATCH (p:Person {risk_score: {$gt: 0.7}})-[*1..2]-(connected)
RETURN connected, relationships

-- Query: Find coordinated campaigns involving multiple platforms
MATCH (c:CampaignCluster)
WHERE size(c.participating_platforms) > 2
  AND c.coordinated_inauthentic_behavior_score > 0.8
RETURN c, c.participant_accounts

-- Query: Temporal anomaly detection (impossible travel)
MATCH (p:Person)-[t1:APPEARS_AT]->(loc1:Location),
      (p)-[t2:APPEARS_AT]->(loc2:Location)
WHERE t1.timestamp < t2.timestamp
  AND t1.timestamp + 3600000 > t2.timestamp  -- Within 1 hour
  AND distance(loc1.coordinates, loc2.coordinates) > 1000000  -- >1000 km apart
RETURN p, loc1, loc2, t1.timestamp, t2.timestamp

-- Query: Risk propagation (find high-risk organizations connected to low-risk ones)
MATCH (high_risk:Organization {risk_score: {$gt: 0.7}})-[r:SHARES_INFRASTRUCTURE]->(low_risk:Organization)
WHERE low_risk.risk_score < 0.5
SET low_risk.risk_score = (high_risk.risk_score + low_risk.risk_score) / 2
RETURN low_risk, low_risk.risk_score
```

---

## Part 3: Collection Agent Implementation Examples

### 3.1 Twitter/X Agent (API-Based)

```python
import tweepy
from datetime import datetime, timedelta
import asyncio
from tenacity import retry, stop_after_attempt, wait_exponential

class TwitterCollectionAgent:
    def __init__(self, api_key, api_secret, access_token, access_token_secret):
        self.client = tweepy.Client(
            bearer_token=api_key,
            consumer_key=api_secret,
            consumer_secret=access_token,
            access_token=access_token_secret,
            wait_on_rate_limit=True
        )
        self.rate_limit_manager = RateLimitManager()
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential())
    async def search_tweets(self, query: str, case_id: str, max_results: int = 100):
        """Search tweets matching query"""
        try:
            tweets = self.client.search_recent_tweets(
                query=query,
                max_results=max_results,
                tweet_fields=['created_at', 'author_id', 'public_metrics', 'lang'],
                expansions=['author_id'],
                user_fields=['created_at', 'followers_count', 'verified']
            )
            
            # Transform to our schema
            processed_tweets = []
            for tweet in tweets.data:
                processed_tweets.append({
                    'source': 'twitter',
                    'source_id': tweet.id,
                    'timestamp': tweet.created_at.timestamp(),
                    'content': tweet.text,
                    'author_id': tweet.author_id,
                    'engagement': tweet.public_metrics,
                    'language': tweet.lang,
                    'confidence': 0.9,
                    'case_id': case_id
                })
            
            # Log to audit trail
            audit_log(case_id, 'twitter_search', {
                'query': query,
                'results': len(processed_tweets),
                'timestamp': datetime.now()
            })
            
            return processed_tweets
        
        except tweepy.TweepyException as e:
            print(f"Twitter API error: {e}")
            raise
    
    async def get_user_timeline(self, user_id: str, case_id: str, lookback_days: int = 30):
        """Get recent tweets from specific user"""
        start_time = datetime.now() - timedelta(days=lookback_days)
        
        tweets = self.client.get_users_tweets(
            id=user_id,
            start_time=start_time,
            max_results=100,
            tweet_fields=['created_at', 'public_metrics', 'lang', 'entities']
        )
        
        processed = []
        for tweet in tweets.data:
            # Extract entities (URLs, mentions, hashtags)
            entities = self._extract_entities(tweet)
            
            processed.append({
                'source': 'twitter',
                'source_id': tweet.id,
                'user_id': user_id,
                'timestamp': tweet.created_at.timestamp(),
                'content': tweet.text,
                'entities': entities,
                'engagement': tweet.public_metrics,
                'case_id': case_id
            })
        
        return processed
    
    def _extract_entities(self, tweet):
        """Extract URLs, mentions, hashtags from tweet"""
        entities = {
            'urls': [],
            'mentions': [],
            'hashtags': []
        }
        
        if hasattr(tweet, 'entities') and tweet.entities:
            if 'urls' in tweet.entities:
                entities['urls'] = [u['expanded_url'] for u in tweet.entities['urls']]
            if 'mentions' in tweet.entities:
                entities['mentions'] = [m['username'] for m in tweet.entities['mentions']]
            if 'hashtags' in tweet.entities:
                entities['hashtags'] = [h['tag'] for h in tweet.entities['hashtags']]
        
        return entities
```

### 3.2 Dark Web Agent (Tor Crawler)

```python
import requests
from stem import Signal
from stem.control import Controller
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import time
import random

class DarkWebCollectionAgent:
    def __init__(self, tor_control_port: int = 9051, tor_socks_port: int = 9050):
        self.tor_control_port = tor_control_port
        self.tor_socks_port = tor_socks_port
        self.session = self._init_tor_session()
    
    def _init_tor_session(self):
        """Initialize Tor session via SOCKS5"""
        proxies = {
            'http': f'socks5://127.0.0.1:{self.tor_socks_port}',
            'https': f'socks5://127.0.0.1:{self.tor_socks_port}'
        }
        session = requests.Session()
        session.proxies.update(proxies)
        return session
    
    def _rotate_tor_identity(self):
        """Request new Tor circuit"""
        try:
            with Controller.from_port(port=self.tor_control_port) as controller:
                controller.authenticate()
                controller.signal(Signal.NEWNYM)
                time.sleep(controller.get_newnym_wait())
        except Exception as e:
            print(f"Tor rotation error: {e}")
    
    def crawl_marketplace(self, onion_url: str, case_id: str, max_pages: int = 10):
        """Crawl dark web marketplace"""
        crawled_items = []
        visited_urls = set()
        
        for page_num in range(max_pages):
            try:
                # Random delay to avoid detection
                time.sleep(random.uniform(5, 15))
                
                # Rotate Tor identity every N requests
                if page_num % 3 == 0:
                    self._rotate_tor_identity()
                
                url = f"{onion_url}?page={page_num}"
                if url in visited_urls:
                    continue
                visited_urls.add(url)
                
                response = self.session.get(
                    url,
                    timeout=30,
                    headers={
                        'User-Agent': self._random_user_agent()
                    }
                )
                
                if response.status_code != 200:
                    continue
                
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Extract marketplace items
                items = soup.find_all('div', class_='listing')
                for item in items:
                    parsed = self._parse_marketplace_item(item)
                    crawled_items.append({
                        'source': 'dark_web',
                        'marketplace_url': onion_url,
                        'timestamp': datetime.now().timestamp(),
                        'item': parsed,
                        'confidence': 0.7,
                        'case_id': case_id
                    })
            
            except Exception as e:
                print(f"Crawl error on page {page_num}: {e}")
                continue
        
        return crawled_items
    
    def _parse_marketplace_item(self, item_element):
        """Extract structured data from marketplace listing"""
        parsed = {
            'title': item_element.find('h2', class_='title').text if item_element.find('h2') else '',
            'seller': item_element.find('span', class_='seller').text if item_element.find('span', class_='seller') else '',
            'price': item_element.find('span', class_='price').text if item_element.find('span', class_='price') else '',
            'description': item_element.find('p', class_='description').text if item_element.find('p') else '',
            'category': item_element.find('span', class_='category').text if item_element.find('span', class_='category') else ''
        }
        
        # Extract IOCs
        parsed['extracted_iocs'] = self._extract_iocs(parsed['description'])
        
        return parsed
    
    def _extract_iocs(self, text: str):
        """Extract indicators of compromise"""
        import re
        
        iocs = {
            'ip_addresses': re.findall(r'\b(?:\d{1,3}\.){3}\d{1,3}\b', text),
            'urls': re.findall(r'https?://[^\s]+', text),
            'email_addresses': re.findall(r'[\w\.-]+@[\w\.-]+\.\w+', text),
            'hashes': re.findall(r'[a-f0-9]{32}|[a-f0-9]{40}|[a-f0-9]{64}', text)
        }
        
        return iocs
    
    def _random_user_agent(self):
        """Return randomized user agent"""
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'
        ]
        return random.choice(user_agents)
```

---

## Part 4: Risk Scoring Engine (Detailed)

```python
from enum import Enum
from dataclasses import dataclass
from typing import Dict, List

class RiskDimension(Enum):
    NATIONAL_SECURITY = 'national_security'
    CRIMINAL = 'criminal'
    FINANCIAL_CRIME = 'financial_crime'
    CYBER = 'cyber'
    REPUTATIONAL = 'reputational'
    SUPPLY_CHAIN = 'supply_chain'

@dataclass
class RiskFactor:
    dimension: RiskDimension
    weight: float  # 0-1
    evidence: str
    source: str
    confidence: float

class RiskScoringEngine:
    def __init__(self, weights: Dict[RiskDimension, float] = None):
        # Default weights (configurable per use case)
        self.weights = weights or {
            RiskDimension.NATIONAL_SECURITY: 0.25,
            RiskDimension.CRIMINAL: 0.20,
            RiskDimension.FINANCIAL_CRIME: 0.20,
            RiskDimension.CYBER: 0.15,
            RiskDimension.REPUTATIONAL: 0.12,
            RiskDimension.SUPPLY_CHAIN: 0.08
        }
        self.risk_factors = []
    
    def add_factor(self, factor: RiskFactor):
        """Add a risk factor"""
        self.risk_factors.append(factor)
    
    def compute_score(self) -> Dict:
        """Compute overall and dimensional risk scores"""
        
        # Group factors by dimension
        dimension_scores = {}
        for dimension in RiskDimension:
            factors = [f for f in self.risk_factors if f.dimension == dimension]
            if factors:
                # Average factor scores, weighted by confidence
                weighted_sum = sum(f.weight * f.confidence for f in factors)
                weight_sum = sum(f.confidence for f in factors)
                dimension_scores[dimension] = weighted_sum / weight_sum if weight_sum > 0 else 0
            else:
                dimension_scores[dimension] = 0
        
        # Compute overall score
        overall_score = sum(
            dimension_scores[dim] * self.weights[dim]
            for dim in RiskDimension
        )
        
        return {
            'overall_score': overall_score,
            'dimensional_scores': {d.value: s for d, s in dimension_scores.items()},
            'factors': [
                {
                    'dimension': f.dimension.value,
                    'weight': f.weight,
                    'evidence': f.evidence,
                    'source': f.source,
                    'confidence': f.confidence
                }
                for f in self.risk_factors
            ],
            'timestamp': datetime.now().timestamp()
        }
    
    def add_sanctions_match(self, sanctions_list: str, confidence: float = 1.0):
        """Add factor for sanctions list match"""
        self.add_factor(RiskFactor(
            dimension=RiskDimension.NATIONAL_SECURITY,
            weight=1.0,
            evidence=f"Entity listed on {sanctions_list}",
            source=sanctions_list,
            confidence=confidence
        ))
    
    def add_dark_web_presence(self, threat_level: str, confidence: float = 0.8):
        """Add factor for dark web presence"""
        weight_map = {'high': 0.9, 'medium': 0.6, 'low': 0.3}
        self.add_factor(RiskFactor(
            dimension=RiskDimension.CRIMINAL,
            weight=weight_map.get(threat_level, 0.5),
            evidence=f"Active dark web presence ({threat_level})",
            source="Dark Web Monitoring",
            confidence=confidence
        ))
    
    def add_infrastructure_exposure(self, exposed_services: List[str], confidence: float = 0.85):
        """Add factor for exposed infrastructure"""
        self.add_factor(RiskFactor(
            dimension=RiskDimension.CYBER,
            weight=min(0.9, len(exposed_services) * 0.2),
            evidence=f"Exposed services: {', '.join(exposed_services)}",
            source="Shodan/Censys",
            confidence=confidence
        ))
    
    def get_explanation(self) -> str:
        """Generate human-readable explanation of score"""
        score_data = self.compute_score()
        overall = score_data['overall_score']
        
        explanation = f"Risk Score: {overall:.2f}/1.0\n\n"
        explanation += "Contributing Factors:\n"
        
        for factor in score_data['factors']:
            explanation += f"• {factor['dimension']}: {factor['evidence']} "
            explanation += f"(Source: {factor['source']}, Confidence: {factor['confidence']:.1%})\n"
        
        explanation += f"\nConfidence: {min(1.0, sum(f['confidence'] for f in score_data['factors']) / len(score_data['factors'])):.1%}"
        
        return explanation
```

---

## Part 5: Deployment & Scaling

### 5.1 Docker Compose Setup (Local Development)

```yaml
version: '3.9'

services:
  # Graph Database
  neo4j:
    image: neo4j:5.13-enterprise
    environment:
      NEO4J_AUTH: neo4j/password123
      NEO4J_PLUGINS: '["graph-data-science"]'
    ports:
      - "7687:7687"
      - "7474:7474"
    volumes:
      - neo4j_data:/data
      - neo4j_logs:/logs
  
  # Time-Series DB
  timescaledb:
    image: timescale/timescaledb:latest-pg15
    environment:
      POSTGRES_USER: osint
      POSTGRES_PASSWORD: password123
      POSTGRES_DB: osint_timeline
    ports:
      - "5432:5432"
    volumes:
      - timescale_data:/var/lib/postgresql/data
  
  # Search/Indexing
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.10.0
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=false
      - "ES_JAVA_OPTS=-Xms512m -Xmx512m"
    ports:
      - "9200:9200"
    volumes:
      - es_data:/usr/share/elasticsearch/data
  
  # Cache Layer
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
  
  # Vector Database
  pinecone:
    # Use Pinecone cloud for now (serverless)
    # Or use Weaviate locally:
    image: semitechnologies/weaviate:latest
    ports:
      - "8080:8080"
      - "50051:50051"
    environment:
      QUERY_DEFAULTS_LIMIT: 100
      PERSISTENCE_DATA_PATH: /var/lib/weaviate
  
  # FastAPI Backend
  api:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      NEO4J_URI: bolt://neo4j:7687
      NEO4J_AUTH: neo4j/password123
      TIMESCALE_URI: postgresql://osint:password123@timescaledb:5432/osint_timeline
      ELASTICSEARCH_URL: http://elasticsearch:9200
      REDIS_URL: redis://redis:6379
      OPENAI_API_KEY: ${OPENAI_API_KEY}
      TWITTER_BEARER_TOKEN: ${TWITTER_BEARER_TOKEN}
    depends_on:
      - neo4j
      - timescaledb
      - elasticsearch
      - redis
    volumes:
      - ./backend:/app
  
  # Next.js Frontend
  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    environment:
      NEXT_PUBLIC_API_URL: http://localhost:8000
    depends_on:
      - api

volumes:
  neo4j_data:
  neo4j_logs:
  timescale_data:
  es_data:
  redis_data:
```

### 5.2 Kubernetes Deployment (Production)

```yaml
---
# Neo4j StatefulSet
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: neo4j
spec:
  serviceName: neo4j
  replicas: 1
  selector:
    matchLabels:
      app: neo4j
  template:
    metadata:
      labels:
        app: neo4j
    spec:
      containers:
      - name: neo4j
        image: neo4j:5.13-enterprise
        ports:
        - containerPort: 7687
          name: bolt
        env:
        - name: NEO4J_AUTH
          valueFrom:
            secretKeyRef:
              name: neo4j-secrets
              key: auth
        resources:
          requests:
            memory: "4Gi"
            cpu: "2"
          limits:
            memory: "8Gi"
            cpu: "4"
        volumeMounts:
        - name: neo4j-data
          mountPath: /data
  volumeClaimTemplates:
  - metadata:
      name: neo4j-data
    spec:
      accessModes: ["ReadWriteOnce"]
      resources:
        requests:
          storage: 100Gi

---
# API Deployment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: osint-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: osint-api
  template:
    metadata:
      labels:
        app: osint-api
    spec:
      containers:
      - name: api
        image: osint-api:latest
        ports:
        - containerPort: 8000
        env:
        - name: NEO4J_URI
          value: "bolt://neo4j.default.svc.cluster.local:7687"
        - name: NEO4J_AUTH
          valueFrom:
            secretKeyRef:
              name: neo4j-secrets
              key: auth
        resources:
          requests:
            memory: "2Gi"
            cpu: "1"
          limits:
            memory: "4Gi"
            cpu: "2"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 5

---
# Service
apiVersion: v1
kind: Service
metadata:
  name: osint-api
spec:
  selector:
    app: osint-api
  ports:
  - port: 8000
    targetPort: 8000
  type: LoadBalancer
```

---

## Conclusion

This technical guide provides the foundation for implementing OAA with production-grade architecture, focusing on:

1. **Agentic Orchestration**: LangGraph-based multi-agent choreography with shared state
2. **Data Models**: Comprehensive Neo4j schema capturing OSINT entities + relationships
3. **Agent Implementation**: Concrete examples for Twitter, dark web, and risk scoring
4. **Deployment**: Docker + Kubernetes for scalability
5. **Auditability**: Full logging + forensic reconstruction

**Next Steps**: Use this as blueprint for MVP development; iterate based on user feedback and government pilot results.
