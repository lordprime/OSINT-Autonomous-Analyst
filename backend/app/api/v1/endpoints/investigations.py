"""
Investigation Management API
CRUD operations for investigations
"""

from fastapi import APIRouter, HTTPException, status, Depends
from typing import List
from datetime import datetime
import uuid

from app.schemas.requests import InvestigationCreate, InvestigationUpdate
from app.schemas.responses import (
    InvestigationResponse, InvestigationListResponse,
    InvestigationTimelineResponse, SuccessResponse
)
from app.schemas.base import Investigation, InvestigationStatus
from app.core.database import neo4j_driver, timescale_pool
from app.api.deps import TokenData

router = APIRouter(tags=["investigations"])


@router.post("/create", response_model=InvestigationResponse, status_code=status.HTTP_201_CREATED)
async def create_investigation(
    data: InvestigationCreate,
    current_user: TokenData = Depends(lambda: TokenData(username="demo_user", role="analyst"))
):
    """
    Create a new investigation
    
    - Stores investigation in Neo4j as central node
    - Creates entry in TimescaleDB for timeline tracking
    - Returns investigation with ID
    """
    investigation_id = str(uuid.uuid4())
    created_at = datetime.utcnow()
    
    # Create in Neo4j
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
            name=data.name,
            target=data.target,
            goal=data.goal,
            status=InvestigationStatus.CREATED.value,
            created_by=current_user.username,
            created_at=created_at.isoformat(),
            updated_at=created_at.isoformat()
        )
    
    # Create in TimescaleDB for timeline
    with timescale_pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO investigations 
                (id, name, target, goal, status, created_by, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (investigation_id, data.name, data.target, data.goal, 
                 InvestigationStatus.CREATED.value, current_user.username,
                 created_at, created_at)
            )
            conn.commit()
    
    investigation = Investigation(
        id=investigation_id,
        name=data.name,
        target=data.target,
        goal=data.goal,
        status=InvestigationStatus.CREATED,
        created_by=current_user.username,
        created_at=created_at,
        updated_at=created_at,
        metadata=data.metadata
    )
    
    return InvestigationResponse(
        investigation=investigation,
        entity_count=0,
        collection_job_count=0,
        hypothesis_count=0
    )


@router.get("", response_model=InvestigationListResponse)
async def list_investigations(
    skip: int = 0,
    limit: int = 50,
    current_user: TokenData = Depends(lambda: TokenData(username="demo_user", role="analyst"))
):
    """List all investigations (paginated)"""
    
    with neo4j_driver.session() as session:
        result = session.run(
            """
            MATCH (i:Investigation)
            WHERE i.created_by = $username OR $role = 'admin'
            RETURN i
            ORDER BY i.created_at DESC
            SKIP $skip
            LIMIT $limit
            """,
            username=current_user.username,
            role=current_user.role,
            skip=skip,
            limit=limit
        )
        
        investigations = []
        for record in result:
            node = record["i"]
            investigations.append(Investigation(
                id=node["id"],
                name=node["name"],
                target=node["target"],
                goal=node["goal"],
                status=InvestigationStatus(node["status"]),
                created_by=node["created_by"],
                created_at=node["created_at"].to_native(),
                updated_at=node["updated_at"].to_native(),
                completed_at=node.get("completed_at").to_native() if node.get("completed_at") else None
            ))
        
        # Get total count
        count_result = session.run(
            """
            MATCH (i:Investigation)
            WHERE i.created_by = $username OR $role = 'admin'
            RETURN count(i) as total
            """,
            username=current_user.username,
            role=current_user.role
        )
        total = count_result.single()["total"]
    
    return InvestigationListResponse(
        investigations=investigations,
        total=total
    )


