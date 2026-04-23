"""
Yggdrasil Cognition Module
===========================

Advanced cognitive systems for the Norse Saga Engine.
Implements hierarchical memory, intelligent retrieval, and cross-domain linking.

Modules:
- hierarchical_memory: Tree-based memory structure with domains
- huginn_advanced: Advanced cognitive retrieval system
- domain_crosslinker: Symbolic linking across memory domains
- memory_orchestrator: Unified interface for memory operations
"""

from .hierarchical_memory import (
    HierarchicalMemoryTree,
    MemoryNode,
    NodeDomain,
    MemoryType,
    SymbolicLink
)

from .huginn_advanced import (
    HuginnAdvanced,
    CognitiveRetrieval,
    RetrievalStrategy,
    QueryComplexity
)

from .domain_crosslinker import (
    DomainCrosslinker,
    CrossDomainQuery,
    RelationshipType
)

from .memory_orchestrator import (
    MemoryOrchestrator,
    MemoryOperation,
    MemoryOperationResult
)

__all__ = [
    # Hierarchical memory
    "HierarchicalMemoryTree",
    "MemoryNode",
    "NodeDomain",
    "MemoryType",
    "SymbolicLink",
    
    # Huginn advanced
    "HuginnAdvanced",
    "CognitiveRetrieval",
    "RetrievalStrategy",
    "QueryComplexity",
    
    # Domain crosslinker
    "DomainCrosslinker",
    "CrossDomainQuery",
    "RelationshipType",
    
    # Memory orchestrator
    "MemoryOrchestrator",
    "MemoryOperation",
    "MemoryOperationResult"
]

__version__ = "8.0.0"
__author__ = "Norse Saga Engine Team"
__description__ = "Advanced cognitive systems for Yggdrasil memory architecture"