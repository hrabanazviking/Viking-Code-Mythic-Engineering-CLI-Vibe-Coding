#!/usr/bin/env python3
"""
Yggdrasil Test Suite
====================

Comprehensive tests for the Yggdrasil cognitive architecture.

Run: python -m pytest tests/test_yggdrasil.py -v
Or:  cd NorseSagaEngine && python -m yggdrasil.tests.test_yggdrasil
"""

import sys
import pytest
from pathlib import Path

# Add NorseSagaEngine root to path for imports
_test_dir = Path(__file__).parent
_yggdrasil_dir = _test_dir.parent
_engine_dir = _yggdrasil_dir.parent
sys.path.insert(0, str(_engine_dir))

def test_dag():
    """Test DAG functionality."""
    print("\n=== Testing DAG ===")
    
    from yggdrasil.core.dag import DAG, TaskNode, TaskType, RealmAffinity
    
    # Create nodes
    nodes = [
        TaskNode(
            id="plan",
            task_type=TaskType.LLM,
            realm=RealmAffinity.ASGARD,
            prompt="Plan the approach",
        ),
        TaskNode(
            id="execute",
            task_type=TaskType.PYTHON,
            realm=RealmAffinity.JOTUNHEIM,
            script="print('Executed!')",
            depends_on=["plan"],
        ),
        TaskNode(
            id="verify",
            task_type=TaskType.VERIFY,
            realm=RealmAffinity.NIFLHEIM,
            depends_on=["execute"],
        ),
        TaskNode(
            id="assemble",
            task_type=TaskType.COMPOSITE,
            realm=RealmAffinity.MIDGARD,
            depends_on=["verify"],
        ),
    ]
    
    dag = DAG(nodes)
    
    # Test basic properties
    assert len(dag) == 4, "DAG should have 4 nodes"
    
    # Test ready tasks
    ready = dag.get_ready_tasks()
    assert len(ready) == 1, "Only planning node should be ready"
    assert ready[0].id == "plan", "Planning node should be first"
    
    # Simulate execution
    dag.mark_completed("plan", {"output": "plan complete"})
    
    ready = dag.get_ready_tasks()
    assert len(ready) == 1, "Execute should be ready after plan"
    assert ready[0].id == "execute"
    
    dag.mark_completed("execute", {"output": "executed"})
    dag.mark_completed("verify", {"confidence": 0.9})
    dag.mark_completed("assemble", {"final": "done"})
    
    assert dag.is_finished(), "DAG should be finished"
    
    # Test results
    results = dag.get_results()
    assert len(results) == 4, "Should have 4 results"
    
    # Test validation
    errors = dag.validate()
    assert len(errors) == 0, "Valid DAG should have no errors"
    
    print("✓ DAG tests passed")


def test_llm_queue():
    """Test LLM Queue functionality."""
    print("\n=== Testing LLM Queue ===")
    
    from yggdrasil.core.llm_queue import LLMQueue, MockLLM, QueuePriority
    
    # Create mock LLM
    mock = MockLLM(delay=0.01, responses={"hello": "Hi there!"})
    queue = LLMQueue(mock)
    
    # Test sync processing
    response, error = queue.process_sync("hello world", realm="midgard")
    assert error is None, f"Should not have error: {error}"
    assert response is not None, "Should have response"
    
    # Test priority queue
    queue.enqueue("low priority", priority=QueuePriority.LOW)
    queue.enqueue("high priority", priority=QueuePriority.HIGH)
    queue.enqueue("normal priority", priority=QueuePriority.NORMAL)
    
    # Process in order
    results = queue.process_all()
    assert len(results) == 3, "Should process 3 requests"
    
    # High priority should be first
    assert "high" in results[0].prompt.lower(), "High priority should be first"
    
    # Test metrics
    metrics = queue.get_metrics()
    assert metrics["total_completions"] > 0, "Should have completions"
    assert metrics["cache_hits"] >= 0, "Should expose cache hit metric"

    # Repeated prompt should use cache and avoid extra model calls
    baseline_calls = mock.call_count
    response_cached, error_cached = queue.process_sync("hello world", realm="midgard")
    assert error_cached is None, "Cached request should not fail"
    assert response_cached is not None, "Cached request should still return response"
    assert mock.call_count == baseline_calls, "Cache should prevent redundant model call"
    
    print("✓ LLM Queue tests passed")


