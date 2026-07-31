from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .models import Clock, Event, Memory, Protagonist, Relationship, TimeSlot, WorldState


SAVE_VERSION = 1


def _tuplify(value: Any) -> Any:
    if isinstance(value, list):
        return tuple(_tuplify(item) for item in value)
    return value


def save_simulation(simulation: "Simulation", path: str | Path) -> Path:
    """Save all deterministic state needed to continue the same timeline."""
    destination = Path(path)
    data = {
        "save_version": SAVE_VERSION,
        "seed": simulation.seed,
        "rng_state": simulation.rng.getstate(),
        "state": asdict(simulation.state),
    }
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return destination


def load_simulation(path: str | Path) -> "Simulation":
    """Load a trusted JSON save created by :func:`save_simulation`."""
    from .simulation import Simulation

    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if data.get("save_version") != SAVE_VERSION:
        raise ValueError(f"Unsupported save version: {data.get('save_version')}")

    raw = data["state"]
    protagonist_data = raw["protagonist"]
    protagonist_data["memories"] = [Memory(**memory) for memory in protagonist_data["memories"]]
    protagonist_data["relationships"] = {
        name: Relationship(**relationship)
        for name, relationship in protagonist_data["relationships"].items()
    }
    state = WorldState(
        clock=Clock(day=raw["clock"]["day"], slot=TimeSlot(raw["clock"]["slot"])),
        protagonist=Protagonist(**protagonist_data),
        events=[Event(day=event["day"], slot=TimeSlot(event["slot"]), action=event["action"],
                      reason=event["reason"], outcome=event["outcome"])
                for event in raw["events"]],
        gate_alert_level=raw["gate_alert_level"],
        rent_payments=raw["rent_payments"],
        shop_visits=raw["shop_visits"],
    )
    simulation = Simulation(seed=data["seed"], state=state)
    simulation.rng.setstate(_tuplify(data["rng_state"]))
    return simulation


from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .simulation import Simulation
