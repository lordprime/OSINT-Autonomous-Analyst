"""
Base Collection Agent - Abstract interface for all data collectors.
Provides standardized error handling, rate limiting, and audit logging.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import time
import logging
from enum import Enum

from app.core.audit import audit_logger
from app.core.config import settings

logger = logging.getLogger(__name__)

# ============================================
# Enums
# ============================================

class CollectionStatus(str, Enum):
    """Status of collection job"""
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    DENIED = "denied"

# ============================================
# Data Models
# ============================================

@dataclass
class CollectionResult:
    """Standardized collection result"""
    job_id: str
    status: CollectionStatus
    items_collected: int
    entities_discovered: int
    errors: List[str]
    metadata: Dict[str, Any]
    audit_log_id: str
    started_at: int
    completed_at: Optional[int] = None

@dataclass
class CollectedItem:
    """Standardized collected data item"""
    source: str  # Agent type (twitter, reddit, etc.)
    source_id: str  # Platform-specific ID
    timestamp: int
    content: str
    author_id: Optional[str] = None
    entities: Dict[str, List[str]] = None  # URLs, mentions, hashtags, etc.
    metadata: Dict[str, Any] = None
    confidence: float = 0.8
    jurisdiction: str = "unknown"

# ============================================
# Base Collection Agent
# ============================================

class BaseCollectionAgent(ABC):
    """
    Abstract base class for all collection agents.
    
    Enforces:
    - Standardized error handling
    - Rate limiting integration
    - Audit logging
    - Data normalization
    """
    
    def __init__(self, agent_type: str):
        self.agent_type = agent_type
        self.logger = logging.getLogger(f"agent.{agent_type}")
    
    @abstractmethod
    async def collect(
        self,
        investigation_id: str,
        query: str,
        user_id: str,
        justification: str,
        **kwargs
    ) -> CollectionResult:
        """
        Execute collection operation.
        
        Args:
            investigation_id: UUID of investigation
            query: Search query or target
            user_id: User initiating collection
            justification: Reason for collection (audit requirement)
            **kwargs: Agent-specific parameters
        
        Returns:
            CollectionResult with status and collected items
        """
        pass
    
    @abstractmethod
    def _execute_collection(
        self,
        query: str,
        **kwargs
    ) -> List[CollectedItem]:
        """
        Agent-specific collection logic.
        Must be implemented by subclasses.
        """
        pass
    
    def _normalize_data(self, raw_data: Any) -> CollectedItem:
        """
        Normalize platform-specific data to standard format.
        Must be implemented by subclasses.
        """
        raise NotImplementedError("Subclass must implement _normalize_data")
    
    def _check_compliance(
        self,
        target: str,
        investigation_id: str,
        user_id: str
    ) -> tuple[bool, Optional[str], Optional[str]]:
        """
        Check if collection is permitted by compliance policies.
        
        Returns:
            (allowed, denial_reason, policy_id)
        """
        # TODO: Implement actual compliance checking (Agent 6)
        # For now, allow all collections
        return True, None, None
    
    def _log_collection(
        self,
        user_id: str,
        investigation_id: str,
        target: str,
        justification: str,
        status: str,
        items_collected: int = 0
    ) -> str:
        """Log collection action to audit trail"""
        return audit_logger.log_collection(
            user_id=user_id,
            investigation_id=investigation_id,
            target_url=target,
            agent_type=self.agent_type,
            justification=justification,
            response_status=status,
            items_collected=items_collected
        )
    
    def _log_denied_collection(
        self,
        user_id: str,
        investigation_id: str,
        target: str,
        denial_reason: str,
        denial_policy_id: str,
        justification: str
    ) -> str:
        """Log denied collection action"""
        return audit_logger.log_denied_action(
            user_id=user_id,
            action_type="collection",
            target=target,
            denial_reason=denial_reason,
            denial_policy_id=denial_policy_id,
            investigation_id=investigation_id,
            justification_provided=justification
        )
    
    async def collect_with_audit(
        self,
        investigation_id: str,
        query: str,
        user_id: str,
        justification: str,
        **kwargs
    ) -> CollectionResult:
        """
        Wrapper that adds compliance checking and audit logging.
        """
        job_id = f"{self.agent_type}_{int(time.time())}"
        started_at = int(time.time())
        
        # 1. Check compliance
        allowed, denial_reason, policy_id = self._check_compliance(
            target=query,
            investigation_id=investigation_id,
            user_id=user_id
        )
        
        if not allowed:
            # Log denied action
            audit_log_id = self._log_denied_collection(
                user_id=user_id,
                investigation_id=investigation_id,
                target=query,
                denial_reason=denial_reason,
                denial_policy_id=policy_id,
                justification=justification
            )
            
            self.logger.warning(
                f"Collection DENIED: {self.agent_type} - {query} - Reason: {denial_reason}"
            )
            
            return CollectionResult(
                job_id=job_id,
                status=CollectionStatus.DENIED,
                items_collected=0,
                entities_discovered=0,
                errors=[denial_reason],
                metadata={"denial_policy_id": policy_id},
                audit_log_id=audit_log_id,
                started_at=started_at,
                completed_at=int(time.time())
            )
        
        # 2. Execute collection
        try:
            self.logger.info(f"Starting collection: {self.agent_type} - {query}")
            
            items = await self._execute_collection(query, **kwargs)
            
            # Log success
            audit_log_id = self._log_collection(
                user_id=user_id,
                investigation_id=investigation_id,
                target=query,
                justification=justification,
                status="completed",
                items_collected=len(items)
            )
            
            self.logger.info(
                f"Collection completed: {self.agent_type} - {len(items)} items"
            )
            
            return CollectionResult(
                job_id=job_id,
                status=CollectionStatus.COMPLETED,
                items_collected=len(items),
                entities_discovered=self._count_unique_entities(items),
                errors=[],
                metadata={"query": query},
                audit_log_id=audit_log_id,
                started_at=started_at,
                completed_at=int(time.time())
            )
        
        except Exception as e:
            # Log failure
            audit_log_id = self._log_collection(
                user_id=user_id,
                investigation_id=investigation_id,
                target=query,
                justification=justification,
                status="failed",
                items_collected=0
            )
            
            self.logger.error(
                f"Collection failed: {self.agent_type} - {query} - Error: {e}",
                exc_info=True
            )
            
            return CollectionResult(
                job_id=job_id,
                status=CollectionStatus.FAILED,
                items_collected=0,
                entities_discovered=0,
                errors=[str(e)],
                metadata={"query": query},
                audit_log_id=audit_log_id,
                started_at=started_at,
                completed_at=int(time.time())
            )
    
    def _count_unique_entities(self, items: List[CollectedItem]) -> int:
        """Count unique entities discovered"""
        unique_entities = set()
        for item in items:
            if item.author_id:
                unique_entities.add(item.author_id)
            if item.entities:
                for entity_list in item.entities.values():
                    unique_entities.update(entity_list)
        return len(unique_entities)
