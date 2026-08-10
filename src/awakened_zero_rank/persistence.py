from __future__ import annotations

import hashlib
import hmac
import json
import os
import tempfile
from dataclasses import asdict
from pathlib import Path
from typing import Any, TYPE_CHECKING

from .models import (Clock, DelayedConsequence, DialogueExchange, Event, Memory,
                     PortalInvestigation, Protagonist, Relationship, TimeSlot, WorldState)


if TYPE_CHECKING:
    from .simulation import Simulation

SAVE_VERSION = 2


def _tuplify(value: Any) -> Any:
    if isinstance(value, list):
        return tuple(_tuplify(item) for item in value)
    return value


def save_simulation(simulation: "Simulation", path: str | Path) -> Path:
    """Save all deterministic state needed to continue the same timeline."""
    _validate_simulation_state(simulation)
    destination = Path(path)
    data = {
        "save_version": SAVE_VERSION,
        "seed": simulation.seed,
        "rng_state": simulation.rng.getstate(),
        "state": asdict(simulation.state),
    }
    payload = json.dumps(
        data, ensure_ascii=False, sort_keys=True,
        separators=(",", ":")).encode("utf-8")
    data["save_digest"] = hashlib.sha256(payload).hexdigest()
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
                "w", encoding="utf-8", newline="\n",
                dir=destination.parent, prefix=f".{destination.name}.",
                suffix=".tmp", delete=False) as temporary:
            temporary_path = Path(temporary.name)
            json.dump(data, temporary, ensure_ascii=False, indent=2)
            temporary.flush()
            os.fsync(temporary.fileno())
        os.replace(temporary_path, destination)
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
    return destination


