"""
Entity & Graph API
Entity search, graph queries, relationship analysis
"""

from fastapi import APIRouter, HTTPException, status
from typing import List
from datetime import datetime
import uuid

from app.schemas.requests import EntitySearch, EntityMerge, GraphQuery
from app.schemas.responses import (
    EntityResponse, EntitySearchResponse, GraphResponse, SuccessResponse
)
from app.schemas.base import Entity, Relationship, EntityType, GraphData, GraphNode, GraphEdge
from app.core.database import neo4j_driver

router = APIRouter(tags=["entities"])


@router.post("/search", response_model=EntitySearchResponse)
async def search_entities(data: EntitySearch):
    """
    Search entities by name/type
    Uses Elasticsearch-style fuzzy matching on Neo4j
    """
    
    with neo4j_driver.session() as session:
        # Build query dynamically
        where_clauses = []
        params = {"query": f"(?i).*{data.query}.*", "min_conf": data.min_confidence}
        
        if data.investigation_id:
            where_clauses.append("(i.id = $inv_id)")
            params["inv_id"] = data.investigation_id
        
        if data.entity_type:
            where_clauses.append("(e.type = $etype)")
            params["etype"] = data.entity_type.value
        
        where_clause = " AND ".join(where_clauses) if where_clauses else "true"
        
        query = f"""
        MATCH (i:Investigation)-[:HAS_ENTITY]->(e:Entity)
        WHERE {where_clause} 
          AND e.name =~ $query
          AND e.confidence >= $min_conf
        RETURN e
        ORDER BY e.confidence DESC, e.created_at DESC
        LIMIT $limit
        """
        
        params["limit"] = data.limit
        
        result = session.run(query, **params)
        
        entities = []
        for record in result:
            node = record["e"]
            entities.append(Entity(
                id=node["id"],
                name=node["name"],
                type=EntityType(node.get("type", "unknown")),
                confidence=node.get("confidence", 0.5),
                properties=node.get("properties", {}),
                sources=node.get("sources", []),
                first_seen=node["created_at"].to_native(),
                last_updated=node.get("updated_at", node["created_at"]).to_native(),
                investigation_id=data.investigation_id or "unknown"
            ))
        
        # Get total count
        count_query = query.replace("RETURN e", "RETURN count(e) as total").replace("LIMIT $limit", "")
        count_result = session.run(count_query, **{k: v for k, v in params.items() if k != "limit"})
        total = count_result.single()["total"]
    
    return EntitySearchResponse(entities=entities, total=total)


@router.get("/{entity_id}", response_model=EntityResponse)
async def get_entity(entity_id: str):
    """Get entity details with relationships"""
    
    with neo4j_driver.session() as session:
        # Get entity
        result = session.run(
            "MATCH (e:Entity {id: $id}) RETURN e",
            id=entity_id
        )
        record = result.single()
        
        if not record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Entity {entity_id} not found"
            )
        
        node = record["e"]
        entity = Entity(
            id=node["id"],
            name=node["name"],
            type=EntityType(node.get("type", "unknown")),
            confidence=node.get("confidence", 0.5),
            properties=node.get("properties", {}),
            sources=node.get("sources", []),
            first_seen=node["created_at"].to_native(),
            last_updated=node.get("updated_at", node["created_at"]).to_native(),
            investigation_id="unknown"  # Will be fetched separately if needed
        )
        
        # Get relationships
        rel_result = session.run(
            """
            MATCH (e1:Entity {id: $id})-[r]-(e2:Entity)
            RETURN r, e2.id as other_id
            """,
            id=entity_id
        )
        
        relationships = []
        for rel_record in rel_result:
            rel = rel_record["r"]
            relationships.append(Relationship(
                id=str(uuid.uuid4()),
                from_entity_id=entity_id,
                to_entity_id=rel_record["other_id"],
                relationship_type=rel.type,
                confidence=rel.get("confidence", 0.5),
                properties=dict(rel.items()),
                sources=rel.get("sources", []),
                created_at=rel.get("created_at", datetime.utcnow()).to_native() if hasattr(rel.get("created_at"), 'to_native') else datetime.utcnow(),
                investigation_id="unknown"
            ))
    
    return EntityResponse(entity=entity, relationships=relationships)


