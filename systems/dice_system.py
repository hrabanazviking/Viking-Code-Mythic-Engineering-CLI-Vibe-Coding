"""
D&D 5E Dice Rolling System for Viking Setting
==============================================

All game mechanics use D&D 5E rules with Viking-era flavor.
Character stats directly affect all rolls.

Roll Types:
- Ability checks (STR, DEX, CON, INT, WIS, CHA)
- Skill checks (with proficiency)
- Attack rolls
- Damage rolls
- Saving throws
- Death saves
- Initiative
- Combat maneuvers

All results are passed to Yggdrasil for AI narration.
"""

import random
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class Ability(Enum):
    """D&D 5E ability scores."""
    STRENGTH = "strength"
    DEXTERITY = "dexterity"
    CONSTITUTION = "constitution"
    INTELLIGENCE = "intelligence"
    WISDOM = "wisdom"
    CHARISMA = "charisma"


class Skill(Enum):
    """D&D 5E skills with their governing abilities."""
    # Strength
    ATHLETICS = ("athletics", Ability.STRENGTH)
    
    # Dexterity
    ACROBATICS = ("acrobatics", Ability.DEXTERITY)
    SLEIGHT_OF_HAND = ("sleight_of_hand", Ability.DEXTERITY)
    STEALTH = ("stealth", Ability.DEXTERITY)
    
    # Intelligence
    ARCANA = ("arcana", Ability.INTELLIGENCE)
    HISTORY = ("history", Ability.INTELLIGENCE)
    INVESTIGATION = ("investigation", Ability.INTELLIGENCE)
    NATURE = ("nature", Ability.INTELLIGENCE)
    RELIGION = ("religion", Ability.INTELLIGENCE)
    
    # Wisdom
    ANIMAL_HANDLING = ("animal_handling", Ability.WISDOM)
    INSIGHT = ("insight", Ability.WISDOM)
    MEDICINE = ("medicine", Ability.WISDOM)
    PERCEPTION = ("perception", Ability.WISDOM)
    SURVIVAL = ("survival", Ability.WISDOM)
    
    # Charisma
    DECEPTION = ("deception", Ability.CHARISMA)
    INTIMIDATION = ("intimidation", Ability.CHARISMA)
    PERFORMANCE = ("performance", Ability.CHARISMA)
    PERSUASION = ("persuasion", Ability.CHARISMA)
    
    # Viking-specific
    SEAMANSHIP = ("seamanship", Ability.WISDOM)
    RUNE_LORE = ("rune_lore", Ability.INTELLIGENCE)
    SAGA_TELLING = ("saga_telling", Ability.CHARISMA)


@dataclass
class DiceRoll:
    """Result of a dice roll."""
    dice_notation: str  # e.g., "1d20+5"
    dice_results: List[int]
    modifier: int
    total: int
    natural_roll: int  # The raw d20 result (before modifiers)
    is_critical: bool = False
    is_fumble: bool = False
    advantage: bool = False
    disadvantage: bool = False
    
    def to_dict(self) -> Dict:
        return {
            "notation": self.dice_notation,
            "dice": self.dice_results,
            "modifier": self.modifier,
            "total": self.total,
            "natural": self.natural_roll,
            "critical": self.is_critical,
            "fumble": self.is_fumble,
            "advantage": self.advantage,
            "disadvantage": self.disadvantage,
        }
    
    def describe(self) -> str:
        """Get a text description of the roll."""
        desc = f"[{self.dice_notation}] = {self.total}"
        if self.is_critical:
            desc += " (CRITICAL!)"
        elif self.is_fumble:
            desc += " (Fumble!)"
        return desc


