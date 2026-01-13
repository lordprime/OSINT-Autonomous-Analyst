"""
Multi-LLM Reasoning Engine - Provider-agnostic interface for autonomous reasoning.
Implements the ReasoningEngine abstraction layer from REASONING_ENGINE_SPEC.md
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass, asdict
from enum import Enum
import time
import logging
import json

from app.core.config import settings

logger = logging.getLogger(__name__)

# ============================================
# Enums
# ============================================

class LLMProvider(str, Enum):
    """Supported LLM providers"""
    CLAUDE = "claude"
    GPT4 = "gpt4"
    LLAMA = "llama"

# ============================================
# Data Models
# ============================================

@dataclass
class Evidence:
    """Evidence contract - All providers must return this structure"""
    source_id: str
    source_type: str  # "document", "assertion", "graph_pattern"
    content: str
    confidence: float  # 0.0-1.0
    timestamp: int
    provenance: str  # How this evidence was obtained

@dataclass
class ConfidenceProvenance:
    """Tracks how confidence was calculated"""
    method: str  # "llm_self_assessment", "evidence_count", "bayesian_update"
    base_score: float
    adjustments: List[Tuple[str, float]]  # (reason, delta)
    final_score: float
    explanation: str

@dataclass
class ReasoningResult:
    """Standard output for all reasoning operations"""
    operation: str
    output: Any
    evidence: List[Evidence]
    confidence: ConfidenceProvenance
    reasoning_trace: str  # Chain-of-thought
    provider: LLMProvider
    timestamp: int

# ============================================
# Base Reasoning Engine
# ============================================

class ReasoningEngine(ABC):
    """
    Abstract base class for all LLM-based reasoning.
    All implementations MUST enforce structured outputs.
    """
    
    @abstractmethod
    async def plan(
        self,
        investigation_goal: str,
        current_context: Dict[str, Any]
    ) -> ReasoningResult:
        """
        Decomposes investigation goal into executable tasks.
        
        Output Structure:
        {
            "tasks": [
                {
                    "task_id": str,
                    "description": str,
                    "agent_type": str,
                    "dependencies": List[str],
                    "estimated_duration_seconds": int
                }
            ]
        }
        """
        pass
    
    @abstractmethod
    async def propose_hypotheses(
        self,
        graph_context: Dict[str, Any],
        text_context: str
    ) -> ReasoningResult:
        """
        Generates testable hypotheses from data patterns.
        
        Output Structure:
        {
            "hypotheses": [
                {
                    "id": str,
                    "text": str,
                    "specificity": float,  # 0.0-1.0
                    "testability": float,  # 0.0-1.0
                    "prior_plausibility": float,  # 0.0-1.0
                    "evidence_required": List[str],
                    "evidence_that_would_refute": List[str]
                }
            ]
        }
        """
        pass
    
    @abstractmethod
    async def test_hypothesis(
        self,
        hypothesis_text: str,
        supporting_evidence: List[Evidence],
        contradicting_evidence: List[Evidence]
    ) -> ReasoningResult:
        """
        Tests hypothesis using Bayesian updating.
        
        Output Structure:
        {
            "hypothesis_id": str,
            "prior": float,
            "likelihood_ratio": float,
            "posterior": float,
            "verdict": "confirmed" | "refuted" | "inconclusive",
            "reasoning": str,
            "missing_evidence": List[str]
        }
        """
        pass
    
    @abstractmethod
    async def explain(
        self,
        entity_id: str,
        question: str,
        graph_context: Dict[str, Any]
    ) -> ReasoningResult:
        """
        Generates narrative explanation for a finding.
        
        Output Structure:
        {
            "explanation": str,
            "evidence_timeline": List[Dict],
            "counterfactuals": List[{
                "remove_evidence_id": str,
                "impact": str
            }],
            "competing_interpretations": List[str]
        }
        """
        pass

# ============================================
# Claude Implementation
# ============================================

class ClaudeReasoningEngine(ReasoningEngine):
    """
    Claude 3.5 Sonnet implementation with structured outputs.
    Hardened against prompt injection via System Prompts.
    """
    
    def __init__(self):
        self.provider = LLMProvider.CLAUDE
        self.model = settings.CLAUDE_MODEL
        self.client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize Anthropic client"""
        if not settings.ANTHROPIC_API_KEY:
            logger.warning("Anthropic API key not configured")
            return
        
        try:
            import anthropic
            self.client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
            logger.info(f"Claude client initialized: {self.model}")
        except Exception as e:
            logger.error(f"Failed to initialize Claude client: {e}")
    
    async def plan(
        self,
        investigation_goal: str,
        current_context: Dict[str, Any]
    ) -> ReasoningResult:
        """Claude planning with structured JSON output"""
        
        if not self.client:
            raise RuntimeError("Claude client not initialized")
        
        system_instruction = """You are an investigative planning agent for OSINT analysis.
Decompose the user's investigation goal into executable collection tasks.

Respond ONLY with valid JSON in this exact structure:
{
  "tasks": [
    {
      "task_id": "task_1",
      "description": "Search company X in SEC EDGAR",
      "agent_type": "surface_web",
      "dependencies": [],
      "estimated_duration_seconds": 120
    }
  ],
  "reasoning": "Explain your planning logic here",
  "confidence": 0.85
}"""

        user_content = f"""Investigation Goal:
{investigation_goal}

Current Context:
{json.dumps(current_context, indent=2)}"""
        
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4000,
                system=system_instruction,
                messages=[{"role": "user", "content": user_content}]
            )
            
            # Parse JSON response
            content = response.content[0].text
            result = json.loads(content)
            
            # Build confidence provenance
            conf_prov = ConfidenceProvenance(
                method="llm_self_assessment",
                base_score=result.get("confidence", 0.7),
                adjustments=[],
                final_score=result.get("confidence", 0.7),
                explanation="Claude self-assessed confidence based on goal clarity"
            )
            
            return ReasoningResult(
                operation="plan",
                output={"tasks": result["tasks"]},
                evidence=[],
                confidence=conf_prov,
                reasoning_trace=result.get("reasoning", ""),
                provider=self.provider,
                timestamp=int(time.time())
            )
        
        except Exception as e:
            logger.error(f"Claude planning failed: {e}")
            raise
    
    async def propose_hypotheses(
        self,
        graph_context: Dict[str, Any],
        text_context: str
    ) -> ReasoningResult:
        """Claude hypothesis generation"""
        
        if not self.client:
            raise RuntimeError("Claude client not initialized")
        
        system_instruction = """You are a hypothesis generator for intelligence analysis.
Generate 3-5 testable, specific hypotheses based on the provided graph patterns and text context.

Respond ONLY with valid JSON:
{
  "hypotheses": [
    {
      "id": "hyp_1",
      "text": "Person A is beneficial owner of Organization B",
      "specificity": 0.8,
      "testability": 0.9,
      "prior_plausibility": 0.6,
      "evidence_required": ["Financial disclosures", "Corporate filings"],
      "evidence_that_would_refute": ["Third-party owner confirmation"]
    }
  ],
  "reasoning": "Explain hypothesis generation logic",
  "confidence": 0.75
}"""

        user_content = f"""Graph patterns detected:
{json.dumps(graph_context, indent=2)}

Text context:
{text_context}"""
        
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4000,
                system=system_instruction,
                messages=[{"role": "user", "content": user_content}]
            )
            
            content = response.content[0].text
            result = json.loads(content)
            
            conf_prov = ConfidenceProvenance(
                method="llm_self_assessment",
                base_score=result.get("confidence", 0.7),
                adjustments=[],
                final_score=result.get("confidence", 0.7),
                explanation="Claude assessed based on pattern strength"
            )
            
            return ReasoningResult(
                operation="propose_hypotheses",
                output={"hypotheses": result["hypotheses"]},
                evidence=[],
                confidence=conf_prov,
                reasoning_trace=result.get("reasoning", ""),
                provider=self.provider,
                timestamp=int(time.time())
            )
        
        except Exception as e:
            logger.error(f"Claude hypothesis generation failed: {e}")
            raise
    
    async def test_hypothesis(
        self,
        hypothesis_text: str,
        supporting_evidence: List[Evidence],
        contradicting_evidence: List[Evidence]
    ) -> ReasoningResult:
        """Bayesian hypothesis testing with Claude"""
        
        if not self.client:
            raise RuntimeError("Claude client not initialized")
        
        # Format evidence
        support_text = "\n".join([
            f"- {e.content} (source: {e.source_type}, confidence: {e.confidence})"
            for e in supporting_evidence
        ])
        contradict_text = "\n".join([
            f"- {e.content} (source: {e.source_type}, confidence: {e.confidence})"
            for e in contradicting_evidence
        ])
        
        system_instruction = """You are testing a hypothesis using Bayesian reasoning.
Provide a Bayesian update based on the evidence.

Respond ONLY with valid JSON:
{
  "prior": 0.5,
  "likelihood_ratio": 2.5,
  "posterior": 0.71,
  "verdict": "confirmed",
  "reasoning": "Explain Bayesian logic",
  "missing_evidence": ["List evidence gaps"],
  "confidence": 0.80
}"""

        user_content = f"""Hypothesis: {hypothesis_text}

Supporting Evidence:
{support_text}

Contradicting Evidence:
{contradict_text}"""
        
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2000,
                system=system_instruction,
                messages=[{"role": "user", "content": user_content}]
            )
            
            content = response.content[0].text
            result = json.loads(content)
            
            # Adjust confidence based on evidence quality
            evidence_quality = sum(e.confidence for e in supporting_evidence + contradicting_evidence) / max(len(supporting_evidence + contradicting_evidence), 1)
            
            conf_prov = ConfidenceProvenance(
                method="bayesian_update",
                base_score=result.get("confidence", 0.7),
                adjustments=[("evidence_quality_adjustment", evidence_quality - 0.5)],
                final_score=min(result.get("confidence", 0.7) * evidence_quality, 1.0),
                explanation=f"Bayesian posterior adjusted by evidence quality ({evidence_quality:.2f})"
            )
            
            return ReasoningResult(
                operation="test_hypothesis",
                output=result,
                evidence=supporting_evidence + contradicting_evidence,
                confidence=conf_prov,
                reasoning_trace=result.get("reasoning", ""),
                provider=self.provider,
                timestamp=int(time.time())
            )
        
        except Exception as e:
            logger.error(f"Claude hypothesis testing failed: {e}")
            raise
    
    async def explain(
        self,
        entity_id: str,
        question: str,
        graph_context: Dict[str, Any]
    ) -> ReasoningResult:
        """Narrative explanation generation"""
        
        if not self.client:
            raise RuntimeError("Claude client not initialized")
        
        system_instruction = """Generate a narrative explanation for a question about an entity.
Provide:
1. Natural language explanation
2. Evidence timeline (chronological)
3. Counterfactuals (what if we remove evidence X?)
4. Competing interpretations

Respond with JSON:
{
  "explanation": "Clear narrative explanation",
  "evidence_timeline": [{"timestamp": 1704067200, "event": "...", "impact": "..."}],
  "counterfactuals": [{"remove_evidence_id": "ev_1", "impact": "Score drops to 0.4"}],
  "competing_interpretations": ["Alternative explanation 1", "Alternative 2"],
  "confidence": 0.85
}"""

        user_content = f"""Question: {question}
Entity ID: {entity_id}

Graph Context:
{json.dumps(graph_context, indent=2)}"""
        
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=3000,
                system=system_instruction,
                messages=[{"role": "user", "content": user_content}]
            )
            
            content = response.content[0].text
            result = json.loads(content)
            
            conf_prov = ConfidenceProvenance(
                method="narrative_construction",
                base_score=result.get("confidence", 0.7),
                adjustments=[],
                final_score=result.get("confidence", 0.7),
                explanation="Narrative confidence based on evidence completeness"
            )
            
            return ReasoningResult(
                operation="explain",
                output=result,
                evidence=[],
                confidence=conf_prov,
                reasoning_trace=result.get("explanation", ""),
                provider=self.provider,
                timestamp=int(time.time())
            )
        
        except Exception as e:
            logger.error(f"Claude explanation failed: {e}")
            raise

