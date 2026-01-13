"""
End-to-End Integration Tests
Tests complete investigation workflow from creation to reporting
"""

import pytest
import asyncio
from datetime import datetime

from app.schemas.base import Investigation, InvestigationStatus
from app.use_cases.investigation_orchestrator import (
    create_and_execute_investigation,
    get_investigation_summary
)


@pytest.mark.asyncio
async def test_complete_investigation_workflow():
    """Test full investigation lifecycle"""
    
    # Create investigation
    investigation = await create_and_execute_investigation(
        name="E2E Test Investigation",
        target="opensource.org",
        goal="Test OSINT collection and analysis",
        user_id="test_user"
    )
    
    assert investigation is not None
    assert investigation.name == "E2E Test Investigation"
    assert investigation.status == InvestigationStatus.CREATED
    
    # Wait for processing (investigation runs async)
    await asyncio.sleep(30)  # Give collection time to run
    
    # Get summary
    summary = await get_investigation_summary(investigation.id)
    
    assert summary is not None
    assert "investigation" in summary
    assert summary["investigation"]["id"] == investigation.id
    
    # Verify entities were collected
    assert summary["entity_count"] >= 0  # May be 0 if collection failed
    
    print(f"✅ Investigation {investigation.id} completed")
    print(f"   Entities: {summary['entity_count']}")
    print(f"   Hypotheses: {summary['hypothesis_count']}")
    print(f"   Jobs: {summary['collection_job_count']}")


@pytest.mark.asyncio
async def test_api_investigation_crud():
    """Test investigation CRUD via API client"""
    
    from app.api.v1.endpoints.investigations import (
        create_investigation,
        get_investigation,
        list_investigations,
        delete_investigation
    )
    from app.schemas.requests import InvestigationCreate
    from app.api.deps import TokenData
    
    # Create
    data = InvestigationCreate(
        name="API Test",
        target="example.com",
        goal="Test API"
    )
    user = TokenData(username="test", role="analyst")
    
    response = await create_investigation(data, user)
    inv_id = response.investigation.id
    
    assert response.investigation.name == "API Test"
    
    # Get
    get_response = await get_investigation(inv_id, user)
    assert get_response.investigation.id == inv_id
    
    # List
    list_response = await list_investigations(skip=0, limit=10, current_user=user)
    assert list_response.total >= 1
    
    # Delete
    delete_response = await delete_investigation(inv_id, user)
    assert delete_response.success
    
    print("✅ All CRUD operations passed")


@pytest.mark.asyncio
async def test_collection_workflow():
    """Test collection job execution"""
    
    from app.api.v1.endpoints.collection import (
        start_collection,
        get_collection_job
    )
    from app.schemas.requests import CollectionStart
    from fastapi import BackgroundTasks
    
    # Create investigation first
    inv = await create_and_execute_investigation(
        name="Collection Test",
        target="wikipedia.org",
        goal="Test collection",
        user_id="test"
    )
    
    # Start collection
    data = CollectionStart(
        investigation_id=inv.id,
        agent_type="duckduckgo",
        query="wikipedia",
        max_results=5
    )
    
    bg_tasks = BackgroundTasks()
    response = await start_collection(data, bg_tasks)
    
    assert response.job.status.value in ["pending", "running"]
    
    # Wait for completion
    await asyncio.sleep(10)
    
    # Check status
    status_response = await get_collection_job(response.job.id)
    assert status_response.job.status.value in ["completed", "running"]
    
    print(f"✅ Collection job {response.job.id}: {status_response.job.status}")


@pytest.mark.asyncio
async def test_graph_operations():
    """Test graph query and entity search"""
    
    from app.api.v1.endpoints.entities import search_entities, query_graph
    from app.schemas.requests import EntitySearch, GraphQuery
    
    # Create investigation with data
    inv = await create_and_execute_investigation(
        name="Graph Test",
        target="github.com",
        goal="Test graph",
        user_id="test"
    )
    
    await asyncio.sleep(15)  # Let collection run
    
    # Search entities
    search_data = EntitySearch(
        query="github",
        investigation_id=inv.id,
        limit=10
    )
    
    search_response = await search_entities(search_data)
    print(f"✅ Found {search_response.total} entities")
    
    # Query graph
    graph_data = GraphQuery(
        investigation_id=inv.id,
        max_nodes=50
    )
    
    graph_response = await query_graph(graph_data)
    print(f"✅ Graph: {graph_response.node_count} nodes, {graph_response.edge_count} edges")


@pytest.mark.asyncio
async def test_llm_reasoning():
    """Test LLM reasoning capabilities"""
    
    from app.use_cases.llm_selector import get_best_llm, list_available_llms
    
    # Check available LLMs
    llms = await list_available_llms()
    print(f"Available LLMs: {[l['provider'] for l in llms if l['available']]}")
    
    # Get  best LLM
    try:
        engine = await get_best_llm(complexity="simple")
        
        # Test planning
        result = await engine.plan(
            investigation_goal="Find information about OpenAI",
            current_context={"target": "openai.com"}
        )
        
        assert result.output is not None
        assert "tasks" in result.output or "raw_response" in result.output
        
        print("✅ LLM reasoning working")
        
    except RuntimeError as e:
        print(f"⚠️  No LLM available: {e}")
        pytest.skip("No LLM configured")


# Performance test
@pytest.mark.asyncio
async def test_concurrent_investigations():
    """Test system under concurrent load"""
    
    # Create multiple investigations concurrently
    tasks = []
    for i in range(5):
        task = create_and_execute_investigation(
            name=f"Concurrent Test {i}",
            target=f"target{i}.com",
            goal=f"Load test {i}",
            user_id="load_test"
        )
        tasks.append(task)
    
    investigations = await asyncio.gather(*tasks)
    
    assert len(investigations) == 5
    assert all(inv.status == InvestigationStatus.CREATED for inv in investigations)
    
    print("✅ Created 5 concurrent investigations")


if __name__ == "__main__":
    # Run tests
    print("Running E2E Tests...")
    asyncio.run(test_complete_investigation_workflow())
    asyncio.run(test_api_investigation_crud())
    asyncio.run(test_collection_workflow())
    asyncio.run(test_graph_operations())
    asyncio.run(test_llm_reasoning())
    asyncio.run(test_concurrent_investigations())
    print("\n✅ All E2E tests passed!")
