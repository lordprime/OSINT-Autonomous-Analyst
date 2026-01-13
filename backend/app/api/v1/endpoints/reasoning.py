"""
Reasoning & Analysis API
AI-powered hypothesis generation, testing, and explanation
"""

from fastapi import APIRouter, HTTPException, status
from typing import Dict, Any
from datetime import datetime
import uuid

from app.schemas.requests import (
    ReasoningPlanRequest, HypothesisGenerate, HypothesisTest, EntityExplain
)
from app.schemas.responses import (
    ReasoningPlanResponse, HypothesesResponse, HypothesisTestResponse,
    EntityExplanationResponse, LLMModelsResponse
)
from app.schemas.base import Hypothesis, LLMModel, LLMProvider, HypothesisVerdict
from app.core.database import neo4j_driver

# Import LLM engines
from app.agents.reasoning.ollama_engine import get_ollama_engine
from app.agents.reasoning.groq_engine import get_groq_engine

router = APIRouter(tags=["reasoning"])


def get_llm_engine(provider: LLMProvider = None):
    """Get LLM engine based on provider"""
    if not provider:
        provider = LLMProvider.OLLAMA  # Default to free option
    
    if provider == LLMProvider.OLLAMA:
        return get_ollama_engine()
    elif provider == LLMProvider.GROQ:
        return get_groq_engine()
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"LLM provider {provider} not yet implemented. Use 'ollama' or 'groq'"
        )


@router.post("/plan", response_model=ReasoningPlanResponse)
async def generate_investigation_plan(data: ReasoningPlanRequest):
    """
    Generate AI-powered investigation plan
    
    Uses LLM to decompose investigation goal into actionable tasks
    """
    
    engine = get_llm_engine(data.llm_provider)
    
    try:
        result = await engine.plan(
            investigation_goal=data.goal,
            current_context=data.current_context
        )
        
        tasks = result.output.get("tasks", [])
        strategy = result.output.get("strategy_notes", "")
        
        # Store plan in Neo4j
        with neo4j_driver.session() as session:
            session.run(
                """
                MATCH (i:Investigation {id: $inv_id})
                CREATE (p:Plan {
                    id: $plan_id,
                    tasks: $tasks,
                    strategy: $strategy,
                    created_at: datetime($created_at),
                    created_by_llm: $llm
                })
                CREATE (i)-[:HAS_PLAN]->(p)
                """,
                inv_id=data.investigation_id,
                plan_id=str(uuid.uuid4()),
                tasks=str(tasks),  # Store as JSON string
                strategy=strategy,
                created_at=datetime.utcnow().isoformat(),
                llm=str(engine.provider.value)
            )
        
        return ReasoningPlanResponse(
            investigation_id=data.investigation_id,
            tasks=tasks,
            strategy_notes=strategy,
            llm_provider=engine.provider.value
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"LLM planning failed: {str(e)}"
        )


@router.post("/hypotheses", response_model=HypothesesResponse)
async def generate_hypotheses(data: HypothesisGenerate):
    """
    Generate hypotheses from investigation data
    
    Analyzes graph patterns and text to propose testable hypotheses
    """
    
    engine = get_llm_engine(data.llm_provider)
    
    try:
        result = await engine.propose_hypotheses(
            graph_context=data.graph_context,
            text_context=data.text_context
        )
        
        hypotheses_data = result.output.get("hypotheses", [])
        
        hypotheses = []
        with neo4j_driver.session() as session:
            for hyp_data in hypotheses_data:
                hyp_id = str(uuid.uuid4())
                
                # Store in Neo4j
                session.run(
                    """
                    MATCH (i:Investigation {id: $inv_id})
                    CREATE (h:Hypothesis {
                        id: $hyp_id,
                        text: $text,
                        confidence: $confidence,
                        created_at: datetime($created_at),
                        created_by_llm: $llm,
                        reasoning: $reasoning
                    })
                    CREATE (i)-[:HAS_HYPOTHESIS]->(h)
                    """,
                    inv_id=data.investigation_id,
                    hyp_id=hyp_id,
                    text=hyp_data.get("text", ""),
                    confidence=hyp_data.get("confidence", 0.5),
                    created_at=datetime.utcnow().isoformat(),
                    llm=engine.provider.value,
                    reasoning=hyp_data.get("rationale", "")
                )
                
                hypotheses.append(Hypothesis(
                    id=hyp_id,
                    investigation_id=data.investigation_id,
                    text=hyp_data.get("text", ""),
                    confidence=hyp_data.get("confidence", 0.5),
                    verdict=None,
                    supporting_evidence=hyp_data.get("evidence_supporting", []),
                    contradicting_evidence=[],
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                    created_by_llm=engine.provider.value,
                    reasoning=hyp_data.get("rationale", "")
                ))
        
        return HypothesesResponse(
            hypotheses=hypotheses,
            investigation_id=data.investigation_id,
            llm_provider=engine.provider.value
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Hypothesis generation failed: {str(e)}"
        )


