"""
Ollama Local LLM Reasoning Engine - Free, local LLM inference.
No API key required - runs on your own hardware.
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


class OllamaReasoningEngine(ReasoningEngine):
    """
    Ollama-based reasoning engine using local LLMs.
    
    Supports models like:
    - llama3:8b (recommended)
    - llama3:70b (better quality, requires more RAM)
    - mistral:7b
    - mixtral:8x7b
    - codellama:13b
    
    Requires Ollama installed: https://ollama.ai
    """
    
    def __init__(self, model: str = None):
        self.provider = LLMProvider.LLAMA
        self.model = model or getattr(settings, 'OLLAMA_MODEL', 'llama3:8b')
        self.host = getattr(settings, 'OLLAMA_HOST', 'http://localhost:11434')
        self._client = None
    
    def _get_client(self):
        """Lazy initialization of Ollama client"""
        if self._client is None:
            try:
                import ollama
                self._client = ollama.Client(host=self.host)
            except ImportError:
                raise ImportError(
                    "ollama package not installed. "
                    "Run: pip install ollama"
                )
        return self._client
    
    async def _generate(self, prompt: str, system: str = None) -> str:
        """Generate text using Ollama"""
        client = self._get_client()
        
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        
        # Run sync ollama in executor
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: client.chat(model=self.model, messages=messages)
        )
        
        return response['message']['content']
    
    async def _generate_json(self, prompt: str, system: str = None) -> Dict[str, Any]:
        """Generate JSON output using Ollama"""
        json_system = (system or "") + "\n\nYou MUST respond with valid JSON only. No explanations or markdown."
        
        response = await self._generate(prompt, json_system)
        
        # Try to extract JSON from response
        try:
            # Handle markdown code blocks
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                response = response.split("```")[1].split("```")[0]
            
            return json.loads(response.strip())
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON from Ollama: {e}")
            return {"raw_response": response, "parse_error": str(e)}
    
    async def plan(
        self,
        investigation_goal: str,
        current_context: Dict[str, Any]
    ) -> ReasoningResult:
        """Decompose investigation goal into tasks"""
        
        system_prompt = """You are an OSINT investigation planner. 
        Decompose the investigation goal into specific, executable tasks.
        Each task should specify which collection agent to use."""
        
        prompt = f"""
        Investigation Goal: {investigation_goal}
        
        Current Context: {json.dumps(current_context, indent=2)}
        
        Create a plan with specific tasks. Return JSON:
        {{
            "tasks": [
                {{
                    "task_id": "unique_id",
                    "description": "what to do",
                    "agent_type": "twitter|reddit|duckduckgo|telegram|instagram|linkedin|facebook",
                    "query": "specific search query",
                    "priority": 1-5,
                    "estimated_duration_seconds": 30
                }}
            ]
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
                base_score=0.7,
                adjustments=[("local_model", -0.1)],
                final_score=0.6,
                explanation="Lower confidence due to local model capabilities"
            ),
            reasoning_trace=f"Used {self.model} to generate investigation plan",
            provider=self.provider,
            timestamp=started
        )
    
    async def propose_hypotheses(
        self,
        graph_context: Dict[str, Any],
        text_context: str
    ) -> ReasoningResult:
        """Generate hypotheses from data patterns"""
        
        system_prompt = """You are an intelligence analyst. 
        Generate testable hypotheses based on the evidence provided.
        Each hypothesis should be specific and falsifiable."""
        
        prompt = f"""
        Graph Context: {json.dumps(graph_context, indent=2)}
        
        Text Context: {text_context}
        
        Generate 3-5 hypotheses. Return JSON:
        {{
            "hypotheses": [
                {{
                    "id": "H1",
                    "text": "hypothesis statement",
                    "confidence": 0.0-1.0,
                    "evidence_supporting": ["evidence 1", "evidence 2"],
                    "evidence_that_would_refute": ["what would disprove this"]
                }}
            ]
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
                base_score=0.65,
                adjustments=[("local_model", -0.1)],
                final_score=0.55,
                explanation="Hypotheses from local model analysis"
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
        """Test hypothesis using evidence"""
        
        system_prompt = """You are a critical analyst. 
        Evaluate the hypothesis based on supporting and contradicting evidence.
        Use Bayesian reasoning to update confidence."""
        
        supporting = [{"content": e.content, "confidence": e.confidence} for e in supporting_evidence]
        contradicting = [{"content": e.content, "confidence": e.confidence} for e in contradicting_evidence]
        
        prompt = f"""
        Hypothesis: {hypothesis_text}
        
        Supporting Evidence: {json.dumps(supporting, indent=2)}
        
        Contradicting Evidence: {json.dumps(contradicting, indent=2)}
        
        Evaluate this hypothesis. Return JSON:
        {{
            "hypothesis_id": "string",
            "prior": 0.5,
            "likelihood_ratio": 1.0-10.0,
            "posterior": 0.0-1.0,
            "verdict": "supported|refuted|inconclusive",
            "reasoning": "explanation",
            "missing_evidence": ["what else would help"]
        }}
        """
        
        started = int(time.time())
        output = await self._generate_json(prompt, system_prompt)
        
        return ReasoningResult(
            operation="test_hypothesis",
            output=output,
            evidence=supporting_evidence + contradicting_evidence,
            confidence=ConfidenceProvenance(
                method="bayesian_update",
                base_score=0.6,
                adjustments=[],
                final_score=0.6,
                explanation="Hypothesis testing via evidence evaluation"
            ),
            reasoning_trace=f"Tested hypothesis with {len(supporting_evidence)} supporting and {len(contradicting_evidence)} contradicting pieces",
            provider=self.provider,
            timestamp=started
        )
    
    async def explain(
        self,
        entity_id: str,
        question: str,
        graph_context: Dict[str, Any]
    ) -> ReasoningResult:
        """Generate explanation for a finding"""
        
        system_prompt = """You are an intelligence briefer.
        Provide clear, evidence-based explanations.
        Always cite specific evidence for claims."""
        
        prompt = f"""
        Entity: {entity_id}
        Question: {question}
        
        Context: {json.dumps(graph_context, indent=2)}
        
        Provide an explanation. Return JSON:
        {{
            "explanation": "narrative explanation",
            "evidence_timeline": [
                {{"date": "YYYY-MM-DD", "event": "what happened", "source": "where from"}}
            ],
            "confidence": 0.0-1.0,
            "caveats": ["limitations or uncertainties"]
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
                base_score=0.65,
                adjustments=[],
                final_score=0.65,
                explanation="Explanation generated from available context"
            ),
            reasoning_trace=f"Generated explanation for {entity_id}",
            provider=self.provider,
            timestamp=started
        )
    
    async def health_check(self) -> Dict[str, Any]:
        """Check if Ollama is running and model is available"""
        try:
            client = self._get_client()
            models = client.list()
            model_names = [m['name'] for m in models.get('models', [])]
            
            return {
                "status": "healthy",
                "host": self.host,
                "available_models": model_names,
                "selected_model": self.model,
                "model_available": self.model in model_names
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "host": self.host
            }


# Factory function
def get_ollama_engine(model: str = None) -> OllamaReasoningEngine:
    """Get an Ollama reasoning engine instance"""
    return OllamaReasoningEngine(model=model)