@router.get("/{entity_id}/connections", response_model=GraphResponse)
async def get_entity_connections(
    entity_id: str,
    depth: int = 2,
    max_nodes: int = 100
):
    """Get entity's connection graph up to specified depth"""
    
    with neo4j_driver.session() as session:
        result = session.run(
            """
            MATCH path = (e:Entity {id: $id})-[*1..$depth]-(connected:Entity)
            WITH e, connected, relationships(path) as rels
            RETURN e, collect(DISTINCT connected) as nodes, collect(DISTINCT rels) as edges
            LIMIT $max
            """,
            id=entity_id,
            depth=depth,
            max=max_nodes
        )
        
        record = result.single()
        if not record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Entity {entity_id} not found"
            )
        
        # Build graph
        nodes = []
        edges = []
        
        # Add center node
        center = record["e"]
        nodes.append(GraphNode(
            id=center["id"],
            label=center["name"],
            type=EntityType(center.get("type", "unknown")),
            confidence=center.get("confidence", 0.5),
            properties=center.get("properties", {})
        ))
        
        # Add connected nodes
        for node in record["nodes"]:
            nodes.append(GraphNode(
                id=node["id"],
                label=node["name"],
                type=EntityType(node.get("type", "unknown")),
                confidence=node.get("confidence", 0.5),
                properties=node.get("properties", {})
            ))
        
        # Add edges
        seen_edges = set()
        for rel_list in record["edges"]:
            for rel in rel_list:
                edge_key = f"{rel.start_node.id}-{rel.end_node.id}-{rel.type}"
                if edge_key not in seen_edges:
                    edges.append(GraphEdge(
                        id=str(uuid.uuid4()),
                        source=str(rel.start_node.id),
                        target=str(rel.end_node.id),
                        label=rel.type,
                        confidence=rel.get("confidence", 0.5),
                        properties=dict(rel.items())
                    ))
                    seen_edges.add(edge_key)
    
    return GraphResponse(
        graph=GraphData(nodes=nodes, edges=edges),
        investigation_id="unknown",  # Could fetch from investigation link
        node_count=len(nodes),
        edge_count=len(edges)
    )


@router.post("/merge", response_model=SuccessResponse)
async def merge_entities(data: EntityMerge):
    """
    Merge duplicate entities into primary entity
    Transfers all relationships and properties
    """
    
    with neo4j_driver.session() as session:
        # Verify all entities exist
        result = session.run(
            """
            MATCH (e:Entity)
            WHERE e.id IN $ids
            RETURN count(e) as found
            """,
            ids=data.entity_ids
        )
        
        found = result.single()["found"]
        if found != len(data.entity_ids):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="One or more entities not found"
            )
        
        # Merge entities
        for entity_id in data.entity_ids:
            if entity_id == data.primary_entity_id:
                continue
            
            session.run(
                """
                MATCH (primary:Entity {id: $primary_id})
                MATCH (duplicate:Entity {id: $dup_id})
                
                // Transfer all relationships
                OPTIONAL MATCH (duplicate)-[r]->(other)
                CREATE (primary)-[r2:SAME_TYPE]->(other)
                SET r2 = properties(r)
                
                // Merge properties
                SET primary.sources = primary.sources + duplicate.sources
                
                // Delete duplicate
                DETACH DELETE duplicate
                """,
                primary_id=data.primary_entity_id,
                dup_id=entity_id
            )
    
    return SuccessResponse(
        message=f"Merged {len(data.entity_ids) - 1} entities into {data.primary_entity_id}"
    )


@router.post("/graph/query", response_model=GraphResponse)
async def query_graph(data: GraphQuery):
    """Execute custom graph query or get investigation graph"""
    
    with neo4j_driver.session() as session:
        if data.cypher_query:
            # Execute custom Cypher query (admin only in production!)
            result = session.run(data.cypher_query)
        elif data.entity_id:
            # Get specific entity's neighborhood
            result = session.run(
                """
                MATCH (e:Entity {id: $id})-[r*1..$depth]-(connected:Entity)
                RETURN e, connected, r
                LIMIT $max
                """,
                id=data.entity_id,
                depth=data.depth,
                max=data.max_nodes
            )
        else:
            # Get full investigation graph
            result = session.run(
                """
                MATCH (i:Investigation {id: $inv_id})-[:HAS_ENTITY]->(e:Entity)
                OPTIONAL MATCH (e)-[r]-(e2:Entity)
                RETURN collect(DISTINCT e) as nodes, collect(DISTINCT r) as edges
                LIMIT $max
                """,
                inv_id=data.investigation_id,
                max=data.max_nodes
            )
        
        nodes = []
        edges = []
        
        for record in result:
            # Parse nodes
            if "nodes" in record:
                for node in record["nodes"]:
                    nodes.append(GraphNode(
                        id=node["id"],
                        label=node["name"],
                        type=EntityType(node.get("type", "unknown")),
                        confidence=node.get("confidence", 0.5),
                        properties=node.get("properties", {})
                    ))
            
            # Parse edges
            if "edges" in record:
                for rel in record["edges"]:
                    if rel:  # Check if relationship exists
                        edges.append(GraphEdge(
                            id=str(uuid.uuid4()),
                            source=str(rel.start_node.id),
                            target=str(rel.end_node.id),
                            label=rel.type,
                            confidence=rel.get("confidence", 0.5),
                            properties=dict(rel.items())
                        ))
    
    return GraphResponse(
        graph=GraphData(nodes=nodes, edges=edges),
        investigation_id=data.investigation_id,
        node_count=len(nodes),
        edge_count=len(edges)
    )
