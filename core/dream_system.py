"""
Dream System Integration

Connects cosmological communication pathways to the dream system
"""

from collections import Counter
from typing import Dict, Any, List
from ..yggdrasil_core import tree

# ---------------------------------------------------------------------------
# Norse dream symbol table — maps keywords to meaning + category
# ---------------------------------------------------------------------------
_DREAM_SYMBOLS: Dict[str, Dict[str, str]] = {
    # Combat / battle omens
    "axe":      {"meaning": "conflict, decisive action",              "category": "battle"},
    "sword":    {"meaning": "justice, war, honour",                   "category": "battle"},
    "spear":    {"meaning": "Odin's will, sacrifice",                 "category": "battle"},
    "shield":   {"meaning": "defence, honour preserved under threat", "category": "battle"},
    "arrow":    {"meaning": "swift fate arriving from a distance",    "category": "battle"},
    "helm":     {"meaning": "leadership tested, authority at stake",  "category": "battle"},
    # Death / endings
    "blood":    {"meaning": "sacrifice, loss, kin-ties severed",      "category": "death"},
    "wound":    {"meaning": "coming hardship, price to be paid",      "category": "death"},
    "death":    {"meaning": "transformation, end of a chapter",       "category": "death"},
    "corpse":   {"meaning": "reckoning approaching, ancestor warning","category": "death"},
    "grave":    {"meaning": "the weight of those who came before",    "category": "death"},
    "bones":    {"meaning": "what remains when all else is stripped", "category": "death"},
    # Divine / gods
    "raven":    {"meaning": "Odin's gaze, wisdom, foreknowledge",     "category": "divine"},
    "eagle":    {"meaning": "sovereignty, far sight, divine favour",  "category": "divine"},
    "crow":     {"meaning": "Hugin or Muninn; thought or memory stirs","category": "divine"},
    "storm":    {"meaning": "Thor's wrath, chaos approaching",        "category": "divine"},
    "lightning":{"meaning": "Mjolnir's voice; swift divine judgement","category": "divine"},
    "stranger": {"meaning": "Odin in disguise, test of hospitality",  "category": "divine"},
    "god":      {"meaning": "direct divine attention on your wyrd",   "category": "divine"},
    # Wyrd / fate / creatures
    "wolf":     {"meaning": "Fenrir's shadow, pack-betrayal or loyalty","category": "wyrd"},
    "serpent":  {"meaning": "Jörmungandr, cycles, hidden treachery",  "category": "wyrd"},
    "snake":    {"meaning": "cunning threat coiled near what you love","category": "wyrd"},
    "spider":   {"meaning": "the Norns weave; a trap being set",      "category": "wyrd"},
    "thread":   {"meaning": "wyrd is being cut or knotted",           "category": "wyrd"},
    "rope":     {"meaning": "bonds of obligation or captivity",       "category": "wyrd"},
    # Cosmic / elemental
    "tree":     {"meaning": "Yggdrasil, deep roots, the nine worlds", "category": "cosmic"},
    "fire":     {"meaning": "Muspelheim, destruction and renewal",    "category": "cosmic"},
    "ice":      {"meaning": "Niflheim, stillness before action",      "category": "cosmic"},
    "frost":    {"meaning": "Niflheim's reach; delay or freezing of plans","category": "cosmic"},
    "ocean":    {"meaning": "Jörmungandr's domain, unseen depths",    "category": "cosmic"},
    "sea":      {"meaning": "perilous crossing; the unknown horizon", "category": "cosmic"},
    "mountain": {"meaning": "immovable obstacle or enduring strength","category": "cosmic"},
    "bridge":   {"meaning": "Bifrost; passage between worlds or lives","category": "cosmic"},
    # Strength / beasts
    "bear":     {"meaning": "berserker strength, protection, raw power","category": "strength"},
    "boar":     {"meaning": "Frey's blessing; ferocity in the charge","category": "strength"},
    "ox":       {"meaning": "patient endurance; labour well spent",   "category": "strength"},
    "stag":     {"meaning": "noble pride; hunted or hunter?",         "category": "strength"},
    # Journey / movement
    "horse":    {"meaning": "Sleipnir, swiftness of fate, a journey", "category": "journey"},
    "ship":     {"meaning": "voyage ahead; Norsemen never die on land","category": "journey"},
    "road":     {"meaning": "a choice of paths; crossroads of wyrd",  "category": "journey"},
    "gate":     {"meaning": "threshold; one world ending, another beginning","category": "journey"},
    # Treasure / obligation
    "gold":     {"meaning": "Freyja's tears, wealth that brings sorrow or joy","category": "treasure"},
    "ring":     {"meaning": "Draupnir, oath-binding, endless obligation","category": "treasure"},
    "silver":   {"meaning": "moonlit promise; deals with hidden cost","category": "treasure"},
    "treasure": {"meaning": "Andvari's gold; cursed abundance",       "category": "treasure"},
    # Family / kin
    "child":    {"meaning": "new beginning, legacy, vulnerability",   "category": "family"},
    "kin":      {"meaning": "frith obligations, ancestral duty",      "category": "family"},
    "mother":   {"meaning": "Frigg's hand; protection or loss of it", "category": "family"},
    "father":   {"meaning": "inherited burden or honour",             "category": "family"},
    "hall":     {"meaning": "the mead-hall; community and its safety","category": "family"},
}

