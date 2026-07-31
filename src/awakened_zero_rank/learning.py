"""Dependency-free RL adapter and evaluation boundary.

This is intentionally not a learning algorithm. It exposes a stable environment so
future Gymnasium/PPO experiments can be measured against the utility policy first.
"""

from __future__ import annotations

from dataclasses import dataclass

from .actions import available_actions
from .models import SLOTS
from .simulation import Simulation


ACTION_NAMES = (
    "Eat", "Rest", "Part-time work", "Study", "Train", "Visit hunter shop",
    "Talk with Aiko", "Guild patrol", "Gate mission",
)


@dataclass(frozen=True)
class Transition:
    observation: tuple[float, ...]
    reward: float
    action: str
    valid_actions: tuple[str, ...]
    event_outcome: str


class LearningEnvironment:
    """Small strategic interface suitable for accelerated agent experiments."""

    def __init__(self, seed: int = 42) -> None:
        self.simulation = Simulation(seed=seed)

    @property
    def valid_actions(self) -> tuple[str, ...]:
        names = {action.name for action in available_actions(self.simulation.state.protagonist)}
        return tuple(name for name in ACTION_NAMES if name in names)

    def observe(self) -> tuple[float, ...]:
        state, p = self.simulation.state, self.simulation.state.protagonist
        relationship = p.relationships.get("Aiko Sato")
        network_trust = sum(r.trust for r in p.relationships.values())
        return (
            p.health / 100, p.energy / 100, p.hunger / 100, p.stress / 100,
            min(p.money, 50_000) / 50_000, p.combat_readiness / 100,
            p.rank_points / 100, state.gate_alert_level / 3,
            SLOTS.index(state.clock.slot) / (len(SLOTS) - 1),
            (relationship.trust if relationship else 0) / 100,
            (relationship.tension if relationship else 0) / 100,
            p.morale / 100,
            max(-1, min(1, network_trust / 400)),
            len(state.discovered_portals) / 6,
        )

    def action_mask(self) -> tuple[int, ...]:
        valid = set(self.valid_actions)
        return tuple(int(name in valid) for name in ACTION_NAMES)

    def step(self, action: str) -> Transition:
        if action not in self.valid_actions:
            raise ValueError(f"Invalid action {action!r}; valid actions: {self.valid_actions}")
        before = self._score()
        event = self.simulation.step(action)
        reward = round(self._score() - before, 3)
        return Transition(self.observe(), reward, action, self.valid_actions, event.outcome)

    def baseline_step(self) -> Transition:
        before = self._score()
        event = self.simulation.step()
        reward = round(self._score() - before, 3)
        return Transition(self.observe(), reward, event.action, self.valid_actions, event.outcome)

    def _score(self) -> float:
        p = self.simulation.state.protagonist
        survival = p.health * 0.5 + p.energy * 0.12 - p.hunger * 0.12 - p.stress * 0.08
        stability = min(p.money, p.rent_cost * 2) / 350 - p.rent_arrears / 250
        progress = p.rank_points * 0.7 + p.missions_completed * 2 + p.ability_mastery * 0.2
        social = sum((r.trust - r.tension) * 0.08 for r in p.relationships.values())
        return survival + stability + progress + social
