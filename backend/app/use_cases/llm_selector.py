"""
LLM Selector - Dynamic routing to best available LLM
Selects LLM based on availability, cost, task complexity
"""

from typing import Optional
from enum import Enum

from app.schemas.base import LLMProvider
from app.agents.reasoning.engine import ReasoningEngine


class TaskComplexity(str, Enum):
    """Task complexity levels"""
    SIMPLE = "simple"      # Basic queries, simple reasoning
    MODERATE = "moderate"  # Multi-step reasoning
    COMPLEX = "complex"    # Advanced analysis, hypothesis testing


class LLMSelector:
    """
    Intelligent LLM selection with fallback chain:
    1. Try preferred provider
    2. Fall back to free options (Ollama → Groq)
    3. Fall back to any available
    """
    
    def __init__(self, default_provider: Optional[LLMProvider] = None):
        self.default_provider = default_provider or LLMProvider.OLLAMA
        self._availability_cache: dict[LLMProvider, bool] = {}
    
    async def get_engine(
        self,
        preferred_provider: Optional[LLMProvider] = None,
        task_complexity: TaskComplexity = TaskComplexity.MODERATE
    ) -> ReasoningEngine:
        """
        Get best available LLM engine
        
        Args:
            preferred_provider: User's preferred LLM
            task_complexity: Complexity level (affects model selection)
        
        Returns:
            ReasoningEngine instance
        
        Raises:
            RuntimeError: If no LLM available
        """
        
        # Determine selection order
        providers_to_try = self._get_provider_priority(
            preferred_provider, task_complexity
        )
        
        # Try each provider in order
        for provider in providers_to_try:
            engine = await self._try_provider(provider)
            if engine:
                return engine
        
        # No LLM available
        raise RuntimeError(
            "No LLM available. Please configure at least one: "
            "Ollama (local), Groq (free), Claude, or OpenAI"
        )
    
    def _get_provider_priority(
        self,
        preferred: Optional[LLMProvider],
        complexity: TaskComplexity
    ) -> list[LLMProvider]:
        """Determine provider priority order"""
        
        priority = []
        
        # 1. Preferred provider first
        if preferred:
            priority.append(preferred)
        
        # 2. Default provider
        if self.default_provider != preferred:
            priority.append(self.default_provider)
        
        # 3. Free options (for cost efficiency)
        free_providers = [LLMProvider.OLLAMA, LLMProvider.GROQ]
        for provider in free_providers:
            if provider not in priority:
                priority.append(provider)
        
        # 4. Paid options (if task is complex and free failed)
        if complexity == TaskComplexity.COMPLEX:
            paid_providers = [LLMProvider.CLAUDE, LLMProvider.OPENAI]
            for provider in paid_providers:
                if provider not in priority:
                    priority.append(provider)
        
        return priority
    
    async def _try_provider(
        self,
        provider: LLMProvider
    ) -> Optional[ReasoningEngine]:
        """Try to get engine from provider"""
        
        # Check cache first
        if provider in self._availability_cache:
            if not self._availability_cache[provider]:
                return None
        
        try:
            engine = self._get_engine_instance(provider)
            
            # Health check
            health = await engine.health_check()
            is_healthy = health.get("status") == "healthy"
            
            self._availability_cache[provider] = is_healthy
            
            if is_healthy:
                return engine
            
        except Exception as e:
            self._availability_cache[provider] = False
            print(f"Provider {provider} unavailable: {e}")
        
        return None
    
    def _get_engine_instance(self, provider: LLMProvider) -> ReasoningEngine:
        """Get engine instance for provider"""
        
        if provider == LLMProvider.OLLAMA:
            from app.agents.reasoning.ollama_engine import get_ollama_engine
            return get_ollama_engine()
        
        elif provider == LLMProvider.GROQ:
            from app.agents.reasoning.groq_engine import get_groq_engine
            return get_groq_engine()
        
        elif provider == LLMProvider.CLAUDE:
            # TODO: Import Claude engine when implemented
            raise NotImplementedError("Claude engine not yet implemented")
        
        elif provider == LLMProvider.OPENAI:
            # TODO: Import OpenAI engine when implemented
            raise NotImplementedError("OpenAI engine not yet implemented")
        
        else:
            raise ValueError(f"Unknown provider: {provider}")
    
    async def get_available_providers(self) -> list[dict]:
        """Get list of all available providers with status"""
        
        providers = []
        
        for provider in LLMProvider:
            try:
                engine = self._get_engine_instance(provider)
                health = await engine.health_check()
                
                providers.append({
                    "provider": provider.value,
                    "available": health.get("status") == "healthy",
                    "model": health.get("selected_model", "unknown"),
                    "details": health
                })
            except Exception as e:
                providers.append({
                    "provider": provider.value,
                    "available": False,
                    "error": str(e)
                })
        
        return providers


# Singleton instance
llm_selector = LLMSelector()


# Convenience functions
async def get_best_llm(
    preferred: Optional[str] = None,
    complexity: str = "moderate"
) -> ReasoningEngine:
    """Get best available LLM engine"""
    
    provider = LLMProvider(preferred) if preferred else None
    task_complexity = TaskComplexity(complexity) if complexity else TaskComplexity.MODERATE
    
    return await llm_selector.get_engine(provider, task_complexity)


async def list_available_llms() -> list[dict]:
    """List all available LLM providers"""
    return await llm_selector.get_available_providers()
