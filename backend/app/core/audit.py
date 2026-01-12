"""
Comprehensive audit logging with government-grade denied action tracking.
Implements write-once immutable logging for forensic reconstruction.
"""

import uuid
import time
import json
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum
import logging

from app.core.database import timescale_pool
from app.core.config import settings

logger = logging.getLogger(__name__)

# ============================================
# Enums
# ============================================

class ActionType(str, Enum):
    """Types of auditable actions"""
    QUERY = "query"
    COLLECTION = "collection"
    HYPOTHESIS_TEST = "hypothesis_test"
    EXPORT = "export"
    DENIED_ACTION = "denied_action"
    DATA_ACCESS = "data_access"
    ENTITY_UPDATE = "entity_update"

# ============================================
# Data Models
# ============================================

@dataclass
class AuditLogEntry:
    """Audit log entry structure"""
    log_id: str = None
    timestamp: int = None
    
    # User context
    user_id: str = None
    user_role: Optional[str] = None
    clearance_level: Optional[str] = None
    
    # Action details
    action_type: str = None
    investigation_id: Optional[str] = None
    target: Optional[str] = None
    
    # Request/Response
    request_payload: Optional[Dict[str, Any]] = None
    response_status: Optional[str] = None
    
    # Compliance
    justification: Optional[str] = None
    policy_ids: Optional[list] = None
    
    # Denied actions (GOVERNMENT-GRADE)
    is_denied: bool = False
    denial_reason: Optional[str] = None
    denial_policy_id: Optional[str] = None
    
    # Metadata
    metadata: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if not self.log_id:
            self.log_id = str(uuid.uuid4())
        if not self.timestamp:
            self.timestamp = int(time.time())

# ============================================
# Audit Logger
# ============================================

