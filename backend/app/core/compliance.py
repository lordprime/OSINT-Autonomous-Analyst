"""
Compliance Engine - Jurisdiction-aware policy enforcement for OSINT collection.
"""

from typing import List, Dict, Any, Optional
from enum import Enum
import logging
import re

from app.core.config import settings

logger = logging.getLogger(__name__)

# ============================================
# Enums
# ============================================

class Jurisdiction(str, Enum):
    US = "US"
    EU = "EU"
    UK = "UK"
    CN = "CN"
    RU = "RU"
    UNKNOWN = "UNKNOWN"

class SensitivityLevel(str, Enum):
    PUBLIC = "public"
    PII = "pii"
    SENSITIVE_PII = "sensitive_pii"
    CLASSIFIED = "classified"

# ============================================
# Compliance Policy Rules
# ============================================

class ComplianceRule:
    def __init__(
        self,
        id: str,
        description: str,
        jurisdictions: List[Jurisdiction],
        prohibited_patterns: List[str],
        denial_message: str
    ):
        self.id = id
        self.description = description
        self.jurisdictions = jurisdictions
        self.prohibited_patterns = prohibited_patterns
        self.denial_message = denial_message

# ============================================
# Compliance Engine
# ============================================

class ComplianceEngine:
    """
    Enforces compliance policies for data collection and retention.
    
    Features:
    - GDPR/CCPA compliance checks
    - PII pattern detection
    - Jurisdiction-based blocking
    - Automated denial logging interface
    """
    
    def __init__(self):
        self.rules = []
        self._initialize_rules()
        
    def _initialize_rules(self):
        """Initialize compliance rules"""
        
        # GDPR Rule: No scraping of EU citizen special category data without explicit justification
        self.rules.append(ComplianceRule(
            id="POLICY_GDPR_001",
            description="GDPR Special Category Data Protection",
            jurisdictions=[Jurisdiction.EU],
            prohibited_patterns=[
                r"(?i)medical record",
                r"(?i)political affiliation",
                r"(?i)biometric data"
            ],
            denial_message="Collection of special category data in EU jurisdiction requires specific warrant/authorization."
        ))
        
        # PII Protection: Block bulk SSN collection
        self.rules.append(ComplianceRule(
            id="POLICY_PII_SSN",
            description="Social Security Number Protection",
            jurisdictions=[Jurisdiction.US],
            prohibited_patterns=[
                r"\b\d{3}-\d{2}-\d{4}\b"
            ],
            denial_message="Collection of US Social Security Numbers is strictly prohibited."
        ))
        
        logger.info(f"Initialized {len(self.rules)} compliance rules")

    def check_collection(
        self,
        target: str,
        jurisdiction: str = "UNKNOWN",
        user_role: str = "analyst"
    ) -> tuple[bool, Optional[str], Optional[str]]:
        """
        Check if collection target violates policies.
        
        Args:
            target: The URL or query string target
            jurisdiction: The target jurisdiction
            user_role: The role of the user
        
        Returns:
            (allowed, denial_reason, policy_id)
        """
        # Override for admin/audit roles if needed
        if user_role == "auditor":
            return True, None, None
            
        current_jurisdiction = Jurisdiction(jurisdiction) if jurisdiction in Jurisdiction.__members__ else Jurisdiction.UNKNOWN
        
        for rule in self.rules:
            # Check if rule applies to jurisdiction
            if current_jurisdiction in rule.jurisdictions or Jurisdiction.UNKNOWN in rule.jurisdictions:
                
                # Check for prohibited patterns
                for pattern in rule.prohibited_patterns:
                    if re.search(pattern, target):
                        logger.warning(f"Compliance violation: {rule.id} triggered by '{target}'")
                        return False, rule.denial_message, rule.id
                        
        return True, None, None

    def redact_pii(self, text: str) -> str:
        """
        Redact common PII from text logs/storage.
        """
        # Redact SSNs
        text = re.sub(r"\b\d{3}-\d{2}-\d{4}\b", "[REDACTED-SSN]", text)
        
        # Redact Credit Cards (simple check)
        text = re.sub(r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b", "[REDACTED-CC]", text)
        
        return text

# ============================================
# Global Instance
# ============================================

compliance_engine = ComplianceEngine()
