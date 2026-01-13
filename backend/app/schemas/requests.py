"""
Request schemas for API endpoints
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from app.schemas.base import EntityType, LLMProvider


# ============================================
# Investigation Requests
# ============================================

class InvestigationCreate(BaseModel):
    """Create new investigation"""
    name: str = Field(..., min_length=3, max_length=200)
    target: str = Field(..., min_length=1, max_length=500)
    goal: str = Field(..., min_length=10, max_length=2000)
    metadata: Dict[str, Any] = {}


class InvestigationUpdate(BaseModel):
    """Update investigation"""
    name: Optional[str] = Field(None, min_length=3, max_length=200)
    goal: Optional[str] = Field(None, min_length=10, max_length=2000)
    metadata: Optional[Dict[str, Any]] = None


# ============================================
# Collection Requests
# ============================================

class CollectionStart(BaseModel):
    """Start collection job"""
    investigation_id: str
    agent_type: str = Field(..., description="duckduckgo, telegram, instagram, linkedin, facebook")
    query: str = Field(..., min_length=1, max_length=500)
    collection_type: Optional[str] = None
    max_results: int = Field(default=100, ge=1, le=1000)
    metadata: Dict[str, Any] = {}
    
    @validator('agent_type')
    def validate_agent_type(cls, v):
        allowed = ['duckduckgo', 'telegram', 'instagram', 'linkedin', 'facebook', 'twitter', 'reddit']
        if v not in allowed:
            raise ValueError(f"agent_type must be one of {allowed}")
        return v


class CollectionCancel(BaseModel):
    """Cancel collection job"""
    reason: Optional[str] = None


# ============================================
# Entity Requests
# ============================================

class EntitySearch(BaseModel):
    """Search entities"""
    investigation_id: Optional[str] = None
    query: str = Field(..., min_length=1)
    entity_type: Optional[EntityType] = None
    min_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    limit: int = Field(default=50, ge=1, le=500)


class EntityMerge(BaseModel):
    """Merge duplicate entities"""
    entity_ids: List[str] = Field(..., min_items=2)
    primary_entity_id: str
    justification: str = Field(..., min_length=10)


# ============================================
# Graph Requests
# ============================================

class GraphQuery(BaseModel):
    """Execute graph query"""
    investigation_id: str
    cypher_query: Optional[str] = None
    entity_id: Optional[str] = None
    depth: int = Field(default=2, ge=1, le=5)
    max_nodes: int = Field(default=100, ge=1, le=500)


# ============================================
# Reasoning Requests
# ============================================

class ReasoningPlanRequest(BaseModel):
    """Request investigation plan from LLM"""
    investigation_id: str
    goal: str
    current_context: Dict[str, Any] = {}
    llm_provider: Optional[LLMProvider] = None


class HypothesisGenerate(BaseModel):
    """Generate hypotheses"""
    investigation_id: str
    graph_context: Dict[str, Any] = {}
    text_context: str = ""
    llm_provider: Optional[LLMProvider] = None


class HypothesisTest(BaseModel):
    """Test hypothesis"""
    hypothesis_id: str
    supporting_evidence_ids: List[str]
    contradicting_evidence_ids: List[str]
    llm_provider: Optional[LLMProvider] = None


class EntityExplain(BaseModel):
    """Explain entity relationships"""
    entity_id: str
    question: str = Field(..., min_length=5)
    investigation_id: str
    llm_provider: Optional[LLMProvider] = None


# ============================================
# Authentication Requests
# ============================================

class UserRegister(BaseModel):
    """Register new user"""
    username: str = Field(..., min_length=3, max_length=50, pattern=r'^[a-zA-Z0-9_-]+$')
    email: str = Field(..., pattern=r'^[\w\.-]+@[\w\.-]+\.\w+$')
    password: str = Field(..., min_length=8)
    role: str = Field(default="analyst")
    
    @validator('role')
    def validate_role(cls, v):
        allowed = ['analyst', 'admin', 'viewer']
        if v not in allowed:
            raise ValueError(f"role must be one of {allowed}")
        return v


class UserLogin(BaseModel):
    """Login request"""
    username: str
    password: str


class TokenRefresh(BaseModel):
    """Refresh token request"""
    refresh_token: str
