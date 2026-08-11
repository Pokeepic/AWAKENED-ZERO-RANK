"""Stable read-only state projection for observer applications."""

from __future__ import annotations

import hashlib
import json
from typing import TYPE_CHECKING, Any

from .story import story_progress

if TYPE_CHECKING:
    from .simulation import Simulation


OBSERVER_SNAPSHOT_SCHEMA_VERSION = 3
RECENT_EVENT_LIMIT = 12
KEY_MEMORY_LIMIT = 5


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
    canonical = json.dumps(
        snapshot, ensure_ascii=False, sort_keys=True,
        separators=(",", ":")).encode("utf-8")
    snapshot["identity"] = {
        "algorithm": "sha256",
        "digest": hashlib.sha256(canonical).hexdigest(),
    }
    return snapshot
