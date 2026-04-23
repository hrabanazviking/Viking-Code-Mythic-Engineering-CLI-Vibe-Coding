#!/usr/bin/env python3
"""
Housekeeping System v3.0 - AI-Powered Data Maintenance
=======================================================

Runs after each turn to:
1. Extract new characters from AI responses and generate full stats
2. Extract new quests and save them
3. Extract new locations and save them
4. Update existing character files with new data fields
5. Generate portraits for new characters

All auto-generated content goes to data/auto_generated/
"""

import json
import yaml
import re
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
import hashlib

from systems.crash_reporting import get_crash_reporter
from systems.thor_guardian import ThorGuardian

logger = logging.getLogger(__name__)


class HousekeepingSystem:
    """
    AI-powered system for maintaining and expanding game data.
    """
    
    # Common patterns that indicate auto-generated placeholder names
    PLACEHOLDER_PATTERNS = [
        r"^(the|a|an)\s+\w+$",           # "the merchant", "a warrior"
        r"^(old|young|tall|grizzled)\s+\w+$",  # "old man", "grizzled warrior"
        r"^\w+\s+(man|woman|person|figure|stranger|traveler)$",  # "hooded figure"
        r"^unknown\b",                    # "unknown merchant"
        r"^mysterious\b",                 # "mysterious stranger"
        r"^npc_\d+",                      # "npc_001"
        r"^char_\d+",                     # "char_042"
    ]
    
    def __init__(self, data_path: str = "data", ai_client=None):
        self.data_path = Path(data_path)
        self.ai_client = ai_client
        
        # Auto-generated content folders
        self.auto_chars_path = self.data_path / "auto_generated" / "characters"
        self.auto_quests_path = self.data_path / "auto_generated" / "quests"
        self.auto_locations_path = self.data_path / "auto_generated" / "locations"
        self.auto_portraits_path = self.data_path / "auto_generated" / "portraits"
        
        # Create directories
        for path in [self.auto_chars_path, self.auto_quests_path, 
                     self.auto_locations_path, self.auto_portraits_path]:
            path.mkdir(parents=True, exist_ok=True)
        
        # Track what we've already processed
        self.processed_names = set()
        self._load_processed()
        
        # Character generator for stats
        self.char_generator = None
        self.crash_reporter = get_crash_reporter()
        self.thor_guardian = ThorGuardian()
    
    def set_ai_client(self, ai_client):
        """Set the AI client for generation."""
        self.ai_client = ai_client
    
    def set_character_generator(self, generator):
        """Set the character generator for stats."""
        self.char_generator = generator
    
    def _load_processed(self):
        """Load list of already processed names."""
        processed_file = self.data_path / "auto_generated" / "processed.json"
        try:
            if processed_file.exists():
                with open(processed_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.processed_names = set(data.get("names", []))
        except Exception as exc:
            logger.warning("Failed to load processed names: %s", exc)
            self.crash_reporter.report_exception(exc, "housekeeping._load_processed")
    
    def _save_processed(self):
        """Save list of processed names."""
        processed_file = self.data_path / "auto_generated" / "processed.json"
        try:
            processed_file.parent.mkdir(parents=True, exist_ok=True)
            with open(processed_file, 'w', encoding='utf-8') as f:
                json.dump({"names": list(self.processed_names)}, f)
        except Exception as exc:
            logger.warning("Failed to save processed names: %s", exc)
            self.crash_reporter.report_exception(exc, "housekeeping._save_processed")
    
    def process_turn(
        self,
        ai_response: str,
        player_action: str,
        current_npcs: List[Dict],
        current_location: str,
        rune_data: Optional[Dict] = None
    ) -> Dict[str, List]:
        """
        Process a turn's AI response for new content.
        
        Returns dict with:
        - new_characters: List of newly created character IDs
        - new_quests: List of newly created quest IDs
        - new_locations: List of newly created location IDs
        """
        results = {
            "new_characters": [],
            "new_quests": [],
            "new_locations": []
        }
        
        try:
            # Huginn scouts new characters from the narration stream.
            characters = self._extract_characters(ai_response, current_npcs)
            for char_info in characters:
                char_id = self._create_character(char_info)
                if char_id:
                    results["new_characters"].append(char_id)

            # Muninn catalogs quest threads from the spoken saga.
            quests = self._extract_quests(ai_response, player_action)
            for quest_info in quests:
                quest_id = self._create_quest(quest_info)
                if quest_id:
                    results["new_quests"].append(quest_id)

            # Ratatoskr carries location whispers through Yggdrasil's bark.
            locations = self._extract_locations(ai_response, current_location)
            for loc_info in locations:
                loc_id = self._create_location(loc_info)
                if loc_id:
                    results["new_locations"].append(loc_id)
        except Exception as exc:
            logger.warning("Housekeeping process_turn failed: %s", exc)
            self.crash_reporter.report_exception(
                exc,
                source="housekeeping.process_turn",
                metadata={"location": current_location, "action": player_action[:120]},
            )

        # ── EntityCanonizer: write YAML stubs to data/auto_generated/ ──
        # Satisfies PROJECT_LAWS: "Entity canonizer must create YAML stubs for any narrated name."
        try:
            if not hasattr(self, '_entity_canonizer'):
                from session.entity_canonizer import EntityCanonizer
                self._entity_canonizer = EntityCanonizer(str(self.data_path))
            canonized = self._entity_canonizer.process_ai_response(
                text=ai_response,
                context={"location": current_location, "npcs": current_npcs},
            )
            results["canonized_entities"] = canonized
        except Exception as _ec_exc:
            logger.warning("EntityCanonizer skipped (non-fatal): %s", _ec_exc)

        return results

    def _extract_characters(self, text: str, known_npcs: List[Dict]) -> List[Dict]:
        """Extract new character names and info from text."""
        # Pattern for Norse-style names (Capitalized, possibly with epithet)
        name_patterns = [
            r'\b([A-Z][a-z]+(?:\s+(?:the\s+)?[A-Z][a-z]+)?)\b',  # "Bjorn the Bold"
            r'"([A-Z][a-z]+(?:\s+[A-Za-z]+)*)"',  # Quoted names
        ]
        
        known_names = set()
        for npc in known_npcs:
            name = npc.get("identity", {}).get("name", "")
            if name:
                known_names.add(name.lower())
        
        found_characters = []
        
        for pattern in name_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                name = match.strip()
                # Skip if too short, common words, or already known
                if len(name) < 3:
                    continue
                if name.lower() in ['the', 'and', 'but', 'for', 'with', 'you', 'your']:
                    continue
                if name.lower() in known_names:
                    continue
                if name.lower() in self.processed_names:
                    continue
                
                # Check if this looks like a character name (mentioned with verbs of action/speech)
                context_pattern = rf'{re.escape(name)}\s+(?:says?|said|spoke|asks?|asked|nods?|nodded|looks?|looked|turns?|turned|walks?|walked)'
                if re.search(context_pattern, text, re.IGNORECASE):
                    # Extract any context about this character
                    context = self._get_character_context(name, text)
                    found_characters.append({
                        "name": name,
                        "context": context
                    })
                    self.processed_names.add(name.lower())
        
        self._save_processed()
        return found_characters[:3]  # Limit to 3 new characters per turn
    
    def _get_character_context(self, name: str, text: str) -> str:
        """Extract context about a character from text."""
        # Find sentences mentioning this character
        sentences = text.replace('\n', ' ').split('.')
        relevant = []
        for s in sentences:
            if name in s:
                relevant.append(s.strip())
        
        return '. '.join(relevant[:3])  # First 3 relevant sentences
    
    def _create_character(self, char_info: Dict) -> Optional[str]:
        """Create a full character file from extracted info."""
        name = char_info.get("name", "")
        if not name:
            return None
        
        # Generate ID
        char_id = name.lower().replace(" ", "_").replace("'", "")
        char_id = re.sub(r'[^a-z0-9_]', '', char_id)
        
        # Check if already exists
        char_file = self.auto_chars_path / f"{char_id}.yaml"
        if char_file.exists():
            return None
        
        # Generate full character using the character generator
        if self.char_generator:
            try:
                # Try to infer culture/class from context
                context = char_info.get("context", "").lower()
                
                culture = "norse_swedish"  # Default
                if "danish" in context:
                    culture = "norse_danish"
                elif "norwegian" in context:
                    culture = "norse_norwegian"
                elif "saxon" in context or "english" in context:
                    culture = "anglo_saxon"
                elif "frank" in context:
                    culture = "frankish"
                elif "slav" in context:
                    culture = "slavic"
                
                char_class = None  # Let generator choose
                if "warrior" in context or "fighter" in context:
                    char_class = "fighter"
                elif "merchant" in context or "trader" in context:
                    char_class = "rogue"
                elif "priest" in context or "gothi" in context:
                    char_class = "cleric"
                elif "völva" in context or "seer" in context:
                    char_class = "sorcerer"
                elif "smith" in context:
                    char_class = "artificer"
                
                # Generate full character
                character = self.char_generator.generate_character(
                    culture=culture,
                    class_name=char_class,
                    level=5  # Mid-level for interesting NPCs
                )
                
                # Override name
                character["identity"]["name"] = name
                character["id"] = char_id
                
                # Add extraction context
                character["meta"]["extracted_from"] = char_info.get("context", "")[:200]
                character["meta"]["auto_generated"] = True
                character["meta"]["generated_date"] = datetime.now().isoformat()
                
                # Save
                with open(char_file, 'w', encoding='utf-8') as f:
                    yaml.dump(character, f, allow_unicode=True, default_flow_style=False)
                
                return char_id
                
            except Exception as e:
                logger.warning("Error generating character %s: %s", name, e)
        
        # Fallback: Create minimal character
        minimal_char = {
            "id": char_id,
            "identity": {
                "name": name,
                "culture": "norse_swedish",
                "gender": "unknown",
                "age": 30
            },
            "meta": {
                "auto_generated": True,
                "needs_expansion": True,
                "extracted_from": char_info.get("context", "")[:200],
                "generated_date": datetime.now().isoformat()
            }
        }
        
        with open(char_file, 'w', encoding='utf-8') as f:
            yaml.dump(minimal_char, f, allow_unicode=True, default_flow_style=False)
        
        return char_id
    
    def _extract_quests(self, text: str, player_action: str) -> List[Dict]:
        """Extract quest mentions from text."""
        quest_patterns = [
            r'(?:must|should|need to|has to|wants you to|asks you to)\s+([^.!?]+)',
            r'quest[:\s]+([^.!?]+)',
            r'mission[:\s]+([^.!?]+)',
            r'task[:\s]+([^.!?]+)',
        ]
        
        found_quests = []
        
        for pattern in quest_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                objective = match.strip()
                if len(objective) > 20 and len(objective) < 200:
                    # Generate quest ID
                    quest_id = hashlib.md5(objective.encode()).hexdigest()[:8]
                    if quest_id not in self.processed_names:
                        found_quests.append({
                            "objective": objective,
                            "context": text[:500]
                        })
                        self.processed_names.add(quest_id)
        
        return found_quests[:2]  # Limit to 2 new quests per turn
    
    def _create_quest(self, quest_info: Dict) -> Optional[str]:
        """Create a quest file from extracted info."""
        objective = quest_info.get("objective", "")
        if not objective:
            return None
        
        # Generate ID
        quest_id = "auto_" + hashlib.md5(objective.encode()).hexdigest()[:8]
        
        quest_file = self.auto_quests_path / f"{quest_id}.yaml"
        if quest_file.exists():
            return None
        
        quest = {
            "id": quest_id,
            "name": objective[:50] + "..." if len(objective) > 50 else objective,
            "description": objective,
            "type": "side",  # Auto-generated quests are side quests
            "status": "discovered",
            "objectives": [
                {
                    "description": objective,
                    "completed": False
                }
            ],
            "rewards": {
                "xp": 100,
                "gold": "1d20 + 10",
                "reputation": []
            },
            "meta": {
                "auto_generated": True,
                "extracted_from": quest_info.get("context", "")[:200],
                "generated_date": datetime.now().isoformat()
            }
        }
        
        with open(quest_file, 'w', encoding='utf-8') as f:
            yaml.dump(quest, f, allow_unicode=True, default_flow_style=False)
        
        return quest_id
    
    def _extract_locations(self, text: str, current_location: str) -> List[Dict]:
        """Extract location mentions from text."""
        location_patterns = [
            r'(?:in|at|to|from)\s+(?:the\s+)?([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
            r'(?:village|town|city|hall|temple|forest|cave|mountain)\s+(?:of|called)\s+([A-Z][a-z]+)',
        ]
        
        # Words to ignore - common words, cultures, directions, etc.
        ignore_words = {
            'the', 'and', 'this', 'that', 'those', 'these', 'there', 'here',
            'you', 'your', 'his', 'her', 'their', 'its', 'them', 'him',
            # Directions
            'north', 'south', 'east', 'west',
            # Times
            'morning', 'evening', 'night', 'dawn', 'dusk', 'day', 'days',
            # Cultural/ethnic terms - NOT locations!
            'frankish', 'franks', 'danish', 'danes', 'norwegian', 'norse',
            'swedish', 'swedes', 'saxon', 'saxons', 'slavic', 'slavs',
            'byzantine', 'roman', 'romans', 'greek', 'greeks',
            'arabic', 'arab', 'arabs', 'abbasid', 'islamic', 'muslim',
            'irish', 'celtic', 'celts', 'pictish', 'picts',
            'frisian', 'frisians', 'finnish', 'finns', 'sami',
            'gothic', 'goths', 'vandal', 'vandals',
            # Common nouns that look like names
            'someone', 'anyone', 'everyone', 'nobody', 'something',
            'nothing', 'everything', 'anything', 'another',
            # Religious/mythological
            'odin', 'thor', 'freya', 'freyja', 'loki', 'tyr', 'heimdall',
            'god', 'gods', 'goddess', 'goddesses',
            # Actions/descriptions often capitalized
            'master', 'lord', 'lady', 'king', 'queen', 'jarl', 'earl',
        }
        
        found_locations = []
        
        for pattern in location_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                loc_name = match.strip()
                if len(loc_name) < 3:
                    continue
                if loc_name.lower() in ignore_words:
                    continue
                if loc_name.lower() in self.processed_names:
                    continue
                
                loc_id = loc_name.lower().replace(" ", "_")
                if loc_id != current_location.lower():
                    found_locations.append({
                        "name": loc_name,
                        "context": self._get_character_context(loc_name, text)
                    })
                    self.processed_names.add(loc_name.lower())
        
        return found_locations[:2]
    
    def _create_location(self, loc_info: Dict) -> Optional[str]:
        """Create a location file from extracted info."""
        name = loc_info.get("name", "")
        if not name:
            return None
        
        loc_id = name.lower().replace(" ", "_")
        loc_id = re.sub(r'[^a-z0-9_]', '', loc_id)
        
        loc_file = self.auto_locations_path / f"{loc_id}.yaml"
        if loc_file.exists():
            return None
        
        location = {
            "id": loc_id,
            "name": name,
            "type": "unknown",  # Will need manual classification
            "description": {
                "short": f"A place called {name}.",
                "full": loc_info.get("context", f"A location mentioned as {name}.")
            },
            "npcs": [],
            "connections": [],
            "meta": {
                "auto_generated": True,
                "needs_expansion": True,
                "generated_date": datetime.now().isoformat()
            }
        }
        
        with open(loc_file, 'w', encoding='utf-8') as f:
            yaml.dump(location, f, allow_unicode=True, default_flow_style=False)
        
        return loc_id
    
    def update_character_schema(self, char_path: Path, new_fields: Dict[str, Any]):
        """
        Update a character file with new schema fields.
        Used to add new data structures to old character files.
        """
        if not char_path.exists():
            return False
        
        with open(char_path, 'r', encoding='utf-8') as f:
            character = yaml.safe_load(f)
        
        if not character:
            return False
        
        modified = False
        
        # Add missing top-level fields
        for field, default_value in new_fields.items():
            if field not in character:
                character[field] = default_value
                modified = True
            elif isinstance(default_value, dict):
                # Merge nested dicts
                for subfield, subdefault in default_value.items():
                    if subfield not in character[field]:
                        character[field][subfield] = subdefault
                        modified = True
        
        if modified:
            with open(char_path, 'w', encoding='utf-8') as f:
                yaml.dump(character, f, allow_unicode=True, default_flow_style=False)
        
        return modified
    
    def batch_update_characters(self):
        """
        Update all character files with the latest schema.
        Adds herbal birth control to all female characters.
        """
        # New fields to add to all characters
        new_fields = {
            "religion": {
                "religion": "norse_pagan",
                "religion_display": "Norse Paganism",
                "patron": "Unknown",
                "patron_domains": [],
                "devotion_level": "moderate"
            },
            "meta": {
                "schema_version": "3.2",
                "last_updated": datetime.now().isoformat()
            }
        }
        
        # Female-specific fields
        female_fields = {
            "reproductive_health": {
                "herbal_birth_control": True,
                "birth_control_method": "Traditional Norse herbal contraceptives",
                "effectiveness": "100%",
                "notes": "Using queen anne's lace (wild carrot), pennyroyal, and tansy preparations"
            }
        }
        
        updated_count = 0
        
        # Process all character directories
        char_dirs = [
            self.data_path / "characters" / "npcs",
            self.data_path / "characters" / "player_characters",
            self.data_path / "characters" / "villains",
            self.auto_chars_path
        ]
        
        for char_dir in char_dirs:
            if not char_dir.exists():
                continue
            
            for char_file in char_dir.rglob("*.yaml"):
                try:
                    with open(char_file, 'r', encoding='utf-8') as f:
                        character = yaml.safe_load(f)
                    
                    if not character:
                        continue
                    
                    modified = False
                    
                    # Add standard new fields
                    for field, default_value in new_fields.items():
                        if field not in character:
                            character[field] = default_value
                            modified = True
                        elif isinstance(default_value, dict):
                            for subfield, subdefault in default_value.items():
                                if subfield not in character[field]:
                                    character[field][subfield] = subdefault
                                    modified = True
                    
                    # Add herbal birth control for females
                    gender = character.get("identity", {}).get("gender", "").lower()
                    if gender == "female":
                        if "reproductive_health" not in character:
                            character["reproductive_health"] = female_fields["reproductive_health"]
                            modified = True
                        elif not character["reproductive_health"].get("herbal_birth_control"):
                            character["reproductive_health"]["herbal_birth_control"] = True
                            character["reproductive_health"]["effectiveness"] = "100%"
                            modified = True
                    
                    if modified:
                        with open(char_file, 'w', encoding='utf-8') as f:
                            yaml.dump(character, f, allow_unicode=True, default_flow_style=False)
                        updated_count += 1
                        logger.info("Updated character schema: %s", char_file)
                        
                except Exception as e:
                    logger.warning("Error updating %s: %s", char_file, e)
        
        return updated_count
    
    def get_auto_generated_stats(self) -> Dict[str, int]:
        """Get counts of auto-generated content."""
        return {
            "characters": len(list(self.auto_chars_path.glob("*.yaml"))),
            "quests": len(list(self.auto_quests_path.glob("*.yaml"))),
            "locations": len(list(self.auto_locations_path.glob("*.yaml"))),
            "portraits": len(list(self.auto_portraits_path.glob("*.png")))
        }

    # =====================================================================
    # CHARACTER RENAME & FLESH OUT (v4.5.0)
    # =====================================================================

    def needs_rename(self, character: Dict) -> bool:
        """
        Check if a character has a placeholder name that should be replaced
        with a proper Norse name and backstory.
        """
        identity = character.get("identity", {})
        name = identity.get("name", "").strip()

        if not name:
            return True

        name_lower = name.lower()

        # Check against placeholder patterns
        for pattern in self.PLACEHOLDER_PATTERNS:
            if re.match(pattern, name_lower):
                return True

        # Check if name is too short (single word, likely generic)
        if len(name) < 3:
            return True

        # Check if character was flagged as needing fleshing out
        meta = character.get("meta", {})
        if meta.get("needs_expansion") or meta.get("needs_rename"):
            return True

        return False

    def rename_and_flesh_out_character(
        self,
        character: Dict,
        context: Dict = None
    ) -> Dict:
        """
        AI-powered rename and backstory generation for auto-generated characters.

        Takes a character with a placeholder name (e.g., "the merchant", "grizzled warrior")
        and gives them a proper Norse name, epithet, backstory, and personality.

        Args:
            character: Character dict with placeholder identity
            context: Optional dict with location, culture, role context

        Returns:
            Updated character dict with proper name and expanded identity
        """
        if not self.ai_client:
            return character

        identity = character.get("identity", {})
        old_name = identity.get("name", "unnamed")
        role = identity.get("role", "commoner")
        gender = identity.get("gender", "male")
        culture = identity.get("culture", "norse")
        age = identity.get("age", "adult")

        # Build context string
        ctx_parts = []
        if context:
            if context.get("location"):
                ctx_parts.append(f"Located at: {context['location']}")
            if context.get("scene"):
                ctx_parts.append(f"Scene context: {context['scene']}")

        context_str = "\n".join(ctx_parts) if ctx_parts else "No additional context."

        prompt = f"""You are a Norse saga historian creating a character entry.

A character was auto-generated with the placeholder description: "{old_name}"
Their role is: {role}
Gender: {gender}
Culture: {culture}
Approximate age: {age}

{context_str}

Give this character a PROPER Old Norse or Viking-era name with an epithet.
Also provide a brief backstory, personality traits, and a distinctive physical feature.

Respond ONLY in YAML format with no markdown fencing:

name: "Thorstein Flat-Nose"
epithet: "Flat-Nose"
byname_reason: "Broke his nose in a brawl at age 14, never set properly"
backstory: "Born in Hordaland to a family of fishermen. Came to trade after a blood feud forced him from his homeland."
personality:
  - pragmatic
  - cautious
  - dry humor
distinctive_feature: "A crooked nose that lists sharply to the left, with a scar crossing the bridge"
speaking_style: "Speaks slowly and deliberately, as if weighing each word on a merchant's scale"
"""

        try:
            from ai.openrouter import Message
            response = self.ai_client.complete(
                [Message(role="user", content=prompt)],
                temperature=0.9
            )

            # Parse YAML response
            text = response.content.strip()
            # Strip markdown fences if present
            text = re.sub(r'^```(?:yaml)?\s*', '', text)
            text = re.sub(r'\s*```$', '', text)

            data = yaml.safe_load(text)

            if data and isinstance(data, dict):
                # Update identity
                if data.get("name"):
                    identity["name"] = data["name"]
                if data.get("epithet"):
                    identity["epithet"] = data["epithet"]
                if data.get("byname_reason"):
                    identity["byname_reason"] = data["byname_reason"]

                # Update backstory
                backstory = character.get("backstory", {})
                if data.get("backstory"):
                    backstory["summary"] = data["backstory"]
                character["backstory"] = backstory

                # Update personality
                if data.get("personality"):
                    personality = character.get("personality", {})
                    personality["traits"] = data["personality"]
                    character["personality"] = personality

                # Update appearance
                if data.get("distinctive_feature"):
                    appearance = character.get("appearance", {})
                    appearance["distinctive_feature"] = data["distinctive_feature"]
                    character["appearance"] = appearance

                # Add speaking style
                if data.get("speaking_style"):
                    character.setdefault("voice", {})["speaking_style"] = data["speaking_style"]

                # Update metadata
                character.setdefault("meta", {})["renamed_from"] = old_name
                character.setdefault("meta", {})["renamed_date"] = datetime.now().isoformat()
                character.setdefault("meta", {})["needs_rename"] = False
                character.setdefault("meta", {})["needs_expansion"] = False

                character["identity"] = identity

                # Update the character file on disk
                new_id = data["name"].lower().replace(" ", "_").replace("-", "_")
                char_path = self.auto_chars_path / f"{new_id}.yaml"
                with open(char_path, 'w', encoding='utf-8') as f:
                    yaml.dump(character, f, default_flow_style=False, allow_unicode=True)

                logger.info("Renamed placeholder character %s -> %s", old_name, data["name"])

        except Exception as e:
            logger.warning("Rename failed for %s: %s", old_name, e)

        return character

    def batch_rename_placeholders(self, characters: List[Dict], context: Dict = None) -> List[Dict]:
        """
        Scan a list of characters and rename any with placeholder names.

        Args:
            characters: List of character dicts
            context: Optional scene/location context

        Returns:
            Updated list with renamed characters
        """
        renamed_count = 0
        for i, char in enumerate(characters):
            if self.needs_rename(char):
                characters[i] = self.rename_and_flesh_out_character(char, context)
                renamed_count += 1

        if renamed_count:
            logger.info("Renamed %s placeholder character(s)", renamed_count)

        return characters


class AIContentExpander:
    """
    Uses AI to expand minimal character/location data into full entries.
    """
    
    def __init__(self, ai_client, char_generator=None):
        self.ai_client = ai_client
        self.char_generator = char_generator
    
    def expand_character(self, minimal_char: Dict) -> Dict:
        """
        Use AI to expand a minimal character into a full one.
        """
        name = minimal_char.get("identity", {}).get("name", "Unknown")
        context = minimal_char.get("meta", {}).get("extracted_from", "")
        
        prompt = f"""Based on this context about a Viking-era character named "{name}":

{context}

Generate a brief character profile including:
1. Gender (male/female)
2. Approximate age
3. Role/occupation
4. 2-3 personality traits
5. A brief backstory sentence
6. Physical description

Format as YAML:
gender: 
age: 
role: 
traits:
  - 
  - 
backstory: 
appearance: 
"""
        
        try:
            response = self.ai_client.generate(
                prompt=prompt,
                temperature=0.7
            )
            
            # Parse YAML response
            expanded = yaml.safe_load(response)
            if expanded:
                # Merge with existing
                if "gender" in expanded:
                    minimal_char["identity"]["gender"] = expanded["gender"]
                if "age" in expanded:
                    minimal_char["identity"]["age"] = expanded["age"]
                if "role" in expanded:
                    minimal_char["identity"]["role"] = expanded["role"]
                if "traits" in expanded:
                    minimal_char["personality"] = {"traits": expanded["traits"]}
                if "backstory" in expanded:
                    minimal_char["backstory"] = {"summary": expanded["backstory"]}
                if "appearance" in expanded:
                    minimal_char["appearance"] = {"summary": expanded["appearance"]}
                
                minimal_char["meta"]["needs_expansion"] = False
                minimal_char["meta"]["expanded_date"] = datetime.now().isoformat()
                
        except Exception as e:
            logger.warning("Error expanding character %s: %s", name, e)
        
        return minimal_char
    
    def expand_location(self, minimal_loc: Dict) -> Dict:
        """
        Use AI to expand a minimal location into a full one.
        """
        name = minimal_loc.get("name", "Unknown")
        context = minimal_loc.get("meta", {}).get("extracted_from", 
                   minimal_loc.get("description", {}).get("full", ""))
        
        prompt = f"""Based on this context about a Viking-era location called "{name}":

{context}

Generate a location profile including:
1. Type (city/village/hall/temple/forest/cave/etc)
2. Full description (2-3 sentences)
3. Atmosphere/mood
4. What services or features it might have

Format as YAML:
type: 
description: 
atmosphere: 
features:
  - 
"""
        
        try:
            response = self.ai_client.generate(
                prompt=prompt,
                temperature=0.7
            )
            
            expanded = yaml.safe_load(response)
            if expanded:
                if "type" in expanded:
                    minimal_loc["type"] = expanded["type"]
                if "description" in expanded:
                    minimal_loc["description"]["full"] = expanded["description"]
                if "atmosphere" in expanded:
                    minimal_loc["atmosphere"] = expanded["atmosphere"]
                if "features" in expanded:
                    minimal_loc["features"] = expanded["features"]
                
                minimal_loc["meta"]["needs_expansion"] = False
                minimal_loc["meta"]["expanded_date"] = datetime.now().isoformat()
                
        except Exception as e:
            logger.warning("Error expanding location %s: %s", name, e)
        
        return minimal_loc