def _read_save_data(path: str | Path) -> tuple[dict[str, Any], int, str]:
    """Read and verify a supported save format exactly once."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    version = data.get("save_version")
    if version not in (1, SAVE_VERSION):
        raise ValueError(f"Unsupported save version: {version}")
    integrity = "legacy-unavailable"
    if version == SAVE_VERSION:
        claimed_digest = data.pop("save_digest", None)
        payload = json.dumps(
            data, ensure_ascii=False, sort_keys=True,
            separators=(",", ":")).encode("utf-8")
        actual_digest = hashlib.sha256(payload).hexdigest()
        if not isinstance(claimed_digest, str) or not hmac.compare_digest(
                claimed_digest, actual_digest):
            raise ValueError("Save integrity check failed")
        integrity = "verified"

    return data, version, integrity


def _simulation_from_data(data: dict[str, Any]) -> "Simulation":
    """Reconstruct a deterministic simulation from verified save data."""
    from .simulation import Simulation

    raw = data["state"]
    protagonist_data = raw["protagonist"]
    protagonist_data["memories"] = [Memory(**memory) for memory in protagonist_data["memories"]]
    protagonist_data["relationships"] = {
        name: Relationship(**relationship)
        for name, relationship in protagonist_data["relationships"].items()
    }
    protagonist_data["dialogue_history"] = [
        DialogueExchange(**exchange) for exchange in protagonist_data.get("dialogue_history", [])
    ]
    state = WorldState(
        clock=Clock(day=raw["clock"]["day"], slot=TimeSlot(raw["clock"]["slot"])),
        protagonist=Protagonist(**protagonist_data),
        events=[Event(day=event["day"], slot=TimeSlot(event["slot"]), action=event["action"],
                      reason=event["reason"], outcome=event["outcome"])
                for event in raw["events"]],
        gate_alert_level=raw["gate_alert_level"],
        rent_payments=raw["rent_payments"],
        shop_visits=raw["shop_visits"],
        season=raw.get("season", "Summer"),
        weather=raw.get("weather", "Clear"),
        temperature_c=raw.get("temperature_c", 29),
        weather_day=raw.get("weather_day", 0),
        calendar_events_seen=raw.get("calendar_events_seen", []),
        relationship_network=raw.get("relationship_network", {}),
        discovered_portals=raw.get("discovered_portals", []),
        portal_investigations={
            name: PortalInvestigation(**investigation)
            for name, investigation in raw.get("portal_investigations", {}).items()
        },
        npc_locations=raw.get("npc_locations", {}),
        delayed_consequences=[
            DelayedConsequence(
                due_day=item["due_day"], source=item["source"],
                people=tuple(item["people"]), description=item["description"],
                resolved=item.get("resolved", False),
            ) for item in raw.get("delayed_consequences", [])
        ],
        social_encounters_seen=raw.get("social_encounters_seen", []),
        active_portal_plan=raw.get("active_portal_plan"),
        economy_day=raw.get("economy_day", 0),
        wage_modifier=raw.get("wage_modifier", 100),
        meal_cost=raw.get("meal_cost", 600),
        objective_progress=raw.get("objective_progress", {
            "financial_buffer": 0, "recovery": 0, "portal_readiness": 0,
        }),
        objective_scores=raw.get("objective_scores", {
            "survival": 0, "stability": 0, "discovery": 0, "relationships": 0,
        }),
    )
    simulation = Simulation(seed=data["seed"], state=state)
    simulation.rng.setstate(_tuplify(data["rng_state"]))
    _validate_simulation_state(simulation)
    return simulation


def _require_integer_range(
        name: str, value: Any, minimum: int,
        maximum: int | None = None) -> None:
    if (isinstance(value, bool) or not isinstance(value, int) or
            value < minimum or
            (maximum is not None and value > maximum)):
        expected = (
            f"{minimum} or greater" if maximum is None
            else f"range {minimum}..{maximum}")
        raise ValueError(
            f"Invalid save field {name}: expected integer in {expected}")


def _validate_simulation_state(simulation: "Simulation") -> None:
    """Reject reconstructed worlds that violate stable simulation invariants."""
    state = simulation.state
    protagonist = state.protagonist
    _require_integer_range("clock.day", state.clock.day, 1)
    for name in (
            "health", "energy", "hunger", "stress", "ability_mastery",
            "social_confidence"):
        _require_integer_range(
            f"protagonist.{name}", getattr(protagonist, name), 0, 100)
    for name in (
            "strength", "agility", "endurance", "perception", "mana",
            "luck"):
        _require_integer_range(
            f"protagonist.{name}", getattr(protagonist, name), 1, 100)
    _require_integer_range(
        "protagonist.injury_severity", protagonist.injury_severity, 0, 5)
    for name in (
            "money", "knowledge", "fitness", "echo_fragments",
            "training_sessions", "reputation", "rank_points",
            "combat_experience", "missions_attempted",
            "missions_completed", "prepared_missions_attempted",
            "prepared_missions_completed", "injuries",
            "treatments_received", "rent_arrears", "gates_witnessed"):
        _require_integer_range(
            f"protagonist.{name}", getattr(protagonist, name), 0)
    _require_integer_range(
        "protagonist.rent_due_day", protagonist.rent_due_day, 1)
    _require_integer_range("protagonist.rent_cost", protagonist.rent_cost, 0)
    if protagonist.missions_completed > protagonist.missions_attempted:
        raise ValueError(
            "Invalid save mission counters: completions exceed attempts")
    if (protagonist.prepared_missions_completed >
            protagonist.prepared_missions_attempted or
            protagonist.prepared_missions_attempted >
            protagonist.missions_attempted):
        raise ValueError("Invalid save prepared-mission counters")
    _require_integer_range("gate_alert_level", state.gate_alert_level, 0, 3)
    for item, quantity in protagonist.inventory.items():
        _require_integer_range(f"inventory[{item!r}]", quantity, 1)


def load_simulation(path: str | Path) -> "Simulation":
    """Load a compatible timeline save."""
    data, _, _ = _read_save_data(path)
    return _simulation_from_data(data)


def verify_simulation_save(path: str | Path) -> dict[str, Any]:
    """Return honest, read-only verification metadata for a save."""
    data, version, integrity = _read_save_data(path)
    simulation = _simulation_from_data(data)
    return {
        "day": simulation.state.clock.day,
        "events": len(simulation.state.events),
        "integrity": integrity,
        "protagonist": simulation.state.protagonist.name,
        "save_version": version,
        "seed": simulation.seed,
        "status": "valid",
        "time_slot": simulation.state.clock.slot.value,
    }
