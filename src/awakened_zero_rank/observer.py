"""Stable read-only state projection for observer applications."""

from __future__ import annotations

import hashlib
import hmac
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import TYPE_CHECKING, Any

from .content import NPCS, PORTALS, STORY_ANCHORS
from .environment import SUMMER_WEATHER
from .story import STORY_PROGRESS_SCHEMA_VERSION, story_progress
from .world import ITEMS, LOCATIONS

if TYPE_CHECKING:
    from .simulation import Simulation


OBSERVER_SNAPSHOT_SCHEMA_VERSION = 4
OBSERVER_COMPARISON_SCHEMA_VERSION = 1
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
_STORY_KEYS = {
    "completed", "completed_count", "ending", "ending_reached", "next",
    "schema_version", "total_anchors",
}
_COMPLETED_STORY_KEYS = {
    "day", "focus_npcs", "key", "outcome", "tier", "title",
}
_ENDING_KEYS = {
    "id", "isolated_count", "prepared_count", "resilient_count", "summary",
    "tier", "title",
}
_STORY_TIERS = {"isolated", "resilient", "prepared", "legacy-unavailable"}
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
_NPC_NAMES = set(NPCS)
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


def _validate_activity(
        activity: Any, current_day: int, current_slot: str) -> None:
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
    current_position = (current_day, _SLOTS.index(current_slot))
    if any(position >= current_position for position in positions):
        raise ValueError("Observer snapshot recent event is ahead of clock")
    if any(left >= right for left, right in zip(positions, positions[1:])):
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
                not isinstance(strategy, str) or not strategy):
            raise ValueError("Observer snapshot portal investigation text is invalid")
        if (
                cooperating_npc is not None and (
                    not isinstance(cooperating_npc, str) or
                    cooperating_npc not in _NPC_NAMES)):
            raise ValueError("Observer snapshot portal collaborator is invalid")
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

def _expected_ending(tiers: list[str]) -> dict[str, Any]:
    counts = {
        tier: tiers.count(tier)
        for tier in ("isolated", "resilient", "prepared")
    }
    final_tier = tiers[-1]
    if "legacy-unavailable" in tiers:
        ending_id = "legacy-unavailable"
        title = "Legacy Ending Unavailable"
        summary = "This timeline predates authenticated story outcome evidence."
    elif final_tier == "isolated":
        ending_id = "unfinished-warning"
        title = "The Unfinished Warning"
        summary = "Ren survived, but the warning he carried remained unresolved."
    elif final_tier == "prepared" and counts["prepared"] >= 4:
        ending_id = "zero-rank-horizon"
        title = "The Zero-Rank Horizon"
        summary = "Ren's evidence and trusted circle changed what Tokyo valued in a hunter."
    else:
        ending_id = "quiet-guardian"
        title = "Tokyo's Quiet Guardian"
        summary = "Ren left Tokyo steadier through persistence rather than recognition."
    return {
        "id": ending_id,
        "isolated_count": counts["isolated"],
        "prepared_count": counts["prepared"],
        "resilient_count": counts["resilient"],
        "summary": summary,
        "tier": final_tier,
        "title": title,
    }


def _validate_story(story: Any, current_day: int) -> None:
    if not isinstance(story, dict) or set(story) != _STORY_KEYS:
        raise ValueError("Observer snapshot story projection is malformed")
    if story["schema_version"] != STORY_PROGRESS_SCHEMA_VERSION:
        raise ValueError("Observer snapshot story projection is invalid")
    completed_count = _integer(story["completed_count"], "story completed count")
    total_anchors = _integer(story["total_anchors"], "story total anchors")
    completed = story["completed"]
    if (
            total_anchors != len(STORY_ANCHORS) or
            not isinstance(completed, list) or
            completed_count != len(completed) or
            not 0 <= completed_count <= total_anchors):
        raise ValueError("Observer snapshot story counts are invalid")
    tiers: list[str] = []
    for entry, anchor in zip(completed, STORY_ANCHORS):
        if not isinstance(entry, dict) or set(entry) != _COMPLETED_STORY_KEYS:
            raise ValueError("Observer snapshot completed story entry is malformed")
        tier = entry["tier"]
        if not isinstance(tier, str) or tier not in _STORY_TIERS:
            raise ValueError("Observer snapshot story tier is invalid")
        outcome = (
            "Outcome tier unavailable in this legacy timeline."
            if tier == "legacy-unavailable" else anchor.outcome(tier)
        )
        expected = {
            "day": anchor.day,
            "focus_npcs": list(anchor.focus_npcs),
            "key": anchor.key,
            "outcome": outcome,
            "tier": tier,
            "title": anchor.title,
        }
        if entry != expected or anchor.day > current_day:
            raise ValueError("Observer snapshot completed story chronology is invalid")
        tiers.append(tier)

    next_summary = story["next"]
    if completed_count < total_anchors:
        anchor = STORY_ANCHORS[completed_count]
        expected_next = {
            "day": anchor.day,
            "days_remaining": max(0, anchor.day - current_day),
            "key": anchor.key,
            "title": anchor.title,
        }
        if next_summary != expected_next:
            raise ValueError("Observer snapshot next story anchor is invalid")
    elif next_summary is not None:
        raise ValueError("Observer snapshot next story anchor is invalid")

    ending_reached = story["ending_reached"]
    expected_reached = completed_count == total_anchors
    if not isinstance(ending_reached, bool) or ending_reached != expected_reached:
        raise ValueError("Observer snapshot story ending status is invalid")
    ending = story["ending"]
    if not expected_reached:
        if ending is not None:
            raise ValueError("Observer snapshot story ending is invalid")
    elif (
            not isinstance(ending, dict) or set(ending) != _ENDING_KEYS or
            ending != _expected_ending(tiers)):
        raise ValueError("Observer snapshot story ending is invalid")

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
        if (
                not isinstance(name, str) or name not in _NPC_NAMES or
                not isinstance(role, str) or not role):
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
    _validate_activity(snapshot["activity"], day, clock["slot"])
    _validate_economy(snapshot["economy"])
    _validate_environment(snapshot["environment"])
    _validate_portals(snapshot["portals"])
    _validate_protagonist(snapshot["protagonist"])
    _validate_relationships(snapshot["relationships"])
    _validate_story(snapshot["story"], day)

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


def compare_observer_snapshots(
        left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    """Verify and compare two observer snapshots without changing either input."""
    verify_observer_snapshot(left)
    verify_observer_snapshot(right)
    comparable_sections = _SNAPSHOT_KEYS - {"identity"}
    changed_sections = sorted(
        section for section in comparable_sections
        if left[section] != right[section]
    )
    return {
        "changed_sections": changed_sections,
        "comparison_schema_version": OBSERVER_COMPARISON_SCHEMA_VERSION,
        "identical": not changed_sections,
        "left": {
            "clock": dict(left["clock"]),
            "digest": left["identity"]["digest"],
            "seed": left["seed"],
        },
        "observer_schema_version": OBSERVER_SNAPSHOT_SCHEMA_VERSION,
        "right": {
            "clock": dict(right["clock"]),
            "digest": right["identity"]["digest"],
            "seed": right["seed"],
        },
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
