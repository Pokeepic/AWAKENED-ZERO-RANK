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
from .models import AUTHORED_RENT_COST, AUTHORED_RENT_DUE_DAY
from .story import STORY_PROGRESS_SCHEMA_VERSION, story_progress
from .world import ITEMS, LOCATIONS, mission_rank_points_are_possible

if TYPE_CHECKING:
    from .simulation import Simulation


OBSERVER_SNAPSHOT_SCHEMA_VERSION = 4
OBSERVER_COMPARISON_SCHEMA_VERSION = 8
OBSERVER_PRESENTATION_CONTRACT_SCHEMA_VERSION = 2
OBSERVER_SITE_COMPARISON_ARTIFACT_SCHEMA_VERSION = 1
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
_ABILITIES = {"None", "Threat Sense", "Threat Sense / Echo Fragment"}
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
_STORY_TITLES = {anchor.title for anchor in STORY_ANCHORS}
_EVENT_ANIMATION_CUES = {
    "Awakening assessment": "awakening",
    "Eat": "food",
    "Gate mission": "mission",
    "Guild patrol": "patrol",
    "Guild registration": "registration",
    "Investigation consequence": "consequence",
    "Part-time work": "work",
    "Pay rent arrears": "finance",
    "Prepare portal": "portal_preparation",
    "Rent deadline": "finance",
    "Rest": "rest",
    "Seek treatment": "treatment",
    "Study": "study",
    "Talk with Aiko": "social",
    "Tanabata evening": "festival",
    "Train": "train",
    "Visit hunter shop": "shopping",
}
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


def _validate_environment(environment: Any, day: int, slot: str) -> None:
    if not isinstance(environment, dict) or set(environment) != _ENVIRONMENT_KEYS:
        raise ValueError("Observer snapshot environment is malformed")
    alert = _integer(environment["gate_alert_level"], "gate alert level")
    temperature = _integer(environment["temperature_c"], "temperature")
    weather = environment["weather"]
    if not 0 <= alert <= 3:
        raise ValueError("Observer snapshot gate alert level is invalid")
    if (
            (day, _SLOTS.index(slot)) ==
            (4, _SLOTS.index("Afternoon")) and alert != 2):
        raise ValueError("Observer snapshot Guild alert evidence is invalid")
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
    if any(name not in discovered for name in names):
        raise ValueError("Observer snapshot portal investigation is undiscovered")
    active_plan = portals["active_plan"]
    if active_plan is not None and active_plan not in names:
        raise ValueError("Observer snapshot active portal plan is invalid")

def _validate_economy(economy: Any, day: int, slot: str) -> None:
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
    if (
            values["rent_due_day"] != AUTHORED_RENT_DUE_DAY or
            values["rent_cost"] != AUTHORED_RENT_COST or
            values["rent_arrears"] > AUTHORED_RENT_COST or
            values["rent_payments"] > 1 or
            (values["rent_payments"] == 1 and values["rent_arrears"] > 0)):
        raise ValueError("Observer snapshot rent ledger is inconsistent")
    if (
            (day < AUTHORED_RENT_DUE_DAY or
             (day == AUTHORED_RENT_DUE_DAY and slot == "Morning")) and
            (values["rent_payments"] != 0 or values["rent_arrears"] != 0)):
        raise ValueError("Observer snapshot rent ledger predates its deadline")

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

