"""Faith, devotion, and afterlife routing for death-state transitions."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

logger = logging.getLogger(__name__)


class ReligionSystem:
    """Crash-resistant spiritual and afterlife routing subsystem."""

    def __init__(self, data_path: str = "systems/data/religious_cosmology.yaml") -> None:
        self.data_path = Path(data_path)
        self.payload: Dict[str, Any] = self._load_payload()

    def _load_payload(self) -> Dict[str, Any]:
        """Huginn scouts the sacred maps while Muninn preserves fallbacks."""
        try:
            if not self.data_path.exists():
                logger.warning("Religion data file missing: %s", self.data_path)
                return {"traditions": {}, "mechanics": {}, "realms": {}, "deities": {}}
            loaded = yaml.safe_load(self.data_path.read_text(encoding="utf-8"))
            if not isinstance(loaded, dict):
                return {"traditions": {}, "mechanics": {}, "realms": {}, "deities": {}}
            return loaded
        except Exception as exc:
            logger.warning("Religion data failed to load: %s", exc)
            return {"traditions": {}, "mechanics": {}, "realms": {}, "deities": {}}

    def _normalize(self, value: Any) -> str:
        return str(value or "").strip().lower()

    def _text_blob(self, *values: Any) -> str:
        return " ".join(self._normalize(v) for v in values if v is not None)

    def detect_tradition(self, character_data: Dict[str, Any]) -> str:
        try:
            raw = self._text_blob(
                character_data.get("faith"),
                character_data.get("religion"),
                character_data.get("belief"),
                character_data.get("patron_deity"),
                character_data.get("patron"),
            )
            traditions = self.payload.get("traditions", {})
            for tradition_id, tradition in traditions.items():
                aliases = [self._normalize(a) for a in tradition.get("aliases", [])]
                if any(alias and alias in raw for alias in aliases):
                    return str(tradition_id)
        except Exception as exc:
            logger.warning("Tradition detection failed: %s", exc)
        return "norse_pagan"

    def _doctrine_weights(self) -> Dict[str, int]:
        global_weights = self.payload.get("mechanics", {}).get("doctrine_weights", {})
        return {
            "virtue": int(global_weights.get("virtue", 2)),
            "transgression": int(global_weights.get("transgression", -3)),
            "devotion": int(global_weights.get("devotion", 1)),
            "repentance": int(global_weights.get("repentance", 2)),
            "fate_alignment": int(global_weights.get("fate_alignment", 1)),
            "emotional_harmony": int(global_weights.get("emotional_harmony", 1)),
        }

    def evaluate_spiritual_state(
        self,
        character_data: Dict[str, Any],
        cause_of_death: str,
        emotional_state: Optional[Dict[str, Any]] = None,
        fate_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Norns balance virtue, transgression, devotion, fate, and emotion."""
        try:
            tradition_id = self.detect_tradition(character_data)
            traditions = self.payload.get("traditions", {})
            tradition = traditions.get(tradition_id, {}) if isinstance(traditions, dict) else {}
            text = self._text_blob(cause_of_death, character_data.get("last_actions", ""))
            weights = self._doctrine_weights()

            virtue_hits = sum(1 for token in tradition.get("virtue_keywords", []) if self._normalize(token) in text)
            transgression_hits = sum(
                1 for token in tradition.get("transgression_keywords", []) if self._normalize(token) in text
            )

            devotion = character_data.get("devotion", {}) if isinstance(character_data, dict) else {}
            piety = int(devotion.get("piety", 0)) if isinstance(devotion, dict) else 0

            rep_tokens = self.payload.get("mechanics", {}).get("global", {}).get("repentance_tokens", [])
            repentance_hits = sum(1 for token in rep_tokens if self._normalize(token) in text)

            fate_score = int((fate_context or {}).get("alignment", 0)) if isinstance(fate_context, dict) else 0
            emotional_tone = self._normalize((emotional_state or {}).get("dominant_emotion", ""))
            emotional_harmony = 1 if emotional_tone in {"resolve", "peace", "acceptance", "compassion"} else 0

            total_score = (
                virtue_hits * weights["virtue"]
                + transgression_hits * weights["transgression"]
                + piety * weights["devotion"]
                + repentance_hits * weights["repentance"]
                + fate_score * weights["fate_alignment"]
                + emotional_harmony * weights["emotional_harmony"]
            )
            return {
                "tradition": tradition_id,
                "virtue_hits": virtue_hits,
                "transgression_hits": transgression_hits,
                "repentance_hits": repentance_hits,
                "piety": piety,
                "fate_score": fate_score,
                "emotional_harmony": emotional_harmony,
                "total_score": total_score,
            }
        except Exception as exc:
            logger.warning("Spiritual evaluation failed: %s", exc)
            return {
                "tradition": "norse_pagan",
                "virtue_hits": 0,
                "transgression_hits": 0,
                "repentance_hits": 0,
                "piety": 0,
                "fate_score": 0,
                "emotional_harmony": 0,
                "total_score": 0,
            }

    def _realm_score(self, realm: Dict[str, Any], cause: str, spiritual: Dict[str, Any]) -> int:
        keywords = [self._normalize(token) for token in realm.get("routing_keywords", [])]
        keyword_hits = sum(2 for token in keywords if token and token in cause)
        virtue_bias = int(realm.get("virtue_bias", 0)) * int(spiritual.get("virtue_hits", 0))
        transgression_bias = int(realm.get("transgression_bias", 0)) * int(spiritual.get("transgression_hits", 0))
        return keyword_hits + virtue_bias + transgression_bias + int(spiritual.get("total_score", 0))

    def _pick_realm_for_cause(self, tradition_id: str, cause_of_death: str, spiritual: Dict[str, Any]) -> str:
        realms = self.payload.get("realms", {})
        best_score = -10**9
        best_realm = ""
        for realm_id, realm in realms.items():
            if not isinstance(realm, dict):
                continue
            if self._normalize(realm.get("tradition")) != self._normalize(tradition_id):
                continue
            score = self._realm_score(realm, cause_of_death, spiritual)
            if score > best_score:
                best_score = score
                best_realm = str(realm_id)
        return best_realm

    def get_deity_profiles(self, deity_ids: List[str]) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        deities = self.payload.get("deities", {})
        for deity_id in deity_ids:
            deity = deities.get(deity_id, {}) if isinstance(deities, dict) else {}
            if isinstance(deity, dict) and deity:
                results.append({"id": deity_id, **deity})
        return results

    def determine_afterlife(
        self,
        character_data: Dict[str, Any],
        cause_of_death: str,
        emotional_state: Optional[Dict[str, Any]] = None,
        fate_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        try:
            spiritual = self.evaluate_spiritual_state(
                character_data=character_data,
                cause_of_death=cause_of_death,
                emotional_state=emotional_state,
                fate_context=fate_context,
            )
            tradition_id = str(spiritual.get("tradition", "norse_pagan"))
            cause = self._normalize(cause_of_death)
            realms = self.payload.get("realms", {})
            traditions = self.payload.get("traditions", {})
            tradition = traditions.get(tradition_id, {}) if isinstance(traditions, dict) else {}

            realm_id = self._pick_realm_for_cause(tradition_id, cause, spiritual)
            if not realm_id:
                realm_id = str(tradition.get("default_realm", "helheim"))
            realm = realms.get(realm_id, {}) if isinstance(realms, dict) else {}

            deity_ids = realm.get("deity_ids", []) if isinstance(realm, dict) else []
            deity_profiles = self.get_deity_profiles(deity_ids)
            return {
                "realm_id": realm_id,
                "realm_name": realm.get("name", realm_id.replace("_", " ").title()),
                "reason": f"{tradition_id} routing via cause '{cause or 'unknown'}'",
                "tradition": tradition_id,
                "realm_summary": realm.get("summary", ""),
                "deity_profiles": deity_profiles,
                "emotion_bridge": emotional_state or {},
                "fate_bridge": fate_context or {},
                "spiritual_state": spiritual,
            }
        except Exception as exc:
            logger.warning("Afterlife routing failed: %s", exc)
            return {
                "realm_id": "helheim",
                "realm_name": "Helheim",
                "reason": "Fallback due to routing error",
                "tradition": "norse_pagan",
                "realm_summary": "Default resting place.",
                "deity_profiles": [],
                "emotion_bridge": emotional_state or {},
                "fate_bridge": fate_context or {},
                "spiritual_state": {"total_score": 0},
            }

    def apply_devotional_action(self, character_data: Dict[str, Any], action_text: str) -> Dict[str, Any]:
        """The Norns weigh devotional repetition and update patron affinity."""
        try:
            lowered = self._normalize(action_text)
            traditions = self.payload.get("traditions", {})
            deities = self.payload.get("deities", {})
            devotion = character_data.setdefault("devotion", {}) if isinstance(character_data, dict) else {}
            if not isinstance(devotion, dict):
                devotion = {}
                character_data["devotion"] = devotion

            current_tradition = self.detect_tradition(character_data)
            best_deity: Optional[str] = None
            best_score = 0

            for deity_id, deity in deities.items():
                if not isinstance(deity, dict):
                    continue
                token_bag = self._text_blob(
                    deity.get("name"),
                    " ".join(self._normalize(v) for v in deity.get("domains", [])),
                    deity.get("tradition"),
                )
                score = sum(1 for token in token_bag.split() if len(token) > 3 and token in lowered)
                if score > best_score:
                    best_score = score
                    best_deity = str(deity_id)

            global_tokens = self.payload.get("mechanics", {}).get("global", {})
            if any(token in lowered for token in global_tokens.get("devotion_action_tokens", [])):
                devotion["piety"] = int(devotion.get("piety", 0)) + 1
            if any(token in lowered for token in global_tokens.get("repentance_tokens", [])):
                devotion["atonement"] = int(devotion.get("atonement", 0)) + 1
            if any(token in lowered for token in global_tokens.get("violence_tokens", [])):
                devotion["moral_injury"] = int(devotion.get("moral_injury", 0)) + 1

            if best_deity:
                affinity = devotion.setdefault("deity_affinity", {})
                if not isinstance(affinity, dict):
                    affinity = {}
                    devotion["deity_affinity"] = affinity
                affinity[best_deity] = int(affinity.get(best_deity, 0)) + max(1, best_score)
                deity = deities.get(best_deity, {})
                deity_tradition = self._normalize(deity.get("tradition"))
                if deity_tradition and deity_tradition in traditions:
                    character_data["religion"] = deity_tradition
                    character_data["patron_deity"] = deity.get("name", best_deity)

            return {
                "religion": character_data.get("religion", current_tradition),
                "patron_deity": character_data.get("patron_deity", ""),
                "devotion": devotion,
                "matched_deity": best_deity,
            }
        except Exception as exc:
            logger.warning("Devotional action failed: %s", exc)
            return {
                "religion": character_data.get("religion", "norse_pagan"),
                "patron_deity": character_data.get("patron_deity", ""),
                "devotion": character_data.get("devotion", {}),
                "matched_deity": None,
            }