class AuditLogger:
    """
    Government-grade audit logger with immutable storage.
    Logs all actions including denied operations.
    """
    
    def __init__(self):
        self.enabled = settings.ENABLE_DENIED_ACTION_LOGGING
    
    def log(self, entry: AuditLogEntry) -> str:
        """
        Log an audit entry to immutable storage.
        
        Returns:
            log_id: UUID of the log entry
        """
        if not self.enabled:
            logger.warning("Audit logging is disabled!")
            return entry.log_id
        
        try:
            with timescale_pool.connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO audit_log (
                            log_id, timestamp, user_id, user_role, clearance_level,
                            action_type, investigation_id, target,
                            request_payload, response_status,
                            justification, policy_ids,
                            is_denied, denial_reason, denial_policy_id,
                            metadata
                        ) VALUES (
                            %s, to_timestamp(%s), %s, %s, %s,
                            %s, %s, %s,
                            %s, %s,
                            %s, %s,
                            %s, %s, %s,
                            %s
                        )
                    """, (
                        entry.log_id,
                        entry.timestamp,
                        entry.user_id,
                        entry.user_role,
                        entry.clearance_level,
                        entry.action_type,
                        entry.investigation_id,
                        entry.target,
                        json.dumps(entry.request_payload) if entry.request_payload else None,
                        entry.response_status,
                        entry.justification,
                        entry.policy_ids,
                        entry.is_denied,
                        entry.denial_reason,
                        entry.denial_policy_id,
                        json.dumps(entry.metadata) if entry.metadata else None
                    ))
                conn.commit()
            
            if entry.is_denied:
                logger.warning(f"DENIED ACTION logged: {entry.action_type} by {entry.user_id} - Reason: {entry.denial_reason}")
            else:
                logger.info(f"Audit logged: {entry.action_type} by {entry.user_id}")
            
            return entry.log_id
            
        except Exception as e:
            logger.error(f"Failed to write audit log: {e}", exc_info=True)
            # CRITICAL: Audit logging failure must not fail silently
            raise
    
    def log_query(
        self,
        user_id: str,
        investigation_id: str,
        query_text: str,
        justification: str,
        user_role: str = None,
        clearance_level: str = None,
        response_status: str = "success"
    ) -> str:
        """Log a query action"""
        entry = AuditLogEntry(
            user_id=user_id,
            user_role=user_role,
            clearance_level=clearance_level,
            action_type=ActionType.QUERY,
            investigation_id=investigation_id,
            target=query_text,
            request_payload={"query": query_text},
            response_status=response_status,
            justification=justification
        )
        return self.log(entry)
    
    def log_collection(
        self,
        user_id: str,
        investigation_id: str,
        target_url: str,
        agent_type: str,
        justification: str,
        user_role: str = None,
        clearance_level: str = None,
        response_status: str = "success",
        items_collected: int = 0
    ) -> str:
        """Log a collection action"""
        entry = AuditLogEntry(
            user_id=user_id,
            user_role=user_role,
            clearance_level=clearance_level,
            action_type=ActionType.COLLECTION,
            investigation_id=investigation_id,
            target=target_url,
            request_payload={
                "agent_type": agent_type,
                "target_url": target_url
            },
            response_status=response_status,
            justification=justification,
            metadata={"items_collected": items_collected}
        )
        return self.log(entry)
    
    def log_denied_action(
        self,
        user_id: str,
        action_type: str,
        target: str,
        denial_reason: str,
        denial_policy_id: str,
        user_role: str = None,
        clearance_level: str = None,
        investigation_id: str = None,
        justification_provided: str = None
    ) -> str:
        """
        Log a DENIED action (GOVERNMENT-GRADE requirement).
        
        Every blocked scrape, rejected query, or policy-enforced denial
        must be logged with reason, policy ID, and user context.
        """
        entry = AuditLogEntry(
            user_id=user_id,
            user_role=user_role,
            clearance_level=clearance_level,
            action_type=ActionType.DENIED_ACTION,
            investigation_id=investigation_id,
            target=target,
            justification=justification_provided,
            is_denied=True,
            denial_reason=denial_reason,
            denial_policy_id=denial_policy_id,
            response_status="denied"
        )
        return self.log(entry)
    
    def query_logs(
        self,
        user_id: Optional[str] = None,
        investigation_id: Optional[str] = None,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
        action_type: Optional[str] = None,
        only_denied: bool = False,
        limit: int = 100
    ) -> list:
        """
        Query audit logs with filters.
        Used for forensic reconstruction.
        """
        conditions = []
        params = []
        
        if user_id:
            conditions.append("user_id = %s")
            params.append(user_id)
        
        if investigation_id:
            conditions.append("investigation_id = %s")
            params.append(investigation_id)
        
        if start_time:
            conditions.append("timestamp >= to_timestamp(%s)")
            params.append(start_time)
        
        if end_time:
            conditions.append("timestamp <= to_timestamp(%s)")
            params.append(end_time)
        
        if action_type:
            conditions.append("action_type = %s")
            params.append(action_type)
        
        if only_denied:
            conditions.append("is_denied = TRUE")
        
        where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
        
        params.append(limit)
        
        try:
            with timescale_pool.connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(f"""
                        SELECT
                            log_id, extract(epoch from timestamp)::bigint as timestamp,
                            user_id, user_role, clearance_level,
                            action_type, investigation_id, target,
                            request_payload, response_status,
                            justification, policy_ids,
                            is_denied, denial_reason, denial_policy_id,
                            metadata
                        FROM audit_log
                        {where_clause}
                        ORDER BY timestamp DESC
                        LIMIT %s
                    """, params)
                    
                    columns = [desc[0] for desc in cur.description]
                    results = []
                    for row in cur.fetchall():
                        results.append(dict(zip(columns, row)))
                    
                    return results
        
        except Exception as e:
            logger.error(f"Failed to query audit logs: {e}")
            return []
    
    def get_denied_actions_summary(
        self,
        user_id: Optional[str] = None,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Get summary of denied actions (for insider threat detection).
        """
        start_time = int(time.time()) - (days * 24 * 3600)
        
        try:
            with timescale_pool.connection() as conn:
                with conn.cursor() as cur:
                    # Total denials
                    where_user = "AND user_id = %s" if user_id else ""
                    params = [start_time]
                    if user_id:
                        params.append(user_id)
                    
                    cur.execute(f"""
                        SELECT COUNT(*) as total_denials
                        FROM audit_log
                        WHERE is_denied = TRUE
                          AND timestamp >= to_timestamp(%s)
                          {where_user}
                    """, params)
                    total_denials = cur.fetchone()[0]
                    
                    # Denials by policy
                    params = [start_time]
                    if user_id:
                        params.append(user_id)
                    
                    cur.execute(f"""
                        SELECT denial_policy_id, COUNT(*) as count
                        FROM audit_log
                        WHERE is_denied = TRUE
                          AND timestamp >= to_timestamp(%s)
                          {where_user}
                        GROUP BY denial_policy_id
                        ORDER BY count DESC
                    """, params)
                    
                    denials_by_policy = [
                        {"policy_id": row[0], "count": row[1]}
                        for row in cur.fetchall()
                    ]
                    
                    return {
                        "total_denials": total_denials,
                        "denials_by_policy": denials_by_policy,
                        "period_days": days
                    }
        
        except Exception as e:
            logger.error(f"Failed to get denied actions summary: {e}")
            return {"error": str(e)}

# ============================================
# Global Audit Logger Instance
# ============================================

audit_logger = AuditLogger()
