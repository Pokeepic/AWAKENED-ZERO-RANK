"""Stable read-only state projection for observer applications."""

from __future__ import annotations

import hashlib
import hmac
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import TYPE_CHECKING, Any

from .story import story_progress

if TYPE_CHECKING:
    from .simulation import Simulation


OBSERVER_SNAPSHOT_SCHEMA_VERSION = 3
RECENT_EVENT_LIMIT = 12
KEY_MEMORY_LIMIT = 5
_SNAPSHOT_KEYS = {
    "activity", "clock", "environment", "identity", "portals",
    "protagonist", "relationships", "schema_version", "seed", "story",
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
    clock = snapshot["clock"]
    if not isinstance(snapshot["seed"], int) or isinstance(snapshot["seed"], bool):
        raise ValueError("Observer snapshot seed is invalid")
    day = clock.get("day") if isinstance(clock, dict) else None
    if not isinstance(day, int) or isinstance(day, bool) or day < 1:
        raise ValueError("Observer snapshot clock is invalid")
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