@dataclass
class CheckResult:
    """Result of an ability/skill check."""
    check_type: str
    ability: Ability
    skill: Optional[Skill]
    dc: int
    roll: DiceRoll
    success: bool
    degree_of_success: str  # critical_success, success, failure, critical_failure
    character_name: str
    
    def to_dict(self) -> Dict:
        return {
            "type": self.check_type,
            "ability": self.ability.value,
            "skill": self.skill.value[0] if self.skill else None,
            "dc": self.dc,
            "roll": self.roll.to_dict(),
            "success": self.success,
            "degree": self.degree_of_success,
            "character": self.character_name,
        }
    
    def describe(self) -> str:
        """Get narration-ready description."""
        skill_name = self.skill.value[0].replace("_", " ").title() if self.skill else self.ability.value.title()
        
        if self.degree_of_success == "critical_success":
            return f"{self.character_name}'s {skill_name} check succeeds magnificently! (Natural 20, {self.roll.total} vs DC {self.dc})"
        elif self.degree_of_success == "critical_failure":
            return f"{self.character_name}'s {skill_name} check fails disastrously! (Natural 1, {self.roll.total} vs DC {self.dc})"
        elif self.success:
            return f"{self.character_name}'s {skill_name} check succeeds. ({self.roll.total} vs DC {self.dc})"
        else:
            return f"{self.character_name}'s {skill_name} check fails. ({self.roll.total} vs DC {self.dc})"


@dataclass
class CombatRoll:
    """Result of a combat roll."""
    roll_type: str  # attack, damage, saving_throw
    attacker: str
    defender: Optional[str]
    weapon: Optional[str]
    attack_roll: Optional[DiceRoll]
    damage_roll: Optional[DiceRoll]
    hit: bool
    damage_dealt: int
    damage_type: str
    
    def to_dict(self) -> Dict:
        return {
            "type": self.roll_type,
            "attacker": self.attacker,
            "defender": self.defender,
            "weapon": self.weapon,
            "attack": self.attack_roll.to_dict() if self.attack_roll else None,
            "damage": self.damage_roll.to_dict() if self.damage_roll else None,
            "hit": self.hit,
            "damage_dealt": self.damage_dealt,
            "damage_type": self.damage_type,
        }


