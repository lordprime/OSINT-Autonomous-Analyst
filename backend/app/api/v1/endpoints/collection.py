"""
Collection Management API
Trigger and manage OSINT data collection from various sources
"""

from fastapi import APIRouter, HTTPException, status, BackgroundTasks
from typing import List, Dict, Any
from datetime import datetime
import uuid
import asyncio

from app.schemas.requests import CollectionStart, CollectionCancel
from app.schemas.responses import CollectionJobResponse, CollectionSourcesResponse, SuccessResponse
from app.schemas.base import CollectionJob, CollectionStatus
from app.core.database import timescale_pool, neo4j_driver

# Import agent registry
from app.agents.collection.registry import get_agent, list_agents

router = APIRouter(tags=["collection"])


async def execute_collection_job(job_id: str, investigation_id: str, agent_type: str, query: str, **kwargs):
    """Background task to execute collection"""
    
    # Update job status to running
    with timescale_pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE collection_jobs SET status = %s, started_at = %s WHERE id = %s",
                (CollectionStatus.RUNNING.value, datetime.utcnow(), job_id)
            )
            conn.commit()
    
    try:
        # Get agent from registry
        agent = get_agent(agent_type)
        
        # Execute collection
        result = await agent.collect(
            investigation_id=investigation_id,
            query=query,
            user_id="system",
            justification=f"Auto-collection for investigation {investigation_id}",
            **kwargs
        )
        
        # Store entities in Neo4j
        with neo4j_driver.session() as session:
            for item in result.items if hasattr(result, 'items') else []:
                # Create entity node
                entity_id = str(uuid.uuid4())
                session.run(
                    """
                    MATCH (i:Investigation {id: $inv_id})
                    CREATE (e:Entity {
                        id: $entity_id,
                        name: $name,
                        type: $type,
                        confidence: $confidence,
                        source: $source,
                        created_at: datetime($created_at)
                    })
                    CREATE (i)-[:HAS_ENTITY]->(e)
                    """,
                    inv_id=investigation_id,
                    entity_id=entity_id,
                    name=item.content[:200] if hasattr(item, 'content') else str(item),
                    type="unknown",
                    confidence=item.confidence if hasattr(item, 'confidence') else 0.5,
                    source=agent_type,
                    created_at=datetime.utcnow().isoformat()
                )
        
        # Update job as completed
        with timescale_pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE collection_jobs 
                    SET status = %s, completed_at = %s, 
                        items_collected = %s, entities_discovered = %s
                    WHERE id = %s
                    """,
                    (CollectionStatus.COMPLETED.value, datetime.utcnow(),
                     result.items_collected if hasattr(result, 'items_collected') else 0,
                     result.entities_discovered if hasattr(result, 'entities_discovered') else 0,
                     job_id)
                )
                conn.commit()
    
    except Exception as e:
        # Update job as failed
        with timescale_pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE collection_jobs 
                    SET status = %s, completed_at = %s, errors = %s
                    WHERE id = %s
                    """,
                    (CollectionStatus.FAILED.value, datetime.utcnow(),
                     [str(e)], job_id)
                )
                conn.commit()


@router.post("/start", response_model=CollectionJobResponse, status_code=status.HTTP_202_ACCEPTED)
async def start_collection(
    data: CollectionStart,
    background_tasks: BackgroundTasks
):
    """
    Start a collection job
    
    Triggers background data collection from specified agent.
    Job runs asynchronously and updates status in database.
    """
    job_id = str(uuid.uuid4())
    created_at = datetime.utcnow()
    
    # Create job record
    with timescale_pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO collection_jobs
                (id, investigation_id, agent_type, query, status, created_at, metadata)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (job_id, data.investigation_id, data.agent_type, data.query,
                 CollectionStatus.PENDING.value, created_at, data.metadata)
            )
            conn.commit()
    
    # Create job relationship in Neo4j
    with neo4j_driver.session() as session:
        session.run(
            """
            MATCH (i:Investigation {id: $inv_id})
            CREATE (j:CollectionJob {
                id: $job_id,
                agent_type: $agent_type,
                query: $query,
                status: $status,
                created_at: datetime($created_at)
            })
            CREATE (i)-[:HAS_JOB]->(j)
            """,
            inv_id=data.investigation_id,
            job_id=job_id,
            agent_type=data.agent_type,
            query=data.query,
            status=CollectionStatus.PENDING.value,
            created_at=created_at.isoformat()
        )
    
    # Start background task
    background_tasks.add_task(
        execute_collection_job,
        job_id=job_id,
        investigation_id=data.investigation_id,
        agent_type=data.agent_type,
        query=data.query,
        collection_type=data.collection_type,
        max_results=data.max_results
    )
    
    job = CollectionJob(
        id=job_id,
        investigation_id=data.investigation_id,
        agent_type=data.agent_type,
        query=data.query,
        status=CollectionStatus.PENDING,
        started_at=created_at,
        items_collected=0,
        entities_discovered=0,
        metadata=data.metadata
    )
    
    return CollectionJobResponse(
        job=job,
        progress_percent=0.0
    )