@router.get("/{investigation_id}", response_model=InvestigationResponse)
async def get_investigation(
    investigation_id: str,
    current_user: TokenData = Depends(lambda: TokenData(username="demo_user", role="analyst"))
):
    """Get investigation details with counts"""
    
    with neo4j_driver.session() as session:
        result = session.run(
            """
            MATCH (i:Investigation {id: $id})
            OPTIONAL MATCH (i)-[:HAS_ENTITY]->(e:Entity)
            OPTIONAL MATCH (i)-[:HAS_JOB]->(j:CollectionJob)
            OPTIONAL MATCH (i)-[:HAS_HYPOTHESIS]->(h:Hypothesis)
            RETURN i, 
                   count(DISTINCT e) as entity_count,
                   count(DISTINCT j) as job_count,
                   count(DISTINCT h) as hypothesis_count
            """,
            id=investigation_id
        )
        
        record = result.single()
        if not record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Investigation {investigation_id} not found"
            )
        
        node = record["i"]
        investigation = Investigation(
            id=node["id"],
            name=node["name"],
            target=node["target"],
            goal=node["goal"],
            status=InvestigationStatus(node["status"]),
            created_by=node["created_by"],
            created_at=node["created_at"].to_native(),
            updated_at=node["updated_at"].to_native(),
            completed_at=node.get("completed_at").to_native() if node.get("completed_at") else None
        )
        
        return InvestigationResponse(
            investigation=investigation,
            entity_count=record["entity_count"],
            collection_job_count=record["job_count"],
            hypothesis_count=record["hypothesis_count"]
        )


@router.patch("/{investigation_id}", response_model=InvestigationResponse)
async def update_investigation(
    investigation_id: str,
    data: InvestigationUpdate,
    current_user: TokenData = Depends(lambda: TokenData(username="demo_user", role="analyst"))
):
    """Update investigation details"""
    
    update_fields = {}
    if data.name:
        update_fields["name"] = data.name
    if data.goal:
        update_fields["goal"] = data.goal
    if data.metadata is not None:
        update_fields["metadata"] = data.metadata
    
    if not update_fields:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields to update"
        )
    
    update_fields["updated_at"] = datetime.utcnow().isoformat()
    
    with neo4j_driver.session() as session:
        # Build SET clause dynamically
        set_clauses = [f"i.{key} = ${key}" for key in update_fields.keys()]
        query = f"""
        MATCH (i:Investigation {{id: $id}})
        SET {', '.join(set_clauses)}
        RETURN i
        """
        
        result = session.run(query, id=investigation_id, **update_fields)
        record = result.single()
        
        if not record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Investigation {investigation_id} not found"
            )
    
    # Return updated investigation
    return await get_investigation(investigation_id, current_user)


@router.delete("/{investigation_id}", response_model=SuccessResponse)
async def delete_investigation(
    investigation_id: str,
    current_user: TokenData = Depends(lambda: TokenData(username="demo_user", role="analyst"))
):
    """Delete investigation and all related data"""
    
    with neo4j_driver.session() as session:
        # Delete investigation and all connected nodes
        result = session.run(
            """
            MATCH (i:Investigation {id: $id})
            OPTIONAL MATCH (i)-[r]->(n)
            DELETE r, n, i
            RETURN count(i) as deleted
            """,
            id=investigation_id
        )
        
        deleted = result.single()["deleted"]
        if deleted == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Investigation {investigation_id} not found"
            )
    
    return SuccessResponse(
        message=f"Investigation {investigation_id} deleted successfully"
    )


@router.get("/{investigation_id}/timeline", response_model=InvestigationTimelineResponse)
async def get_investigation_timeline(
    investigation_id: str,
    current_user: TokenData = Depends(lambda: TokenData(username="demo_user", role="analyst"))
):
    """Get investigation timeline from TimescaleDB"""
    
    with timescale_pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT timestamp, event_type, description, metadata
                FROM timeline_events
                WHERE investigation_id = %s
                ORDER BY timestamp ASC
                """,
                (investigation_id,)
            )
            
            events = []
            for row in cur.fetchall():
                events.append({
                    "timestamp": row[0].isoformat(),
                    "event_type": row[1],
                    "description": row[2],
                    "metadata": row[3] or {}
                })
    
    if not events:
        # Check if investigation exists
        with neo4j_driver.session() as session:
            result = session.run(
                "MATCH (i:Investigation {id: $id}) RETURN i",
                id=investigation_id
            )
            if not result.single():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Investigation {investigation_id} not found"
                )
    
    start_date = datetime.fromisoformat(events[0]["timestamp"]) if events else datetime.utcnow()
    end_date = datetime.fromisoformat(events[-1]["timestamp"]) if events else datetime.utcnow()
    
    return InvestigationTimelineResponse(
        investigation_id=investigation_id,
        events=events,
        start_date=start_date,
        end_date=end_date
    )