# ============================================
# Multi-Provider Router
# ============================================

class MultiProviderReasoningEngine:
    """
    Router that selects optimal provider based on operation type.
    """
    
    def __init__(self):
        self.providers = {}
        self._initialize_providers()
        
        # Default provider selection by operation
        self.operation_preferences = {
            "plan": LLMProvider.CLAUDE,
            "propose_hypotheses": LLMProvider.CLAUDE,
            "test_hypothesis": LLMProvider.CLAUDE,
            "explain": LLMProvider.CLAUDE
        }
    
    def _initialize_providers(self):
        """Initialize available providers"""
        # Claude
        if settings.ANTHROPIC_API_KEY:
            self.providers[LLMProvider.CLAUDE] = ClaudeReasoningEngine()
            logger.info("Claude reasoning engine initialized")
        
        # TODO: Add GPT-4 and Llama implementations
        # if settings.OPENAI_API_KEY:
        #     self.providers[LLMProvider.GPT4] = GPT4ReasoningEngine()
        
        if not self.providers:
            logger.warning("No LLM providers configured!")
    
    async def execute(
        self,
        operation: str,
        preferred_provider: Optional[LLMProvider] = None,
        **kwargs
    ) -> ReasoningResult:
        """
        Execute reasoning operation with provider selection.
        
        Args:
            operation: "plan", "propose_hypotheses", "test_hypothesis", "explain"
            preferred_provider: Override default provider
            **kwargs: Operation-specific arguments
        """
        # Select provider
        provider = preferred_provider or self.operation_preferences.get(operation, LLMProvider.CLAUDE)
        
        if provider not in self.providers:
            raise ValueError(f"Provider not available: {provider}")
        
        engine = self.providers[provider]
        
        # Route to appropriate method
        method = getattr(engine, operation)
        return await method(**kwargs)

# ============================================
# Global Instance
# ============================================

reasoning_engine = MultiProviderReasoningEngine()