_CATEGORY_MEANINGS: Dict[str, str] = {
    "battle":   "Conflict looms on the horizon — steel yourself.",
    "death":    "The Norns weave endings; something must pass away.",
    "divine":   "The gods turn their gaze upon you.",
    "wyrd":     "The threads of fate are shifting; wyrd is in motion.",
    "cosmic":   "Forces older than men are stirring.",
    "strength": "Raw power is yours to claim or face.",
    "journey":  "A path opens; movement and change are coming.",
    "treasure": "Desire and obligation are tangled ahead.",
    "family":   "Blood-bonds will be tested.",
}


class DreamSystem:
    """Handles integration between Dreams pathway and dream system"""
    def __init__(self):
        # tree.state may be None during early init — guard with getattr
        state = getattr(tree, 'state', None) or {}
        self.dream_interpretations = state.get('dream_interpretations', {})

    def process_dream_vision(self, dream_data: Dict[str, Any]):
        """Process incoming dream vision"""
        if not isinstance(dream_data, dict):
            return None
        # Extract dream content with safe fallbacks
        content = dream_data.get("content", "")
        dreamer = dream_data.get("dreamer", "unknown")

        # Interpret dream
        interpretation = self.interpret_dream(content)

        # Store interpretation
        self.dream_interpretations[dreamer] = interpretation
        return interpretation

    def interpret_dream(self, content: str) -> Dict[str, Any]:
        """Interpret dream content using Norse symbolic analysis.

        Scans *content* for known Norse dream symbols, derives dominant
        omen category, and returns a structured interpretation dict.
        Certainty scales with the number of distinct symbols matched.
        """
        if not content or not content.strip():
            return {
                "symbols": [],
                "meaning": "The dream spoke no clear words to the watcher.",
                "certainty": 0.10,
            }

        content_lower = content.lower()

        # Collect all matching symbols preserving insertion order
        matched: List[Dict[str, str]] = []
        seen: set = set()
        for keyword, data in _DREAM_SYMBOLS.items():
            if keyword in content_lower and keyword not in seen:
                matched.append({"symbol": keyword, **data})
                seen.add(keyword)

        if not matched:
            return {
                "symbols": [],
                "meaning": "The vision was clouded — its wyrd remains hidden.",
                "certainty": 0.15,
            }

        # Dominant omen category (most symbol hits)
        cat_counts: Counter = Counter(m["category"] for m in matched)
        dominant_cat = cat_counts.most_common(1)[0][0]
        dominant_meaning = _CATEGORY_MEANINGS.get(
            dominant_cat, "The dream holds meaning yet undeciphered."
        )

        # Certainty scales with distinct symbol count, capped at 0.95
        certainty = round(min(0.35 + len(matched) * 0.12, 0.95), 2)

        # Composite detail from the up-to-3 most specific symbol meanings
        top_meanings = list(dict.fromkeys(m["meaning"] for m in matched[:3]))
        meaning_detail = "; ".join(top_meanings)

        return {
            "symbols": [m["symbol"] for m in matched],
            "meaning": f"{dominant_meaning} ({meaning_detail})",
            "certainty": certainty,
        }

    def connect_to_wyrd_pathway(self):
        """Register handler for Dreams-Wyrd pathway messages"""
        dreams_wyrd_pathway = tree.get_pathway(
            source=(None, None, tree.config['systems']['DREAMS']),
            destination=(None, None, tree.config['systems']['WYRD'])
        )
        if isinstance(dreams_wyrd_pathway, dict):
            # Register as a handler (not a message).  'handlers' is processed
            # by engine dispatch; 'messages' is for data payloads only.
            dreams_wyrd_pathway.setdefault('handlers', []).append(self.process_dream_vision)
