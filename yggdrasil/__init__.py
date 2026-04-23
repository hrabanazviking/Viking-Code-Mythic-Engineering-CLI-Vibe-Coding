"""
Yggdrasil Cognitive Architecture
================================

A Norse mythology-inspired cognitive processing and memory system for AI applications.

The Nine Worlds:
    - Asgard: Divine Oversight & Strategic Planning
    - Vanaheim: Harmony & Resource Cultivation  
    - Alfheim: Illusion & Agile Routing
    - Midgard: Manifestation & Final Weaving
    - Jotunheim: Raw Power & Chaotic Execution
    - Svartalfheim: Forging & Tool Crafting
    - Niflheim: Preservation & Misty Verification
    - Muspelheim: Transformation & Fiery Critique
    - Helheim: Reflection & Ancestral Memory

The Ravens:
    - Huginn (Thought): Dynamic querying, retrieval, routing
    - Muninn (Memory): Persistent storage, structure, archives

The Bridge:
    - Bifrost: Routes queries between realms

Version: 1.0.0
Author: Volmarr the Viking / RuneForgeAI
License: Viking Ethical Use License
"""

__version__ = "1.0.0"
__author__ = "Volmarr the Viking"

from yggdrasil.core.world_tree import WorldTree, YggdrasilOrchestrator
from yggdrasil.core.dag import DAG, TaskNode
from yggdrasil.core.bifrost import Bifrost, RealmRouter
from yggdrasil.core.llm_queue import LLMQueue

from yggdrasil.ravens.huginn import Huginn
from yggdrasil.ravens.muninn import Muninn
from yggdrasil.ravens.raven_rag import RavenRAG

# World imports
from yggdrasil.worlds import (
    Asgard,
    Vanaheim, 
    Alfheim,
    Midgard,
    Jotunheim,
    Svartalfheim,
    Niflheim,
    Muspelheim,
    Helheim
)

__all__ = [
    # Core
    "WorldTree",
    "YggdrasilOrchestrator",
    "DAG",
    "TaskNode",
    "Bifrost",
    "RealmRouter",
    "LLMQueue",
    
    # Ravens
    "Huginn",
    "Muninn",
    "RavenRAG",
    
    # Worlds
    "Asgard",
    "Vanaheim",
    "Alfheim",
    "Midgard",
    "Jotunheim",
    "Svartalfheim",
    "Niflheim",
    "Muspelheim",
    "Helheim",
]
