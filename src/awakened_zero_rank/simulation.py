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
        action, reason = self.agent.choose(protagonist, clock.slot)
        outcome = action.apply(protagonist)
        self._apply_passive_needs()
        protagonist.clamp()
        event = Event(clock.day, clock.slot, action.name, reason, outcome)
        self.state.events.append(event)
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

