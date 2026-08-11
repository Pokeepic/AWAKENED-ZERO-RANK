"""Stable read-only state projection for observer applications."""

from __future__ import annotations

import hashlib
import hmac
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import TYPE_CHECKING, Any

from .content import PORTALS
from .environment import SUMMER_WEATHER
from .story import story_progress
from .world import ITEMS, LOCATIONS

if TYPE_CHECKING:
    from .simulation import Simulation


OBSERVER_SNAPSHOT_SCHEMA_VERSION = 4
RECENT_EVENT_LIMIT = 12
KEY_MEMORY_LIMIT = 5
_SNAPSHOT_KEYS = {
    "activity", "clock", "economy", "environment", "identity", "portals",
    "protagonist", "relationships", "schema_version", "seed", "story",
}
_SLOTS = ("Morning", "Afternoon", "Evening", "Late Night")
_RESOURCE_KEYS = {"energy", "health", "hunger", "money", "morale", "stress"}
_PROTAGONIST_KEYS = {
    "ability", "current_goal", "equipment", "hunter_rank", "location", "mood",
    "name", "progression", "resources",
}
_EQUIPMENT_KEYS = {"armor", "inventory", "weapon"}
_PROGRESSION_KEYS = {
    "ability_mastery", "combat_readiness", "fitness", "knowledge",
    "missions_attempted", "missions_completed", "rank_points",
}
_HUNTER_RANKS = {"Unranked", "F", "E", "D", "C"}
_RELATIONSHIP_KEYS = {
    "affection", "familiarity", "loyalty", "name", "role", "tension", "trust",
}
_EVENT_KEYS = {"action", "day", "outcome", "reason", "slot"}
_MEMORY_KEYS = {"day", "importance", "summary"}
_ENVIRONMENT_KEYS = {"gate_alert_level", "season", "temperature_c", "weather"}
_PORTAL_KEYS = {"active_plan", "discovered", "investigations"}
_INVESTIGATION_KEYS = {
    "cooperating_npc", "joint_missions", "portal_name", "preparation_bonus",
    "preparation_strategy", "progress", "risk",
}
_PORTAL_NAMES = {portal.name for portal in PORTALS}
_WEATHER_TEMPERATURES = {
    weather.name: weather.temperature_c for weather in SUMMER_WEATHER
}