@router.post("/test", response_model=HypothesisTestResponse)
async def test_hypothesis(data: HypothesisTest):
    """
    Test hypothesis using Bayesian reasoning
    
    Evaluates supporting/contradicting evidence to update hypothesis confidence
    """
    
    engine = get_llm_engine(data.llm_provider)
    
    # Get hypothesis from database
    with neo4j_driver.session() as session:
        result = session.run(
            "MATCH (h:Hypothesis {id: $id}) RETURN h",
            id=data.hypothesis_id
        )
        record = result.single()
        
        if not record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Hypothesis {data.hypothesis_id} not found"
            )
        
        hyp_node = record["h"]
        hypothesis_text = hyp_node["text"]
    
    try:
        # Create Evidence objects (simplified - in production would fetch from DB)
        from app.agents.reasoning.engine import Evidence
        
        supporting = [
            Evidence(evidence_id=eid, content=f"Supporting evidence {i}", 
                    confidence=0.7, source_type="collection")
            for i, eid in enumerate(data.supporting_evidence_ids)
        ]
        
        contradicting = [
            Evidence(evidence_id=eid, content=f"Contradicting evidence {i}",
                    confidence=0.6, source_type="collection")
            for i, eid in enumerate(data.contradicting_evidence_ids)
        ]
        
        result = await engine.test_hypothesis(
            hypothesis_text=hypothesis_text,
            supporting_evidence=supporting,
            contradicting_evidence=contradicting
        )
        
        verdict_str = result.output.get("verdict", "inconclusive")
        verdict = HypothesisVerdict(verdict_str) if verdict_str in ["supported", "refuted", "inconclusive"] else HypothesisVerdict.INCONCLUSIVE
        confidence = result.output.get("posterior", 0.5)
        reasoning = result.output.get("reasoning", "")
        
        # Update hypothesis in database
        with neo4j_driver.session() as session:
            session.run(
                """
                MATCH (h:Hypothesis {id: $id})
                SET h.verdict = $verdict,
                    h.confidence = $confidence,
                    h.reasoning = $reasoning,
                    h.updated_at = datetime($updated_at)
                """,
                id=data.hypothesis_id,
                verdict=verdict.value,
                confidence=confidence,
                reasoning=reasoning,
                updated_at=datetime.utcnow().isoformat()
            )
        
        hypothesis = Hypothesis(
            id=data.hypothesis_id,
            investigation_id="unknown",  # Fetch if needed
            text=hypothesis_text,
            confidence=confidence,
            verdict=verdict,
            supporting_evidence=data.supporting_evidence_ids,
            contradicting_evidence=data.contradicting_evidence_ids,
            created_at=hyp_node["created_at"].to_native(),
            updated_at=datetime.utcnow(),
            created_by_llm=hyp_node["created_by_llm"],
            reasoning=reasoning
        )
        
        return HypothesisTestResponse(
            hypothesis=hypothesis,
            verdict=verdict.value,
            confidence=confidence,
            reasoning=reasoning
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Hypothesis testing failed: {str(e)}"
        )


@router.post("/explain", response_model=EntityExplanationResponse)
async def explain_entity(data: EntityExplain):
    """
    Generate AI explanation for entity relationships and patterns
    """
    
    engine = get_llm_engine(data.llm_provider)
    
    # Get entity context from graph
    with neo4j_driver.session() as session:
        result = session.run(
            """
            MATCH (e:Entity {id: $id})
            OPTIONAL MATCH (e)-[r]-(connected:Entity)
            RETURN e, collect({rel: type(r), entity: connected.name}) as connections
            """,
            id=data.entity_id
        )
        record = result.single()
        
        if not record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Entity {data.entity_id} not found"
            )
        
        entity = record["e"]
        connections = record["connections"]
        
        graph_context = {
            "entity": dict(entity.items()),
            "connections": connections
        }
    
    try:
        result = await engine.explain(
            entity_id=data.entity_id,
            question=data.question,
            graph_context=graph_context
        )
        
        return EntityExplanationResponse(
            entity_id=data.entity_id,
            explanation=result.output.get("explanation", ""),
            evidence_timeline=result.output.get("evidence_timeline", []),
            confidence=result.output.get("confidence", 0.5),
            caveats=result.output.get("caveats", [])
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Explanation generation failed: {str(e)}"
        )


@router.get("/models", response_model=LLMModelsResponse)
async def get_available_models():
    """List available LLM models and their status"""
    
    models = []
    
    # Check Ollama
    try:
        ollama = get_ollama_engine()
        health = await ollama.health_check()
        models.append(LLMModel(
            provider=LLMProvider.OLLAMA,
            model_name="llama3:8b",
            available=health.get("status") == "healthy",
            description="Local LLM (free, no API key)"
        ))
    except:
        models.append(LLMModel(
            provider=LLMProvider.OLLAMA,
            model_name="llama3:8b",
            available=False,
            description="Ollama not running"
        ))
    
    # Check Groq
    try:
        groq = get_groq_engine()
        health = await groq.health_check()
        models.append(LLMModel(
            provider=LLMProvider.GROQ,
            model_name="llama-3.1-70b-versatile",
            available=health.get("status") == "healthy",
            description="Fast cloud LLM (free tier)"
        ))
    except:
        models.append(LLMModel(
            provider=LLMProvider.GROQ,
            model_name="llama-3.1-70b-versatile",
            available=False,
            description="Groq API key not configured"
        ))
    
    return LLMModelsResponse(
        models=models,
        default_provider="ollama"
    )