@router.get("/jobs", response_model=List[CollectionJobResponse])
async def list_collection_jobs(
    investigation_id: str = None,
    status: CollectionStatus = None,
    limit: int = 50
):
    """List collection jobs with optional filters"""
    
    with timescale_pool.connection() as conn:
        with conn.cursor() as cur:
            query = "SELECT * FROM collection_jobs WHERE 1=1"
            params = []
            
            if investigation_id:
                query += " AND investigation_id = %s"
                params.append(investigation_id)
            
            if status:
                query += " AND status = %s"
                params.append(status.value)
            
            query += " ORDER BY created_at DESC LIMIT %s"
            params.append(limit)
            
            cur.execute(query, params)
            
            jobs = []
            for row in cur.fetchall():
                job = CollectionJob(
                    id=row[0],
                    investigation_id=row[1],
                    agent_type=row[2],
                    query=row[3],
                    status=CollectionStatus(row[4]),
                    started_at=row[5],
                    completed_at=row[6],
                    items_collected=row[7] or 0,
                    entities_discovered=row[8] or 0,
                    errors=row[9] or [],
                    metadata=row[10] or {}
                )
                
                # Calculate progress
                progress = 100.0 if job.status == CollectionStatus.COMPLETED else (
                    0.0 if job.status == CollectionStatus.PENDING else 50.0
                )
                
                jobs.append(CollectionJobResponse(
                    job=job,
                    progress_percent=progress
                ))
    
    return jobs


@router.get("/jobs/{job_id}", response_model=CollectionJobResponse)
async def get_collection_job(job_id: str):
    """Get collection job status"""
    
    with timescale_pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM collection_jobs WHERE id = %s",
                (job_id,)
            )
            row = cur.fetchone()
            
            if not row:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Collection job {job_id} not found"
                )
            
            job = CollectionJob(
                id=row[0],
                investigation_id=row[1],
                agent_type=row[2],
                query=row[3],
                status=CollectionStatus(row[4]),
                started_at=row[5],
                completed_at=row[6],
                items_collected=row[7] or 0,
                entities_discovered=row[8] or 0,
                errors=row[9] or [],
                metadata=row[10] or {}
            )
            
            progress = 100.0 if job.status == CollectionStatus.COMPLETED else (
                0.0 if job.status == CollectionStatus.PENDING else 50.0
            )
            
            return CollectionJobResponse(
                job=job,
                progress_percent=progress
            )


@router.post("/jobs/{job_id}/cancel", response_model=SuccessResponse)
async def cancel_collection_job(
    job_id: str,
    data: CollectionCancel
):
    """Cancel a running collection job"""
    
    with timescale_pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE collection_jobs 
                SET status = %s, completed_at = %s
                WHERE id = %s AND status IN (%s, %s)
                RETURNING id
                """,
                (CollectionStatus.CANCELLED.value, datetime.utcnow(), job_id,
                 CollectionStatus.PENDING.value, CollectionStatus.RUNNING.value)
            )
            
            if not cur.fetchone():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Job cannot be cancelled (not found or already completed)"
                )
            
            conn.commit()
    
    return SuccessResponse(
        message=f"Collection job {job_id} cancelled"
    )


@router.get("/sources", response_model=CollectionSourcesResponse)
async def get_collection_sources():
    """List available collection sources"""
    
    sources = [
        {
            "id": "duckduckgo",
            "name": "DuckDuckGo Search",
            "description": "Web search engine (no API key required)",
            "requires_api_key": False,
            "collection_types": ["text", "news"]
        },
        {
            "id": "telegram",
            "name": "Telegram",
            "description": "Public Telegram channels",
            "requires_api_key": True,
            "collection_types": ["messages", "channel_info"]
        },
        {
            "id": "instagram",
            "name": "Instagram",
            "description": "Public Instagram profiles",
            "requires_api_key": False,
            "collection_types": ["profile", "posts", "hashtags"]
        },
        {
            "id": "linkedin",
            "name": "LinkedIn",
            "description": "Public company pages and job postings",
            "requires_api_key": False,
            "collection_types": ["company", "profile", "jobs"]
        },
        {
            "id": "facebook",
            "name": "Facebook",
            "description": "Public Facebook pages",
            "requires_api_key": False,
            "collection_types": ["page", "posts", "events"]
        }
    ]
    
    return CollectionSourcesResponse(sources=sources)
