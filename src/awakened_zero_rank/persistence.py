from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import tempfile
from dataclasses import asdict
from pathlib import Path
from typing import Any, TYPE_CHECKING

from .content import NPCS, PORTALS, STORY_ANCHORS
from .models import (AUTHORED_RENT_COST, AUTHORED_RENT_DUE_DAY, Clock,
                     DelayedConsequence, DialogueExchange, Event, Memory,
                     PortalInvestigation, Protagonist, Relationship, TimeSlot,
                     WorldState)
from .world import ITEMS, LOCATIONS, mission_rank_points_are_possible


if TYPE_CHECKING:
    from .simulation import Simulation

SAVE_VERSION = 2
_HUNTER_RANKS = {"Unranked", "F", "E", "D", "C"}
_ABILITIES = {"None", "Threat Sense", "Threat Sense / Echo Fragment"}


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
    story_anchor_keys = {anchor.key for anchor in STORY_ANCHORS}
    calendar_events_seen = raw.get("calendar_events_seen", [])
    story_outcomes = raw.get("story_outcomes")
    if story_outcomes is None:
        story_outcomes = {
            key: "legacy-unavailable"
            for key in calendar_events_seen
            if key in story_anchor_keys
        }
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
        calendar_events_seen=calendar_events_seen,
        story_outcomes=story_outcomes,
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
    if protagonist.location not in LOCATIONS:
        raise ValueError(
            f"Invalid save field protagonist.location: "
            f"unknown location {protagonist.location!r}")
    if (
            protagonist.hunter_rank not in _HUNTER_RANKS or
            protagonist.ability not in _ABILITIES or
            (protagonist.hunter_rank == "Unranked") !=
            (protagonist.ability == "None")):
        raise ValueError(
            "Invalid save protagonist lifecycle: "
            "hunter rank and ability are inconsistent")
    awakened_by_clock = (
        state.clock.day, tuple(TimeSlot).index(state.clock.slot)
    ) >= (3, tuple(TimeSlot).index(TimeSlot.EVENING))
    if (protagonist.hunter_rank == "Unranked") == awakened_by_clock:
        raise ValueError("Invalid save protagonist Awakening chronology")
    clock_position = (state.clock.day, tuple(TimeSlot).index(state.clock.slot))
    fixed_locations = {
        (3, tuple(TimeSlot).index(TimeSlot.EVENING)): "Tokyo Awakening Bureau",
        (4, tuple(TimeSlot).index(TimeSlot.AFTERNOON)): "Tokyo Hunter Guild",
    }
    if (
            clock_position in fixed_locations and
            protagonist.location != fixed_locations[clock_position]):
        raise ValueError("Invalid save fixed-event location")
    awakening_position = (3, tuple(TimeSlot).index(TimeSlot.EVENING))
    if (
            (clock_position < awakening_position and
             protagonist.ability_mastery != 0) or
            (clock_position == awakening_position and
             protagonist.ability_mastery != 1) or
            (clock_position > awakening_position and
             protagonist.ability_mastery == 0)):
        raise ValueError("Invalid save Awakening mastery chronology")
    if (
            clock_position ==
            (4, tuple(TimeSlot).index(TimeSlot.AFTERNOON)) and
            state.gate_alert_level != 2):
        raise ValueError("Invalid save Guild alert evidence")
    if not awakened_by_clock:
        expected_goal = "Earn enough yen to pay rent"
    elif clock_position < (4, tuple(TimeSlot).index(TimeSlot.AFTERNOON)):
        expected_goal = "Register with the Tokyo Hunter Guild"
    elif protagonist.rent_arrears:
        expected_goal = f"Clear ¥{protagonist.rent_arrears:,} in rent arrears"
    elif protagonist.hunter_rank == "F":
        expected_goal = "Survive gate work and reach Rank E"
    else:
        expected_goal = (
            f"Build a stable life as a Rank {protagonist.hunter_rank} hunter")
    for field, expected_kind in (
            ("equipped_weapon", "weapon"),
            ("equipped_armor", "armor")):
        item_name = getattr(protagonist, field)
        if item_name is None:
            continue
        item = ITEMS.get(item_name)
        if item is None or item.kind != expected_kind:
            raise ValueError(
                f"Invalid save field protagonist.{field}: "
                f"expected catalogued {expected_kind}")
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
    rank_bounds = {
        "Unranked": (0, 29), "F": (0, 29), "E": (30, 59),
        "D": (60, 89), "C": (90, None),
    }
    minimum, maximum = rank_bounds[protagonist.hunter_rank]
    if (protagonist.rank_points < minimum or
            (maximum is not None and protagonist.rank_points > maximum)):
        raise ValueError(
            "Invalid save protagonist progression: "
            "hunter rank and rank points are inconsistent")
    if not mission_rank_points_are_possible(
            protagonist.missions_completed, protagonist.rank_points):
        raise ValueError(
            "Invalid save protagonist progression: "
            "rank points require completed mission evidence from exact awards")
    fixed_hunter_record_positions = {
        (3, tuple(TimeSlot).index(TimeSlot.EVENING)),
        (4, tuple(TimeSlot).index(TimeSlot.AFTERNOON)),
    }
    if (
            clock_position <=
            (4, tuple(TimeSlot).index(TimeSlot.AFTERNOON)) and
            any((protagonist.rank_points, protagonist.missions_attempted,
                 protagonist.missions_completed))):
        raise ValueError("Invalid save hunter record chronology")
    if (
            clock_position <=
            (4, tuple(TimeSlot).index(TimeSlot.AFTERNOON)) and
            (protagonist.inventory or
             protagonist.equipped_weapon is not None or
             protagonist.equipped_armor is not None)):
        raise ValueError("Invalid save equipment chronology")
    _require_integer_range(
        "protagonist.rent_due_day", protagonist.rent_due_day, 1)
    _require_integer_range("protagonist.rent_cost", protagonist.rent_cost, 0)
    _require_integer_range("rent_payments", state.rent_payments, 0)
    _require_integer_range("shop_visits", state.shop_visits, 0)
    if (
            clock_position <=
            (4, tuple(TimeSlot).index(TimeSlot.AFTERNOON)) and
            state.shop_visits != 0):
        raise ValueError("Invalid save hunter shop chronology")
    if (
            protagonist.rent_due_day != AUTHORED_RENT_DUE_DAY or
            protagonist.rent_cost != AUTHORED_RENT_COST or
            protagonist.rent_arrears > AUTHORED_RENT_COST or
            state.rent_payments > 1 or
            (state.rent_payments == 1 and protagonist.rent_arrears > 0)):
        raise ValueError("Invalid save rent ledger")
    if (
            (state.clock.day < AUTHORED_RENT_DUE_DAY or
             (state.clock.day == AUTHORED_RENT_DUE_DAY and
              state.clock.slot is TimeSlot.MORNING)) and
            (state.rent_payments != 0 or protagonist.rent_arrears != 0)):
        raise ValueError("Invalid save rent ledger predates its deadline")
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
    slot_order = {slot: index for index, slot in enumerate(TimeSlot)}
    previous_event_position: tuple[int, int] | None = None
    for index, event in enumerate(state.events):
        _require_integer_range(f"events[{index}].day", event.day, 1, state.clock.day)
        for field in ("action", "reason", "outcome"):
            value = getattr(event, field)
            if not isinstance(value, str) or not value:
                raise ValueError(
                    f"Invalid save field events[{index}].{field}: "
                    "expected non-empty text")
        position = (event.day, slot_order[event.slot])
        if position >= clock_position:
            raise ValueError(
                "Invalid save field events: event is at or ahead of clock")
        if previous_event_position is not None and position <= previous_event_position:
            raise ValueError(
                "Invalid save field events: expected strictly chronological order")
        previous_event_position = position
    for index, memory in enumerate(protagonist.memories):
        _require_integer_range(
            f"protagonist.memories[{index}].day",
            memory.day, 1, state.clock.day)
        _require_integer_range(
            f"protagonist.memories[{index}].importance",
            memory.importance, 1, 10)
        if not isinstance(memory.summary, str) or not memory.summary:
            raise ValueError(
                f"Invalid save field protagonist.memories[{index}].summary: "
                "expected non-empty text")
    previous_dialogue_day: int | None = None
    for index, exchange in enumerate(protagonist.dialogue_history):
        _require_integer_range(
            f"protagonist.dialogue_history[{index}].day",
            exchange.day, 1)
        if previous_dialogue_day is not None and exchange.day < previous_dialogue_day:
            raise ValueError(
                "Invalid save field protagonist.dialogue_history: "
                "expected chronological order")
        previous_dialogue_day = exchange.day
        for field in (
                "intention", "ren_line", "npc_name", "npc_line", "reaction"):
            value = getattr(exchange, field)
            if not isinstance(value, str) or not value:
                raise ValueError(
                    f"Invalid save field protagonist.dialogue_history"
                    f"[{index}].{field}: expected non-empty text")
    story_anchor_keys = {anchor.key for anchor in STORY_ANCHORS}
    resolved_story_keys = set(state.story_outcomes)
    calendar_story_keys = set(state.calendar_events_seen) & story_anchor_keys
    if resolved_story_keys != calendar_story_keys:
        raise ValueError(
            "Invalid save field story_outcomes: "
            "expected exact agreement with story calendar history")
    expected_story_prefix = {
        anchor.key for anchor in STORY_ANCHORS[:len(resolved_story_keys)]}
    if resolved_story_keys != expected_story_prefix:
        raise ValueError(
            "Invalid save field story_outcomes: "
            "resolved anchors must form a chronological prefix")
    for key, outcome in state.story_outcomes.items():
        if (key not in story_anchor_keys or
                outcome not in {
                    "isolated", "resilient", "prepared",
                    "legacy-unavailable"}):
            raise ValueError(
                f"Invalid save field story_outcomes[{key!r}]: "
                "expected a catalogued anchor and recognized outcome tier")
        if key not in state.calendar_events_seen:
            raise ValueError(
                f"Invalid save field story_outcomes[{key!r}]: "
                "resolved anchor is missing from calendar history")
    npc_names = set(NPCS)
    for name, relationship in protagonist.relationships.items():
        if name not in npc_names or relationship.name != name:
            raise ValueError(
                f"Invalid save field protagonist.relationships[{name!r}]: "
                "key and relationship name must match a catalogued NPC")
        for field, minimum, maximum in (
                ("trust", -100, 100), ("familiarity", 0, 100),
                ("meetings", 0, None), ("affection", -100, 100),
                ("tension", 0, 100), ("loyalty", 0, 100)):
            _require_integer_range(
                f"protagonist.relationships[{name!r}].{field}",
                getattr(relationship, field), minimum, maximum)
    registered_by_clock = clock_position >= (
        4, tuple(TimeSlot).index(TimeSlot.AFTERNOON))
    has_aiko = "Aiko Sato" in protagonist.relationships
    if (
            protagonist.guild_registered != registered_by_clock or
            has_aiko != registered_by_clock):
        raise ValueError("Invalid save Guild registration evidence")
    introductions = {
        "Daichi Mori": (5, tuple(TimeSlot).index(TimeSlot.AFTERNOON)),
        "Mei Kuroda": (6, tuple(TimeSlot).index(TimeSlot.EVENING)),
        "Haruto Ishikawa": (9, tuple(TimeSlot).index(TimeSlot.LATE_NIGHT)),
    }
    if any(
            (name in protagonist.relationships) !=
            (clock_position >= introduced)
            for name, introduced in introductions.items()):
        raise ValueError("Invalid save relationship chronology")
    initial_evidence = {
        "Aiko Sato": ((4, tuple(TimeSlot).index(TimeSlot.AFTERNOON)), 3, 5, 4),
        "Daichi Mori": ((5, tuple(TimeSlot).index(TimeSlot.AFTERNOON)), 4, 3, 2),
        "Mei Kuroda": ((6, tuple(TimeSlot).index(TimeSlot.EVENING)), 1, 2, 2),
        "Haruto Ishikawa": ((9, tuple(TimeSlot).index(TimeSlot.LATE_NIGHT)), 3, 3, 2),
    }
    for name, (introduced, trust, familiarity, loyalty) in initial_evidence.items():
        if clock_position != introduced:
            continue
        relationship = protagonist.relationships[name]
        if (
                relationship.trust != trust or
                relationship.familiarity != familiarity or
                relationship.loyalty != loyalty or
                relationship.affection != 0 or
                relationship.tension != 0 or
                relationship.meetings != 1):
            raise ValueError("Invalid save relationship introduction evidence")
    for speaker, connections in state.relationship_network.items():
        if speaker not in npc_names:
            raise ValueError(
                "Invalid save field relationship_network: "
                f"unknown NPC {speaker!r}")
        for target, standing in connections.items():
            if target not in npc_names:
                raise ValueError(
                    "Invalid save field relationship_network: "
                    f"unknown NPC {target!r}")
            _require_integer_range(
                f"relationship_network[{speaker!r}][{target!r}]",
                standing, -100, 100)
    if any(name not in npc_names for name in state.npc_locations):
        raise ValueError(
            "Invalid save field npc_locations: expected catalogued NPC names")
    if any(exchange.npc_name not in npc_names
           for exchange in protagonist.dialogue_history):
        raise ValueError(
            "Invalid save field protagonist.dialogue_history: "
            "expected catalogued NPC speakers")
    for index, consequence in enumerate(state.delayed_consequences):
        _require_integer_range(
            f"delayed_consequences[{index}].due_day",
            consequence.due_day, 1)
        for field in ("source", "description"):
            value = getattr(consequence, field)
            if not isinstance(value, str) or not value:
                raise ValueError(
                    f"Invalid save field delayed_consequences[{index}]."
                    f"{field}: expected non-empty text")
        if (len(consequence.people) != len(set(consequence.people)) or
                any(person not in npc_names for person in consequence.people)):
            raise ValueError(
                f"Invalid save field delayed_consequences[{index}].people: "
                "expected unique catalogued NPC names")
        if not isinstance(consequence.resolved, bool):
            raise ValueError(
                f"Invalid save field delayed_consequences[{index}].resolved: "
                "expected boolean")
    portal_names = {portal.name for portal in PORTALS}
    if (len(state.discovered_portals) != len(set(state.discovered_portals)) or
            any(name not in portal_names for name in state.discovered_portals)):
        raise ValueError(
            "Invalid save field discovered_portals: "
            "expected unique catalogued portal names")
    for name, investigation in state.portal_investigations.items():
        if name not in portal_names or investigation.portal_name != name:
            raise ValueError(
                f"Invalid save field portal_investigations[{name!r}]: "
                "key and portal name must match a catalogued portal")
        _require_integer_range(
            f"portal_investigations[{name!r}].progress",
            investigation.progress, 0, 100)
        _require_integer_range(
            f"portal_investigations[{name!r}].risk",
            investigation.risk, 0, 100)
        _require_integer_range(
            f"portal_investigations[{name!r}].last_investigated_day",
            investigation.last_investigated_day, 0, state.clock.day)
        _require_integer_range(
            f"portal_investigations[{name!r}].preparation_bonus",
            investigation.preparation_bonus, 0)
        _require_integer_range(
            f"portal_investigations[{name!r}].joint_missions",
            investigation.joint_missions, 0)
        if (not isinstance(investigation.preparation_strategy, str) or
                not investigation.preparation_strategy):
            raise ValueError(
                f"Invalid save field portal_investigations[{name!r}]"
                ".preparation_strategy: expected non-empty text")
        if (investigation.cooperating_npc is not None and
                investigation.cooperating_npc not in npc_names):
            raise ValueError(
                f"Invalid save field portal_investigations[{name!r}]"
                ".cooperating_npc: expected a catalogued NPC")
        if any(person not in npc_names for person in investigation.reported_to):
            raise ValueError(
                f"Invalid save field portal_investigations[{name!r}]"
                ".reported_to: expected catalogued NPC names")
    if any(name not in state.discovered_portals
           for name in state.portal_investigations):
        raise ValueError(
            "Invalid save field portal_investigations: "
            "investigated portals must be discovered")
    if (state.active_portal_plan is not None and
            state.active_portal_plan not in state.portal_investigations):
        raise ValueError(
            "Invalid save field active_portal_plan: "
            "expected a catalogued investigated portal")
    if (
            clock_position <=
            (4, tuple(TimeSlot).index(TimeSlot.AFTERNOON)) and
            (state.discovered_portals or state.portal_investigations or
             state.active_portal_plan is not None)):
        raise ValueError("Invalid save portal chronology")
    awakening_position = (3, tuple(TimeSlot).index(TimeSlot.EVENING))
    registration_position = (4, tuple(TimeSlot).index(TimeSlot.AFTERNOON))
    awakening_count = sum(
        memory == Memory(
            day=3,
            summary="Awakening assessment: Awakened at Rank F with Threat Sense.",
            importance=10)
        for memory in protagonist.memories)
    registration_count = sum(
        memory.day == 4 and memory.importance == 8 and
        re.fullmatch(
            r"Guild registration: Aiko Sato issued an F-rank license; "
            r"travel and filing cost ¥(?:0|[1-9]\d{0,2}(?:,\d{3})*)\.",
            memory.summary) is not None
        for memory in protagonist.memories)
    if (
            awakening_count != int(clock_position >= awakening_position) or
            registration_count != int(clock_position >= registration_position)):
        raise ValueError("Invalid save fixed-event memory chronology")
    fixed_events = {
        (3, tuple(TimeSlot).index(TimeSlot.EVENING)): (
            3, TimeSlot.AFTERNOON, "Awakening assessment",
            "a city gate alert triggered Ren's mandatory screening (world event)",
            "Awakened at Rank F with Threat Sense."),
        (4, tuple(TimeSlot).index(TimeSlot.AFTERNOON)): (
            4, TimeSlot.MORNING, "Guild registration",
            "newly awakened citizens must register before accepting hunter work "
            "(world event)", None),
    }
    expected_event = fixed_events.get(clock_position)
    if expected_event is not None:
        latest = state.events[-1] if state.events else None
        expected_day, expected_slot, action, reason, outcome = expected_event
        if (
                latest is None or latest.day != expected_day or
                latest.slot is not expected_slot or latest.action != action or
                latest.reason != reason or
                (outcome is not None and latest.outcome != outcome) or
                (outcome is None and re.fullmatch(
                    r"Aiko Sato issued an F-rank license; travel and filing "
                    r"cost ¥(?:0|[1-9]\d{0,2}(?:,\d{3})*)\.",
                    latest.outcome) is None)):
            raise ValueError("Invalid save fixed-event activity evidence")
        awakening_memories = [
            memory for memory in protagonist.memories
            if memory == Memory(
                day=3,
                summary=(
                    "Awakening assessment: Awakened at Rank F with "
                    "Threat Sense."),
                importance=10)
        ]
        if len(awakening_memories) != 1:
            raise ValueError("Invalid save fixed-event memory evidence")
        if clock_position == (4, tuple(TimeSlot).index(TimeSlot.AFTERNOON)):
            registration_memories = [
                memory for memory in protagonist.memories
                if memory.day == 4 and memory.importance == 8 and
                re.fullmatch(
                    r"Guild registration: Aiko Sato issued an F-rank license; "
                    r"travel and filing cost "
                    r"¥(?:0|[1-9]\d{0,2}(?:,\d{3})*)\.",
                    memory.summary) is not None
            ]
            if len(registration_memories) != 1:
                raise ValueError("Invalid save fixed-event memory evidence")
    if protagonist.current_goal != expected_goal:
        raise ValueError("Invalid save protagonist current goal")


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