class DiceRoller:
    """
    Core dice rolling functionality.
    """

    @staticmethod
    def _sanitize_notation(notation: str) -> str:
        """SH-03: Normalize dice notation before parsing.

        - Strips whitespace
        - Removes characters that are not valid in dice notation
        - Collapses repeated operators (++ → +, +- → -)
        - Returns '1d20' as a safe fallback for empty/unrecognizable input
        """
        import re as _re
        if not isinstance(notation, str):
            return "1d20"
        n = notation.strip().lower().replace(" ", "")
        # Keep only valid notation characters: digits, 'd', '+', '-', 'k', 'h', 'l'
        n = _re.sub(r"[^0-9d+\-khl]", "", n)
        # Collapse repeated signs
        n = _re.sub(r"\+{2,}", "+", n)
        n = _re.sub(r"\+-|-\+", "-", n)
        return n if n else "1d20"

    @staticmethod
    def roll(dice_notation: str) -> DiceRoll:
        """
        Roll dice using standard notation. Never raises — returns a fumble roll
        on invalid or malformed input.
        Examples: "1d20", "2d6+3", "1d8-1", "4d6kh3" (keep highest 3)
        """
        _FUMBLE = DiceRoll(
            dice_notation=str(dice_notation),
            dice_results=[1], modifier=0, total=1, natural_roll=1, is_fumble=True,
        )
        if not isinstance(dice_notation, str) or not dice_notation.strip():
            logger.warning("DiceRoller.roll(): invalid notation %r; returning fumble.", dice_notation)
            return _FUMBLE
        try:
            # SH-03: sanitize before parsing
            notation_lower = DiceRoller._sanitize_notation(dice_notation)

            # Check for keep highest/lowest.
            # Also extract any trailing modifier from the kh/kl suffix
            # (e.g. "4d6kh3+5" → keep_highest=3, modifier=+5).
            keep_highest = 0
            keep_lowest = 0
            modifier = 0
            kh_kl_modifier_parsed = False

            def _parse_keep_suffix(suffix: str):
                """Return (keep_count, modifier) from a kh/kl suffix like '3+5' or '3-2'."""
                if "+" in suffix:
                    sub = suffix.split("+", 1)
                    k = int(sub[0]) if sub[0].strip() else 1
                    m = int(float(sub[1])) if len(sub) > 1 and sub[1].strip() else 0
                    return k, m
                if "-" in suffix and suffix.count("-") == 1:
                    sub = suffix.split("-", 1)
                    k = int(sub[0]) if sub[0].strip() else 1
                    m = -int(float(sub[1])) if len(sub) > 1 and sub[1].strip() else 0
                    return k, m
                return (int(suffix) if suffix.strip() else 1), 0

            if "kh" in notation_lower:
                parts = notation_lower.split("kh", 1)
                notation_lower = parts[0]
                keep_highest, modifier = _parse_keep_suffix(parts[1]) if len(parts) > 1 and parts[1] else (1, 0)
                kh_kl_modifier_parsed = True
            elif "kl" in notation_lower:
                parts = notation_lower.split("kl", 1)
                notation_lower = parts[0]
                keep_lowest, modifier = _parse_keep_suffix(parts[1]) if len(parts) > 1 and parts[1] else (1, 0)
                kh_kl_modifier_parsed = True

            # Parse modifier from base notation (skip if already extracted from kh/kl suffix)
            if not kh_kl_modifier_parsed:
                if "+" in notation_lower:
                    parts = notation_lower.split("+", 1)
                    notation_lower = parts[0]
                    raw_mod = parts[1].strip() if len(parts) > 1 else ""
                    modifier = int(float(raw_mod)) if raw_mod else 0
                elif "-" in notation_lower and notation_lower.count("-") == 1:
                    parts = notation_lower.split("-", 1)
                    notation_lower = parts[0]
                    raw_mod = parts[1].strip() if len(parts) > 1 else ""
                    modifier = -int(float(raw_mod)) if raw_mod else 0

            # Parse dice count and size
            if "d" not in notation_lower:
                # Just a number
                val = int(float(notation_lower)) if notation_lower.strip() else 0
                return DiceRoll(
                    dice_notation=dice_notation,
                    dice_results=[val],
                    modifier=modifier,
                    total=val + modifier,
                    natural_roll=val,
                )

            parts = notation_lower.split("d")
            dice_count = max(1, int(parts[0])) if parts[0].strip() else 1
            dice_size = max(1, int(parts[1])) if len(parts) > 1 and parts[1].strip() else 1

            # Roll the dice
            results = [random.randint(1, dice_size) for _ in range(dice_count)]

            # Apply keep highest/lowest
            if keep_highest > 0:
                results = sorted(results, reverse=True)[:keep_highest]
            elif keep_lowest > 0:
                results = sorted(results)[:keep_lowest]

            if not results:
                logger.warning("DiceRoller.roll(): empty results for %r; returning fumble.", dice_notation)
                return _FUMBLE

            total = sum(results) + modifier
            natural = results[0] if len(results) == 1 else max(results)

            # Check for critical/fumble on d20
            is_critical = dice_size == 20 and dice_count == 1 and results[0] == 20
            is_fumble = dice_size == 20 and dice_count == 1 and results[0] == 1

            return DiceRoll(
                dice_notation=dice_notation,
                dice_results=results,
                modifier=modifier,
                total=total,
                natural_roll=natural,
                is_critical=is_critical,
                is_fumble=is_fumble,
            )
        except Exception as exc:
            logger.warning("DiceRoller.roll(): failed for %r: %s; returning fumble.", dice_notation, exc)
            return _FUMBLE
    
    @staticmethod
    def roll_with_advantage(modifier: int = 0) -> DiceRoll:
        """Roll d20 with advantage (roll twice, take higher)."""
        roll1 = random.randint(1, 20)
        roll2 = random.randint(1, 20)
        best = max(roll1, roll2)
        
        return DiceRoll(
            dice_notation=f"2d20kh1+{modifier}" if modifier >= 0 else f"2d20kh1{modifier}",
            dice_results=[roll1, roll2],
            modifier=modifier,
            total=best + modifier,
            natural_roll=best,
            is_critical=(best == 20),
            is_fumble=(best == 1),
            advantage=True
        )
    
    @staticmethod
    def roll_with_disadvantage(modifier: int = 0) -> DiceRoll:
        """Roll d20 with disadvantage (roll twice, take lower)."""
        roll1 = random.randint(1, 20)
        roll2 = random.randint(1, 20)
        worst = min(roll1, roll2)
        
        return DiceRoll(
            dice_notation=f"2d20kl1+{modifier}" if modifier >= 0 else f"2d20kl1{modifier}",
            dice_results=[roll1, roll2],
            modifier=modifier,
            total=worst + modifier,
            natural_roll=worst,
            is_critical=(worst == 20),
            is_fumble=(worst == 1),
            disadvantage=True
        )


