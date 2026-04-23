"""
Personality Engine
==================

Derives a comprehensive, multi-framework psychological profile from every
section of a character YAML sheet.  Twenty distinct analytical dimensions
are calculated dynamically — no pre-authored text is required.

Frameworks synthesised:
  Big Five (OCEAN)          Jungian functions          HEXACO
  Myers-Briggs (MBTI)       Enneagram (core + wing)    Human Design
  Temperament (4 humours)   Pearson/Campbell archetypes Gene Keys
  Norse soul-layer model    Attachment theory          D&D 5E stat derivations
  Astrology (Sun/Moon/Rise) Emotional Intelligence      Cognitive friction
  Fate/Wyrd thread          Social power calculation   Vulnerability index
  Character arc trajectory  Hidden-depth scoring       Cultural integration
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Lookup tables
# ---------------------------------------------------------------------------

_MBTI_PROFILES: Dict[str, Dict[str, str]] = {
    "INTJ": {"title": "The Architect",      "summary": "Strategic mastermind; long-horizon planner; independent; high standards; natural systems-builder.",         "shadow": "Arrogance, emotional coldness, over-planning"},
    "INTP": {"title": "The Logician",       "summary": "Analytical theorist; pursues conceptual truth; detached but curious; questions everything.",               "shadow": "Analysis paralysis, neglect of feelings, ivory tower"},
    "ENTJ": {"title": "The Commander",      "summary": "Natural executive; decisive, driven, unapologetically direct; turns vision into structured action.",        "shadow": "Domineering, impatience, dismissing emotional needs"},
    "ENTP": {"title": "The Debater",        "summary": "Visionary provocateur; thrives on ideas and argument; charming, fast-thinking, resists routine.",          "shadow": "Unreliability, combativeness, abandoning projects"},
    "INFJ": {"title": "The Advocate",       "summary": "Idealist with a mission; deeply empathic and principled; rare combination of vision and compassion.",      "shadow": "Perfectionism, martyr complex, self-neglect"},
    "INFP": {"title": "The Mediator",       "summary": "Poetic dreamer; guided by internal values; seeks meaning and authentic connection.",                        "shadow": "Impracticality, excessive self-criticism, avoidance"},
    "ENFJ": {"title": "The Protagonist",    "summary": "Charismatic leader who serves others; attuned to group dynamics; natural mentor and mobiliser.",           "shadow": "Over-involvement, people-pleasing, identity-loss"},
    "ENFP": {"title": "The Campaigner",     "summary": "Enthusiastic connector; ideas and people magnetise them; infectious optimism; hates stagnation.",          "shadow": "Disorganisation, scattered energy, emotional volatility"},
    "ISTJ": {"title": "The Logistician",    "summary": "Dependable pillar; methodical, detail-conscious, loyal to duty; holds the world together.",               "shadow": "Rigidity, difficulty with ambiguity, suppressed emotion"},
    "ISFJ": {"title": "The Defender",       "summary": "Quiet protector; devoted to those they love; remembers everything; puts others first.",                   "shadow": "Self-sacrifice to excess, difficulty asserting needs"},
    "ESTJ": {"title": "The Executive",      "summary": "Practical organiser; enforces order and standards; values tradition, efficiency, clear roles.",            "shadow": "Inflexibility, bluntness, over-reliance on rules"},
    "ESFJ": {"title": "The Consul",         "summary": "Community cornerstone; attentive, warm, sociable; deeply invested in harmony and belonging.",              "shadow": "Approval-seeking, conflict avoidance, judgemental"},
    "ISTP": {"title": "The Virtuoso",       "summary": "Hands-on problem-solver; calm under pressure; masterful with tools and systems; reserved.",               "shadow": "Emotional unavailability, risk-taking, commitment issues"},
    "ISFP": {"title": "The Adventurer",     "summary": "Gentle artist; lives in the present; attuned to beauty and experience; non-confrontational.",              "shadow": "Sensitivity to criticism, over-flexibility, self-doubt"},
    "ESTP": {"title": "The Entrepreneur",   "summary": "Bold pragmatist; action-oriented, street-smart, enjoys risk; makes things happen now.",                   "shadow": "Impulsivity, insensitivity, short-termism"},
    "ESFP": {"title": "The Entertainer",    "summary": "Life of the gathering; spontaneous, generous, sensory-alive; turns every moment into an experience.",     "shadow": "Avoiding hard truths, over-indulgence, lack of focus"},
}

_ENNEAGRAM_PROFILES: Dict[str, Dict[str, str]] = {
    "1":  {"title": "The Reformer",      "core_drive": "To be good, righteous, and consistent with their ideals",        "shadow": "Resentment beneath perfectionism"},
    "2":  {"title": "The Helper",        "core_drive": "To be needed and to give love; fear of being unloved",           "shadow": "Hidden pride and conditional giving"},
    "3":  {"title": "The Achiever",      "core_drive": "To succeed and be admired; fear of worthlessness",               "shadow": "Image-management overriding authenticity"},
    "4":  {"title": "The Individualist", "core_drive": "To be unique and significant; fear of being ordinary",           "shadow": "Envy and self-absorbed melancholy"},
    "5":  {"title": "The Investigator",  "core_drive": "To understand everything; fear of being helpless",               "shadow": "Isolation disguised as self-sufficiency"},
    "6":  {"title": "The Loyalist",      "core_drive": "Security and support; fear of being without guidance",           "shadow": "Anxiety projected as suspicion"},
    "7":  {"title": "The Enthusiast",    "core_drive": "To have experiences; fear of pain and deprivation",              "shadow": "Escapism and fragmented attention"},
    "8":  {"title": "The Challenger",    "core_drive": "To be strong and self-reliant; fear of vulnerability",           "shadow": "Control disguised as protection"},
    "9":  {"title": "The Peacemaker",    "core_drive": "To maintain harmony; fear of conflict and separation",           "shadow": "Passive resistance and self-erasure"},
}

_WING_NAMES: Dict[str, str] = {
    "1w2": "The Idealist", "1w9": "The Philosopher",
    "2w1": "The Servant", "2w3": "The Host",
    "3w2": "The Enchanting Star", "3w4": "The Expert",
    "4w3": "The Aristocrat", "4w5": "The Bohemian",
    "5w4": "The Iconoclast", "5w6": "The Problem-Solver",
    "6w5": "The Defender", "6w7": "The Buddy",
    "7w6": "The Entertainer", "7w8": "The Realist",
    "8w7": "The Maverick", "8w9": "The Bear",
    "9w8": "The Referee", "9w1": "The Dreamer",
}

_TEMPERAMENT: Dict[str, str] = {
    "sanguine":         "Social, optimistic, quick-thinking, impulsive, pleasure-seeking.",
    "choleric":         "Ambitious, decisive, dominant, quick to anger, goal-driven.",
    "melancholic":      "Analytical, idealistic, deep-feeling, perfectionistic, introverted.",
    "phlegmatic":       "Calm, reliable, patient, resistant to change, steady.",
    "sanguine-choleric": "Socially dominant; warm + forceful; thrives on attention and results.",
    "choleric-melancholic": "Driven perfectionist; critical + decisive; high standards + anger.",
    "melancholic-phlegmatic": "Quiet idealist; consistent + detail-oriented; deep but steady.",
    "phlegmatic-sanguine":   "Agreeable and easy-going; helpful + pleasant; low friction.",
}

_JUNGIAN_FUNCTION_STYLES: Dict[str, str] = {
    "Extraverted Intuition (Ne)":  "Sees multiple possibilities simultaneously; loves ideation and connection.",
    "Introverted Intuition (Ni)":  "Converges on a single vision; penetrates to future implications.",
    "Extraverted Sensing (Se)":    "Fully present in the physical world; acts in real-time.",
    "Introverted Sensing (Si)":    "Stores detailed personal experience; deeply values tradition.",
    "Extraverted Thinking (Te)":   "Organises external reality logically; values efficiency and results.",
    "Introverted Thinking (Ti)":   "Builds internal logical frameworks; seeks precision and understanding.",
    "Extraverted Feeling (Fe)":    "Attunes to others' emotional states; shapes social harmony.",
    "Introverted Feeling (Fi)":    "Deep personal values; strong moral compass; authentic above all.",
}

_BIG5_LABELS: Dict[str, List[Tuple[int, str]]] = {
    "openness":          [(90, "visionary"), (75, "curious and imaginative"), (55, "moderately open"), (35, "conventional"), (0, "traditional and concrete")],
    "conscientiousness": [(90, "meticulous and disciplined"), (75, "organised and reliable"), (55, "balanced"), (35, "flexible and spontaneous"), (0, "impulsive and unstructured")],
    "extraversion":      [(90, "highly energised by people and social dominance"), (75, "sociable and outgoing"), (55, "ambiverted"), (35, "reserved"), (0, "deeply introverted")],
    "agreeableness":     [(90, "cooperative, warm, and genuinely other-focused"), (75, "agreeable and empathic"), (55, "balanced"), (35, "direct and challenging"), (0, "highly competitive and blunt")],
    "neuroticism":       [(90, "emotionally volatile and reactive"), (75, "sensitive to stress"), (55, "moderate emotional stability"), (35, "calm and composed"), (0, "highly stable")],
}

_RUNE_FATE: Dict[str, str] = {
    "Fehu":   "Born under the rune of wealth and abundance — fate favours earned reward and material mastery.",
    "Uruz":   "Born under primal strength — fate calls for endurance and the unleashing of raw power.",
    "Thurisaz":"Born under the force of conflict — fate is forged in confrontation and reactive power.",
    "Ansuz":  "Born under divine wisdom — fate runs through revelation, speech, and inspired vision.",
    "Raidho": "Born under the journey rune — fate is a road; movement and alignment are the path.",
    "Kenaz":  "Born under illumination — fate comes through knowledge, craft, and creative fire.",
    "Gebo":   "Born under sacred exchange — fate is woven into bonds, reciprocity, and honoured gifts.",
    "Wunjo":  "Born under joy — fate flows through fellowship, harmony, and authentic belonging.",
    "Hagalaz":"Born under the hailstorm — fate comes through disruption; transformation by shattering.",
    "Nauthiz":"Born under necessity — fate is shaped by constraint; strength found in hardship.",
    "Isa":    "Born under stillness — fate asks for patience; frozen potential awaiting the right moment.",
    "Jera":   "Born under the harvest — fate rewards cyclical effort; what is sown will be reaped.",
    "Eihwaz": "Born under the yew tree — fate is transformation; death and rebirth as spiritual axis.",
    "Perthro":"Born under mystery — fate is unknowable; the well holds secrets not yet surfaced.",
    "Algiz":  "Born under protection — fate is guarded; a connection to the divine shields the soul.",
    "Sowilo": "Born under the sun — fate is victory, vitality, and the clear power of aligned will.",
    "Tiwaz":  "Born under justice — fate demands honour, decisive sacrifice, and right action.",
    "Berkano":"Born under growth — fate is renewal; birth, nurture, and gentle becoming.",
    "Ehwaz":  "Born under partnership — fate runs through trust, movement, and loyal union.",
    "Mannaz": "Born under humanity — fate is the self in community; wisdom through self-knowledge.",
    "Laguz":  "Born under deep water — fate flows through emotion, intuition, and the unconscious.",
    "Ingwaz": "Born under inner fire — fate is gestation; the power that builds before it erupts.",
    "Dagaz":  "Born under the dawn — fate is breakthrough; radical clarity after enduring darkness.",
    "Othala": "Born under heritage — fate is rooted in ancestry, home, and inherited wisdom.",
}

_ARCHETYPE_NOTES: Dict[str, str] = {
    "The Magician":  "Commands transformation through knowledge and skill; keeper of secret arts.",
    "The Trickster": "Disrupts order to reveal truth; creative chaos in service of change.",
    "The Hero":      "Pursues the quest; courage and sacrifice in service of community.",
    "The Lover":     "Seeks beauty, connection, passion; attuned to the heart's call.",
    "The Ruler":     "Maintains order; claims sovereignty over domain; drives structure.",
    "The Caregiver": "Nurtures and protects; driven by love and duty to others.",
    "The Seeker":    "Restless for meaning; follows the horizon; freedom over security.",
    "The Creator":   "Makes new things; expresses inner vision; leaves something lasting.",
    "The Destroyer": "Clears what no longer serves; powerful agent of endings.",
    "The Sage":      "Seeks truth; contemplates the whole; wisdom over action.",
    "The Innocent":  "Embodies hope and optimism; seeks safety and goodness.",
    "The Jester":    "Lives in the moment; play, laughter, and lightness as spiritual practice.",
}

_D5E_STAT_PERSONALITY: Dict[str, List[Tuple[int, str]]] = {
    "charisma":     [(18, "Magnetic social presence; commands rooms and hearts"), (15, "Charming and persuasive"), (12, "Personable"), (8, "Socially reserved"), (0, "Awkward or abrasive")],
    "intelligence": [(18, "Brilliant mind; sees patterns others miss"), (15, "Sharp and analytical"), (12, "Curious and capable"), (8, "Practical over theoretical"), (0, "Impulsive; acts on instinct")],
    "wisdom":       [(18, "Deep perceptive insight; rarely deceived"), (15, "Thoughtful and attuned"), (12, "Grounded"), (8, "Distracted or naive"), (0, "Poor judgment under pressure")],
    "strength":     [(18, "Commands physical authority; presence of power"), (15, "Strong and capable"), (12, "Active and capable"), (8, "Relies on other strengths"), (0, "Physically vulnerable")],
    "dexterity":    [(18, "Graceful, agile, precise; elegant under pressure"), (15, "Nimble and quick"), (12, "Coordinated"), (8, "Careful and deliberate"), (0, "Clumsy or slow")],
    "constitution": [(18, "Iron endurance; withstands punishment others cannot"), (15, "Resilient and hardy"), (12, "Steady"), (8, "Prone to fatigue or illness"), (0, "Fragile; avoids hardship")],
}


# ---------------------------------------------------------------------------
# Profile dataclass
# ---------------------------------------------------------------------------

@dataclass
class PersonalityReport:
    """Complete calculated personality profile for a character."""

    # Core identity
    name: str = ""
    role: str = ""
    age: int = 0
    dnd_class: str = ""
    dnd_level: int = 0
    alignment: str = ""

    # Frameworks
    mbti_analysis: Dict[str, str] = field(default_factory=dict)
    enneagram_analysis: Dict[str, str] = field(default_factory=dict)
    temperament_note: str = ""
    big_five: Dict[str, Any] = field(default_factory=dict)
    cognitive_style: Dict[str, str] = field(default_factory=dict)
    emotional_intelligence: Dict[str, Any] = field(default_factory=dict)
    hexaco: Dict[str, Any] = field(default_factory=dict)

    # Norse soul
    norse_soul: Dict[str, Any] = field(default_factory=dict)
    shadow_and_light: Dict[str, str] = field(default_factory=dict)

    # Behaviour
    stress_response: Dict[str, Any] = field(default_factory=dict)
    social_power: Dict[str, Any] = field(default_factory=dict)
    combat_archetype: Dict[str, str] = field(default_factory=dict)

    # Fate
    fate_thread: Dict[str, str] = field(default_factory=dict)

    # Relationships
    relationship_patterns: Dict[str, Any] = field(default_factory=dict)
    hidden_depths: Dict[str, Any] = field(default_factory=dict)
    vulnerability_matrix: Dict[str, Any] = field(default_factory=dict)
    value_alignment: Dict[str, Any] = field(default_factory=dict)

    # Derivations
    d5e_ability_narrative: Dict[str, str] = field(default_factory=dict)
    character_arc: Dict[str, Any] = field(default_factory=dict)
    cultural_integration: Dict[str, Any] = field(default_factory=dict)

    # Meta scores
    coherence_score: int = 0          # 0-100: how well frameworks align
    coherence_notes: List[str] = field(default_factory=list)
    archetype_synthesis: str = ""     # dominant archetype label


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

class PersonalityEngine:
    """Derives a complete PersonalityReport from a character dict."""

    def analyze(self, char: Dict[str, Any], soul_layer: Optional[Any] = None) -> PersonalityReport:
        """Run full personality analysis and return a PersonalityReport."""
        report = PersonalityReport()
        try:
            identity   = _d(char, "identity")
            psych      = _d(char, "psychology")
            pers       = _d(char, "personality")
            dnd5e      = _d(char, "dnd5e")
            astrology  = _d(char, "astrology")
            backstory  = _d(char, "backstory")
            goals      = _d(char, "goals_and_motivations")
            rels       = _d(char, "relationships")
            skills     = _d(char, "skills")
            ai_beh     = _d(char, "ai_behavior")
            voice      = _d(char, "voice_and_mannerisms")
            prefs      = _d(char, "preferences")

            report.name       = str(identity.get("name", char.get("id", "Unknown")))
            report.role       = str(identity.get("role", identity.get("occupation", "")))
            report.age        = int(identity.get("age", 0) or 0)
            report.dnd_class  = str(dnd5e.get("class", ""))
            report.dnd_level  = int(dnd5e.get("level", 0) or 0)
            report.alignment  = str(pers.get("alignment", "").replace("_", " ").title())

            report.mbti_analysis        = self._mbti_analysis(psych, pers, dnd5e)
            report.enneagram_analysis   = self._enneagram_analysis(psych, pers)
            report.temperament_note     = self._temperament_note(psych)
            report.big_five             = self._big_five(psych, pers)
            report.cognitive_style      = self._cognitive_style(psych)
            report.emotional_intelligence = self._emotional_intelligence(psych)
            report.hexaco               = self._hexaco(psych)
            report.norse_soul           = self._norse_soul(char, soul_layer)
            report.shadow_and_light     = self._shadow_and_light(psych, pers)
            report.stress_response      = self._stress_response(psych, pers, ai_beh, goals)
            report.social_power         = self._social_power(char, dnd5e, pers, skills, rels)
            report.combat_archetype     = self._combat_archetype(dnd5e, psych, pers, ai_beh)
            report.fate_thread          = self._fate_thread(astrology, identity, pers)
            report.relationship_patterns = self._relationship_patterns(rels, psych, pers)
            report.hidden_depths        = self._hidden_depths(pers, goals, backstory, psych)
            report.vulnerability_matrix = self._vulnerability_matrix(psych, pers, goals, ai_beh)
            report.value_alignment      = self._value_alignment(pers, psych)
            report.d5e_ability_narrative = self._d5e_ability_narrative(dnd5e)
            report.character_arc        = self._character_arc(backstory, goals, pers, psych)
            report.cultural_integration = self._cultural_integration(identity, skills, backstory, pers)
            report.coherence_score, report.coherence_notes = self._coherence_score(psych, pers, dnd5e, rels)
            report.archetype_synthesis  = self._archetype_synthesis(psych, pers, dnd5e, identity)
        except Exception as exc:
            logger.warning("PersonalityEngine.analyze failed: %s", exc, exc_info=True)
        return report

    # ── Framework analyses ────────────────────────────────────────────────

    def _mbti_analysis(self, psych: dict, pers: dict, dnd5e: dict) -> Dict[str, str]:
        mbti = str(psych.get("myers_briggs", "")).strip().upper()
        if not mbti or mbti not in _MBTI_PROFILES:
            return {}
        p = _MBTI_PROFILES[mbti]
        extraversion = int(psych.get("extraversion", 50) or 50)
        openness     = int(psych.get("openness", 50) or 50)
        agree        = int(psych.get("agreeableness", 50) or 50)
        # Coherence check
        e_flag = "E" if "E" in mbti else "I"
        n_flag = "N" if "N" in mbti else "S"
        t_flag = "T" if "T" in mbti else "F"
        coherence_notes = []
        if e_flag == "E" and extraversion < 50:
            coherence_notes.append("MBTI type is E but Extraversion score is below 50 — possible social mask")
        if n_flag == "N" and openness < 55:
            coherence_notes.append("MBTI type is N but Openness is low — intuition may be undeveloped")
        if t_flag == "F" and agree < 50:
            coherence_notes.append("MBTI type is F but Agreeableness is low — head overrides heart")
        # Decision-making note
        j_flag = "J" if "J" in mbti else "P"
        decision_style = "Plans and closes; decides early and commits" if j_flag == "J" else "Keeps options open; adapts in real-time"
        return {
            "type": mbti,
            "title": p["title"],
            "summary": p["summary"],
            "shadow": p["shadow"],
            "decision_style": decision_style,
            "coherence_flags": "; ".join(coherence_notes) if coherence_notes else "All indicators align",
        }

    def _enneagram_analysis(self, psych: dict, pers: dict) -> Dict[str, str]:
        raw = str(psych.get("enneagram", "")).strip()
        if not raw:
            return {}
        core_digit = raw[0] if raw else ""
        wing = raw if len(raw) >= 3 else ""
        if core_digit not in _ENNEAGRAM_PROFILES:
            return {}
        p = _ENNEAGRAM_PROFILES[core_digit]
        wing_name = _WING_NAMES.get(wing, "")
        # Stress / growth direction table
        _stress = {"1":"4","2":"8","3":"9","4":"2","5":"7","6":"3","7":"1","8":"5","9":"6"}
        _growth = {"1":"7","2":"4","3":"6","4":"1","5":"8","6":"9","7":"5","8":"2","9":"3"}
        stress_type = _stress.get(core_digit, "")
        growth_type = _growth.get(core_digit, "")
        stress_note = f"Under extreme stress: takes on negative traits of Type {stress_type} ({_ENNEAGRAM_PROFILES.get(stress_type, {}).get('title', '')})" if stress_type else ""
        growth_note = f"In growth: integrates healthy traits of Type {growth_type} ({_ENNEAGRAM_PROFILES.get(growth_type, {}).get('title', '')})" if growth_type else ""
        return {
            "type": raw,
            "title": p["title"],
            "wing_name": wing_name,
            "core_drive": p["core_drive"],
            "shadow": p["shadow"],
            "stress_direction": stress_note,
            "growth_direction": growth_note,
        }

    def _temperament_note(self, psych: dict) -> str:
        raw = str(psych.get("temperament", "")).strip().lower()
        for k, v in _TEMPERAMENT.items():
            if raw == k.lower():
                return f"{raw.title()}: {v}"
        # Partial match
        for k, v in _TEMPERAMENT.items():
            if any(part in raw for part in k.lower().split("-")):
                return f"{raw.title()}: {v}"
        return raw.title() if raw else ""

    def _big_five(self, psych: dict, pers: dict) -> Dict[str, Any]:
        traits = {}
        for key in ("openness", "conscientiousness", "extraversion", "agreeableness", "neuroticism"):
            val = psych.get(key)
            if val is None:
                continue
            score = int(val)
            label = _label_from_thresholds(_BIG5_LABELS[key], score)
            bar = _score_bar(score)
            traits[key] = {"score": score, "label": label, "bar": bar}
        # Derived: dominant dimension
        if traits:
            dom = max(traits, key=lambda k: traits[k]["score"])
            traits["dominant_dimension"] = dom.replace("_", " ").title()
            # Big Five fingerprint
            traits["fingerprint"] = _big_five_fingerprint(traits)
        return traits

    def _cognitive_style(self, psych: dict) -> Dict[str, str]:
        jf = _d(psych, "jungian_functions")
        if not jf:
            return {}
        result = {}
        for role in ("dominant", "auxiliary", "tertiary", "inferior"):
            fn = str(jf.get(role, "")).strip()
            if fn:
                note = _JUNGIAN_FUNCTION_STYLES.get(fn, fn)
                result[role] = f"{fn} — {note}"
        if result:
            dom = str(jf.get("dominant", ""))
            if "Extraverted" in dom:
                result["processing_mode"] = "Outer-directed: processes by engaging the world, people, or systems."
            else:
                result["processing_mode"] = "Inner-directed: processes internally before externalising."
        return result

    def _emotional_intelligence(self, psych: dict) -> Dict[str, Any]:
        ei = _d(psych, "emotional_intelligence")
        if not ei:
            return {}
        dims = {
            "emotional_depth":      "Capacity to feel deeply and sit with complex emotions",
            "self_expression":      "Ability to express internal state outwardly",
            "vulnerability":        "Willingness to be emotionally exposed",
            "coping":               "Recovery speed and strategy after emotional events",
            "cognitive_flexibility":"Ability to hold contradictory feelings simultaneously",
            "emotional_sensitivity":"Attunement to others' emotional states",
            "impulse_control":      "Delay of emotional reaction under provocation",
            "reflective_depth":     "Tendency to examine one's own emotional processes",
        }
        result: Dict[str, Any] = {}
        scores: List[int] = []
        for key, desc in dims.items():
            val = ei.get(key)
            if val is not None:
                score = int(val)
                scores.append(score)
                result[key] = {"score": score, "bar": _score_bar(score), "desc": desc}
        if scores:
            avg = sum(scores) // len(scores)
            result["overall_eq"] = avg
            result["eq_bar"] = _score_bar(avg)
            low_keys = [k for k, v in result.items() if isinstance(v, dict) and v.get("score", 100) < 40]
            high_keys = [k for k, v in result.items() if isinstance(v, dict) and v.get("score", 0) >= 80]
            result["strengths"] = [k.replace("_", " ").title() for k in high_keys]
            result["blind_spots"] = [k.replace("_", " ").title() for k in low_keys]
        return result

    def _hexaco(self, psych: dict) -> Dict[str, Any]:
        hx = _d(psych, "hexaco_traits")
        if not hx:
            return {}
        dims = {
            "honesty_humility": "Sincere, fair, non-greedy, modest",
            "emotionality":     "Emotional depth, anxiety level, empathy",
            "extraversion":     "Social confidence, liveliness, positive self-regard",
            "agreeableness":    "Patience, flexibility, gentleness with others",
            "conscientiousness":"Diligence, perfectionism, prudence",
            "openness":         "Aesthetic sensitivity, inquisitiveness, creativity",
        }
        result: Dict[str, Any] = {}
        for key, desc in dims.items():
            val = hx.get(key)
            if val is not None:
                score = int(val)
                result[key] = {"score": score, "bar": _score_bar(score), "desc": desc}
        # Honesty-Humility as moral compass indicator
        hh = hx.get("honesty_humility")
        if hh is not None:
            hh_int = int(hh)
            if hh_int >= 80:
                result["moral_compass"] = "High integrity; genuinely averse to manipulation and greed."
            elif hh_int >= 60:
                result["moral_compass"] = "Generally honest; strategic exceptions when stakes are high."
            elif hh_int >= 40:
                result["moral_compass"] = "Pragmatic ethics; truth is instrumental."
            else:
                result["moral_compass"] = "Low honesty-humility; deception and self-interest are comfortable tools."
        return result

    def _norse_soul(self, char: dict, soul_layer: Optional[Any]) -> Dict[str, Any]:
        result: Dict[str, Any] = {}
        # Try live SoulLayer first
        if soul_layer is not None:
            try:
                hamingja = soul_layer.hamingja
                hugr     = soul_layer.hugr
                fylgja   = soul_layer.fylgja
                friction = soul_layer.friction
                result["hamingja_value"] = round(hamingja.value, 3)
                result["hamingja_label"] = hamingja.state_label
                result["hamingja_bar"]   = _score_bar(int(hamingja.value * 100))
                dom = hugr.dominant_emotion()
                result["hugr_dominant"] = f"{dom[0]} ({dom[1]:+.2f})" if dom else "Neutral"
                result["hugr_all_emotions"] = {k: round(v, 2) for k, v in hugr.emotions.items() if abs(v) > 0.05}
                result["fylgja_trauma_count"] = len(fylgja.trauma_scars)
                result["fylgja_traumas"] = fylgja.trauma_scars[-3:]
                result["fylgja_override_risk"] = friction.friction_score >= fylgja.override_threshold
                result["cognitive_friction"] = round(friction.friction_score, 2)
                result["friction_bar"] = _score_bar(int(friction.friction_score * 100))
                result["active_echoes"] = len(soul_layer.active_echoes)
                result["source"] = "live_soul_layer"
            except Exception as exc:
                logger.debug("norse_soul from SoulLayer failed: %s", exc)
                soul_layer = None

        if soul_layer is None:
            # Derive from static YAML psychology
            psych = _d(char, "psychology")
            neuro = int(psych.get("neuroticism", 50) or 50)
            extrav = int(psych.get("extraversion", 50) or 50)
            consc  = int(psych.get("conscientiousness", 50) or 50)
            # Hamingja approximation from honor_orientation
            honor = int(psych.get("honor_orientation", 50) or 50)
            hamingja_approx = min(1.0, honor / 100.0)
            if hamingja_approx >= 0.8:
                label = "blessed"
            elif hamingja_approx >= 0.6:
                label = "favored"
            elif hamingja_approx >= 0.4:
                label = "uncertain"
            elif hamingja_approx >= 0.2:
                label = "burdened"
            else:
                label = "cursed"
            result["hamingja_estimated"] = round(hamingja_approx, 2)
            result["hamingja_label"] = label
            result["hamingja_bar"] = _score_bar(int(hamingja_approx * 100))
            result["hugr_stability"] = "High" if neuro < 40 else ("Moderate" if neuro < 65 else "Low")
            result["hugr_note"] = (
                "Emotional volatility is contained; reactions are measured."
                if neuro < 40 else
                "Moderate reactivity; stress events produce visible emotional response."
                if neuro < 65 else
                "High neuroticism — inner emotional world is turbulent."
            )
            friction_approx = max(0.0, (neuro - 30) / 100.0)
            result["cognitive_friction_estimated"] = round(friction_approx, 2)
            result["friction_bar"] = _score_bar(int(friction_approx * 100))
            result["fylgja_note"] = (
                "Strong instinctive self; Fylgja is active and protective."
                if consc > 70 else
                "Fylgja drivers are present but not dominant in behavior."
            )
            result["source"] = "derived_from_psychology"
        return result

    def _shadow_and_light(self, psych: dict, pers: dict) -> Dict[str, str]:
        result: Dict[str, str] = {}
        # Pearson archetype
        archetypes = _d(psych, "archetypes")
        if archetypes:
            pearson = str(archetypes.get("pearson", ""))
            campbell = str(archetypes.get("campbell", ""))
            shadow_arch = str(archetypes.get("shadow", ""))
            if pearson:
                note = _ARCHETYPE_NOTES.get(pearson, "")
                result["light_archetype"] = f"{pearson}: {note}" if note else pearson
            if campbell:
                note = _ARCHETYPE_NOTES.get(campbell, "")
                result["mythic_role"] = f"{campbell}: {note}" if note else campbell
            if shadow_arch:
                result["shadow_archetype"] = shadow_arch
                result["shadow_integration_note"] = _shadow_integration(psych, pers, shadow_arch)
        # Virtues vs vices
        virtues = pers.get("virtues", [])
        vices   = pers.get("vices", [])
        if virtues or vices:
            vcount = len(virtues) if isinstance(virtues, list) else 1
            vccount = len(vices) if isinstance(vices, list) else 1
            total = vcount + vccount
            if total > 0:
                light_pct = int((vcount / total) * 100)
                result["virtue_vice_ratio"] = f"{light_pct}% light / {100 - light_pct}% shadow (by count)"
                result["moral_complexity"] = (
                    "Deeply complex moral landscape" if abs(light_pct - 50) < 20
                    else ("Strong virtue orientation" if light_pct > 70 else "Shadow-dominant character")
                )
        # Gene Keys
        gene_keys = _d(psych, "gene_keys")
        if gene_keys:
            shadow_gk = str(gene_keys.get("shadow", ""))
            gift_gk   = str(gene_keys.get("gift", ""))
            siddhi_gk = str(gene_keys.get("siddhi", ""))
            if shadow_gk or gift_gk:
                result["gene_key_path"] = f"Shadow: {shadow_gk} → Gift: {gift_gk} → Siddhi: {siddhi_gk}".strip(" →")
        return result

    def _stress_response(self, psych: dict, pers: dict, ai_beh: dict, goals: dict) -> Dict[str, Any]:
        result: Dict[str, Any] = {}
        coping = psych.get("coping_mechanisms", [])
        triggers = psych.get("emotional_triggers", [])
        armor = psych.get("emotional_armor", "")
        if isinstance(coping, list):
            result["coping_mechanisms"] = coping
        if isinstance(triggers, list):
            result["emotional_triggers"] = triggers
        if armor:
            result["emotional_armor"] = armor
        # AI behavior triggers
        becomes_defensive = _ensure_list(ai_beh.get("triggers", {}).get("becomes_defensive", []))
        becomes_hostile   = _ensure_list(ai_beh.get("triggers", {}).get("becomes_hostile", []))
        if becomes_defensive:
            result["defensive_triggers"] = becomes_defensive
        if becomes_hostile:
            result["hostile_triggers"] = becomes_hostile
        # Fears
        fears = _ensure_list(goals.get("fears", []))
        if fears:
            result["core_fears"] = fears
        # Neuroticism-derived stress style
        neuro = int(psych.get("neuroticism", 50) or 50)
        if neuro >= 70:
            result["stress_style"] = "High-reactivity: stress produces visible emotional shifts; coping mechanisms are frequently activated."
        elif neuro >= 45:
            result["stress_style"] = "Moderate-reactivity: stress is felt but generally managed; occasional breakthrough reactions."
        else:
            result["stress_style"] = "Low-reactivity: rarely rattled; threat responses are controlled and measured."
        # Tells under stress
        tells = _d(ai_beh, "tells")
        if tells:
            nervous_tells = _ensure_list(tells.get("nervous", []))
            if nervous_tells:
                result["stress_tells"] = nervous_tells
        return result

    def _social_power(self, char: dict, dnd5e: dict, pers: dict, skills: dict, rels: dict) -> Dict[str, Any]:
        result: Dict[str, Any] = {}
        stats = _d(dnd5e, "stats")
        charisma = int(stats.get("charisma", 10) or 10)
        intelligence = int(stats.get("intelligence", 10) or 10)
        wisdom   = int(stats.get("wisdom", 10) or 10)
        cha_mod  = (charisma - 10) // 2
        int_mod  = (intelligence - 10) // 2
        wis_mod  = (wisdom - 10) // 2
        # Count social skill proficiencies
        social_skills = {"persuasion", "deception", "intimidation", "insight", "performance"}
        profs = _ensure_list(dnd5e.get("skill_proficiencies", []))
        social_proficiencies = [s for s in profs if s.lower() in social_skills]
        social_prof_bonus = len(social_proficiencies) * 3
        # Relationship network score
        allies  = _ensure_list(rels.get("allies", []))
        enemies = _ensure_list(rels.get("enemies", []))
        network_score = len(allies) * 5 - len(enemies) * 3
        # Base social power formula
        raw_score = 50 + (cha_mod * 8) + (int_mod * 3) + (wis_mod * 2) + social_prof_bonus + network_score
        social_score = max(0, min(100, raw_score))
        result["social_power_score"] = social_score
        result["social_power_bar"]   = _score_bar(social_score)
        result["charisma_modifier"]  = f"+{cha_mod}" if cha_mod >= 0 else str(cha_mod)
        result["social_proficiencies"] = social_proficiencies
        result["ally_count"]  = len(allies)
        result["enemy_count"] = len(enemies)
        # Persuasion vs intimidation dominance
        psych = _d(char, "psychology")
        agree = int(psych.get("agreeableness", 50) or 50)
        result["influence_style"] = (
            "Charm and rapport (high agreeableness + charisma)" if agree >= 65 and charisma >= 15
            else "Logic and authority (intelligence-led influence)" if intelligence >= 15
            else "Respect through competence and demonstrated strength"
        )
        # Power tier
        if social_score >= 80:
            result["power_tier"] = "Elite social operator"
        elif social_score >= 65:
            result["power_tier"] = "Highly capable in social domains"
        elif social_score >= 50:
            result["power_tier"] = "Competent and functional"
        elif social_score >= 35:
            result["power_tier"] = "Limited social reach"
        else:
            result["power_tier"] = "Socially marginal"
        return result

    def _combat_archetype(self, dnd5e: dict, psych: dict, pers: dict, ai_beh: dict) -> Dict[str, str]:
        result: Dict[str, str] = {}
        cls     = str(dnd5e.get("class", "")).lower()
        subcls  = str(dnd5e.get("subclass", "")).lower()
        level   = int(dnd5e.get("level", 1) or 1)
        stats   = _d(dnd5e, "stats")
        str_s   = int(stats.get("strength", 10) or 10)
        dex_s   = int(stats.get("dexterity", 10) or 10)
        int_s   = int(stats.get("intelligence", 10) or 10)
        cha_s   = int(stats.get("charisma", 10) or 10)
        con_s   = int(stats.get("constitution", 10) or 10)
        dominant_stat = max(
            ("strength", str_s), ("dexterity", dex_s), ("intelligence", int_s),
            ("charisma", cha_s), ("constitution", con_s),
            key=lambda x: x[1]
        )[0]
        conf_style = str(ai_beh.get("conflict_style", pers.get("conflict_style", "")))
        # Combat identity
        if cls in ("rogue", "ranger", "monk"):
            result["combat_identity"] = "Precision striker — speed, positioning, and targeted elimination."
        elif cls in ("fighter", "barbarian", "paladin"):
            result["combat_identity"] = "Front-line combatant — durability, sustained pressure, direct engagement."
        elif cls in ("wizard", "sorcerer", "warlock"):
            result["combat_identity"] = "Arcane artillery — keeps range, concentrates devastating effects."
        elif cls in ("druid", "cleric"):
            result["combat_identity"] = "Adaptive support — battlefield control and healing as primary role."
        elif cls in ("bard",):
            result["combat_identity"] = "Charisma combatant — debuffs, inspiration, and social manipulation in combat."
        else:
            result["combat_identity"] = "Unconventional combatant — class suggests improvisation."
        result["dominant_stat"]     = dominant_stat.title()
        result["conflict_style"]    = conf_style[:200] if conf_style else "Unknown"
        result["class_subclass"]    = f"{cls.title()} ({subcls.title()})" if subcls else cls.title()
        result["level_assessment"]  = _level_assessment(level)
        if subcls:
            result["subclass_note"] = _subclass_note(subcls)
        return result

    def _fate_thread(self, astrology: dict, identity: dict, pers: dict) -> Dict[str, str]:
        result: Dict[str, str] = {}
        birth_rune = str(astrology.get("birth_rune", "")).strip()
        if birth_rune and birth_rune in _RUNE_FATE:
            result["birth_rune"]   = birth_rune
            result["rune_destiny"] = _RUNE_FATE[birth_rune]
        sun  = str(astrology.get("sun_sign", "")).strip()
        moon = str(astrology.get("moon_sign", "")).strip()
        rise = str(astrology.get("rising_sign", "")).strip()
        if sun or moon or rise:
            result["astro_signature"] = f"☉ {sun}  ☽ {moon}  ↑ {rise}".strip()
            result["astro_note"]      = _astro_note(sun, moon, rise)
        hd = _d(astrology, "human_design")
        if hd:
            hd_type    = str(hd.get("type", ""))
            authority  = str(hd.get("authority", ""))
            profile    = str(hd.get("profile", ""))
            result["human_design"] = f"{hd_type} — {authority} authority — Profile {profile}".strip(" —")
        chinese = str(astrology.get("chinese_zodiac", ""))
        element = str(astrology.get("chinese_element", ""))
        if chinese:
            result["chinese_zodiac"] = f"{chinese} ({element} element)" if element else chinese
        deity = str(identity.get("patron_deity", pers.get("patron_deity", ""))).strip()
        if deity:
            result["patron_deity"] = deity
            result["divine_alignment"] = _deity_alignment(deity)
        return result

    def _relationship_patterns(self, rels: dict, psych: dict, pers: dict) -> Dict[str, Any]:
        result: Dict[str, Any] = {}
        attach = str(psych.get("attachment_style", "")).strip()
        if attach:
            result["attachment_style"] = attach
            result["attachment_interpretation"] = _attachment_note(attach)
        trust = str(pers.get("trust_threshold", psych.get("trust_threshold", ""))).strip()
        if trust:
            result["trust_threshold"] = trust[:160]
        loyalty = str(pers.get("loyalty_nature", "")).strip()
        if loyalty:
            result["loyalty_pattern"] = loyalty[:160]
        allies  = _ensure_list(rels.get("allies", []))
        enemies = _ensure_list(rels.get("enemies", []))
        complicated = _ensure_list(rels.get("complicated", []))
        family  = _ensure_list(rels.get("family", []))
        result["ally_count"]       = len(allies)
        result["enemy_count"]      = len(enemies)
        result["family_count"]     = len(family)
        result["complications"]    = len(complicated)
        result["network_complexity"] = _network_complexity(allies, enemies, complicated, family)
        # Romance style
        rom = str(rels.get("romantic_interests", "")).strip()
        if rom:
            result["romantic_summary"] = rom[:200]
        return result

    def _hidden_depths(self, pers: dict, goals: dict, backstory: dict, psych: dict) -> Dict[str, Any]:
        result: Dict[str, Any] = {}
        secrets = _ensure_list(goals.get("secrets", []))
        if secrets:
            result["secret_count"]   = len(secrets)
            result["secret_preview"] = [str(s)[:80] for s in secrets[:3]]
        hidden = str(pers.get("hidden_depths", psych.get("hidden_depths", ""))).strip()
        if hidden:
            result["hidden_depths_text"] = hidden[:300]
        die_for  = str(goals.get("what_they_would_die_for", "")).strip()
        kill_for = str(goals.get("what_they_would_kill_for", "")).strip()
        need     = str(goals.get("driving_need", "")).strip()
        if die_for:
            result["would_die_for"]  = die_for[:120]
        if kill_for:
            result["would_kill_for"] = kill_for[:120]
        if need:
            result["driving_need"]   = need[:200]
        # Depth score: more secrets + deeper hidden text = higher score
        depth_score = min(100, len(secrets) * 12 + (40 if hidden else 0) + (20 if need else 0))
        result["depth_score"] = depth_score
        result["depth_bar"]   = _score_bar(depth_score)
        return result

    def _vulnerability_matrix(self, psych: dict, pers: dict, goals: dict, ai_beh: dict) -> Dict[str, Any]:
        result: Dict[str, Any] = {}
        fears    = _ensure_list(goals.get("fears", []))
        flaws    = _ensure_list(pers.get("flaws", []))
        triggers = _ensure_list(psych.get("emotional_triggers", []))
        vulnerabilities = _ensure_list(goals.get("vulnerabilities", _d(pers, "vulnerabilities")))
        dsm = _ensure_list(_d(psych, "dsm_traits"))
        if fears:
            result["fears"] = [str(f)[:80] for f in fears[:5]]
        if flaws:
            result["flaws"] = [str(f)[:80] for f in flaws[:5]]
        if triggers:
            result["emotional_triggers"] = [str(t)[:80] for t in triggers[:5]]
        if vulnerabilities:
            result["specific_vulnerabilities"] = [str(v)[:80] for v in vulnerabilities[:5]]
        if dsm:
            result["clinical_markers"] = [str(d)[:80] for d in dsm[:3]]
        vuln_score = min(100, len(fears) * 8 + len(flaws) * 8 + len(triggers) * 6 + len(dsm) * 10)
        result["vulnerability_score"] = vuln_score
        result["vulnerability_bar"]   = _score_bar(vuln_score)
        neuro = int(psych.get("neuroticism", 50) or 50)
        result["emotional_exposure"] = (
            "High: emotional wounds are close to the surface"    if neuro >= 65
            else "Moderate: stress-dependent emotional exposure" if neuro >= 45
            else "Low: well-armoured against emotional intrusion"
        )
        return result

    def _value_alignment(self, pers: dict, psych: dict) -> Dict[str, Any]:
        result: Dict[str, Any] = {}
        ideals  = _ensure_list(pers.get("ideals", []))
        virtues = _ensure_list(pers.get("virtues", []))
        vices   = _ensure_list(pers.get("vices", []))
        flaws   = _ensure_list(pers.get("flaws", []))
        if ideals:
            result["stated_ideals"] = [str(i)[:80] for i in ideals[:3]]
        if virtues:
            result["demonstrated_virtues"] = [str(v)[:80] for v in virtues[:3]]
        if vices:
            result["active_vices"] = [str(v)[:80] for v in vices[:3]]
        # Alignment note
        align = str(pers.get("alignment", "")).strip().lower().replace("_", " ")
        if align:
            result["alignment_interpretation"] = _alignment_note(align)
        # Coherence between stated ideals and vices
        if ideals and vices:
            result["value_tension"] = (
                "Significant moral contradiction: stated ideals pull against active vices — creates compelling inner conflict."
                if vices else "Values and behaviour appear broadly consistent."
            )
        return result

    def _d5e_ability_narrative(self, dnd5e: dict) -> Dict[str, str]:
        stats = _d(dnd5e, "stats")
        if not stats:
            return {}
        result: Dict[str, str] = {}
        for stat in ("strength", "dexterity", "constitution", "intelligence", "wisdom", "charisma"):
            val = stats.get(stat)
            if val is None:
                continue
            score = int(val)
            label = _label_from_thresholds(_D5E_STAT_PERSONALITY[stat], score)
            mod = (score - 10) // 2
            sign = "+" if mod >= 0 else ""
            result[stat] = f"{score} ({sign}{mod}) — {label}"
        return result

    def _character_arc(self, backstory: dict, goals: dict, pers: dict, psych: dict) -> Dict[str, Any]:
        result: Dict[str, Any] = {}
        events = _ensure_list(backstory.get("significant_events", []))
        turning = str(backstory.get("turning_point", "")).strip()
        regrets = _ensure_list(backstory.get("regrets", []))
        current = str(backstory.get("current_situation", "")).strip()
        lt_goals = _ensure_list(goals.get("long_term", []))
        st_goals = _ensure_list(goals.get("short_term", []))
        if events:
            result["formative_events_count"] = len(events)
        if turning:
            result["turning_point"] = turning[:200]
        if regrets:
            result["regrets"] = [str(r)[:80] for r in regrets[:3]]
            result["shadow_wounds"] = f"{len(regrets)} unresolved regret(s) — these shape avoidance patterns and defensive behaviour."
        if current:
            result["current_situation"] = current[:200]
        if lt_goals:
            result["long_term_goals"] = [str(g)[:80] for g in lt_goals[:3]]
        if st_goals:
            result["immediate_goals"] = [str(g)[:80] for g in st_goals[:3]]
        # Arc stage derivation
        friction_est = max(0.0, (int(psych.get("neuroticism", 40) or 40) - 30) / 100.0)
        regret_weight = min(1.0, len(regrets) * 0.25)
        arc_score = int((friction_est + regret_weight) * 50)
        if arc_score < 20:
            result["arc_stage"] = "Integration — character has largely made peace with their history."
        elif arc_score < 40:
            result["arc_stage"] = "Consolidation — growth is ongoing; key wounds are being processed."
        elif arc_score < 60:
            result["arc_stage"] = "Active tension — formative conflicts are unresolved and affecting present behaviour."
        else:
            result["arc_stage"] = "Crisis potential — shadow material is close to the surface; breakthrough or breakdown imminent."
        return result

    def _cultural_integration(self, identity: dict, skills: dict, backstory: dict, pers: dict) -> Dict[str, Any]:
        result: Dict[str, Any] = {}
        languages = _ensure_list(identity.get("languages", []))
        result["languages"] = languages
        result["language_count"] = len(languages)
        cultural_exposure = _ensure_list(backstory.get("significant_events", []))
        adaptable = any("adapt" in str(t).lower() for t in _ensure_list(pers.get("traits", [])))
        # Score
        lang_score   = min(60, len(languages) * 10)
        adapt_bonus  = 20 if adaptable else 0
        event_bonus  = min(20, len(cultural_exposure) * 4)
        ci_score     = lang_score + adapt_bonus + event_bonus
        result["cultural_integration_score"] = min(100, ci_score)
        result["cultural_bar"] = _score_bar(min(100, ci_score))
        if ci_score >= 75:
            result["cultural_note"] = "Cross-cultural master; fluid and natural across multiple societies."
        elif ci_score >= 50:
            result["cultural_note"] = "Highly capable; navigates different cultures with deliberate skill."
        elif ci_score >= 30:
            result["cultural_note"] = "Functional across cultures; some rough edges."
        else:
            result["cultural_note"] = "Culturally rooted; limited experience outside home context."
        return result

    def _coherence_score(self, psych: dict, pers: dict, dnd5e: dict, rels: dict) -> Tuple[int, List[str]]:
        """Measure how consistently all psychological frameworks agree."""
        notes: List[str] = []
        score = 70  # start at 70 (most characters are reasonably coherent)
        mbti = str(psych.get("myers_briggs", "")).upper()
        extrav = int(psych.get("extraversion", 50) or 50)
        openness = int(psych.get("openness", 50) or 50)
        agree = int(psych.get("agreeableness", 50) or 50)
        consc = int(psych.get("conscientiousness", 50) or 50)
        neuro = int(psych.get("neuroticism", 50) or 50)
        # MBTI/Big Five coherence
        if "E" in mbti and extrav >= 65:
            score += 4; notes.append("MBTI Extraversion aligns with Big Five score")
        elif "I" in mbti and extrav <= 40:
            score += 4; notes.append("MBTI Introversion aligns with Big Five score")
        elif mbti and abs(extrav - 50) < 15:
            notes.append("Ambiverted score; MBTI E/I may overstate the dimension")
        if "N" in mbti and openness >= 65:
            score += 3; notes.append("MBTI Intuition aligns with high Openness")
        if "F" in mbti and agree >= 65:
            score += 3; notes.append("MBTI Feeling aligns with high Agreeableness")
        if "T" in mbti and agree <= 45:
            score += 3; notes.append("MBTI Thinking aligns with lower Agreeableness")
        # Enneagram coherence
        enneagram = str(psych.get("enneagram", ""))[0:1]
        if enneagram == "3" and extrav >= 65:
            score += 4; notes.append("Type 3 Achiever aligns with high Extraversion")
        if enneagram == "5" and extrav <= 40:
            score += 4; notes.append("Type 5 Investigator aligns with lower Extraversion")
        if enneagram == "1" and consc >= 70:
            score += 3; notes.append("Type 1 Reformer aligns with high Conscientiousness")
        # D&D class coherence
        cls = str(dnd5e.get("class", "")).lower()
        stats = _d(dnd5e, "stats")
        cha = int(stats.get("charisma", 10) or 10)
        if cls in ("bard", "sorcerer", "paladin") and cha >= 15:
            score += 4; notes.append(f"{cls.title()} class aligns with high Charisma ({cha})")
        if cls in ("rogue",) and "N" in mbti:
            score += 3; notes.append("Rogue class aligns with MBTI Intuition — adaptive and calculating")
        # Clamp
        score = max(30, min(100, score))
        return score, notes

    def _archetype_synthesis(self, psych: dict, pers: dict, dnd5e: dict, identity: dict) -> str:
        archetypes_data = _d(psych, "archetypes")
        pearson = str(archetypes_data.get("pearson", "")) if archetypes_data else ""
        campbell = str(archetypes_data.get("campbell", "")) if archetypes_data else ""
        enneagram = str(psych.get("enneagram", ""))[0:1]
        mbti = str(psych.get("myers_briggs", "")).upper()
        cls  = str(dnd5e.get("class", "")).lower()
        role = str(identity.get("role", "")).lower()
        # Build synthesis from all available signals
        parts: List[str] = []
        if pearson:
            parts.append(pearson)
        if campbell and campbell != pearson:
            parts.append(campbell)
        if enneagram:
            enn_title = _ENNEAGRAM_PROFILES.get(enneagram, {}).get("title", "")
            if enn_title:
                parts.append(enn_title)
        if mbti in _MBTI_PROFILES:
            parts.append(_MBTI_PROFILES[mbti]["title"])
        if not parts:
            # Fallback from class/role
            archetype_map = {
                "rogue": "The Trickster", "fighter": "The Hero", "wizard": "The Sage",
                "bard": "The Jester", "paladin": "The Ruler", "ranger": "The Seeker",
                "cleric": "The Caregiver", "druid": "The Creator", "barbarian": "The Destroyer",
                "captain": "The Ruler", "merchant": "The Magician", "skald": "The Jester",
                "jarl": "The Ruler", "huskarl": "The Hero",
            }
            for key in [cls, role]:
                if key in archetype_map:
                    parts.append(archetype_map[key]); break
        # Synthesise into one statement
        if len(parts) >= 2:
            return f"Primary: {parts[0]}. Secondary resonance: {', '.join(parts[1:3])}. This character's dominant mode is {parts[0].lower()} energy — {_ARCHETYPE_NOTES.get(parts[0], 'complex and layered')}."
        elif parts:
            return f"{parts[0]}: {_ARCHETYPE_NOTES.get(parts[0], 'complex and multi-faceted character energy.')}"
        return "Archetype data insufficient — profile emerges through play."


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _d(obj: Any, key: str) -> dict:
    """Safe nested dict access."""
    if not isinstance(obj, dict):
        return {}
    result = obj.get(key, {})
    return result if isinstance(result, dict) else {}


def _ensure_list(val: Any) -> List[Any]:
    if isinstance(val, list):
        return val
    if val:
        return [val]
    return []


def _label_from_thresholds(thresholds: List[Tuple[int, str]], score: int) -> str:
    for threshold, label in sorted(thresholds, reverse=True):
        if score >= threshold:
            return label
    return thresholds[-1][1]


def _score_bar(score: int, width: int = 20) -> str:
    """Return a Unicode progress bar string for a 0-100 score."""
    score = max(0, min(100, score))
    filled = int(round(score / 100 * width))
    empty  = width - filled
    return "█" * filled + "░" * empty + f" {score}"


def _big_five_fingerprint(traits: dict) -> str:
    """Generate a one-line Big Five fingerprint."""
    letters: List[str] = []
    for key, abbr, threshold in [
        ("openness", "O", 60), ("conscientiousness", "C", 60),
        ("extraversion", "E", 55), ("agreeableness", "A", 60), ("neuroticism", "N", 50),
    ]:
        if key in traits:
            score = traits[key].get("score", 50)
            letters.append(abbr.upper() if score >= threshold else abbr.lower())
    return "".join(letters)


def _level_assessment(level: int) -> str:
    if level >= 17:
        return "Legendary tier — forces of the world bend around this character."
    if level >= 11:
        return "Powerful — commands respect; capable of shaping regional events."
    if level >= 7:
        return "Established — seasoned and skilled; a notable figure in their world."
    if level >= 4:
        return "Rising — past the raw recruit stage; building toward mastery."
    return "Novice — early in their path; core identity still forming."


def _subclass_note(subclass: str) -> str:
    notes = {
        "mastermind": "Mastermind Rogue — manipulates information and people as weapons; operates through proxies.",
        "thief": "Thief Rogue — speed, sleight of hand, opportunistic action.",
        "assassin": "Assassin Rogue — preparation and the decisive first strike.",
        "champion": "Champion Fighter — physical excellence as the core of combat identity.",
        "battle master": "Battle Master Fighter — tactical control; reads the fight and adjusts.",
        "evocation": "Evocation Wizard — raw destructive power; force over subtlety.",
        "oath of vengeance": "Oath of Vengeance Paladin — relentless pursuit; nemesis archetype.",
        "totem warrior": "Totem Warrior Barbarian — spiritual connection to natural forces.",
    }
    for k, v in notes.items():
        if k in subclass.lower():
            return v
    return subclass.replace("-", " ").replace("_", " ").title()


def _shadow_integration(psych: dict, pers: dict, shadow_arch: str) -> str:
    neuro = int(psych.get("neuroticism", 50) or 50)
    reflect = int(_d(psych, "emotional_intelligence").get("reflective_depth", 50) or 50)
    integration_score = max(0, min(100, (100 - neuro) // 2 + reflect // 2))
    if integration_score >= 70:
        return f"Well-integrated shadow ({shadow_arch}): the character is largely aware of their darker drives."
    elif integration_score >= 45:
        return f"Partial integration ({shadow_arch}): shadow surfaces under stress; mostly controlled."
    else:
        return f"Unintegrated shadow ({shadow_arch}): these drives operate below conscious awareness; potentially volatile."


def _astro_note(sun: str, moon: str, rise: str) -> str:
    parts: List[str] = []
    sun_notes = {
        "Aries": "Sun Aries: bold, pioneering, direct.", "Taurus": "Sun Taurus: patient, sensual, stubborn.",
        "Gemini": "Sun Gemini: quick-witted, adaptable, dual-natured.", "Cancer": "Sun Cancer: nurturing, emotionally deep.",
        "Leo": "Sun Leo: magnetic, proud, generous.", "Virgo": "Sun Virgo: precise, analytical, quietly powerful.",
        "Libra": "Sun Libra: balanced, charming, diplomatically strategic.", "Scorpio": "Sun Scorpio: intense, transformative, secretive.",
        "Sagittarius": "Sun Sagittarius: expansive, free, philosophical.", "Capricorn": "Sun Capricorn: disciplined, ambitious, enduring.",
        "Aquarius": "Sun Aquarius: visionary, unconventional, detached.", "Pisces": "Sun Pisces: empathic, dreamy, boundary-dissolving.",
    }
    rise_notes = {
        "Leo": "Leo Rising: projects confidence and warmth; commands attention.",
        "Scorpio": "Scorpio Rising: projects intensity and depth; others feel seen.",
        "Aquarius": "Aquarius Rising: projects uniqueness; operates outside convention.",
        "Libra": "Libra Rising: projects charm and elegance; socially magnetic.",
        "Virgo": "Virgo Rising: projects precision and reliability; trustworthy.",
        "Aries": "Aries Rising: projects boldness and energy; leads with action.",
    }
    if sun in sun_notes:
        parts.append(sun_notes[sun])
    if rise in rise_notes:
        parts.append(rise_notes[rise])
    if not parts and (sun or moon or rise):
        parts.append(f"☉ {sun} ☽ {moon} ↑ {rise}")
    return " ".join(parts)


def _deity_alignment(deity: str) -> str:
    deity_lower = deity.lower()
    map_ = {
        "odin":   "The Allfather's devotee — wisdom, sacrifice, and the relentless pursuit of truth.",
        "loki":   "Loki's chosen — chaos as creative force; the gift of crossing boundaries.",
        "thor":   "Thor's warrior — strength, protection, duty, and the storm.",
        "freyja": "Freyja's devotee — love, beauty, battle-magic, and fierce independence.",
        "freyr":  "Freyr's follower — fertility, abundance, and the joy of the earth.",
        "tyr":    "Tyr's follower — justice, law, sacrifice of the self for the greater good.",
        "hel":    "Hel's wanderer — the threshold between life and death; comfort with endings.",
        "skadi":  "Skadi's child — isolation, winter, self-sufficiency, and the hunt.",
        "mimir":  "Mimir's keeper — counsel, deep wisdom, and the price of knowing.",
    }
    for k, v in map_.items():
        if k in deity_lower:
            return v
    return f"Devoted to {deity}."


def _attachment_note(style: str) -> str:
    style_lower = style.lower()
    if "secure" in style_lower and "earned" not in style_lower:
        return "Comfortable with intimacy and independence; trusts and is trustworthy."
    if "earned secure" in style_lower:
        return "Worked toward security; still carries echoes of early insecurity; relationships require maintenance."
    if "avoidant" in style_lower:
        return "Prioritises self-reliance; unconsciously withdraws when intimacy deepens."
    if "anxious" in style_lower or "preoccupied" in style_lower:
        return "Seeks closeness intensely; fears abandonment; monitors relationships closely."
    if "disorganised" in style_lower or "fearful" in style_lower:
        return "Deep ambivalence around intimacy; desires connection but fears its cost."
    return style


def _network_complexity(allies: list, enemies: list, complicated: list, family: list) -> str:
    total = len(allies) + len(enemies) + len(complicated) + len(family)
    if total >= 12:
        return "Vast and intricate — navigating this network requires constant social intelligence."
    if total >= 7:
        return "Rich and layered — multiple meaningful bonds with competing loyalties."
    if total >= 4:
        return "Moderate — a core group of relationships that define the character's world."
    if total >= 1:
        return "Small and deliberately chosen — quality over breadth."
    return "Isolated — no significant named relationships."


def _alignment_note(align: str) -> str:
    notes = {
        "lawful good":     "Principled protector — values justice and order as paths to goodness.",
        "neutral good":    "Pragmatic altruist — does good without rigid adherence to law or freedom.",
        "chaotic good":    "Free-spirited hero — compassionate but untethered by convention.",
        "lawful neutral":  "The code before the cause — rules are the structure of civilisation.",
        "true neutral":    "Balance as philosophy — refuses to tip any scale.",
        "chaotic neutral": "The self is the only law — freedom, impulse, and authenticity.",
        "lawful evil":     "Order weaponised — uses structure to dominate and control.",
        "neutral evil":    "Self-interest without disguise — uses any means available.",
        "chaotic evil":    "Destruction as expression — pure appetite, no restraint.",
    }
    for k, v in notes.items():
        if k in align:
            return v
    return align


# ---------------------------------------------------------------------------
# Public AI-integration helpers
# ---------------------------------------------------------------------------

def get_personality_ai_block(char: Dict[str, Any], soul_layer: Optional[Any] = None) -> str:
    """Return a structured, LLM-optimized personality block for AI prompts.

    Intended for single-character focused dialogue (build_character_voice_prompt).
    Returns ~20-30 lines of dense structured text covering all key dimensions.
    Returns empty string on any failure — never raises.
    """
    try:
        r = PersonalityEngine().analyze(char, soul_layer=soul_layer)
        lines: List[str] = ["=== DEEP PERSONALITY PROFILE ==="]

        # ── Frameworks ──────────────────────────────────────────────────────
        fw_parts: List[str] = []
        m = r.mbti_analysis
        e = r.enneagram_analysis
        if m.get("type"):
            fw_parts.append(f"MBTI {m['type']} — {m.get('title', '')}")
        if e.get("type"):
            wn = f" ({e['wing_name']})" if e.get("wing_name") else ""
            fw_parts.append(f"Enneagram {e['type']}{wn} — {e.get('title', '')}")
        if r.temperament_note:
            fw_parts.append(r.temperament_note.split(":")[0].strip())
        if fw_parts:
            lines.append(" | ".join(fw_parts))

        # ── Core drive / shadow / growth ────────────────────────────────────
        if e.get("core_drive"):
            lines.append(f"Core Drive: {e['core_drive']}")
        if e.get("shadow"):
            lines.append(f"Shadow: {e['shadow']}")
        if e.get("stress_direction"):
            lines.append(f"Stress direction: {e['stress_direction']}")
        if e.get("growth_direction"):
            lines.append(f"Growth direction: {e['growth_direction']}")
        if m.get("decision_style"):
            lines.append(f"Decision style: {m['decision_style']}")
        if m.get("shadow"):
            lines.append(f"MBTI shadow: {m['shadow']}")

        # ── Big Five summary ─────────────────────────────────────────────────
        b5 = r.big_five
        if b5:
            scores = []
            for k in ("openness", "conscientiousness", "extraversion", "agreeableness", "neuroticism"):
                d = b5.get(k)
                if isinstance(d, dict):
                    scores.append(f"{k[0].upper()}:{d['score']}")
            dom = b5.get("dominant_dimension", "")
            fp = b5.get("fingerprint", "")
            suffix = f" — Dominant: {dom}" if dom else ""
            fp_suffix = f" | Fingerprint: {fp}" if fp else ""
            if scores:
                lines.append(f"Big Five: {' '.join(scores)}{suffix}{fp_suffix}")

        # ── EI ───────────────────────────────────────────────────────────────
        ei = r.emotional_intelligence
        if ei:
            ei_parts: List[str] = []
            if ei.get("overall_eq") is not None:
                ei_parts.append(f"EQ {ei['overall_eq']}/100")
            s = ei.get("strengths", [])
            b = ei.get("blind_spots", [])
            if s:
                ei_parts.append(f"Strengths: {', '.join(s[:2])}")
            if b:
                ei_parts.append(f"Blind Spots: {', '.join(b[:2])}")
            if ei_parts:
                lines.append(f"Emotional Intelligence: {' | '.join(ei_parts)}")

        # ── Norse soul ───────────────────────────────────────────────────────
        ns = r.norse_soul
        if ns:
            ns_parts: List[str] = []
            h_label = ns.get("hamingja_label", "")
            h_val = ns.get("hamingja_value") if ns.get("hamingja_value") is not None else ns.get("hamingja_estimated", "")
            if h_label:
                ns_parts.append(f"Hamingja: {h_label} ({h_val})")
            if ns.get("hugr_dominant"):
                ns_parts.append(f"Hugr dominant: {ns['hugr_dominant']}")
            if ns.get("hugr_note"):
                ns_parts.append(ns["hugr_note"])
            elif ns.get("hugr_stability"):
                ns_parts.append(f"Emotional stability: {ns['hugr_stability']}")
            if ns.get("fylgja_override_risk"):
                ns_parts.append("Fylgja override risk: HIGH — instinct may override will")
            if ns_parts:
                lines.append(f"Norse Soul: {' | '.join(ns_parts)}")

        # ── HEXACO moral compass ──────────────────────────────────────────────
        hx = r.hexaco
        if hx and hx.get("moral_compass"):
            lines.append(f"Moral Compass: {hx['moral_compass']}")

        # ── Attachment & social power ────────────────────────────────────────
        rp = r.relationship_patterns
        if rp.get("attachment_style"):
            interp = rp.get("attachment_interpretation", "")
            lines.append(f"Attachment: {rp['attachment_style']}" + (f" — {interp}" if interp else ""))
        if rp.get("trust_threshold"):
            lines.append(f"Trust threshold: {rp['trust_threshold']}")
        if rp.get("loyalty_pattern"):
            lines.append(f"Loyalty: {rp['loyalty_pattern']}")

        sp = r.social_power
        if sp.get("social_power_score") is not None:
            lines.append(
                f"Social Power: {sp['social_power_score']}/100 — {sp.get('power_tier', '')} — "
                f"Influence via: {sp.get('influence_style', '')}"
            )

        # ── Stress response ──────────────────────────────────────────────────
        sr = r.stress_response
        if sr.get("stress_style"):
            lines.append(f"Stress Style: {sr['stress_style']}")
        if sr.get("emotional_armor"):
            lines.append(f"Emotional Armor: {sr['emotional_armor']}")
        if sr.get("emotional_triggers"):
            lines.append(f"Triggers: {', '.join(str(x) for x in sr['emotional_triggers'][:4])}")
        if sr.get("core_fears"):
            lines.append(f"Core Fears: {', '.join(str(x) for x in sr['core_fears'][:3])}")
        if sr.get("defensive_triggers"):
            lines.append(f"Becomes Defensive: {', '.join(str(x) for x in sr['defensive_triggers'][:3])}")
        if sr.get("hostile_triggers"):
            lines.append(f"Becomes Hostile: {', '.join(str(x) for x in sr['hostile_triggers'][:3])}")
        if sr.get("stress_tells"):
            lines.append(f"Stress Tells: {', '.join(str(x) for x in sr['stress_tells'][:3])}")

        # ── Hidden depths & values ────────────────────────────────────────────
        hd = r.hidden_depths
        if hd.get("driving_need"):
            lines.append(f"Driving Need: {hd['driving_need']}")
        if hd.get("would_die_for"):
            lines.append(f"Would die for: {hd['would_die_for']}")
        if hd.get("would_kill_for"):
            lines.append(f"Would kill for: {hd['would_kill_for']}")
        if hd.get("hidden_depths_text"):
            lines.append(f"Hidden Depths: {hd['hidden_depths_text'][:200]}")

        va = r.value_alignment
        val_parts: List[str] = []
        if va.get("demonstrated_virtues"):
            val_parts.append(f"Virtues: {', '.join(str(x) for x in va['demonstrated_virtues'][:3])}")
        if va.get("active_vices"):
            val_parts.append(f"Vices: {', '.join(str(x) for x in va['active_vices'][:2])}")
        if val_parts:
            lines.append(" | ".join(val_parts))
        if va.get("alignment_interpretation"):
            lines.append(f"Moral alignment: {va['alignment_interpretation']}")

        # ── Shadow & light ────────────────────────────────────────────────────
        sl = r.shadow_and_light
        if sl.get("light_archetype"):
            lines.append(f"Light Archetype: {sl['light_archetype']}")
        if sl.get("shadow_archetype") and sl.get("shadow_integration_note"):
            lines.append(f"Shadow: {sl['shadow_archetype']} — {sl['shadow_integration_note']}")
        if sl.get("gene_key_path"):
            lines.append(f"Gene Key Path: {sl['gene_key_path']}")

        # ── Fate ─────────────────────────────────────────────────────────────
        ft = r.fate_thread
        if ft.get("rune_destiny"):
            lines.append(f"Fate/Rune: {ft['rune_destiny']}")
        if ft.get("astro_note"):
            lines.append(f"Astrological character: {ft['astro_note']}")
        if ft.get("patron_deity"):
            da = ft.get("divine_alignment", "")
            lines.append(f"Patron: {ft['patron_deity']}" + (f" — {da}" if da else ""))

        # ── Combat ────────────────────────────────────────────────────────────
        ca = r.combat_archetype
        if ca.get("combat_identity"):
            lines.append(f"Combat Identity: {ca['combat_identity']}")
        if ca.get("conflict_style"):
            lines.append(f"Conflict Style: {ca['conflict_style']}")

        # ── Arc & archetype synthesis ─────────────────────────────────────────
        arc = r.character_arc
        if arc.get("arc_stage"):
            lines.append(f"Character Arc Stage: {arc['arc_stage']}")
        if arc.get("shadow_wounds"):
            lines.append(f"Shadow Wounds: {arc['shadow_wounds']}")
        if r.archetype_synthesis:
            lines.append(f"Archetype: {r.archetype_synthesis}")

        # ── AI directive ──────────────────────────────────────────────────────
        lines.append("")
        lines.append(
            "AI ROLEPLAY DIRECTIVE: Embody this character through their core drive and decision style. "
            "Let Enneagram stress-direction traits emerge under pressure — show it in word choice and reaction speed. "
            "Their shadow surfaces when vulnerability is threatened; do not resolve it artificially. "
            "Honour their attachment style in close scenes — trust is extended according to that pattern. "
            "Virtues and vices create genuine inner tension; let both appear. "
            "Their fate thread and patron deity colour how they interpret misfortune and luck. "
            "Do NOT have them act out of character unless driven by the above mechanics."
        )

        return "\n".join(lines)

    except Exception as exc:
        logger.debug("get_personality_ai_block failed: %s", exc)
        return ""


def get_personality_compact_block(char: Dict[str, Any]) -> str:
    """Return a compact single-line personality summary for multi-NPC AI prompts.

    Intended for build_npc_context() where multiple NPCs share context space.
    Returns empty string when psychology data is insufficient or on failure.
    """
    try:
        r = PersonalityEngine().analyze(char)
        parts: List[str] = []

        m = r.mbti_analysis
        e = r.enneagram_analysis
        if m.get("type") and m.get("title"):
            parts.append(f"{m['type']} {m['title']}")
        if e.get("type") and e.get("title"):
            wn = f" ({e['wing_name']})" if e.get("wing_name") else ""
            parts.append(f"Enn.{e['type']}{wn} {e['title']}")
        if r.temperament_note:
            parts.append(r.temperament_note.split(":")[0].strip())

        sr = r.stress_response
        if sr.get("emotional_triggers"):
            parts.append(f"Triggers: {', '.join(str(x) for x in sr['emotional_triggers'][:2])}")
        if e.get("core_drive"):
            parts.append(f"Drive: {str(e['core_drive'])[:70]}")

        sp = r.social_power
        if sp.get("influence_style"):
            parts.append(f"Influence: {str(sp['influence_style'])[:60]}")

        ns = r.norse_soul
        if ns.get("hamingja_label"):
            parts.append(f"Hamingja: {ns['hamingja_label']}")

        sl = r.shadow_and_light
        if sl.get("shadow_archetype"):
            parts.append(f"Shadow: {sl['shadow_archetype']}")

        if not parts:
            return ""

        return "[PERSONALITY] " + " — ".join(parts)

    except Exception as exc:
        logger.debug("get_personality_compact_block failed: %s", exc)
        return ""
