# Yggdrasil Cognitive Architecture

## The World Tree of AI Memory and Processing

Yggdrasil is a Norse mythology-inspired cognitive processing and memory system for AI applications. Named after the great World Tree that connects the Nine Worlds in Norse cosmology, this architecture provides structured, hierarchical processing of queries through specialized realms.

## Overview

```
                        ┌─────────────┐
                        │   ASGARD    │
                        │  Planning   │
                        └──────┬──────┘
                               │
            ┌──────────────────┼──────────────────┐
            │                  │                  │
     ┌──────┴──────┐    ┌──────┴──────┐    ┌──────┴──────┐
     │  VANAHEIM   │    │   ALFHEIM   │    │  HELHEIM    │
     │  Resources  │    │   Routing   │    │   Memory    │
     └──────┬──────┘    └──────┬──────┘    └──────┬──────┘
            │                  │                  │
            └──────────────────┼──────────────────┘
                               │
     ┌─────────────────────────┼─────────────────────────┐
     │                         │                         │
┌────┴────┐             ┌──────┴──────┐            ┌─────┴─────┐
│JOTUNHEIM│             │   MIDGARD   │            │SVARTALFHEIM│
│Execution│             │  Assembly   │            │  Forging   │
└────┬────┘             └──────┬──────┘            └─────┬─────┘
     │                         │                         │
     └─────────────────────────┼─────────────────────────┘
                               │
            ┌──────────────────┼──────────────────┐
            │                  │                  │
     ┌──────┴──────┐    ┌──────┴──────┐    
     │  NIFLHEIM   │    │ MUSPELHEIM  │    
     │ Verification│    │   Critique  │    
     └─────────────┘    └─────────────┘    
```

## The Nine Worlds

| World | Domain | Function |
|-------|--------|----------|
| **Asgard** | Divine Oversight | Strategic planning, query decomposition, DAG generation |
| **Vanaheim** | Harmony | Resource allocation, argument preparation, load balancing |
| **Alfheim** | Illusion | Dynamic routing, path selection, probabilistic branching |
| **Midgard** | Manifestation | Final assembly, output formatting, delivery |
| **Jotunheim** | Raw Power | Heavy computation, parallel execution, simulations |
| **Svartalfheim** | Forging | Tool creation, script generation, artifacts |
| **Niflheim** | Preservation | Verification, validation, confidence scoring |
| **Muspelheim** | Transformation | Critique, refinement, error correction |
| **Helheim** | Memory | Storage, retrieval, ancestral wisdom |

## The Ravens

### Huginn (Thought)
The raven of dynamic querying and retrieval. Huginn scouts ahead through Yggdrasil's branches, bringing back only the relevant information needed for the current thought.

- Query analysis and routing
- Hierarchical index traversal
- Context compression for token efficiency
- Multi-hop reasoning chains

### Muninn (Memory)
The raven of persistent storage and structure. Muninn maintains the long-term memory and organizational structure of the entire system.

- Hierarchical memory tree
- Multi-format support (JSON, YAML, Markdown)
- Self-healing data structures
- Automatic indexing

## Quick Start

### Basic Usage

```python
from yggdrasil import WorldTree

# Create the World Tree with an LLM callable
def my_llm(prompt):
    # Your LLM implementation
    return "response"

tree = WorldTree(llm_callable=my_llm)

# Process a query
result = tree.process("Analyze the weather patterns in Scandinavia")

print(result.final_output)
print(f"Confidence: {result.confidence}")
print(f"Execution time: {result.execution_time}s")
```

### Using the Ravens

```python
from yggdrasil.ravens import Huginn, Muninn

# Initialize
muninn = Muninn(data_path="./memory")
huginn = Huginn(muninn=muninn)

# Store knowledge
muninn.store(
    content="Odin is the All-Father",
    path="mythology/gods",
    memory_type="fact",
    importance=8
)

# Retrieve with Huginn
result = huginn.fly("Tell me about Norse gods")
print(result.results)
```

### RAG Integration

```python
from yggdrasil.ravens import RavenRAG

rag = RavenRAG()

# Store knowledge
rag.store(
    content="Viking ships were called longships",
    path="history/vikings",
    memory_type="fact"
)

# Query with context
context = rag.query("What did Vikings sail?")
print(context.retrieved_content)
print(context.to_prompt_string())
```

### Norse Saga Engine Integration

