from __future__ import annotations

import random

from .agent import UtilityAgent
from .models import Event, WorldState


class Simulation:
    def __init__(self, seed: int = 42, state: WorldState | None = None) -> None:
        self.seed = seed
        self.state = state or WorldState()
        self.rng = random.Random(seed)
        self.agent = UtilityAgent(self.rng)

    def step(self) -> Event:
        clock = self.state.clock
        protagonist = self.state.protagonist
        special = self._special_event()
        if special is not None:
            self.state.events.append(special)
            clock.advance()
            return special
        action, reason = self.agent.choose(protagonist, clock.slot)
        outcome = action.apply(protagonist)
        self._apply_passive_needs()
        protagonist.clamp()
        event = Event(clock.day, clock.slot, action.name, reason, outcome)
        self.state.events.append(event)
        self._update_gate_alert()
        clock.advance()
        return event

    def run(self, steps: int) -> list[Event]:
        return [self.step() for _ in range(steps)]

    def _apply_passive_needs(self) -> None:
        p = self.state.protagonist
        if p.hunger >= 85:
            p.health -= 8
        if p.energy <= 10:
            p.health -= 5
            p.stress += 8

    def _special_event(self) -> Event | None:
        clock = self.state.clock
        p = self.state.protagonist

        if clock.day == 3 and clock.slot.value == "Afternoon" and not p.awakened:
            p.money -= min(p.money, 320)
            p.location = "Tokyo Awakening Bureau"
            p.awakened = True
            p.hunter_rank = "F"
            p.ability = "Threat Sense"
            p.reputation += 1
            return Event(
                clock.day, clock.slot, "Awakening assessment",
                "a city gate alert triggered Ren's mandatory screening (world event)",
                "Awakened at Rank F with Threat Sense.",
            )

        if clock.day == p.rent_due_day and clock.slot.value == "Morning":
            paid = min(p.money, p.rent_cost)
            p.money -= paid
            unpaid = p.rent_cost - paid
            p.rent_arrears += unpaid
            p.stress += 5 if unpaid == 0 else 25
            p.clamp()
            self.state.rent_payments += int(unpaid == 0)
            outcome = (f"Paid ¥{paid:,} rent in full." if unpaid == 0 else
                       f"Paid ¥{paid:,}; ¥{unpaid:,} became rent arrears.")
            return Event(
                clock.day, clock.slot, "Rent deadline",
                "the apartment payment was automatically due (world event)", outcome,
            )
        return None

    def _update_gate_alert(self) -> None:
        if self.rng.random() < 0.08:
            self.state.gate_alert_level = min(3, self.state.gate_alert_level + 1)
            self.state.protagonist.gates_witnessed += 1
        elif self.state.gate_alert_level:
            self.state.gate_alert_level -= 1