def _weapon_has_prop(weapon: dict, prop: str) -> bool:
    """
    Check if a weapon has a given property.
    Handles both dict format {"finesse": True} (old) and list format ["finesse", ...] (SRD).
    """
    try:
        props = weapon.get("properties", {})
        if isinstance(props, dict):
            return bool(props.get(prop))
        if isinstance(props, list):
            # SRD list: each item is a string like "finesse" or "versatile (1d10)"
            return any(str(p).lower().startswith(prop.lower()) for p in props)
    except Exception:
        pass
    return False


class CharacterRoller:
    """
    Rolls using character stats.
    """
    
    def __init__(self):
        self.roller = DiceRoller()
        
    def _fuzzy_get_first_found(self, data: Dict, key_paths: List[List[str]]) -> Any:
        """Helper to try multiple nested paths for a value."""
        for path in key_paths:
            current = data
            for k in path:
                if isinstance(current, dict):
                    # case-insensitive key search
                    found = {sk.lower(): sv for sk, sv in current.items() if isinstance(sk, str)}
                    current = found.get(k.lower())
                else:
                    current = None
                    break
            if current is not None:
                return current
        return None
    
    def get_ability_modifier(self, character: Dict, ability: Ability) -> int:
        """Get ability modifier from character stats with robust fuzzy matching."""
        ab_name = ability.value.lower()
        score = self._fuzzy_get_first_found(character, [
            ["dnd5e", "abilities", ab_name],
            ["stats", "ability_scores", ab_name],
            ["stats", "abilities", ab_name],
            ["attributes", ab_name],
            ["stats", ab_name],
            ["dnd5e", ab_name],
            [ab_name]
        ])
        
        try:
            if score is None:
                score = 10
            return (int(score) - 10) // 2
        except (ValueError, TypeError):
            return 0
    
    def get_proficiency_bonus(self, character: Dict) -> int:
        """Get proficiency bonus based on level or explicit pb."""
        pb = self._fuzzy_get_first_found(character, [
            ["dnd5e", "proficiency_bonus"],
            ["stats", "proficiency_bonus"],
            ["proficiency_bonus"]
        ])
        if pb is not None:
            try:
                return int(pb)
            except (ValueError, TypeError):
                pass
                
        level = self._fuzzy_get_first_found(character, [
            ["dnd5e", "level"],
            ["stats", "level"],
            ["level"]
        ])
        try:
            lvl = int(level) if level is not None else 1
            return (lvl - 1) // 4 + 2
        except (ValueError, TypeError):
            return 2
            
    def get_armor_class(self, character: Dict) -> int:
        """Get character armor class robustly."""
        ac = self._fuzzy_get_first_found(character, [
            ["dnd5e", "armor_class"],
            ["dnd5e", "ac"],
            ["stats", "armor_class"],
            ["stats", "ac"],
            ["armor_class"],
            ["ac"]
        ])
        try:
            return int(ac) if ac is not None else 10
        except (ValueError, TypeError):
            return 10
    
    def is_proficient(self, character: Dict, skill: Skill) -> bool:
        """Check if character is proficient in a skill — exact name match.
        Normalises separators (spaces and hyphens become underscores) before
        comparing so 'sleight of hand', 'sleight-of-hand', and 'sleight_of_hand'
        all match Skill.SLEIGHT_OF_HAND correctly."""
        skill_name = skill.value[0].lower()
        profs = self._fuzzy_get_first_found(character, [
            ["dnd5e", "proficiencies", "skills"],
            ["stats", "proficiencies", "skills"],
            ["proficiencies", "skills"],
            ["skills"],
        ])

        if isinstance(profs, list):
            flat_profs = [
                str(p).lower().replace("-", "_").replace(" ", "_") for p in profs
            ]
            return skill_name in flat_profs  # exact match — no substrings
        return False
    
    def ability_check(
        self,
        character: Dict,
        ability: Ability,
        dc: int,
        advantage: bool = False,
        disadvantage: bool = False
    ) -> CheckResult:
        """Make an ability check."""
        char_name = character.get("identity", {}).get("name", "Unknown")
        modifier = self.get_ability_modifier(character, ability)
        
        # Roll
        if advantage and not disadvantage:
            roll = self.roller.roll_with_advantage(modifier)
        elif disadvantage and not advantage:
            roll = self.roller.roll_with_disadvantage(modifier)
        else:
            roll = self.roller.roll(f"1d20+{modifier}" if modifier >= 0 else f"1d20{modifier}")
        
        # Determine success
        success = roll.total >= dc
        
        # Determine degree
        if roll.is_critical:
            degree = "critical_success"
            success = True
        elif roll.is_fumble:
            degree = "critical_failure"
            success = False
        elif roll.total >= dc + 10:
            degree = "critical_success"
        elif roll.total <= dc - 10:
            degree = "critical_failure"
        elif success:
            degree = "success"
        else:
            degree = "failure"
        
        result = CheckResult(
            check_type="ability_check",
            ability=ability,
            skill=None,
            dc=dc,
            roll=roll,
            success=success,
            degree_of_success=degree,
            character_name=char_name
        )
        
        logger.info(f"[ROLL] {result.describe()}")
        return result
    
    def skill_check(
        self,
        character: Dict,
        skill: Skill,
        dc: int,
        advantage: bool = False,
        disadvantage: bool = False
    ) -> CheckResult:
        """Make a skill check."""
        # Coerce dc — callers may pass a string label
        try:
            dc = int(dc)
        except (TypeError, ValueError):
            logger.warning(
                "skill_check() received non-numeric dc=%r; defaulting to 15.", dc
            )
            dc = 15

        try:
            char_name = character.get("identity", {}).get("name", "Unknown")
            ability = skill.value[1]  # Get governing ability

            # Calculate modifier
            modifier = self.get_ability_modifier(character, ability)
            if self.is_proficient(character, skill):
                modifier += self.get_proficiency_bonus(character)

            # Roll
            if advantage and not disadvantage:
                roll = self.roller.roll_with_advantage(modifier)
            elif disadvantage and not advantage:
                roll = self.roller.roll_with_disadvantage(modifier)
            else:
                roll = self.roller.roll(f"1d20+{modifier}" if modifier >= 0 else f"1d20{modifier}")

            # Determine success
            success = roll.total >= dc

            # Determine degree
            if roll.is_critical:
                degree = "critical_success"
                success = True
            elif roll.is_fumble:
                degree = "critical_failure"
                success = False
            elif roll.total >= dc + 10:
                degree = "critical_success"
            elif roll.total <= dc - 10:
                degree = "critical_failure"
            elif success:
                degree = "success"
            else:
                degree = "failure"

            result = CheckResult(
                check_type="skill_check",
                ability=ability,
                skill=skill,
                dc=dc,
                roll=roll,
                success=success,
                degree_of_success=degree,
                character_name=char_name
            )

            logger.info("[ROLL] %s", result.describe())
            return result
        except Exception as exc:
            char_name = "Unknown"
            try:
                char_name = character.get("identity", {}).get("name", "Unknown")
            except Exception:
                pass
            skill_label = getattr(skill, "name", str(skill))
            logger.warning(
                "skill_check() failed for character=%r skill=%s: %s",
                char_name, skill_label, exc, exc_info=True,
            )
            try:
                fallback_ability = skill.value[1]
            except Exception:
                fallback_ability = Ability.STRENGTH
            _dummy = DiceRoll(
                dice_notation="1d20", dice_results=[0],
                modifier=0, total=0, natural_roll=0,
            )
            return CheckResult(
                check_type="skill_check",
                ability=fallback_ability,
                skill=skill if isinstance(skill, Skill) else None,
                dc=dc,
                roll=_dummy,
                success=False,
                degree_of_success="failure",
                character_name=char_name,
            )
    
    def saving_throw(
        self,
        character: Dict,
        ability: Ability,
        dc: int,
        advantage: bool = False,
        disadvantage: bool = False
    ) -> CheckResult:
        """Make a saving throw."""
        # Coerce ability — callers may pass a raw string instead of the enum
        if not isinstance(ability, Ability):
            try:
                ability = Ability(str(ability).lower())
            except ValueError:
                logger.warning(
                    "saving_throw() received invalid ability %r; defaulting to STRENGTH.", ability
                )
                ability = Ability.STRENGTH

        try:
            char_name = character.get("identity", {}).get("name", "Unknown")
            modifier = self.get_ability_modifier(character, ability)

            # Check for saving throw proficiency
            proficiencies = character.get("stats", {}).get("proficiencies", {})
            save_profs = proficiencies.get("saving_throws", [])
            if ability.value in save_profs:
                modifier += self.get_proficiency_bonus(character)

            # Roll
            if advantage and not disadvantage:
                roll = self.roller.roll_with_advantage(modifier)
            elif disadvantage and not advantage:
                roll = self.roller.roll_with_disadvantage(modifier)
            else:
                roll = self.roller.roll(f"1d20+{modifier}" if modifier >= 0 else f"1d20{modifier}")

            success = roll.total >= dc

            if roll.is_critical:
                degree = "critical_success"
                success = True
            elif roll.is_fumble:
                degree = "critical_failure"
                success = False
            elif success:
                degree = "success"
            else:
                degree = "failure"

            result = CheckResult(
                check_type="saving_throw",
                ability=ability,
                skill=None,
                dc=dc,
                roll=roll,
                success=success,
                degree_of_success=degree,
                character_name=char_name
            )

            logger.info("[ROLL] Saving throw: %s", result.describe())
            return result
        except Exception as exc:
            char_name = "Unknown"
            try:
                char_name = character.get("identity", {}).get("name", "Unknown")
            except Exception:
                pass
            logger.warning(
                "saving_throw() failed for character=%r ability=%s: %s",
                char_name, ability, exc, exc_info=True,
            )
            _dummy = DiceRoll(
                dice_notation="1d20", dice_results=[0],
                modifier=0, total=0, natural_roll=0,
            )
            return CheckResult(
                check_type="saving_throw",
                ability=ability,
                skill=None,
                dc=dc if isinstance(dc, int) else 0,
                roll=_dummy,
                success=False,
                degree_of_success="failure",
                character_name=char_name,
            )
    
    def attack_roll(
        self,
        attacker: Dict,
        defender: Dict,
        weapon: Dict = None,
        advantage: bool = False,
        disadvantage: bool = False
    ) -> CombatRoll:
        """Make an attack roll."""
        try:
            attacker_name = attacker.get("identity", {}).get("name", "Attacker")
            defender_name = defender.get("identity", {}).get("name", "Defender")

            # Determine attack ability (STR or DEX for finesse)
            # weapon["properties"] may be a dict (old) or list (new SRD format)
            if weapon and _weapon_has_prop(weapon, "finesse"):
                str_mod = self.get_ability_modifier(attacker, Ability.STRENGTH)
                dex_mod = self.get_ability_modifier(attacker, Ability.DEXTERITY)
                attack_mod = max(str_mod, dex_mod)
            elif weapon and _weapon_has_prop(weapon, "ranged"):
                attack_mod = self.get_ability_modifier(attacker, Ability.DEXTERITY)
            else:
                attack_mod = self.get_ability_modifier(attacker, Ability.STRENGTH)

            # Add proficiency (assume proficient with equipped weapons)
            attack_mod += self.get_proficiency_bonus(attacker)

            # Get defender AC
            defender_ac = self.get_armor_class(defender)

            # Roll attack
            if advantage and not disadvantage:
                atk_roll = self.roller.roll_with_advantage(attack_mod)
            elif disadvantage and not advantage:
                atk_roll = self.roller.roll_with_disadvantage(attack_mod)
            else:
                atk_roll = self.roller.roll(f"1d20+{attack_mod}" if attack_mod >= 0 else f"1d20{attack_mod}")

            # Determine hit
            hit = atk_roll.total >= defender_ac or atk_roll.is_critical
            if atk_roll.is_fumble:
                hit = False

            # Roll damage if hit
            damage_dealt = 0
            damage_roll = None
            damage_type = "slashing"
            weapon_name = "unarmed"

            if hit and weapon:
                weapon_name = weapon.get("name", "weapon")
                damage_dice = weapon.get("damage", "1d6")
                damage_type = weapon.get("damage_type", "slashing")

                # Add ability modifier to damage
                if _weapon_has_prop(weapon, "finesse"):
                    str_mod = self.get_ability_modifier(attacker, Ability.STRENGTH)
                    dex_mod = self.get_ability_modifier(attacker, Ability.DEXTERITY)
                    dmg_mod = max(str_mod, dex_mod)
                elif _weapon_has_prop(weapon, "ranged"):
                    dmg_mod = self.get_ability_modifier(attacker, Ability.DEXTERITY)
                else:
                    dmg_mod = self.get_ability_modifier(attacker, Ability.STRENGTH)

                damage_roll = self.roller.roll(
                    f"{damage_dice}+{dmg_mod}" if dmg_mod >= 0 else f"{damage_dice}{dmg_mod}"
                )

                # Critical hits double dice
                if atk_roll.is_critical:
                    extra_dice = self.roller.roll(damage_dice)
                    damage_roll.dice_results.extend(extra_dice.dice_results)
                    damage_roll.total += extra_dice.total

                damage_dealt = max(0, damage_roll.total)
            elif hit:
                # Unarmed strike — D&D 5e: 1 + STR modifier, minimum 1
                str_mod = self.get_ability_modifier(attacker, Ability.STRENGTH)
                damage_dealt = max(1, 1 + str_mod)
                damage_type = "bludgeoning"

            result = CombatRoll(
                roll_type="attack",
                attacker=attacker_name,
                defender=defender_name,
                weapon=weapon_name,
                attack_roll=atk_roll,
                damage_roll=damage_roll,
                hit=hit,
                damage_dealt=damage_dealt,
                damage_type=damage_type
            )

            logger.info(
                "[COMBAT] %s attacks %s: %s (%d vs AC %d)",
                attacker_name, defender_name,
                "HIT" if hit else "MISS", atk_roll.total, defender_ac,
            )
            if hit:
                logger.info("[COMBAT] Damage: %d %s", damage_dealt, damage_type)

            return result
        except Exception as exc:
            logger.error("attack_roll() failed: %s", exc, exc_info=True)
            try:
                attacker_name = attacker.get("identity", {}).get("name", "Attacker")
            except Exception:
                attacker_name = "Attacker"
            try:
                defender_name = defender.get("identity", {}).get("name", "Defender")
            except Exception:
                defender_name = "Defender"
            return CombatRoll(
                roll_type="attack",
                attacker=attacker_name,
                defender=defender_name,
                weapon=None,
                attack_roll=None,
                damage_roll=None,
                hit=False,
                damage_dealt=0,
                damage_type="none",
            )
    
    def initiative(self, character: Dict) -> int:
        """Roll initiative for a character."""
        dex_mod = self.get_ability_modifier(character, Ability.DEXTERITY)
        roll = self.roller.roll(f"1d20+{dex_mod}" if dex_mod >= 0 else f"1d20{dex_mod}")
        
        char_name = character.get("identity", {}).get("name", "Unknown")
        logger.info(f"[INITIATIVE] {char_name}: {roll.total}")
        
        return roll.total
    
    def death_save(self, character: Dict) -> Tuple[bool, str]:
        """
        Make a death saving throw.
        Returns (stabilized, result_type)
        """
        roll = self.roller.roll("1d20")
        
        if roll.natural_roll == 20:
            return (True, "critical_success")  # Regain 1 HP
        elif roll.natural_roll == 1:
            return (False, "critical_failure")  # Two failures
        elif roll.total >= 10:
            return (False, "success")
        else:
            return (False, "failure")


# Viking-specific DC guidelines
VIKING_DCS = {
    # Combat-related
    "easy_combat": 5,
    "medium_combat": 10,
    "hard_combat": 15,
    "very_hard_combat": 20,
    "legendary_combat": 25,
    
    # Social
    "convince_friendly": 10,
    "convince_neutral": 15,
    "convince_hostile": 20,
    "intimidate_thrall": 5,
    "intimidate_karl": 12,
    "intimidate_jarl": 18,
    
    # Sailing
    "calm_seas": 5,
    "rough_seas": 12,
    "storm": 18,
    "maelstrom": 25,
    
    # Survival
    "forage_summer": 10,
    "forage_winter": 18,
    "navigate_known": 8,
    "navigate_unknown": 15,
    
    # Lore
    "common_knowledge": 10,
    "uncommon_knowledge": 15,
    "rare_knowledge": 20,
    "lost_knowledge": 25,
    
    # Seidr/Magic
    "simple_ritual": 12,
    "complex_ritual": 18,
    "powerful_ritual": 22,
    "divine_ritual": 28,
}


# Factory function
def create_character_roller() -> CharacterRoller:
    """Create a character roller instance."""
    return CharacterRoller()