```python
from yggdrasil.integration import NorseSagaCognition

# Initialize for game
cognition = NorseSagaCognition(
    llm_callable=my_llm,
    data_path="./game_data"
)

# Start session
cognition.start_session()

# Store character memory
cognition.store_character_memory(
    character_id="ragnar",
    memory_content="Met the player at the docks",
    memory_type="interaction",
    importance=6
)

# Generate NPC dialogue
response = cognition.generate_dialogue(
    npc_id="ragnar",
    player_input="Greetings, warrior!",
    situation="In the mead hall"
)

# End session
cognition.end_session()
```

## Architecture

### DAG-Based Processing

Yggdrasil uses a Directed Acyclic Graph (DAG) to orchestrate task execution:

```python
from yggdrasil.core import DAG, TaskNode, TaskType, RealmAffinity

dag = DAG()

dag.add_node(TaskNode(
    id="plan",
    task_type=TaskType.LLM,
    realm=RealmAffinity.ASGARD,
    prompt="Plan the approach"
))

dag.add_node(TaskNode(
    id="execute",
    task_type=TaskType.PYTHON,
    realm=RealmAffinity.JOTUNHEIM,
    script="calculate_result()",
    depends_on=["plan"]
))
```

### Bifrost Routing

The Bifrost bridge intelligently routes queries to appropriate realms:

```python
from yggdrasil.core import Bifrost

bifrost = Bifrost()

decision = bifrost.route("Calculate the sum of these numbers")
print(decision.primary_realm)  # JOTUNHEIM
print(decision.task_type)      # PYTHON
```

### LLM Queue

Sequential LLM processing to prevent cognitive overload:

```python
from yggdrasil.core import LLMQueue, QueuePriority

queue = LLMQueue(llm_callable)

# Add requests with priority
queue.enqueue("Important query", priority=QueuePriority.HIGH)
queue.enqueue("Background task", priority=QueuePriority.LOW)

# Process all
results = queue.process_all()
```

## Configuration

Configure Yggdrasil via `config/default.yaml`:

```yaml
world_tree:
  execution_mode: "sequential"
  max_iterations: 3

realms:
  jotunheim:
    max_workers: 4
    use_processes: false
  
  helheim:
    in_memory: false
    max_memories: 10000

ravens:
  huginn:
    max_results: 5
    compress_results: true
```

## Testing

Run the test suite:

```bash
cd NorseSagaEngine
python yggdrasil/tests/test_yggdrasil.py
```

## Directory Structure

```
yggdrasil/
├── __init__.py
├── core/
│   ├── __init__.py
│   ├── dag.py           # Task graph engine
│   ├── bifrost.py       # Realm router
│   ├── llm_queue.py     # LLM queue management
│   └── world_tree.py    # Main orchestrator
├── worlds/
│   ├── __init__.py
│   ├── asgard.py        # Planning
│   ├── vanaheim.py      # Resources
│   ├── alfheim.py       # Routing
│   ├── midgard.py       # Assembly
│   ├── jotunheim.py     # Execution
│   ├── svartalfheim.py  # Forging
│   ├── niflheim.py      # Verification
│   ├── muspelheim.py    # Critique
│   └── helheim.py       # Memory
├── ravens/
│   ├── __init__.py
│   ├── huginn.py        # Retrieval
│   ├── muninn.py        # Storage
│   └── raven_rag.py     # Combined RAG
├── integration/
│   ├── __init__.py
│   └── norse_saga.py    # Game integration
├── config/
│   ├── __init__.py
│   └── default.yaml
├── prompts/
│   └── system_prompts.yaml
└── tests/
    ├── __init__.py
    └── test_yggdrasil.py
```

## Philosophy

> "Huginn and Muninn fly every day over the spacious earth;
> I fear for Huginn, that he come not back,
> yet more anxious am I for Muninn."
> — Grímnismál, Poetic Edda

Yggdrasil embodies the wisdom that **Thought without Memory is fleeting**, but **Memory without Thought is inert**. By uniting Huginn (active retrieval) with Muninn (structured storage), and routing through the Nine Worlds (specialized processing), we create a cognitive architecture that is:

- **Efficient**: Offloads computation to appropriate realms
- **Structured**: Hierarchical organization prevents chaos
- **Self-healing**: Detects and corrects data inconsistencies
- **Token-efficient**: Compression and targeted retrieval
- **Modular**: Each world operates independently

## Author

Volmarr the Viking / RuneForgeAI

---

*"The roots of Yggdrasil reach through all worlds, connecting wisdom to action, memory to thought, and chaos to order."*


