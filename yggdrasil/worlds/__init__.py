"""
The Nine Worlds of Yggdrasil
============================

Each world handles a specific domain of cognitive processing:

1. Asgard - Divine Oversight & Strategic Planning
2. Vanaheim - Harmony & Resource Cultivation
3. Alfheim - Illusion & Agile Routing
4. Midgard - Manifestation & Final Weaving
5. Jotunheim - Raw Power & Chaotic Execution
6. Svartalfheim - Forging & Tool Crafting
7. Niflheim - Preservation & Misty Verification
8. Muspelheim - Transformation & Fiery Critique
9. Helheim - Reflection & Ancestral Memory
"""

from typing import Any, Dict

from yggdrasil.worlds.asgard import Asgard
from yggdrasil.worlds.vanaheim import Vanaheim
from yggdrasil.worlds.alfheim import Alfheim
from yggdrasil.worlds.midgard import Midgard
from yggdrasil.worlds.jotunheim import Jotunheim
from yggdrasil.worlds.svartalfheim import Svartalfheim
from yggdrasil.worlds.niflheim import Niflheim
from yggdrasil.worlds.muspelheim import Muspelheim
from yggdrasil.worlds.helheim import Helheim

__all__ = [
    "Asgard",
    "Vanaheim",
    "Alfheim",
    "Midgard",
    "Jotunheim",
    "Svartalfheim",
    "Niflheim",
    "Muspelheim",
    "Helheim",
    "collect_domain_telemetry",
]

# World registry for dynamic access
WORLDS = {
    "asgard": Asgard,
    "vanaheim": Vanaheim,
    "alfheim": Alfheim,
    "midgard": Midgard,
    "jotunheim": Jotunheim,
    "svartalfheim": Svartalfheim,
    "niflheim": Niflheim,
    "muspelheim": Muspelheim,
    "helheim": Helheim,
}


def get_world(name: str):
    """Get a world class by name."""
    return WORLDS.get(name.lower())



def collect_domain_telemetry(world_instances: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """Gather per-domain runtime telemetry from instantiated world objects."""
    telemetry: Dict[str, Dict[str, Any]] = {}
    for domain, world in (world_instances or {}).items():
        if not world:
            continue
        telemetry[domain] = {
            "world_class": world.__class__.__name__,
            "has_history": bool(getattr(world, "_execution_history", None) or getattr(world, "_plans", None)),
            "attributes": [
                key for key in ["_execution_history", "_plan_history", "_transformation_history", "_verification_history", "_memory_cache"]
                if hasattr(world, key)
            ],
        }
    return telemetry
