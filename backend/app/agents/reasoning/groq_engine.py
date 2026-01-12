"""
Groq Reasoning Engine - Fast, free-tier LLM inference.
Requires free API key from https://console.groq.com
"""

from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
import time
import logging
import json
import asyncio

from app.agents.reasoning.engine import (
    ReasoningEngine,
    ReasoningResult,
    Evidence,
    ConfidenceProvenance,
    LLMProvider
)
from app.core.config import settings

logger = logging.getLogger(__name__)


class GroqReasoningEngine(ReasoningEngine):
    """
    Groq-based reasoning engine using their ultra-fast inference.
    
    Features:
    - Free tier available (get API key at groq.com)
    - Very fast inference (100+ tokens/second)
    - Supports Llama 3 70B, Mixtral 8x7B
    
    Models:
    - llama-3.1-70b-versatile (recommended)
    - llama-3.1-8b-instant (faster, less capable)
    - mixtral-8x7b-32768 (good for long context)
    """
    
    def __init__(self, model: str = None):
        self.provider = LLMProvider.LLAMA  # Uses Llama models
        self.model = model or getattr(settings, 'GROQ_MODEL', 'llama-3.1-70b-versatile')
        self._client = None
    
    def _get_client(self):
        """Lazy initialization of Groq client"""
        if self._client is None:
            try:
                from groq import Groq
            except ImportError:
                raise ImportError(
                    "groq package not installed. "
                    "Run: pip install groq"
                )
            
            api_key = getattr(settings, 'GROQ_API_KEY', None)
            if not api_key:
                raise ValueError(
                    "GROQ_API_KEY not set. "
                    "Get a free key at https://console.groq.com"
                )
            
            self._client = Groq(api_key=api_key)
        return self._client
    
    async def _generate(self, prompt: str, system: str = None) -> str:
        """Generate text using Groq"""
        client = self._get_client()
        
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        
        # Groq client is sync, run in executor
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
                max_tokens=4096
            )
        )
        
        return response.choices[0].message.content
    
    async def _generate_json(self, prompt: str, system: str = None) -> Dict[str, Any]:
        """Generate JSON output using Groq"""
        json_system = (system or "") + "\n\nRespond with valid JSON only. No markdown code blocks."
        
        response = await self._generate(prompt, json_system)
        
        try:
            # Handle markdown code blocks
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                response = response.split("```")[1].split("```")[0]
            
            return json.loads(response.strip())
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON from Groq: {e}")
            return {"raw_response": response, "parse_error": str(e)}
    
    async def plan(
        self,
        investigation_goal: str,
        current_context: Dict[str, Any]
    ) -> ReasoningResult:
        """Decompose investigation goal into tasks"""
        
        system_prompt = """You are an expert OSINT investigation planner.
        Create detailed, actionable investigation plans.
        Consider multiple data sources and collection methods."""
        
        prompt = f"""
        Investigation Goal: {investigation_goal}
        
        Current Context: {json.dumps(current_context, indent=2)}
        
        Create a comprehensive investigation plan. Return JSON:
        {{
            "tasks": [
                {{
                    "task_id": "T1",
                    "description": "detailed description",
                    "agent_type": "twitter|reddit|duckduckgo|telegram|instagram|linkedin|facebook",
                    "query": "specific search query or target",
                    "priority": 1,
                    "dependencies": [],
                    "estimated_duration_seconds": 30
                }}
            ],
            "strategy_notes": "overall investigation strategy"
        }}
        """
        
        started = int(time.time())
        output = await self._generate_json(prompt, system_prompt)
        
        return ReasoningResult(
            operation="plan",
            output=output,
            evidence=[],
            confidence=ConfidenceProvenance(
                method="llm_generation",
                base_score=0.8,
                adjustments=[("groq_fast_inference", 0.0)],
                final_score=0.8,
                explanation="High-quality plan from Llama 3 70B"
            ),
            reasoning_trace=f"Generated investigation plan using {self.model}",
            provider=self.provider,
            timestamp=started
        )
    
    async def propose_hypotheses(
        self,
        graph_context: Dict[str, Any],
        text_context: str
    ) -> ReasoningResult:
        """Generate hypotheses from data patterns"""
        
        system_prompt = """You are a senior intelligence analyst.
        Generate well-reasoned, testable hypotheses.
        Consider alternative explanations and potential biases."""
        
        prompt = f"""
        Graph Context (entities and relationships):
        {json.dumps(graph_context, indent=2)}
        
        Text Context:
        {text_context}
        
        Generate investigative hypotheses. Return JSON:
        {{
            "hypotheses": [
                {{
                    "id": "H1",
                    "text": "specific, testable hypothesis",
                    "confidence": 0.0-1.0,
                    "rationale": "why this hypothesis",
                    "evidence_supporting": ["specific evidence"],
                    "evidence_that_would_refute": ["what would disprove this"],
                    "collection_needed": ["what data to collect to test"]
                }}
            ],
            "analytical_notes": "overall patterns observed"
        }}
        """
        
        started = int(time.time())
        output = await self._generate_json(prompt, system_prompt)
        
        return ReasoningResult(
            operation="propose_hypotheses",
            output=output,
            evidence=[],
            confidence=ConfidenceProvenance(
                method="pattern_analysis",
                base_score=0.75,
                adjustments=[],
                final_score=0.75,
                explanation="Hypotheses generated with analytical rigor"
            ),
            reasoning_trace=f"Generated hypotheses using {self.model}",
            provider=self.provider,
            timestamp=started
        )
    
    async def test_hypothesis(
        self,
        hypothesis_text: str,
        supporting_evidence: List[Evidence],
        contradicting_evidence: List[Evidence]
    ) -> ReasoningResult:
        """Test hypothesis using Bayesian reasoning"""
        
        system_prompt = """You are a critical intelligence evaluator.
        Apply rigorous Bayesian reasoning.
        Be explicit about probability updates and reasoning."""
        
        supporting = [
            {"content": e.content, "confidence": e.confidence, "source": e.source_type}
            for e in supporting_evidence
        ]
        contradicting = [
            {"content": e.content, "confidence": e.confidence, "source": e.source_type}
            for e in contradicting_evidence
        ]
        
        prompt = f"""
        Hypothesis to evaluate:
        "{hypothesis_text}"
        
        Supporting Evidence:
        {json.dumps(supporting, indent=2)}
        
        Contradicting Evidence:
        {json.dumps(contradicting, indent=2)}
        
        Perform Bayesian analysis. Return JSON:
        {{
            "hypothesis_id": "string",
            "prior": 0.5,
            "likelihood_ratio": "calculated from evidence strength",
            "posterior": "updated probability",
            "verdict": "supported|refuted|inconclusive",
            "confidence_in_verdict": 0.0-1.0,
            "key_evidence": "most important evidence for conclusion",
            "reasoning": "step-by-step Bayesian reasoning",
            "missing_evidence": ["what would strengthen analysis"],
            "alternative_explanations": ["other ways to interpret evidence"]
        }}
        """
        
        started = int(time.time())
        output = await self._generate_json(prompt, system_prompt)
        
        return ReasoningResult(
            operation="test_hypothesis",
            output=output,
            evidence=supporting_evidence + contradicting_evidence,
            confidence=ConfidenceProvenance(
                method="bayesian_inference",
                base_score=0.8,
                adjustments=[],
                final_score=0.8,
                explanation="Rigorous Bayesian hypothesis testing"
            ),
            reasoning_trace=f"Tested hypothesis with {len(supporting_evidence)} supporting, {len(contradicting_evidence)} contradicting evidence",
            provider=self.provider,
            timestamp=started
        )
    
    async def explain(
        self,
        entity_id: str,
        question: str,
        graph_context: Dict[str, Any]
    ) -> ReasoningResult:
        """Generate detailed explanation"""
        
        system_prompt = """You are an expert intelligence briefer.
        Provide clear, well-structured explanations.
        Always cite evidence and acknowledge uncertainties."""
        
        prompt = f"""
        Entity of Interest: {entity_id}
        
        Question: {question}
        
        Available Context:
        {json.dumps(graph_context, indent=2)}
        
        Provide a comprehensive explanation. Return JSON:
        {{
            "explanation": "detailed narrative explanation",
            "executive_summary": "2-3 sentence summary",
            "evidence_timeline": [
                {{"date": "YYYY-MM-DD", "event": "description", "source": "source", "confidence": 0.0-1.0}}
            ],
            "key_entities": ["important entities mentioned"],
            "confidence": 0.0-1.0,
            "caveats": ["limitations or uncertainties"],
            "recommended_actions": ["what to investigate next"]
        }}
        """
        
        started = int(time.time())
        output = await self._generate_json(prompt, system_prompt)
        
        return ReasoningResult(
            operation="explain",
            output=output,
            evidence=[],
            confidence=ConfidenceProvenance(
                method="narrative_synthesis",
                base_score=0.8,
                adjustments=[],
                final_score=0.8,
                explanation="Comprehensive explanation with evidence"
            ),
            reasoning_trace=f"Generated explanation for {entity_id} using {self.model}",
            provider=self.provider,
            timestamp=started
        )
    
    async def health_check(self) -> Dict[str, Any]:
        """Check Groq API availability"""
        try:
            client = self._get_client()
            # Simple test call
            response = client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "test"}],
                max_tokens=5
            )
            return {
                "status": "healthy",
                "model": self.model,
                "test_response_id": response.id
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "model": self.model
            }


# Factory function
def get_groq_engine(model: str = None) -> GroqReasoningEngine:
    """Get a Groq reasoning engine instance"""
    return GroqReasoningEngine(model=model)