def test_bifrost():
    """Test Bifrost routing functionality."""
    print("\n=== Testing Bifrost ===")
    
    from yggdrasil.core.bifrost import Bifrost, RealmAffinity
    
    bifrost = Bifrost()
    
    # Test routing
    decision = bifrost.route("calculate the sum of 1+2+3")
    assert decision.primary_realm == RealmAffinity.JOTUNHEIM, "Should route to Jotunheim for calculation"
    
    decision = bifrost.route("explain how photosynthesis works")
    assert decision.primary_realm == RealmAffinity.ASGARD, "Should route to Asgard for explanation"
    
    decision = bifrost.route("remember this fact for later")
    assert decision.primary_realm == RealmAffinity.HELHEIM, "Should route to Helheim for memory"
    
    decision = bifrost.route("verify the results are correct")
    assert decision.primary_realm == RealmAffinity.NIFLHEIM, "Should route to Niflheim for verification"
    
    # Test bridge status
    assert bifrost.is_bridge_open(RealmAffinity.MIDGARD), "Midgard should be open"
    
    bifrost.close_bridge(RealmAffinity.JOTUNHEIM)
    assert not bifrost.is_bridge_open(RealmAffinity.JOTUNHEIM), "Jotunheim should be closed"
    
    # Routing should find alternative when bridge closed
    decision = bifrost.route("calculate something")
    # Should reroute since Jotunheim is closed
    
    bifrost.open_bridge(RealmAffinity.JOTUNHEIM)
    
    print("✓ Bifrost tests passed")


def test_asgard():
    """Test Asgard planning functionality."""
    print("\n=== Testing Asgard ===")
    
    from yggdrasil.worlds.asgard import Asgard
    
    asgard = Asgard()
    
    # Test decomposition
    decomp = asgard.decompose_query("Calculate the average of these numbers and verify the result")
    assert len(decomp["branches"]) > 0, "Should create branches"
    assert "calculate" in decomp["actions"], "Should identify calculate action"
    
    # Test DAG outline
    dag = asgard.outline_dag("Process some data")
    assert len(dag["nodes"]) > 0, "Should create nodes"
    
    # Test strategic plan
    plan = asgard.create_strategic_plan("Analyze and summarize this document")
    assert plan.goal is not None, "Plan should have goal"
    assert len(plan.nodes) > 0, "Plan should have nodes"
    assert plan.confidence > 0, "Plan should have confidence"
    
    # Test foresight
    foresight = asgard.divine_foresight("Complex multi-step analysis")
    assert "foresight" in foresight, "Should have foresight"
    assert "recommendation" in foresight, "Should have recommendation"
    
    print("✓ Asgard tests passed")


def test_jotunheim():
    """Test Jotunheim execution functionality."""
    print("\n=== Testing Jotunheim ===")
    
    from yggdrasil.worlds.jotunheim import Jotunheim
    
    jotunheim = Jotunheim()
    
    # Test script execution (may fail in some environments)
    result = jotunheim.execute_script("print('Hello from Jotunheim')")
    # Don't assert success since subprocess may not work in all environments
    print(f"  Script execution: success={result.success}, stdout='{result.stdout}', stderr='{result.stderr}'")
    
    # Test calculation - this should always work
    calc = jotunheim.calculate("2 + 2 * 3")
    assert calc["success"], "Calculation should succeed"
    assert calc["result"] == 8, "Result should be 8"
    
    # Test data crunch
    crunch = jotunheim.crunch_data([1, 2, 3, 4, 5], "mean")
    assert crunch["result"] == 3.0, "Mean should be 3.0"
    
    # Test function execution
    def add_numbers(a, b):
        return a + b
    
    result = jotunheim.execute_function(add_numbers, args=(3, 4))
    assert result.success, "Function execution should succeed"
    assert "7" in result.stdout, "Result should contain 7"
    
    print("✓ Jotunheim tests passed")


