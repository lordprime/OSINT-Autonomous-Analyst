"""
Response schemas for API endpoints
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime
from app.schemas.base import (
    Investigation, Entity, Relationship, CollectionJob,
    Hypothesis, Evidence, GraphData, LLMModel, User, Token
)


# ============================================
# Standard Response Wrappers
# ============================================

class SuccessResponse(BaseModel):
    """Standard success response"""
    success: bool = True
    message: str
    data: Optional[Any] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ErrorResponse(BaseModel):
    """Standard error response"""
    success: bool = False
    error: str
    details: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class PaginatedResponse(BaseModel):
    """Paginated response"""
    items: List[Any]
    total: int
    page: int
    page_size: int
    has_next: bool
    has_prev: bool


# ============================================
# Investigation Responses
# ============================================

class InvestigationResponse(BaseModel):
    """Single investigation response"""
    investigation: Investigation
    entity_count: int = 0
    collection_job_count: int = 0
    hypothesis_count: int = 0


class InvestigationListResponse(BaseModel):
    """List of investigations"""
    investigations: List[Investigation]
    total: int


class InvestigationTimelineResponse(BaseModel):
    """Investigation timeline"""
    investigation_id: str
    events: List[Dict[str, Any]]
    start_date: datetime
    end_date: datetime


# ============================================
# Collection Responses
# ============================================

class CollectionJobResponse(BaseModel):
    """Collection job status"""
    job: CollectionJob
    progress_percent: float = Field(ge=0.0, le=100.0)


class CollectionSourcesResponse(BaseModel):
    """Available collection sources"""
    sources: List[Dict[str, Any]]


# ============================================
# Entity & Graph Responses
# ============================================

class EntityResponse(BaseModel):
    """Single entity response"""
    entity: Entity
    relationships: List[Relationship] = []


class EntitySearchResponse(BaseModel):
    """Entity search results"""
    entities: List[Entity]
    total: int


class GraphResponse(BaseModel):
    """Graph data response"""
    graph: GraphData
    investigation_id: str
    node_count: int
    edge_count: int


# ============================================
# Reasoning Responses
# ============================================

class ReasoningPlanResponse(BaseModel):
    """Investigation plan from LLM"""
    investigation_id: str
    tasks: List[Dict[str, Any]]
    strategy_notes: str
    llm_provider: str


class HypothesesResponse(BaseModel):
    """Generated hypotheses"""
    hypotheses: List[Hypothesis]
    investigation_id: str
    llm_provider: str


class HypothesisTestResponse(BaseModel):
    """Hypothesis test result"""
    hypothesis: Hypothesis
    verdict: str
    confidence: float
    reasoning: str


class EntityExplanationResponse(BaseModel):
    """Entity explanation from LLM"""
    entity_id: str
    explanation: str
    evidence_timeline: List[Dict[str, Any]]
    confidence: float
    caveats: List[str]


class LLMModelsResponse(BaseModel):
    """Available LLM models"""
    models: List[LLMModel]
    default_provider: str


# ============================================
# Authentication Responses
# ============================================

class UserResponse(BaseModel):
    """User profile response"""
    user: User


class LoginResponse(BaseModel):
    """Login success response"""
    token: Token
    user: User


# ============================================
# Health Check Responses
# ============================================

class HealthCheckResponse(BaseModel):
    """Service health status"""
    status: str
    version: str
    services: Dict[str, str]
    timestamp: datetime = Field(default_factory=datetime.utcnow)