def _validate_protagonist(
        protagonist: Any, day: int, slot: str, rent_arrears: int) -> None:
    if not isinstance(protagonist, dict) or set(protagonist) != _PROTAGONIST_KEYS:
        raise ValueError("Observer snapshot protagonist is malformed")
    if any(
            not isinstance(protagonist[name], str) or not protagonist[name]
            for name in ("ability", "current_goal", "mood", "name")):
        raise ValueError("Observer snapshot protagonist identity is invalid")
    hunter_rank = protagonist["hunter_rank"]
    ability = protagonist["ability"]
    location = protagonist["location"]
    if (
            not isinstance(hunter_rank, str) or hunter_rank not in _HUNTER_RANKS or
            ability not in _ABILITIES or
            (hunter_rank == "Unranked") != (ability == "None") or
            not isinstance(location, str) or location not in LOCATIONS):
        raise ValueError("Observer snapshot protagonist status is invalid")
    awakened = (day, _SLOTS.index(slot)) >= (3, _SLOTS.index("Evening"))
    if (hunter_rank == "Unranked") == awakened:
        raise ValueError("Observer snapshot Awakening chronology is invalid")
    position = (day, _SLOTS.index(slot))
    fixed_locations = {
        (3, _SLOTS.index("Evening")): "Tokyo Awakening Bureau",
        (4, _SLOTS.index("Afternoon")): "Tokyo Hunter Guild",
    }
    if position in fixed_locations and location != fixed_locations[position]:
        raise ValueError("Observer snapshot fixed-event location is invalid")
    if not awakened:
        expected_goal = "Earn enough yen to pay rent"
    elif position < (4, _SLOTS.index("Afternoon")):
        expected_goal = "Register with the Tokyo Hunter Guild"
    elif rent_arrears:
        expected_goal = f"Clear ¥{rent_arrears:,} in rent arrears"
    elif hunter_rank == "F":
        expected_goal = "Survive gate work and reach Rank E"
    else:
        expected_goal = f"Build a stable life as a Rank {hunter_rank} hunter"
    if protagonist["current_goal"] != expected_goal:
        raise ValueError("Observer snapshot current goal is inconsistent")

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
            position == (3, _SLOTS.index("Evening")) and
            progression_values["ability_mastery"] != 1):
        raise ValueError("Observer snapshot Awakening mastery evidence is invalid")
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
    points = progression_values["rank_points"]
    rank_bounds = {
        "Unranked": (0, 29), "F": (0, 29), "E": (30, 59),
        "D": (60, 89), "C": (90, None),
    }
    minimum, maximum = rank_bounds[hunter_rank]
    if points < minimum or (maximum is not None and points > maximum):
        raise ValueError("Observer snapshot hunter rank points are inconsistent")
    if (
            progression_values["missions_completed"] >
            progression_values["missions_attempted"]):
        raise ValueError("Observer snapshot mission counters are invalid")
    completed = progression_values["missions_completed"]
    if not mission_rank_points_are_possible(completed, points):
        raise ValueError("Observer snapshot mission rank points are inconsistent")

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


def _validate_relationships(relationships: Any, day: int, slot: str) -> None:
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
    registered = (day, _SLOTS.index(slot)) >= (4, _SLOTS.index("Afternoon"))
    if ("Aiko Sato" in names) != registered:
        raise ValueError("Observer snapshot Guild registration evidence is invalid")
    position = (day, _SLOTS.index(slot))
    introductions = {
        "Daichi Mori": (5, _SLOTS.index("Afternoon")),
        "Mei Kuroda": (6, _SLOTS.index("Evening")),
        "Haruto Ishikawa": (9, _SLOTS.index("Late Night")),
    }
    if any((name in names) != (position >= introduced)
           for name, introduced in introductions.items()):
        raise ValueError("Observer snapshot relationship chronology is invalid")
    initial_evidence = {
        "Aiko Sato": ((4, _SLOTS.index("Afternoon")), 3, 5, 4),
        "Daichi Mori": ((5, _SLOTS.index("Afternoon")), 4, 3, 2),
        "Mei Kuroda": ((6, _SLOTS.index("Evening")), 1, 2, 2),
        "Haruto Ishikawa": ((9, _SLOTS.index("Late Night")), 3, 3, 2),
    }
    relationships_by_name = {
        relationship["name"]: relationship for relationship in relationships}
    for name, (introduced, trust, familiarity, loyalty) in initial_evidence.items():
        if position != introduced:
            continue
        relationship = relationships_by_name[name]
        if relationship != {
                "name": name,
                "role": NPCS[name].role,
                "trust": trust,
                "familiarity": familiarity,
                "affection": 0,
                "tension": 0,
                "loyalty": loyalty}:
            raise ValueError(
                "Observer snapshot relationship introduction evidence is invalid")