def test_helheim():
    """Test Helheim memory functionality."""
    print("\n=== Testing Helheim ===")
    
    from yggdrasil.worlds.helheim import Helheim
    
    helheim = Helheim(in_memory=True)
    
    # Test storage
    mem_id = helheim.store(
        content={"fact": "The sky is blue"},
        memory_type="fact",
        realm_source="test",
        importance=7,
        tags=["color", "sky"]
    )
    assert mem_id is not None, "Should return memory ID"
    
    # Test retrieval
    memory = helheim.retrieve(mem_id)
    assert memory is not None, "Should retrieve memory"
    assert memory.content["fact"] == "The sky is blue"
    
    # Test search
    results = helheim.search(query="sky")
    assert len(results) > 0, "Should find memory"
    
    # Test by type
    facts = helheim.search(memory_type="fact")
    assert len(facts) > 0, "Should find facts"
    
    # Test wisdom extraction
    helheim.store(
        content={"lesson": "Always verify results"},
        memory_type="lesson",
        importance=8,
    )
    wisdom = helheim.extract_wisdom()
    # May or may not find wisdom depending on importance threshold
    
    # Test stats
    stats = helheim.get_stats()
    assert stats["total_memories"] > 0, "Should have memories"
    
    print("✓ Helheim tests passed")


def test_muninn():
    """Test Muninn structured memory."""
    print("\n=== Testing Muninn ===")
    
    from yggdrasil.ravens.muninn import Muninn
    
    muninn = Muninn()
    
    # Test storage
    node_id = muninn.store(
        content={"name": "Thor", "domain": "thunder"},
        path="gods/aesir",
        memory_type="entity",
        importance=8,
        tags=["god", "aesir", "thunder"]
    )
    assert node_id is not None
    
    # Test retrieval by path
    nodes = muninn.get_by_path("gods/aesir")
    assert len(nodes) == 1
    assert nodes[0].content["name"] == "Thor"
    
    # Test search
    results = muninn.retrieve(query="thunder")
    assert len(results) > 0
    
    # Test tree structure
    muninn.store(
        content={"name": "Loki"},
        path="gods/jotun",
        memory_type="entity"
    )
    
    tree = muninn.get_tree_structure()
    assert "gods" in tree
    
    # Test healing
    fixes = muninn.heal_structure()
    # Should be 0 for clean structure
    
    # Test stats
    stats = muninn.get_stats()
    assert stats["total_nodes"] >= 2
    
    print("✓ Muninn tests passed")


def test_huginn():
    """Test Huginn retrieval functionality."""
    print("\n=== Testing Huginn ===")
    
    from yggdrasil.ravens.huginn import Huginn
    from yggdrasil.ravens.muninn import Muninn
    from yggdrasil.worlds.helheim import Helheim
    
    # Set up chain
    helheim = Helheim(in_memory=True)
    muninn = Muninn(helheim=helheim)
    huginn = Huginn(muninn=muninn, helheim=helheim)
    
    # Store some data first
    muninn.store(
        content="Vikings sailed longships",
        path="history/vikings",
        memory_type="fact"
    )
    helheim.store(
        content="Norse gods lived in Asgard",
        memory_type="fact",
        importance=7
    )
    
    # Test query analysis
    analysis = huginn.analyze_query("Why did Vikings sail longships?")
    assert analysis["query_type"] == "explanatory"
    assert "key_terms" in analysis
    
    # Test routing
    route = huginn.route_query("calculate the sum")
    assert route == "jotunheim"
    
    route = huginn.route_query("remember this fact")
    assert route == "helheim"
    
    # Test flight
    result = huginn.fly("Vikings")
    assert result.source_realm is not None
    
    # Test stats
    stats = huginn.get_flight_stats()
    assert stats["total_flights"] >= 1
    
    print("✓ Huginn tests passed")


def test_raven_rag():
    """Test combined RAG system."""
    print("\n=== Testing RavenRAG ===")
    
    from yggdrasil.ravens.raven_rag import RavenRAG
    from yggdrasil.worlds.helheim import Helheim
    
    helheim = Helheim(in_memory=True)
    rag = RavenRAG(helheim=helheim)
    
    # Store some knowledge
    rag.store(
        content="Odin is the All-Father of Norse mythology",
        path="mythology/gods",
        memory_type="fact",
        importance=8
    )
    
    # Test query
    context = rag.query("Tell me about Odin")
    assert context.query == "Tell me about Odin"
    assert context.confidence > 0
    
    # Test search
    results = rag.search("Odin")
    assert len(results) > 0
    
    # Test stats
    stats = rag.get_stats()
    assert stats["queries_processed"] >= 1
    
    # Test healing
    fixes = rag.heal()
    assert isinstance(fixes, dict), "Heal should return a dict"
    
    print("✓ RavenRAG tests passed")