def _content_digest(snapshot: dict[str, Any]) -> str:
    content = {
        key: value for key, value in snapshot.items()
        if key not in {"identity", "path"}
    }
    canonical = json.dumps(
        content, ensure_ascii=False, sort_keys=True,
        separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _integer(value: Any, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(f"Observer snapshot {label} is invalid")
    return value


def _validate_activity(activity: Any, current_day: int) -> None:
    if not isinstance(activity, dict) or set(activity) != {
            "key_memories", "recent_events"}:
        raise ValueError("Observer snapshot activity is malformed")
    events = activity["recent_events"]
    memories = activity["key_memories"]
    if not isinstance(events, list) or len(events) > RECENT_EVENT_LIMIT:
        raise ValueError("Observer snapshot recent events are invalid")
    positions: list[tuple[int, int]] = []
    for event in events:
        if not isinstance(event, dict) or set(event) != _EVENT_KEYS:
            raise ValueError("Observer snapshot recent event is malformed")
        day = _integer(event["day"], "recent event day")
        if not 1 <= day <= current_day or event["slot"] not in _SLOTS:
            raise ValueError("Observer snapshot recent event chronology is invalid")
        if any(
                not isinstance(event[field], str) or not event[field]
                for field in ("action", "outcome", "reason")):
            raise ValueError("Observer snapshot recent event text is invalid")
        positions.append((day, _SLOTS.index(event["slot"])))
    if positions != sorted(positions):
        raise ValueError("Observer snapshot recent events are out of order")
    if not isinstance(memories, list) or len(memories) > KEY_MEMORY_LIMIT:
        raise ValueError("Observer snapshot key memories are invalid")
    memory_order: list[tuple[int, int]] = []
    for memory in memories:
        if not isinstance(memory, dict) or set(memory) != _MEMORY_KEYS:
            raise ValueError("Observer snapshot key memory is malformed")
        day = _integer(memory["day"], "key memory day")
        importance = _integer(memory["importance"], "key memory importance")
        if not 1 <= day <= current_day or not 1 <= importance <= 10:
            raise ValueError("Observer snapshot key memory values are invalid")
        if not isinstance(memory["summary"], str) or not memory["summary"]:
            raise ValueError("Observer snapshot key memory summary is invalid")
        memory_order.append((-importance, -day))
    if memory_order != sorted(memory_order):
        raise ValueError("Observer snapshot key memories are out of order")


def _validate_environment(environment: Any) -> None:
    if not isinstance(environment, dict) or set(environment) != _ENVIRONMENT_KEYS:
        raise ValueError("Observer snapshot environment is malformed")
    alert = _integer(environment["gate_alert_level"], "gate alert level")
    temperature = _integer(environment["temperature_c"], "temperature")
    weather = environment["weather"]
    if not 0 <= alert <= 3:
        raise ValueError("Observer snapshot gate alert level is invalid")
    if (
            environment["season"] != "Summer" or
            weather not in _WEATHER_TEMPERATURES or
            temperature != _WEATHER_TEMPERATURES[weather]):
        raise ValueError("Observer snapshot environment conditions are invalid")


def _validate_portals(portals: Any) -> None:
    if not isinstance(portals, dict) or set(portals) != _PORTAL_KEYS:
        raise ValueError("Observer snapshot portals are malformed")
    discovered = portals["discovered"]
    if (
            not isinstance(discovered, list) or
            any(
                not isinstance(name, str) or name not in _PORTAL_NAMES
                for name in discovered
            ) or
            len(discovered) != len(set(discovered))):
        raise ValueError("Observer snapshot discovered portals are invalid")
    investigations = portals["investigations"]
    if not isinstance(investigations, list):
        raise ValueError("Observer snapshot portal investigations are malformed")
    names: list[str] = []
    for investigation in investigations:
        if (
                not isinstance(investigation, dict) or
                set(investigation) != _INVESTIGATION_KEYS):
            raise ValueError("Observer snapshot portal investigation is malformed")
        name = investigation["portal_name"]
        strategy = investigation["preparation_strategy"]
        cooperating_npc = investigation["cooperating_npc"]
        if (
                not isinstance(name, str) or name not in _PORTAL_NAMES or
                not isinstance(strategy, str) or not strategy or
                cooperating_npc is not None and (
                    not isinstance(cooperating_npc, str) or not cooperating_npc)):
            raise ValueError("Observer snapshot portal investigation text is invalid")
        progress = _integer(investigation["progress"], "portal progress")
        risk = _integer(investigation["risk"], "portal risk")
        preparation_bonus = _integer(
            investigation["preparation_bonus"], "portal preparation bonus")
        joint_missions = _integer(
            investigation["joint_missions"], "portal joint missions")
        if (
                not 0 <= progress <= 100 or not 0 <= risk <= 100 or
                preparation_bonus < 0 or joint_missions < 0):
            raise ValueError("Observer snapshot portal investigation bounds are invalid")
        names.append(name)
    if names != sorted(set(names)):
        raise ValueError("Observer snapshot portal investigations are not canonical")
    active_plan = portals["active_plan"]
    if active_plan is not None and active_plan not in names:
        raise ValueError("Observer snapshot active portal plan is invalid")

def _validate_economy(economy: Any) -> None:
    keys = {
        "meal_cost", "rent_arrears", "rent_cost", "rent_due_day",
        "rent_payments", "shop_visits", "wage_modifier",
    }
    if not isinstance(economy, dict) or set(economy) != keys:
        raise ValueError("Observer snapshot economy is malformed")
    values = {
        name: _integer(value, f"economy {name}")
        for name, value in economy.items()
    }
    if values["rent_due_day"] < 1 or any(
            values[name] < 0 for name in (
                "rent_arrears", "rent_cost", "rent_payments", "shop_visits")):
        raise ValueError("Observer snapshot economy bounds are invalid")
    if values["wage_modifier"] not in {85, 95, 100, 105, 115}:
        raise ValueError("Observer snapshot wage modifier is invalid")
    if values["meal_cost"] not in {500, 600, 700, 800}:
        raise ValueError("Observer snapshot meal cost is invalid")

def _validate_protagonist(protagonist: Any) -> None:
    if not isinstance(protagonist, dict) or set(protagonist) != _PROTAGONIST_KEYS:
        raise ValueError("Observer snapshot protagonist is malformed")
    if any(
            not isinstance(protagonist[name], str) or not protagonist[name]
            for name in ("ability", "current_goal", "mood", "name")):
        raise ValueError("Observer snapshot protagonist identity is invalid")
    hunter_rank = protagonist["hunter_rank"]
    location = protagonist["location"]
    if (
            not isinstance(hunter_rank, str) or hunter_rank not in _HUNTER_RANKS or
            not isinstance(location, str) or location not in LOCATIONS):
        raise ValueError("Observer snapshot protagonist status is invalid")

    resources = protagonist["resources"]
    if not isinstance(resources, dict) or set(resources) != _RESOURCE_KEYS:
        raise ValueError("Observer snapshot resources are malformed")
    resource_values = {
        name: _integer(value, f"resource {name}")
        for name, value in resources.items()
    }
    if resource_values["money"] < 0 or any(
            not 0 <= resource_values[name] <= 100
            for name in _RESOURCE_KEYS - {"money"}):
        raise ValueError("Observer snapshot resource bounds are invalid")

    progression = protagonist["progression"]
    if not isinstance(progression, dict) or set(progression) != _PROGRESSION_KEYS:
        raise ValueError("Observer snapshot progression is malformed")
    progression_values = {
        name: _integer(value, f"progression {name}")
        for name, value in progression.items()
    }
    if (
            any(
                not 0 <= progression_values[name] <= 100
                for name in ("ability_mastery", "combat_readiness")
            ) or
            any(
                progression_values[name] < 0
                for name in (
                    "fitness", "knowledge", "missions_attempted",
                    "missions_completed", "rank_points",
                )
            )):
        raise ValueError("Observer snapshot progression bounds are invalid")
    if (
            progression_values["missions_completed"] >
            progression_values["missions_attempted"]):
        raise ValueError("Observer snapshot mission counters are invalid")

    equipment = protagonist["equipment"]
    if not isinstance(equipment, dict) or set(equipment) != _EQUIPMENT_KEYS:
        raise ValueError("Observer snapshot equipment is malformed")
    for field, expected_kind in (("weapon", "weapon"), ("armor", "armor")):
        item_name = equipment[field]
        if item_name is None:
            continue
        item = ITEMS.get(item_name) if isinstance(item_name, str) else None
        if item is None or item.kind != expected_kind:
            raise ValueError(
                f"Observer snapshot equipped {expected_kind} is invalid")
    inventory = equipment["inventory"]
    if not isinstance(inventory, dict):
        raise ValueError("Observer snapshot inventory is malformed")
    if any(not isinstance(item_name, str) or not item_name for item_name in inventory):
        raise ValueError("Observer snapshot inventory item is invalid")
    if list(inventory) != sorted(inventory):
        raise ValueError("Observer snapshot inventory is not canonical")
    for item_name, quantity in inventory.items():
        if _integer(quantity, f"inventory {item_name}") < 1:
            raise ValueError("Observer snapshot inventory quantity is invalid")


def _validate_relationships(relationships: Any) -> None:
    if not isinstance(relationships, list):
        raise ValueError("Observer snapshot relationships are malformed")
    names: list[str] = []
    for relationship in relationships:
        if (
                not isinstance(relationship, dict) or
                set(relationship) != _RELATIONSHIP_KEYS):
            raise ValueError("Observer snapshot relationship is malformed")
        name, role = relationship["name"], relationship["role"]
        if not isinstance(name, str) or not name or not isinstance(role, str) or not role:
            raise ValueError("Observer snapshot relationship identity is invalid")
        names.append(name)
        metrics = {
            key: _integer(relationship[key], f"relationship {key}")
            for key in _RELATIONSHIP_KEYS - {"name", "role"}
        }
        if any(
                not -100 <= metrics[key] <= 100
                for key in ("affection", "trust")):
            raise ValueError("Observer snapshot relationship sentiment is invalid")
        if any(
                not 0 <= metrics[key] <= 100
                for key in ("familiarity", "loyalty", "tension")):
            raise ValueError("Observer snapshot relationship metric is invalid")
    if names != sorted(set(names)):
        raise ValueError("Observer snapshot relationships are not canonical")


def _validate_snapshot_semantics(snapshot: dict[str, Any]) -> int:
    clock = snapshot["clock"]
    if not isinstance(clock, dict) or set(clock) != {"day", "slot"}:
        raise ValueError("Observer snapshot clock is invalid")
    day = _integer(clock["day"], "clock day")
    if day < 1 or clock["slot"] not in _SLOTS:
        raise ValueError("Observer snapshot clock is invalid")
    _validate_activity(snapshot["activity"], day)
    _validate_economy(snapshot["economy"])
    _validate_environment(snapshot["environment"])
    _validate_portals(snapshot["portals"])
    _validate_protagonist(snapshot["protagonist"])
    _validate_relationships(snapshot["relationships"])
    story = snapshot["story"]
    if not isinstance(story, dict) or story.get("schema_version") != 3:
        raise ValueError("Observer snapshot story projection is invalid")
    return day


def verify_observer_snapshot(snapshot: dict[str, Any]) -> dict[str, Any]:
    """Verify schema and canonical content identity without claiming authorship."""
    if not isinstance(snapshot, dict):
        raise TypeError("Observer snapshot must be a JSON object")
    keys = set(snapshot)
    if keys not in (_SNAPSHOT_KEYS, _SNAPSHOT_KEYS | {"path"}):
        raise ValueError("Observer snapshot has missing or unknown top-level fields")
    if "path" in snapshot and not isinstance(snapshot["path"], str):
        raise ValueError("Observer snapshot path provenance must be a string")
    if snapshot["schema_version"] != OBSERVER_SNAPSHOT_SCHEMA_VERSION:
        raise ValueError(
            f"Unsupported observer snapshot schema: {snapshot['schema_version']}")
    identity = snapshot["identity"]
    if not isinstance(identity, dict) or set(identity) != {"algorithm", "digest"}:
        raise ValueError("Observer snapshot identity is malformed")
    if identity["algorithm"] != "sha256":
        raise ValueError("Unsupported observer snapshot identity algorithm")
    claimed = identity["digest"]
    if not isinstance(claimed, str) or len(claimed) != 64:
        raise ValueError("Observer snapshot digest is malformed")
    actual = _content_digest(snapshot)
    if not hmac.compare_digest(claimed, actual):
        raise ValueError("Observer snapshot integrity check failed")
    _integer(snapshot["seed"], "seed")
    day = _validate_snapshot_semantics(snapshot)
    return {
        "day": day,
        "digest": claimed,
        "schema_version": OBSERVER_SNAPSHOT_SCHEMA_VERSION,
        "seed": snapshot["seed"],
        "status": "valid",
    }


def save_observer_snapshot(
        snapshot: dict[str, Any], destination: str | Path) -> Path:
    """Validate, stage, and publish a non-overwriting snapshot artifact."""
    verify_observer_snapshot(snapshot)
    target = Path(destination)
    if target.exists():
        raise ValueError("Observer snapshot destination already exists")
    target.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(
            prefix=f".{target.name}.staging-", dir=target.parent) as temporary:
        staging = Path(temporary) / target.name
        staging.write_text(
            json.dumps(
                snapshot, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        loaded = json.loads(staging.read_text(encoding="utf-8"))
        verify_observer_snapshot(loaded)
        if loaded != snapshot:
            raise ValueError("Observer snapshot staging verification failed")
        if target.exists():
            raise ValueError(
                "Observer snapshot destination appeared during staging")
        staging.rename(target)
    return target


def observer_snapshot(simulation: Simulation) -> dict[str, Any]:
    """Return deterministic, JSON-ready current state without advancing the world."""
    state = simulation.state
    protagonist = state.protagonist
    relationships = [
        {
            "affection": relationship.affection,
            "familiarity": relationship.familiarity,
            "loyalty": relationship.loyalty,
            "name": relationship.name,
            "role": relationship.role,
            "tension": relationship.tension,
            "trust": relationship.trust,
        }
        for _, relationship in sorted(protagonist.relationships.items())
    ]
    investigations = [
        {
            "cooperating_npc": investigation.cooperating_npc,
            "joint_missions": investigation.joint_missions,
            "portal_name": investigation.portal_name,
            "preparation_bonus": investigation.preparation_bonus,
            "preparation_strategy": investigation.preparation_strategy,
            "progress": investigation.progress,
            "risk": investigation.risk,
        }
        for _, investigation in sorted(state.portal_investigations.items())
    ]
    recent_events = [
        {
            "action": event.action,
            "day": event.day,
            "outcome": event.outcome,
            "reason": event.reason,
            "slot": event.slot.value,
        }
        for event in state.events[-RECENT_EVENT_LIMIT:]
    ]
    key_memories = [
        {
            "day": memory.day,
            "importance": memory.importance,
            "summary": memory.summary,
        }
        for memory in protagonist.memories[:KEY_MEMORY_LIMIT]
    ]
    snapshot = {
        "activity": {
            "key_memories": key_memories,
            "recent_events": recent_events,
        },
        "clock": {"day": state.clock.day, "slot": state.clock.slot.value},
        "economy": {
            "meal_cost": state.meal_cost,
            "rent_arrears": protagonist.rent_arrears,
            "rent_cost": protagonist.rent_cost,
            "rent_due_day": protagonist.rent_due_day,
            "rent_payments": state.rent_payments,
            "shop_visits": state.shop_visits,
            "wage_modifier": state.wage_modifier,
        },
        "environment": {
            "gate_alert_level": state.gate_alert_level,
            "season": state.season,
            "temperature_c": state.temperature_c,
            "weather": state.weather,
        },
        "portals": {
            "active_plan": state.active_portal_plan,
            "discovered": list(state.discovered_portals),
            "investigations": investigations,
        },
        "protagonist": {
            "ability": protagonist.ability,
            "current_goal": protagonist.current_goal,
            "equipment": {
                "armor": protagonist.equipped_armor,
                "inventory": dict(sorted(protagonist.inventory.items())),
                "weapon": protagonist.equipped_weapon,
            },
            "hunter_rank": protagonist.hunter_rank,
            "location": protagonist.location,
            "mood": protagonist.mood,
            "name": protagonist.name,
            "progression": {
                "ability_mastery": protagonist.ability_mastery,
                "combat_readiness": protagonist.combat_readiness,
                "fitness": protagonist.fitness,
                "knowledge": protagonist.knowledge,
                "missions_attempted": protagonist.missions_attempted,
                "missions_completed": protagonist.missions_completed,
                "rank_points": protagonist.rank_points,
            },
            "resources": {
                "energy": protagonist.energy,
                "health": protagonist.health,
                "hunger": protagonist.hunger,
                "money": protagonist.money,
                "morale": protagonist.morale,
                "stress": protagonist.stress,
            },
        },
        "relationships": relationships,
        "schema_version": OBSERVER_SNAPSHOT_SCHEMA_VERSION,
        "seed": simulation.seed,
        "story": story_progress(state),
    }
    snapshot["identity"] = {
        "algorithm": "sha256",
        "digest": _content_digest(snapshot),
    }
    return snapshot