def _validate_snapshot_semantics(snapshot: dict[str, Any]) -> int:
    clock = snapshot["clock"]
    if not isinstance(clock, dict) or set(clock) != {"day", "slot"}:
        raise ValueError("Observer snapshot clock is invalid")
    day = _integer(clock["day"], "clock day")
    if day < 1 or clock["slot"] not in _SLOTS:
        raise ValueError("Observer snapshot clock is invalid")
    _validate_activity(snapshot["activity"], day, clock["slot"])
    _validate_economy(snapshot["economy"], day, clock["slot"])
    _validate_environment(snapshot["environment"], day, clock["slot"])
    _validate_portals(snapshot["portals"])
    _validate_relationships(snapshot["relationships"], day, clock["slot"])
    _validate_story(snapshot["story"], day)
    _validate_protagonist(
        snapshot["protagonist"], day, clock["slot"],
        snapshot["economy"]["rent_arrears"])

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


def observer_presentation_contract() -> dict[str, Any]:
    """Return the versioned read-only presentation vocabulary."""
    contract = {
        "animation_cues": sorted(
            set(_EVENT_ANIMATION_CUES.values()) | {"other", "story"}
        ),
        "comparison_schema_version": OBSERVER_COMPARISON_SCHEMA_VERSION,
        "contract_schema_version": OBSERVER_PRESENTATION_CONTRACT_SCHEMA_VERSION,
        "control_capabilities": [],
        "observer_schema_version": OBSERVER_SNAPSHOT_SCHEMA_VERSION,
        "read_only": True,
        "recent_activity_relations": ["append", "replace", "unchanged"],
        "update_modes": ["animate", "refresh", "replace", "unchanged"],
    }
    canonical = json.dumps(
        contract, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return {
        **contract,
        "contract_sha256": hashlib.sha256(canonical).hexdigest(),
    }


def verify_observer_presentation_contract(
        contract: dict[str, Any]) -> dict[str, Any]:
    """Verify a downloaded presentation contract without changing it."""
    expected = observer_presentation_contract()
    expected_keys = set(expected)
    if not isinstance(contract, dict) or set(contract) != expected_keys:
        raise ValueError("Observer presentation contract is malformed")
    claimed = contract["contract_sha256"]
    if not isinstance(claimed, str) or len(claimed) != 64:
        raise ValueError("Observer presentation contract digest is malformed")
    payload = {
        key: value for key, value in contract.items()
        if key != "contract_sha256"
    }
    canonical = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    actual = hashlib.sha256(canonical).hexdigest()
    if not hmac.compare_digest(claimed, actual):
        raise ValueError("Observer presentation contract integrity check failed")
    expected_payload = {
        key: value for key, value in expected.items()
        if key != "contract_sha256"
    }
    if payload != expected_payload:
        raise ValueError("Observer presentation contract is unsupported")
    return {
        "comparison_schema_version": OBSERVER_COMPARISON_SCHEMA_VERSION,
        "contract_schema_version": OBSERVER_PRESENTATION_CONTRACT_SCHEMA_VERSION,
        "contract_sha256": claimed,
        "observer_schema_version": OBSERVER_SNAPSHOT_SCHEMA_VERSION,
        "status": "valid",
    }


def save_observer_presentation_contract(
        contract: dict[str, Any], destination: str | Path) -> Path:
    """Validate, stage, and publish a non-overwriting presentation contract."""
    verify_observer_presentation_contract(contract)
    target = Path(destination)
    if target.exists():
        raise ValueError(
            "Observer presentation contract destination already exists")
    target.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(
            prefix=f".{target.name}.staging-", dir=target.parent) as temporary:
        staging = Path(temporary) / target.name
        staging.write_text(
            json.dumps(
                contract, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        loaded = json.loads(staging.read_text(encoding="utf-8"))
        verify_observer_presentation_contract(loaded)
        if loaded != contract:
            raise ValueError(
                "Observer presentation contract staging verification failed")
        if target.exists():
            raise ValueError(
                "Observer presentation contract destination appeared during staging")
        staging.rename(target)
    return target


def publish_observer_site_data(
        snapshot: dict[str, Any], destination: str | Path) -> Path:
    """Atomically publish a verified contract and snapshot directory."""
    snapshot_summary = verify_observer_snapshot(snapshot)
    contract = observer_presentation_contract()
    contract_summary = verify_observer_presentation_contract(contract)
    if (snapshot_summary["schema_version"] !=
            contract_summary["observer_schema_version"]):
        raise ValueError("Observer site data schemas are incompatible")
    target = Path(destination)
    if target.exists():
        raise ValueError("Observer site data destination already exists")
    target.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(
            prefix=f".{target.name}.staging-", dir=target.parent) as temporary:
        staging = Path(temporary)
        contract_path = staging / "observer-contract.json"
        snapshot_path = staging / "observer-snapshot.json"
        save_observer_presentation_contract(contract, contract_path)
        save_observer_snapshot(snapshot, snapshot_path)
        loaded_contract = json.loads(contract_path.read_text(encoding="utf-8"))
        loaded_snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
        verify_observer_presentation_contract(loaded_contract)
        verify_observer_snapshot(loaded_snapshot)
        if loaded_contract != contract or loaded_snapshot != snapshot:
            raise ValueError("Observer site data staging verification failed")
        if target.exists():
            raise ValueError(
                "Observer site data destination appeared during staging")
        staging.rename(target)
    return target


def _load_observer_site_data(
        destination: str | Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    root = Path(destination)
    if not root.is_dir():
        raise ValueError("Observer site data directory is missing")
    expected_files = {"observer-contract.json", "observer-snapshot.json"}
    actual_files = {entry.name for entry in root.iterdir()}
    if actual_files != expected_files:
        raise ValueError("Observer site data directory contents are malformed")
    contract = json.loads(
        (root / "observer-contract.json").read_text(encoding="utf-8"))
    snapshot = json.loads(
        (root / "observer-snapshot.json").read_text(encoding="utf-8"))
    contract_summary = verify_observer_presentation_contract(contract)
    snapshot_summary = verify_observer_snapshot(snapshot)
    if (snapshot_summary["schema_version"] !=
            contract_summary["observer_schema_version"]):
        raise ValueError("Observer site data schemas are incompatible")
    summary = {
        "contract_sha256": contract_summary["contract_sha256"],
        "day": snapshot_summary["day"],
        "observer_schema_version": snapshot_summary["schema_version"],
        "seed": snapshot_summary["seed"],
        "snapshot_sha256": snapshot_summary["digest"],
        "status": "valid",
    }
    return snapshot, summary


def verify_observer_site_data(
        destination: str | Path) -> dict[str, Any]:
    """Strictly verify a published observer site-data directory."""
    _, summary = _load_observer_site_data(destination)
    return summary


def _animation_cue(action: str) -> str:
    if action in _STORY_TITLES:
        return "story"
    if action.startswith("Meet "):
        return "social"
    return _EVENT_ANIMATION_CUES.get(action, "other")


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
    left_position = (
        left["clock"]["day"], _SLOTS.index(left["clock"]["slot"]))
    right_position = (
        right["clock"]["day"], _SLOTS.index(right["clock"]["slot"]))
    clock_delta_slots = (
        (right_position[0] - left_position[0]) * len(_SLOTS) +
        right_position[1] - left_position[1]
    )
    clock_relation = (
        "forward" if left_position < right_position
        else "backward" if left_position > right_position
        else "same"
    )
    same_seed = left["seed"] == right["seed"]
    left_events = left["activity"]["recent_events"]
    right_events = right["activity"]["recent_events"]
    recent_activity_relation = (
        "unchanged" if left_events == right_events
        else "append" if (
            right_events and
            right_events == (left_events + [right_events[-1]])[-RECENT_EVENT_LIMIT:]
        )
        else "replace"
    )
    appended_event = (
        dict(right_events[-1]) if recent_activity_relation == "append" else None
    )
    animation_cue = (
        _animation_cue(appended_event["action"]) if appended_event else None
    )
    update_mode = (
        "unchanged" if not changed_sections
        else "replace" if not same_seed or clock_relation == "backward"
        else "animate" if (
            clock_delta_slots == 1 and recent_activity_relation == "append"
        )
        else "refresh"
    )
    return {
        "animation_cue": animation_cue,
        "appended_event": appended_event,
        "changed_sections": changed_sections,
        "clock_delta_slots": clock_delta_slots,
        "clock_relation": clock_relation,
        "comparison_schema_version": OBSERVER_COMPARISON_SCHEMA_VERSION,
        "identical": not changed_sections,
        "left": {
            "clock": dict(left["clock"]),
            "digest": left["identity"]["digest"],
            "seed": left["seed"],
        },
        "observer_schema_version": OBSERVER_SNAPSHOT_SCHEMA_VERSION,
        "recent_activity_relation": recent_activity_relation,
        "right": {
            "clock": dict(right["clock"]),
            "digest": right["identity"]["digest"],
            "seed": right["seed"],
        },
        "same_seed": same_seed,
        "update_mode": update_mode,
    }


def compare_observer_site_data(
        left: str | Path, right: str | Path) -> dict[str, Any]:
    """Verify and compare two published observer site-data directories."""
    left_snapshot, left_summary = _load_observer_site_data(left)
    right_snapshot, right_summary = _load_observer_site_data(right)
    snapshot_comparison = compare_observer_snapshots(
        left_snapshot, right_snapshot)
    contract_identical = (
        left_summary["contract_sha256"] == right_summary["contract_sha256"])
    return {
        "contract_identical": contract_identical,
        "identical": contract_identical and snapshot_comparison["identical"],
        "left": left_summary,
        "right": right_summary,
        "snapshot": snapshot_comparison,
    }


def _validate_observer_site_comparison(comparison: dict[str, Any]) -> None:
    def fail() -> None:
        raise ValueError("Observer site comparison artifact content is invalid")

    if not isinstance(comparison, dict) or set(comparison) != {
            "contract_identical", "identical", "left", "right", "snapshot"}:
        fail()

    def valid_digest(value: Any) -> bool:
        return (
            isinstance(value, str) and len(value) == 64 and
            all(character in "0123456789abcdef" for character in value)
        )

    def valid_summary(summary: Any) -> bool:
        return (
            isinstance(summary, dict) and set(summary) == {
                "contract_sha256", "day", "observer_schema_version", "seed",
                "snapshot_sha256", "status",
            } and valid_digest(summary["contract_sha256"]) and
            type(summary["day"]) is int and summary["day"] >= 1 and
            summary["observer_schema_version"] ==
            OBSERVER_SNAPSHOT_SCHEMA_VERSION and
            type(summary["seed"]) is int and
            valid_digest(summary["snapshot_sha256"]) and
            summary["status"] == "valid"
        )

    left, right = comparison["left"], comparison["right"]
    snapshot = comparison["snapshot"]
    if not valid_summary(left) or not valid_summary(right):
        fail()
    if not isinstance(snapshot, dict) or set(snapshot) != {
            "animation_cue", "appended_event", "changed_sections",
            "clock_delta_slots", "clock_relation", "comparison_schema_version",
            "identical", "left", "observer_schema_version",
            "recent_activity_relation", "right", "same_seed", "update_mode",
    }:
        fail()
    if (snapshot["comparison_schema_version"] !=
            OBSERVER_COMPARISON_SCHEMA_VERSION or
            snapshot["observer_schema_version"] !=
            OBSERVER_SNAPSHOT_SCHEMA_VERSION):
        fail()
    endpoints = (("left", left), ("right", right))
    for name, summary in endpoints:
        endpoint = snapshot[name]
        if (not isinstance(endpoint, dict) or set(endpoint) != {
                "clock", "digest", "seed"} or
                not isinstance(endpoint["clock"], dict) or
                set(endpoint["clock"]) != {"day", "slot"} or
                endpoint["clock"]["day"] != summary["day"] or
                endpoint["clock"]["slot"] not in _SLOTS or
                endpoint["digest"] != summary["snapshot_sha256"] or
                endpoint["seed"] != summary["seed"]):
            fail()
    contract_identical = (
        left["contract_sha256"] == right["contract_sha256"])
    if (type(comparison["contract_identical"]) is not bool or
            comparison["contract_identical"] != contract_identical or
            type(snapshot["identical"]) is not bool or
            type(comparison["identical"]) is not bool or
            comparison["identical"] != (
                contract_identical and snapshot["identical"])):
        fail()
    changed = snapshot["changed_sections"]
    if (not isinstance(changed, list) or changed != sorted(set(changed)) or
            not set(changed) <= (_SNAPSHOT_KEYS - {"identity"}) or
            snapshot["identical"] != (not changed)):
        fail()
    delta = snapshot["clock_delta_slots"]
    relation = snapshot["clock_relation"]
    if (type(delta) is not int or relation not in {"backward", "forward", "same"} or
            relation != ("forward" if delta > 0 else "backward" if delta < 0
                         else "same")):
        fail()
    if (type(snapshot["same_seed"]) is not bool or
            snapshot["same_seed"] != (left["seed"] == right["seed"]) or
            snapshot["recent_activity_relation"] not in {
                "append", "replace", "unchanged"} or
            snapshot["update_mode"] not in {
                "animate", "refresh", "replace", "unchanged"}):
        fail()
    cue = snapshot["animation_cue"]
    if cue is not None and cue not in observer_presentation_contract()[
            "animation_cues"]:
        fail()
    appended = snapshot["appended_event"]
    is_append = snapshot["recent_activity_relation"] == "append"
    if is_append != isinstance(appended, dict) or is_append != (cue is not None):
        fail()
    expected_update = (
        "unchanged" if snapshot["identical"]
        else "replace" if not snapshot["same_seed"] or relation == "backward"
        else "animate" if delta == 1 and is_append
        else "refresh"
    )
    if snapshot["update_mode"] != expected_update:
        fail()


def observer_site_comparison_artifact(
        comparison: dict[str, Any]) -> dict[str, Any]:
    """Return a content-addressed verified deployment comparison artifact."""
    _validate_observer_site_comparison(comparison)
    payload = {
        "artifact_schema_version":
            OBSERVER_SITE_COMPARISON_ARTIFACT_SCHEMA_VERSION,
        "comparison": comparison,
    }
    canonical = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return {
        **payload,
        "comparison_sha256": hashlib.sha256(canonical).hexdigest(),
    }


def load_observer_site_comparison_artifact(
        path: str | Path) -> dict[str, Any]:
    """Load a deployment comparison artifact after strict verification."""
    artifact = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(artifact, dict) or set(artifact) != {
            "artifact_schema_version", "comparison", "comparison_sha256"}:
        raise ValueError("Observer site comparison artifact fields are invalid")
    if (artifact["artifact_schema_version"] !=
            OBSERVER_SITE_COMPARISON_ARTIFACT_SCHEMA_VERSION):
        raise ValueError("Observer site comparison artifact schema is unsupported")
    claimed = artifact["comparison_sha256"]
    if not isinstance(claimed, str) or len(claimed) != 64:
        raise ValueError("Observer site comparison artifact digest is malformed")
    payload = {
        "artifact_schema_version": artifact["artifact_schema_version"],
        "comparison": artifact["comparison"],
    }
    canonical = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    actual = hashlib.sha256(canonical).hexdigest()
    if not hmac.compare_digest(claimed, actual):
        raise ValueError(
            "Observer site comparison artifact integrity verification failed")
    _validate_observer_site_comparison(artifact["comparison"])
    return artifact


def save_observer_site_comparison(
        comparison: dict[str, Any], destination: str | Path) -> Path:
    """Stage and publish a verified non-overwriting comparison artifact."""
    artifact = observer_site_comparison_artifact(comparison)
    target = Path(destination)
    if target.exists():
        raise ValueError("Observer site comparison destination already exists")
    target.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(
            prefix=f".{target.name}.staging-", dir=target.parent) as temporary:
        staging = Path(temporary) / target.name
        staging.write_text(
            json.dumps(
                artifact, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        loaded = load_observer_site_comparison_artifact(staging)
        if loaded != artifact:
            raise ValueError(
                "Observer site comparison artifact staging verification failed")
        if target.exists():
            raise ValueError(
                "Observer site comparison destination appeared during staging")
        staging.rename(target)
    return target


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
