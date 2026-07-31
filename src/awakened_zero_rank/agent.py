from __future__ import annotations

import random

from .actions import Action, available_actions
from .models import Protagonist, TimeSlot


class UtilityAgent:
    """Transparent baseline policy; small seeded noise breaks near-ties."""

    def __init__(self, rng: random.Random) -> None:
        self.rng = rng

    def choose(self, protagonist: Protagonist, slot: TimeSlot) -> tuple[Action, str]:
        scores = [
            (action.score(protagonist, slot) + self.rng.uniform(0, 2), action)
            for action in available_actions()
        ]
        score, action = max(scores, key=lambda item: item[0])
        reason = self._reason(action.name, protagonist)
        return action, f"{reason} (utility {score:.1f})"

    @staticmethod
    def _reason(action: str, p: Protagonist) -> str:
        reasons = {
            "Eat": f"hunger is {p.hunger}/100",
            "Rest": f"energy is {p.energy}/100 and stress is {p.stress}/100",
            "Part-time work": f"¥{max(0, p.rent_cost - p.money):,} is still needed for rent",
            "Study": f"knowledge is only {p.knowledge}",
            "Train": f"fitness is only {p.fitness}",
        }
        return reasons[action]

