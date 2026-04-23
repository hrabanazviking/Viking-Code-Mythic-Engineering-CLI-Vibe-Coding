"""AI-directed location graph and movement manager."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import yaml

logger = logging.getLogger(__name__)


@dataclass
class LocationResolution:
    """Resolved location target from user intent or state-intent payload."""

    city_id: str
    sub_location_id: str = ""
    display_name: str = ""
    source: str = ""


@dataclass
class LocationStateChangeReport:
    """Tracks what happened while applying location intent."""

    created_locations: List[str] = field(default_factory=list)
    moved_player: bool = False
    moved_npcs: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class LocationAIManager:
    """Huginn maps travel threads while Muninn preserves location canon."""

    def __init__(self, data_path: str):
        self.data_path = Path(data_path)
        self.auto_locations_path = self.data_path / "auto_generated" / "locations"
        self.auto_locations_path.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def normalize_token(value: str) -> str:
        token = (value or "").strip().lower().replace("-", "_")
        token = re.sub(r"\s+", "_", token)
        token = re.sub(r"[^a-z0-9_]", "", token)
        return token

    def _candidate_tokens(self, city_data: Dict[str, Any]) -> Iterable[str]:
        fields = [
            city_data.get("id", ""),
            city_data.get("name", ""),
            city_data.get("name_old_norse", ""),
            city_data.get("region", ""),
        ]
        for value in fields:
            token = self.normalize_token(str(value))
            if token:
                yield token

    def load_generated_locations(self) -> List[Dict[str, Any]]:
        records: List[Dict[str, Any]] = []
        try:
            for path in sorted(self.auto_locations_path.glob("*.yaml")):
                with path.open("r", encoding="utf-8") as handle:
                    data = yaml.safe_load(handle) or {}
                if isinstance(data, dict):
                    records.append(data)
        except Exception as exc:
            logger.warning("Generated location load skipped: %s", exc)
        return records

    def persist_generated_location(self, payload: Dict[str, Any]) -> Optional[str]:
        try:
            loc_id = self.normalize_token(str(payload.get("id") or payload.get("name") or ""))
            if not loc_id:
                return None
            parent_city = self.normalize_token(str(payload.get("parent_city") or payload.get("city_id") or ""))
            location = {
                "id": loc_id,
                "name": payload.get("name", loc_id.replace("_", " ").title()),
                "type": payload.get("type", "dynamic"),
                "parent_city": parent_city,
                "travel_mode": payload.get("travel_mode", "local"),
                "description": payload.get("description", {}),
                "connections": payload.get("connections", []),
                # SRD combat hazards: conditions with elevated probability at this location
                "combat_hazards": payload.get("combat_hazards", []),
                "meta": {
                    "auto_generated": True,
                    "generated_by": payload.get("generated_by", "state_intent"),
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                },
            }
            path = self.auto_locations_path / f"{loc_id}.yaml"
            with path.open("w", encoding="utf-8") as handle:
                yaml.safe_dump(location, handle, allow_unicode=True, sort_keys=False)
            return loc_id
        except Exception as exc:
            logger.warning("Generated location persist failed: %s", exc)
            return None

    def resolve_destination(
        self,
        destination: str,
        *,
        current_city_id: str,
        city_data: Dict[str, Any],
        generated_locations: List[Dict[str, Any]],
        city_catalog: Optional[List[Dict[str, Any]]] = None,
    ) -> Optional[LocationResolution]:
        needle = self.normalize_token(destination)
        if not needle:
            return None

        current_city = self.normalize_token(current_city_id)

        catalog_index: Dict[str, Dict[str, Any]] = {}
        for city in city_catalog or []:
            city_id = self.normalize_token(str(city.get("id", "")))
            if city_id:
                catalog_index[city_id] = city

        for loc in (city_data.get("grid", {}) or {}).get("locations", []):
            loc_id = self.normalize_token(str(loc.get("id", "")))
            loc_name = self.normalize_token(str(loc.get("name", "")))
            if needle in {loc_id, loc_name} or needle in loc_name:
                return LocationResolution(
                    city_id=current_city,
                    sub_location_id=loc_id,
                    display_name=str(loc.get("name", "")) or destination,
                    source="city_grid",
                )

        for loc in generated_locations:
            loc_id = self.normalize_token(str(loc.get("id", "")))
            loc_name = self.normalize_token(str(loc.get("name", "")))
            parent_city = self.normalize_token(str(loc.get("parent_city", "")))
            if not (needle in {loc_id, loc_name} or needle in loc_name):
                continue
            if parent_city and parent_city != current_city:
                return LocationResolution(
                    city_id=parent_city,
                    sub_location_id=loc_id,
                    display_name=str(loc.get("name", "")) or destination,
                    source="generated_cross_city",
                )
            return LocationResolution(
                city_id=current_city,
                sub_location_id=loc_id,
                display_name=str(loc.get("name", "")) or destination,
                source="generated_local",
            )

        for connection in city_data.get("connections", []):
            dest_id = self.normalize_token(str(connection.get("destination", "")))
            connected_city = catalog_index.get(dest_id, {})
            connected_tokens = set(self._candidate_tokens(connected_city))
            if needle in connected_tokens:
                return LocationResolution(
                    city_id=dest_id,
                    sub_location_id="",
                    display_name=str(connected_city.get("name", ""))
                    or str(connection.get("destination", ""))
                    or destination,
                    source="city_connection_metadata",
                )
            if needle == dest_id or needle in dest_id:
                return LocationResolution(
                    city_id=dest_id,
                    sub_location_id="",
                    display_name=str(connection.get("destination", "")) or destination,
                    source="city_connection",
                )

        region_matches: List[Dict[str, Any]] = []
        for connection in city_data.get("connections", []):
            dest_id = self.normalize_token(str(connection.get("destination", "")))
            connected_city = catalog_index.get(dest_id, {})
            connected_region = self.normalize_token(str(connected_city.get("region", "")))
            if connected_region and connected_region == needle:
                region_matches.append(connected_city)

        if len(region_matches) == 1:
            match = region_matches[0]
            return LocationResolution(
                city_id=self.normalize_token(str(match.get("id", ""))),
                sub_location_id="",
                display_name=str(match.get("name", "")) or destination,
                source="city_region_connection",
            )

        if needle == current_city:
            return LocationResolution(
                city_id=current_city,
                sub_location_id="",
                display_name=current_city_id,
                source="current_city",
            )
        return None

    def can_reach_in_one_turn(
        self,
        *,
        origin_city_id: str,
        destination: LocationResolution,
        city_data: Dict[str, Any],
        destination_city_data: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str]:
        origin_city = self.normalize_token(origin_city_id)
        if destination.city_id == origin_city:
            return True, "local_move"

        for connection in city_data.get("connections", []):
            dest_id = self.normalize_token(str(connection.get("destination", "")))
            if dest_id != destination.city_id:
                continue
            days = int(connection.get("distance_days", 1) or 1)
            if days <= 1:
                return True, "direct_fast_route"
            return False, f"distance_days_{days}"

        # Fallback for generated cross-city locations that include explicit one_turn hint
        dest_connections = (destination_city_data or {}).get("connections", [])
        for connection in dest_connections:
            dest_id = self.normalize_token(str(connection.get("destination", "")))
            if dest_id == origin_city and int(connection.get("distance_days", 1) or 1) <= 1:
                return True, "reverse_fast_route"

        return False, "no_single_turn_route"