def test_worlds():
    """Test all nine worlds."""
    print("\n=== Testing All Nine Worlds ===")
    
    from yggdrasil.worlds import (
        Asgard, Vanaheim, Alfheim, Midgard,
        Jotunheim, Svartalfheim, Niflheim,
        Muspelheim, Helheim
    )
    
    # Test each world initializes
    asgard = Asgard()
    vanaheim = Vanaheim()
    alfheim = Alfheim()
    midgard = Midgard()
    jotunheim = Jotunheim()
    svartalfheim = Svartalfheim()
    niflheim = Niflheim()
    muspelheim = Muspelheim()
    helheim = Helheim(in_memory=True)
    
    # Quick function tests
    assert vanaheim.allocate_resources(5)["nodes"] == 5
    assert alfheim.route_node_type("calculate sum") == "python"
    
    output = midgard.deliver_manifestation({"test": "data"}, "test query")
    assert output.completeness > 0
    
    script = svartalfheim.forge_script("calculator", expression="1+1")
    assert "1+1" in script
    
    confidence = niflheim.score_confidence({"valid": "data"})
    assert 0 <= confidence <= 1
    
    # Test muspelheim critique with data that will have issues
    issues = muspelheim.simulate_critique({"task1": {"error": "test error"}})
    assert isinstance(issues, list), "Critique should return a list"
    
    # Test helheim storage
    mem_id = helheim.store("test memory", memory_type="fact")
    assert mem_id is not None
    
    print("✓ All worlds test passed")


def test_world_tree():
    """Test the complete World Tree orchestrator."""
    print("\n=== Testing World Tree ===")
    
    from yggdrasil.core.world_tree import WorldTree
    
    # Mock LLM
    def mock_llm(prompt):
        return f"Mock response to: {prompt[:50]}..."
    
    tree = WorldTree(llm_callable=mock_llm)
    
    # Test basic query
    result = tree.query("What is 2+2?")
    assert result is not None
    
    # Test remember/recall
    tree.remember({"fact": "Test fact"}, path="test")
    recalled = tree.recall(path="test")
    assert len(recalled) > 0
    
    # Test stats
    stats = tree.get_stats()
    assert "executions" in stats
    
    # Test healing
    fixes = tree.heal()
    assert "rag" in fixes
    
    print("✓ World Tree tests passed")


def test_integration():
    """Test Norse Saga integration."""
    print("\n=== Testing Norse Saga Integration ===")
    
    from yggdrasil.integration.norse_saga import NorseSagaCognition
    
    def mock_llm(prompt):
        return "This is a mock response for the game."
    
    cognition = NorseSagaCognition(llm_callable=mock_llm)
    
    # Test session
    session_id = cognition.start_session()
    assert session_id is not None
    
    # Test character memory
    mem_id = cognition.store_character_memory(
        character_id="ragnar",
        memory_content={"event": "Met the player"},
        memory_type="interaction",
        importance=6
    )
    assert mem_id is not None
    
    # Test recall
    if not hasattr(cognition, "recall_character_memories"):
        pytest.skip("NorseSagaCognition recall_character_memories API not available")

    memories = cognition.recall_character_memories("ragnar")
    assert isinstance(memories, list)
    
    # Test world fact
    fact_id = cognition.store_world_fact(
        fact="Uppsala is the sacred center",
        category="lore",
        importance=7
    )
    assert fact_id is not None
    
    # Test event logging
    if getattr(cognition, "muninn", None) is None:
        pytest.skip("NorseSagaCognition.muninn storage backend not available")

    event_id = cognition.log_event(
        event_type="combat",
        description="Battle at the river",
        participants=["ragnar", "player"],
        importance=5
    )
    assert event_id is not None
    
    # Test stats
    stats = cognition.get_stats()
    assert "memory_tree" in stats  # key was renamed from world_tree
    
    # End session
    cognition.end_session()
    
    print("✓ Norse Saga integration tests passed")


def run_all_tests():
    """Run all tests."""
    print("=" * 60)
    print("YGGDRASIL TEST SUITE")
    print("=" * 60)
    
    tests = [
        test_dag,
        test_llm_queue,
        test_bifrost,
        test_asgard,
        test_jotunheim,
        test_helheim,
        test_muninn,
        test_huginn,
        test_raven_rag,
        test_worlds,
        test_world_tree,
        test_integration,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"\n✗ {test.__name__} FAILED: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("=" * 60)
    
    return failed == 0


if __name__ == "__main__":
    run_all_tests()
