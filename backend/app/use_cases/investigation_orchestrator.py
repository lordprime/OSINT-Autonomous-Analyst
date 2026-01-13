"""
Investigation Orchestrator
High-level coordination of investigation workflows
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import uuid
import asyncio

from app.schemas.base import Investigation, InvestigationStatus
from app.core.database import neo4j_driver, timescale_pool


class InvestigationOrchestrator:
    """
    Orchestrates the complete investigation lifecycle:
    1. Planning (LLM generates collection plan)
    2. Collection (triggers agents)
    3. Analysis (builds graph, generates hypotheses)
    4. Reporting (exports findings)
    """
    
    def __init__(self):
        self.active_investigations: Dict[str, Dict[str, Any]] = {}
    
    async def create_investigation(
        self,
        name: str,
        target: str,
        goal: str,
        user_id: str,
        auto_start: bool = True
    ) -> Investigation:
        """Create investigation and optionally auto-start collection"""
        
        investigation_id = str(uuid.uuid4())
        created_at = datetime.utcnow()
        
        # Store in Neo4j
        with neo4j_driver.session() as session:
            session.run(
                """
                CREATE (i:Investigation {
                    id: $id,
                    name: $name,
                    target: $target,
                    goal: $goal,
                    status: $status,
                    created_by: $created_by,
                    created_at: datetime($created_at),
                    updated_at: datetime($updated_at)
                })
                """,
                id=investigation_id,
                name=name,
                target=target,
                goal=goal,
                status=InvestigationStatus.CREATED.value,
                created_by=user_id,
                created_at=created_at.isoformat(),
                updated_at=created_at.isoformat()
            )
        
        # Store in TimescaleDB
        with timescale_pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO investigations 
                    (id, name, target, goal, status, created_by, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (investigation_id, name, target, goal,
                     InvestigationStatus.CREATED.value, user_id,
                     created_at, created_at)
                )
                conn.commit()
        
        investigation = Investigation(
            id=investigation_id,
            name=name,
            target=target,
            goal=goal,
            status=InvestigationStatus.CREATED,
            created_by=user_id,
            created_at=created_at,
            updated_at=created_at
        )
        
        # Auto-start if requested
        if auto_start:
            asyncio.create_task(self.execute_investigation(investigation_id))
        
        return investigation
    
    async def execute_investigation(self, investigation_id: str):
        """Execute full investigation pipeline"""
        
        try:
            # Update status to planning
            await self._update_status(investigation_id, InvestigationStatus.PLANNING)
            
            # Step 1: Generate collection plan (LLM)
            plan = await self._generate_plan(investigation_id)
            
            # Step 2: Execute collection tasks
            await self._update_status(investigation_id, InvestigationStatus.COLLECTING)
            await self._execute_collections(investigation_id, plan)
            
            # Step 3: Analyze collected data
            await self._update_status(investigation_id, InvestigationStatus.ANALYZING)
            await self._analyze_data(investigation_id)
            
            # Step 4: Mark complete
            await self._update_status(investigation_id, InvestigationStatus.COMPLETED)
            
        except Exception as e:
            await self._update_status(investigation_id, InvestigationStatus.FAILED)
            print(f"Investigation {investigation_id} failed: {e}")
    
    async def _update_status(self, investigation_id: str, status: InvestigationStatus):
        """Update investigation status"""
        
        with neo4j_driver.session() as session:
            session.run(
                """
                MATCH (i:Investigation {id: $id})
                SET i.status = $status, i.updated_at = datetime()
                """,
                id=investigation_id,
                status=status.value
            )
        
        with timescale_pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE investigations SET status = %s, updated_at = %s WHERE id = %s",
                    (status.value, datetime.utcnow(), investigation_id)
                )
                conn.commit()
    
    async def _generate_plan(self, investigation_id: str) -> Dict[str, Any]:
        """Generate collection plan using LLM"""
        
        # Get investigation details
        with neo4j_driver.session() as session:
            result = session.run(
                "MATCH (i:Investigation {id: $id}) RETURN i",
                id=investigation_id
            )
            inv = result.single()["i"]
        
        # Use reasoning engine to generate plan
        from app.agents.reasoning.ollama_engine import get_ollama_engine
        
        engine = get_ollama_engine()
        result = await engine.plan(
            investigation_goal=inv["goal"],
            current_context={"target": inv["target"]}
        )
        
        return result.output
    
    async def _execute_collections(self, investigation_id: str, plan: Dict[str, Any]):
        """Execute collection tasks from plan"""
        
        tasks = plan.get("tasks", [])
        
        # Import here to avoid circular dependency
        from app.api.v1.endpoints.collection import execute_collection_job
        
        # Execute tasks in parallel
        collection_tasks = []
        for task in tasks:
            job_id = str(uuid.uuid4())
            agent_type = task.get("agent_type", "duckduckgo")
            query = task.get("query", "")
            
            # Create job
            with timescale_pool.connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO collection_jobs
                        (id, investigation_id, agent_type, query, status, created_at)
                        VALUES (%s, %s, %s, %s, 'pending', %s)
                        """,
                        (job_id, investigation_id, agent_type, query, datetime.utcnow())
                    )
                    conn.commit()
            
            # Execute
            task_coro = execute_collection_job(
                job_id, investigation_id, agent_type, query
            )
            collection_tasks.append(task_coro)
        
        # Wait for all collections
        await asyncio.gather(*collection_tasks, return_exceptions=True)
    
    async def _analyze_data(self, investigation_id: str):
        """Analyze collected data and generate hypotheses"""
        
        # Get graph context
        with neo4j_driver.session() as session:
            result = session.run(
                """
                MATCH (i:Investigation {id: $id})-[:HAS_ENTITY]->(e:Entity)
                RETURN count(e) as entity_count
                """,
                id=investigation_id
            )
            entity_count = result.single()["entity_count"]
        
        if entity_count > 0:
            # Generate hypotheses using LLM
            from app.agents.reasoning.ollama_engine import get_ollama_engine
            
            engine = get_ollama_engine()
            result = await engine.propose_hypotheses(
                graph_context={"entity_count": entity_count},
                text_context=f"Investigation with {entity_count} discovered entities"
            )
            
            # Store hypotheses
            hypotheses = result.output.get("hypotheses", [])
            for hyp in hypotheses:
                with neo4j_driver.session() as session:
                    session.run(
                        """
                        MATCH (i:Investigation {id: $inv_id})
                        CREATE (h:Hypothesis {
                            id: $hyp_id,
                            text: $text,
                            confidence: $confidence,
                            created_at: datetime()
                        })
                        CREATE (i)-[:HAS_HYPOTHESIS]->(h)
                        """,
                        inv_id=investigation_id,
                        hyp_id=str(uuid.uuid4()),
                        text=hyp.get("text", ""),
                        confidence=hyp.get("confidence", 0.5)
                    )
    
    async def get_investigation_report(self, investigation_id: str) -> Dict[str, Any]:
        """Generate comprehensive investigation report"""
        
        with neo4j_driver.session() as session:
            result = session.run(
                """
                MATCH (i:Investigation {id: $id})
                OPTIONAL MATCH (i)-[:HAS_ENTITY]->(e:Entity)
                OPTIONAL MATCH (i)-[:HAS_HYPOTHESIS]->(h:Hypothesis)
                OPTIONAL MATCH (i)-[:HAS_JOB]->(j:CollectionJob)
                RETURN i, 
                       collect(DISTINCT e) as entities,
                       collect(DISTINCT h) as hypotheses,
                       collect(DISTINCT j) as jobs
                """,
                id=investigation_id
            )
            
            record = result.single()
            inv = record["i"]
            
            return {
                "investigation": dict(inv.items()),
                "entity_count": len(record["entities"]),
                "hypothesis_count": len(record["hypotheses"]),
                "collection_job_count": len(record["jobs"]),
                "entities": [dict(e.items()) for e in record["entities"]],
                "hypotheses": [dict(h.items()) for h in record["hypotheses"]]
            }


# Singleton instance
orchestrator = InvestigationOrchestrator()


# Convenience functions
async def create_and_execute_investigation(
    name: str,
    target: str,
    goal: str,
    user_id: str = "system"
) -> Investigation:
    """Create and auto-execute investigation"""
    return await orchestrator.create_investigation(
        name, target, goal, user_id, auto_start=True
    )


async def get_investigation_summary(investigation_id: str) -> Dict[str, Any]:
    """Get investigation summary report"""
    return await orchestrator.get_investigation_report(investigation_id)
