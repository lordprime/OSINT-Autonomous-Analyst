"""
Base schemas for OSINT Autonomous Analyst
All Pydantic models for data validation and serialization
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


# ============================================
# Enums
# ============================================

class InvestigationStatus(str, Enum):
    CREATED = "created"
    PLANNING = "planning"
    COLLECTING = "collecting"
    ANALYZING = "analyzing"
    COMPLETED = "completed"
    FAILED = "failed"


class CollectionStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class EntityType(str, Enum):
    PERSON = "person"
    ORGANIZATION = "organization"
    LOCATION = "location"
    EMAIL = "email"
    PHONE = "phone"
    URL = "url"
    IP_ADDRESS = "ip_address"
    CRYPTOCURRENCY = "cryptocurrency"
    USERNAME = "username"
    DOCUMENT = "document"


class HypothesisVerdict(str, Enum):
    SUPPORTED = "supported"
    REFUTED = "refuted"
    INCONCLUSIVE = "inconclusive"


class LLMProvider(str, Enum):
    OLLAMA = "ollama"
    GROQ = "groq"
    CLAUDE = "claude"
    OPENAI = "openai"


# ============================================
# Core Models
# ============================================

class Investigation(BaseModel):
    """Investigation data model"""
    id: str
    name: str
    target: str
    goal: str
    status: InvestigationStatus
    created_by: str
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = {}
    
    class Config:
        from_attributes = True


class Entity(BaseModel):
    """Entity in knowledge graph"""
    id: str
    name: str
    type: EntityType
    confidence: float = Field(ge=0.0, le=1.0)
    properties: Dict[str, Any] = {}
    sources: List[str] = []
    first_seen: datetime
    last_updated: datetime
    investigation_id: str
    
    class Config:
        from_attributes = True


class Relationship(BaseModel):
    """Relationship between entities"""
    id: str
    from_entity_id: str
    to_entity_id: str
    relationship_type: str
    confidence: float = Field(ge=0.0, le=1.0)
    properties: Dict[str, Any] = {}
    sources: List[str] = []
    created_at: datetime
    investigation_id: str
    
    class Config:
        from_attributes = True


class CollectionJob(BaseModel):
    """Data collection job"""
    id: str
    investigation_id: str
    agent_type: str
    query: str
    status: CollectionStatus
    started_at: datetime
    completed_at: Optional[datetime] = None
    items_collected: int = 0
    entities_discovered: int = 0
    errors: List[str] = []
    metadata: Dict[str, Any] = {}
    
    class Config:
        from_attributes = True


class Hypothesis(BaseModel):
    """Investigation hypothesis"""
    id: str
    investigation_id: str
    text: str
    confidence: float = Field(ge=0.0, le=1.0)
    verdict: Optional[HypothesisVerdict] = None
    supporting_evidence: List[str] = []
    contradicting_evidence: List[str] = []
    created_at: datetime
    updated_at: datetime
    created_by_llm: str
    reasoning: str
    
    class Config:
        from_attributes = True


class Evidence(BaseModel):
    """Evidence piece for hypothesis testing"""
    id: str
    hypothesis_id: str
    content: str
    source: str
    source_type: str
    confidence: float = Field(ge=0.0, le=1.0)
    supports_hypothesis: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class TimelineEvent(BaseModel):
    """Event in investigation timeline"""
    id: str
    investigation_id: str
    timestamp: datetime
    event_type: str
    description: str
    entity_ids: List[str] = []
    metadata: Dict[str, Any] = {}
    
    class Config:
        from_attributes = True


class AuditLog(BaseModel):
    """Audit log entry"""
    id: str
    investigation_id: Optional[str] = None
    user_id: str
    action: str
    resource_type: str
    resource_id: str
    justification: Optional[str] = None
    timestamp: datetime
    metadata: Dict[str, Any] = {}
    
    class Config:
        from_attributes = True


# ============================================
# Authentication Models
# ============================================

class User(BaseModel):
    """User account"""
    id: str
    username: str
    email: str
    role: str = "analyst"
    created_at: datetime
    last_login: Optional[datetime] = None
    is_active: bool = True
    
    class Config:
        from_attributes = True


class Token(BaseModel):
    """JWT token response"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    refresh_token: Optional[str] = None


class TokenData(BaseModel):
    """Decoded token data"""
    username: str
    role: str = "analyst"
    exp: Optional[int] = None


# ============================================
# Graph Models
# ============================================

class GraphNode(BaseModel):
    """Node in graph visualization"""
    id: str
    label: str
    type: EntityType
    confidence: float
    properties: Dict[str, Any] = {}


class GraphEdge(BaseModel):
    """Edge in graph visualization"""
    id: str
    source: str
    target: str
    label: str
    confidence: float
    properties: Dict[str, Any] = {}


class GraphData(BaseModel):
    """Complete graph data for visualization"""
    nodes: List[GraphNode]
    edges: List[GraphEdge]
    metadata: Dict[str, Any] = {}


# ============================================
# LLM Models
# ============================================

class LLMModel(BaseModel):
    """Available LLM model"""
    provider: LLMProvider
    model_name: str
    available: bool
    description: str


class ReasoningPlan(BaseModel):
    """AI-generated investigation plan"""
    investigation_id: str
    tasks: List[Dict[str, Any]]
    strategy_notes: str
    created_at: datetime
    created_by_llm: str
