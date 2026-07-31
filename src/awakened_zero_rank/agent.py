from __future__ import annotations

import random

from .actions import Action, available_actions
from .models import Protagonist, TimeSlot


class UtilityAgent:
    """Transparent baseline policy; small seeded noise breaks near-ties."""

    def __init__(self, rng: random.Random) -> None:
        self.rng = rng

    def choose(self, protagonist: Protagonist, slot: TimeSlot, gate_alert: int = 0) -> tuple[Action, str]:
        scores = [
            (action.score(protagonist, slot, gate_alert) + self.rng.uniform(0, 2), action)
            for action in available_actions(protagonist)
        ]
        score, action = max(scores, key=lambda item: item[0])
        reason = self._reason(action.name, protagonist, gate_alert)
        return action, f"{reason} (utility {score:.1f})"

    @staticmethod
    def _reason(action: str, p: Protagonist, gate_alert: int) -> str:
        housing_debt = p.rent_arrears or max(0, p.rent_cost - p.money)
        reasons = {
            "Eat": f"hunger is {p.hunger}/100",
            "Rest": f"energy is {p.energy}/100 and stress is {p.stress}/100",
            "Part-time work": f"¥{housing_debt:,} is still needed for housing",
            "Study": f"knowledge is only {p.knowledge}",
            "Train": f"fitness is only {p.fitness}",
            "Guild patrol": f"safe hunter experience pays while readiness is {p.combat_readiness}/100",
            "Gate mission": f"gate alert is {gate_alert}/3 and readiness is {p.combat_readiness}/100",
        }
        return reasons[action]
