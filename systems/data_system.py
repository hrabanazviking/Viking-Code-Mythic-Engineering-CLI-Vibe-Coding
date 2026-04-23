#!/usr/bin/env python3
"""
Data System v3.0 - Robust Future-Proof Data Management
=======================================================

Supports:
- YAML files
- JSON files
- JSONL files (JSON Lines - one JSON object per line)
- Automatic schema migration
- Data validation
- Extensible fields

All data operations go through this system for consistency.
"""

import json
import csv
import importlib
import importlib.util
import re
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, Iterator
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class DataLoader:
    """
    Universal data loader supporting multiple formats.
    """
    
    SUPPORTED_EXTENSIONS = {
        '.yaml', '.yml', '.json', '.jsonl', '.csv', '.cvs', '.txt', '.md',
        '.html', '.htm', '.xml', '.pdf'
    }
    
    @staticmethod
    def load_file(filepath: Union[str, Path]) -> Union[Dict, List[Dict], None]:
        """
        Load data from any supported file format.
        
        Args:
            filepath: Path to the file
            
        Returns:
            Loaded data (dict for YAML/JSON, list of dicts for JSONL)
        """
        filepath = Path(filepath)
        
        if not filepath.exists():
            logger.warning(f"File not found: {filepath}")
            return None
        
        ext = filepath.suffix.lower()
        
        try:
            if ext in {'.yaml', '.yml'}:
                return DataLoader._load_yaml(filepath)
            elif ext == '.json':
                return DataLoader._load_json(filepath)
            elif ext == '.jsonl':
                return DataLoader._load_jsonl(filepath)
            elif ext in {'.csv', '.cvs'}:
                return DataLoader._load_csv(filepath)
            elif ext in {'.txt', '.md', '.html', '.htm', '.xml'}:
                return DataLoader._load_text(filepath)
            elif ext == '.pdf':
                return DataLoader._load_pdf(filepath)
            else:
                logger.warning(f"Unsupported file format: {ext}")
                return None
        except Exception as e:
            logger.error(f"Error loading {filepath}: {e}")
            return None
    
    @staticmethod
    def _load_yaml(filepath: Path) -> Optional[Dict]:
        """Load YAML file."""
        with open(filepath, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    @staticmethod
    def _load_json(filepath: Path) -> Optional[Dict]:
        """Load JSON file."""
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    @staticmethod
    def _load_jsonl(filepath: Path) -> List[Dict]:
        """Load JSONL file (one JSON object per line)."""
        results = []
        with open(filepath, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                try:
                    results.append(json.loads(line))
                except json.JSONDecodeError as e:
                    logger.warning(f"Invalid JSON at line {line_num} in {filepath}: {e}")
        return results

    @staticmethod
    def _load_csv(filepath: Path) -> List[Dict[str, Any]]:
        """Load CSV/CVS file with header row into a list of records."""
        results: List[Dict[str, Any]] = []
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                clean_row = {key: value for key, value in row.items() if key}
                if clean_row:
                    results.append(clean_row)
        return results

    @staticmethod
    def _load_text(filepath: Path) -> Dict[str, Any]:
        """Load plain text file into a chart-friendly payload."""
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        if filepath.suffix.lower() in {'.html', '.htm', '.xml'}:
            content = re.sub(r"<[^>]+>", " ", content)
        lines = [line.strip() for line in content.splitlines() if line.strip()]
        return {
            "content": content,
            "entries": lines,
        }

    @staticmethod
    def _load_pdf(filepath: Path) -> Dict[str, Any]:
        """Load PDF text content into chart-friendly payload."""
        content = ""
        module_name = "pypdf" if importlib.util.find_spec("pypdf") else "PyPDF2"
        if importlib.util.find_spec(module_name):
            reader_mod = importlib.import_module(module_name)
            reader = reader_mod.PdfReader(str(filepath))
            pages = [page.extract_text() or "" for page in reader.pages]
            content = "\n".join(pages)
        else:
            logger.warning("No PDF reader installed; returning empty PDF payload for %s", filepath)
        lines = [line.strip() for line in content.splitlines() if line.strip()]
        return {"content": content, "entries": lines}
    
    @staticmethod
    def iter_jsonl(filepath: Union[str, Path]) -> Iterator[Dict]:
        """
        Iterate over JSONL file without loading all into memory.
        
        Useful for very large files.
        """
        filepath = Path(filepath)
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    try:
                        yield json.loads(line)
                    except json.JSONDecodeError:
                        continue
    
    @staticmethod
    def save_file(
        filepath: Union[str, Path], 
        data: Union[Dict, List],
        format: str = 'yaml'
    ) -> bool:
        """
        Save data to file.
        
        Args:
            filepath: Path to save to
            data: Data to save
            format: 'yaml', 'json', or 'jsonl'
        """
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            if format == 'yaml':
                with open(filepath, 'w', encoding='utf-8') as f:
                    yaml.dump(data, f, allow_unicode=True, default_flow_style=False)
            elif format == 'json':
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
            elif format == 'jsonl':
                with open(filepath, 'w', encoding='utf-8') as f:
                    if isinstance(data, list):
                        for item in data:
                            f.write(json.dumps(item, ensure_ascii=False) + '\n')
                    else:
                        f.write(json.dumps(data, ensure_ascii=False) + '\n')
            else:
                logger.error(f"Unknown format: {format}")
                return False
            
            return True
        except Exception as e:
            logger.error(f"Error saving {filepath}: {e}")
            return False
    
    @staticmethod
    def append_jsonl(filepath: Union[str, Path], data: Dict) -> bool:
        """Append a single record to a JSONL file."""
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(filepath, 'a', encoding='utf-8') as f:
                f.write(json.dumps(data, ensure_ascii=False) + '\n')
            return True
        except Exception as e:
            logger.error(f"Error appending to {filepath}: {e}")
            return False


class ChartLoader:
    """
    Loads chart/table data from multiple file formats.
    
    Charts can be:
    - YAML with 'entries' or 'items' list
    - JSON with array or object with entries
    - JSONL with one entry per line
    """
    
    def __init__(self, charts_path: str = "data/charts"):
        self.charts_path = Path(charts_path)
        self.charts: Dict[str, List[Dict]] = {}
        self._chart_metadata: Dict[str, Dict] = {}
        self._raw_charts: Dict[str, Any] = {}  # Store raw data for reference charts
    
    def load_all_charts(self):
        """Load all charts from the charts directory."""
        if not self.charts_path.exists():
            logger.warning(f"Charts path not found: {self.charts_path}")
            return
        
        for filepath in self.charts_path.iterdir():
            if filepath.suffix.lower() in DataLoader.SUPPORTED_EXTENSIONS:
                self.load_chart(filepath)
    
    def load_chart(self, filepath: Union[str, Path]) -> Optional[List[Dict]]:
        """
        Load a single chart file.
        
        Returns the list of entries.
        """
        filepath = Path(filepath)
        chart_name = filepath.stem
        
        data = DataLoader.load_file(filepath)
        if data is None:
            return None
        
        entries = []
        metadata = {}
        
        if isinstance(data, list):
            # JSONL or JSON array
            entries = data
        elif isinstance(data, dict):
            # YAML or JSON object
            # Look for entries in common keys
            for key in ['entries', 'items', 'runes', 'values', 'data', 'records']:
                if key in data:
                    entries = data[key]
                    break
            
            # Store metadata
            for key in ['name', 'description', 'version', 'mechanics']:
                if key in data:
                    metadata[key] = data[key]
        
        # Always store raw data for direct access
        self._raw_charts[chart_name] = data
        
        if entries:
            self.charts[chart_name] = entries
            self._chart_metadata[chart_name] = metadata
            logger.info(f"Loaded chart '{chart_name}' with {len(entries)} entries")
            return entries
        
        # For reference/lookup charts without standard entries, just log at debug
        logger.debug(f"Chart '{chart_name}' loaded as reference data (no standard entries)")
        return None
    
    def get_raw_chart(self, name: str) -> Any:
        """Get raw chart data by name (for reference charts without standard entries)."""
        return self._raw_charts.get(name)
    
    def get_chart(self, name: str) -> List[Dict]:
        """Get a chart by name."""
        return self.charts.get(name, [])
    
    def get_random_entry(self, chart_name: str) -> Optional[Dict]:
        """Get a random entry from a chart."""
        import random
        chart = self.charts.get(chart_name, [])
        if chart:
            return random.choice(chart)
        return None
    
    def get_entries_by_field(
        self, 
        chart_name: str, 
        field: str, 
        value: Any
    ) -> List[Dict]:
        """Get entries matching a field value."""
        chart = self.charts.get(chart_name, [])
        return [e for e in chart if e.get(field) == value]
    
    def sample_entries(
        self, 
        chart_name: str, 
        count: int = 1
    ) -> List[Dict]:
        """Get random sample of entries."""
        import random
        chart = self.charts.get(chart_name, [])
        if not chart:
            return []
        return random.sample(chart, min(count, len(chart)))
    
    def list_charts(self) -> List[str]:
        """List all loaded chart names."""
        return list(self.charts.keys())
    
    def get_chart_info(self, name: str) -> Dict:
        """Get metadata about a chart."""
        return {
            'name': name,
            'entries': len(self.charts.get(name, [])),
            'metadata': self._chart_metadata.get(name, {})
        }


class CharacterDatabase:
    """
    Robust character data management with schema migration.
    """
    
    # Current schema version
    SCHEMA_VERSION = "3.0"
    
    # Default fields for all characters
    DEFAULT_SCHEMA = {
        "id": "",
        "identity": {
            "name": "Unknown",
            "gender": "unknown",
            "age": 30,
            "culture": "norse_swedish",
            "class": "fighter",
            "level": 1,
            "role": ""
        },
        "stats": {
            "strength": 10,
            "dexterity": 10,
            "constitution": 10,
            "intelligence": 10,
            "wisdom": 10,
            "charisma": 10,
            "hp_max": 10,
            "hp_current": 10,
            "ac": 10
        },
        "personality": {
            "traits": [],
            "alignment": "neutral",
            "mbti": "",
            "enneagram": "",
            "temperament": "",
            "spirituality": ""
        },
        "religion": {
            "religion": "norse_pagan",
            "religion_display": "Norse Paganism",
            "patron": "",
            "patron_domains": [],
            "devotion_level": "moderate"
        },
        "appearance": {
            "summary": "",
            "build": "",
            "hair": "",
            "eyes": "",
            "distinguishing_features": "",
            "religious_symbol": ""
        },
        "backstory": {
            "summary": "",
            "origin": "",
            "events": []
        },
        "equipment": {
            "weapons": [],
            "armor": "",
            "items": []
        },
        "relationships": {
            "allies": [],
            "enemies": [],
            "family": []
        },
        "emotion_profile": {
            "tf_axis": 0.50,
            "gender_axis": 0.0,
            "individual_offset": 0.0,
            "baseline_intensity": 1.0,
            "expression_threshold": 0.55,
            "rumination_bias": 0.30,
            "decay_rate": 0.10,
            "channel_weights": {
                "fear": 1.0,
                "anger": 1.0,
                "sadness": 1.0,
                "joy": 1.0,
                "shame": 0.9,
                "attachment": 1.0,
            },
            "chronotype": "diurnal",
            "stress_resistance": 0.5,
        },
        "meta": {
            "schema_version": SCHEMA_VERSION,
            "created": "",
            "last_updated": "",
            "auto_generated": False,
            "source": "manual"
        }
    }
    
    def __init__(self, data_path: str = "data"):
        self.data_path = Path(data_path)
        self.characters_path = self.data_path / "characters"
        self.auto_chars_path = self.data_path / "auto_generated" / "characters"
        
        # Ensure directories exist
        self.auto_chars_path.mkdir(parents=True, exist_ok=True)
        
        # Cache
        self._character_cache: Dict[str, Dict] = {}
    
    def load_character(self, char_id: str) -> Optional[Dict]:
        """Load a character by ID, checking all locations."""
        # Check cache first
        if char_id in self._character_cache:
            return self._character_cache[char_id]
        
        # Search locations
        search_paths = [
            self.characters_path / "player_characters",
            self.characters_path / "npcs",
            self.characters_path / "npcs" / "scandinavia",
            self.characters_path / "villains",
            self.auto_chars_path
        ]
        
        for search_path in search_paths:
            if not search_path.exists():
                continue
            
            # Check YAML
            yaml_file = search_path / f"{char_id}.yaml"
            if yaml_file.exists():
                char = DataLoader.load_file(yaml_file)
                if char:
                    char = self._migrate_schema(char)
                    self._character_cache[char_id] = char
                    return char
            
            # Check JSON
            json_file = search_path / f"{char_id}.json"
            if json_file.exists():
                char = DataLoader.load_file(json_file)
                if char:
                    char = self._migrate_schema(char)
                    self._character_cache[char_id] = char
                    return char
        
        return None
    
    def save_character(self, character: Dict, auto_generated: bool = False) -> bool:
        """Save a character."""
        char_id = character.get('id', '')
        if not char_id:
            logger.error("Character has no ID")
            return False
        
        # Update metadata
        character.setdefault('meta', {})
        character['meta']['schema_version'] = self.SCHEMA_VERSION
        character['meta']['last_updated'] = datetime.now().isoformat()
        
        # Choose save location
        if auto_generated or character.get('meta', {}).get('auto_generated'):
            save_path = self.auto_chars_path / f"{char_id}.yaml"
        else:
            save_path = self.characters_path / "npcs" / f"{char_id}.yaml"
        
        success = DataLoader.save_file(save_path, character, format='yaml')
        
        if success:
            self._character_cache[char_id] = character
        
        return success
    
    def _migrate_schema(self, character: Dict) -> Dict:
        """Migrate character to current schema version."""
        current_version = character.get('meta', {}).get('schema_version', '1.0')
        
        if current_version == self.SCHEMA_VERSION:
            return character
        
        # Add missing fields from default schema
        migrated = self._deep_merge(self.DEFAULT_SCHEMA.copy(), character)
        
        # Mark as migrated
        migrated['meta']['schema_version'] = self.SCHEMA_VERSION
        migrated['meta']['last_migrated'] = datetime.now().isoformat()
        
        return migrated
    
    def _deep_merge(self, base: Dict, override: Dict) -> Dict:
        """Deep merge two dictionaries."""
        result = base.copy()
        
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def list_all_characters(self) -> List[str]:
        """List all character IDs."""
        char_ids = set()
        
        search_paths = [
            self.characters_path,
            self.auto_chars_path
        ]
        
        for search_path in search_paths:
            if not search_path.exists():
                continue
            
            for filepath in search_path.rglob("*.yaml"):
                char_ids.add(filepath.stem)
            for filepath in search_path.rglob("*.json"):
                char_ids.add(filepath.stem)
        
        return sorted(char_ids)
    
    def batch_migrate_all(self) -> int:
        """
        Migrate all characters to current schema.
        
        Returns number of characters migrated.
        """
        migrated = 0
        
        for char_id in self.list_all_characters():
            char = self.load_character(char_id)
            if char:
                old_version = char.get('meta', {}).get('schema_version', '1.0')
                if old_version != self.SCHEMA_VERSION:
                    # Save will trigger migration
                    if self.save_character(char, char.get('meta', {}).get('auto_generated', False)):
                        migrated += 1
                        logger.info(f"Migrated {char_id} from {old_version} to {self.SCHEMA_VERSION}")
        
        return migrated
    
    def clear_cache(self):
        """Clear the character cache."""
        self._character_cache.clear()


class LocationDatabase:
    """
    Robust location data management.
    """
    
    def __init__(self, data_path: str = "data"):
        self.data_path = Path(data_path)
        self.world_path = self.data_path / "world"
        self.auto_locations_path = self.data_path / "auto_generated" / "locations"
        
        self.auto_locations_path.mkdir(parents=True, exist_ok=True)
        
        self._location_cache: Dict[str, Dict] = {}
    
    def load_location(self, loc_id: str) -> Optional[Dict]:
        """Load a location by ID."""
        if loc_id in self._location_cache:
            return self._location_cache[loc_id]
        
        search_paths = [
            self.world_path / "cities",
            self.world_path / "regions",
            self.world_path,
            self.auto_locations_path
        ]
        
        for search_path in search_paths:
            if not search_path.exists():
                continue
            
            for ext in ['.yaml', '.json']:
                filepath = search_path / f"{loc_id}{ext}"
                if filepath.exists():
                    loc = DataLoader.load_file(filepath)
                    if loc:
                        self._location_cache[loc_id] = loc
                        return loc
        
        return None
    
    def save_location(self, location: Dict, auto_generated: bool = False) -> bool:
        """Save a location."""
        loc_id = location.get('id', '')
        if not loc_id:
            return False
        
        location.setdefault('meta', {})
        location['meta']['last_updated'] = datetime.now().isoformat()
        
        if auto_generated or location.get('meta', {}).get('auto_generated'):
            save_path = self.auto_locations_path / f"{loc_id}.yaml"
        else:
            save_path = self.world_path / "cities" / f"{loc_id}.yaml"
        
        return DataLoader.save_file(save_path, location, format='yaml')
    
    def list_all_locations(self) -> List[str]:
        """List all location IDs."""
        loc_ids = set()
        
        for search_path in [self.world_path, self.auto_locations_path]:
            if search_path.exists():
                for filepath in search_path.rglob("*.yaml"):
                    loc_ids.add(filepath.stem)
                for filepath in search_path.rglob("*.json"):
                    loc_ids.add(filepath.stem)
        
        return sorted(loc_ids)


class DataManager:
    """
    Central data management hub.
    
    Coordinates all data systems for consistent access.
    """
    
    def __init__(self, data_path: str = "data"):
        self.data_path = Path(data_path)
        
        # Initialize subsystems
        self.charts = ChartLoader(str(self.data_path / "charts"))
        self.characters = CharacterDatabase(str(self.data_path))
        self.locations = LocationDatabase(str(self.data_path))
        
        # Load charts on init
        self.charts.load_all_charts()
    
    def get_chart(self, name: str) -> List[Dict]:
        """Get a chart by name."""
        return self.charts.get_chart(name)
    
    def get_character(self, char_id: str) -> Optional[Dict]:
        """Get a character by ID."""
        return self.characters.load_character(char_id)
    
    def save_character(self, character: Dict, auto: bool = False) -> bool:
        """Save a character."""
        return self.characters.save_character(character, auto)
    
    def get_location(self, loc_id: str) -> Optional[Dict]:
        """Get a location by ID."""
        return self.locations.load_location(loc_id)
    
    def save_location(self, location: Dict, auto: bool = False) -> bool:
        """Save a location."""
        return self.locations.save_location(location, auto)
    
    def get_random_chart_entry(self, chart_name: str) -> Optional[Dict]:
        """Get random entry from a chart."""
        return self.charts.get_random_entry(chart_name)
    
    def run_schema_migration(self) -> int:
        """Run schema migration on all characters."""
        return self.characters.batch_migrate_all()
