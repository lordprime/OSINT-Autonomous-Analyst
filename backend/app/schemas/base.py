"""
Input Sanitization Schemas
Defines base models and types for securely handling user input.
"""

from pydantic import BaseModel, constr, Field, field_validator
import re
from typing import ClassVar

class SafeModel(BaseModel):
    """
    Base model that forbids extra fields and provides common sanitization validators.
    """
    
    # Strict config to reject unknown fields (often used in mass assignment attacks)
    class Config:
        extra = "forbid"
        str_strip_whitespace = True
    
    @field_validator('*', mode='before')
    @classmethod
    def check_for_injection_chars(cls, v):
        """
        Global validator to check for potentially dangerous characters in strings.
        This is a broad check; specific fields should use constr() for tighter control.
        """
        if isinstance(v, str):
            # Block Null bytes, commonly used in C-based exploits
            if '\x00' in v:
                raise ValueError("Input contains null bytes")
        return v

# ============================================
# Reusable Safe Types
# ============================================

# SafeString: Rejects common SQL/Command injection characters
# Allow alphanumeric, spaces, simple punctuation.
# Block: ; (chaining), ` (execution), $ (variables), < > (HTML/XML)
SafeString = constr(
    pattern=r"^[a-zA-Z0-9\s\-_.,!?@#%&*()]+$",
    min_length=1,
    max_length=1000
)

# SearchQuery: Slightly more permissive but limits length
SearchQuery = constr(
    min_length=3,
    max_length=200
)

# Example Usage
class JobRequest(SafeModel):
    """Example schema demonstrating sanitized input"""
    job_id: str
    target: SafeString  # Enforces regex
    depth: int = Field(gt=0, le=5)
