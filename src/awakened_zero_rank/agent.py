from __future__ import annotations

import random

from .actions import Action, available_actions
from .models import Protagonist, TimeSlot


class UtilityAgent:
    """Transparent baseline policy; small seeded noise breaks near-ties."""

    def __init__(self, rng: random.Random) -> None:
        self.rng = rng

    def choose(
        self, protagonist: Protagonist, slot: TimeSlot, gate_alert: int = 0,
        weather: str = "Clear", has_portal_plan: bool = False,
    ) -> tuple[Action, str]:
        scores = [
            (action.score(protagonist, slot, gate_alert)
             + self._weather_adjustment(action.name, weather)
             + self._portal_plan_adjustment(action.name, gate_alert, has_portal_plan)
             + self.rng.uniform(0, 2), action)
            for action in available_actions(protagonist)
        ]
        score, action = max(scores, key=lambda item: item[0])
        reason = self._reason(action.name, protagonist, gate_alert, has_portal_plan)
        return action, f"{reason} (utility {score:.1f})"

    @staticmethod
    def _weather_adjustment(action: str, weather: str) -> float:
        if weather == "Thunderstorm":
            return {"Rest": 18, "Study": 9, "Train": -35, "Gate mission": -24,
                    "Visit hunter shop": -50}.get(action, 0)
        if weather == "Heatwave":
            return {"Rest": 8, "Eat": 5, "Train": -18, "Gate mission": -8}.get(action, 0)
        if weather == "Rain":
            return {"Study": 5, "Train": -10, "Gate mission": -5}.get(action, 0)
        return 0

    @staticmethod
    def _portal_plan_adjustment(action: str, gate_alert: int,
                                has_portal_plan: bool) -> float:
        if gate_alert < 3:
            return 0
        if action == "Prepare portal":
            return -60 if has_portal_plan else 35
        if action == "Gate mission":
            return 12 if has_portal_plan else -40
        return 0

    @staticmethod
    def _reason(action: str, p: Protagonist, gate_alert: int,
                has_portal_plan: bool = False) -> str:
        housing_debt = p.rent_arrears or max(0, p.rent_cost - p.money)
        aiko_familiarity = p.relationships.get("Aiko Sato")
        plan_state = "ready" if has_portal_plan else "missing"
        reasons = {
            "Eat": f"hunger is {p.hunger}/100",
            "Rest": f"energy is {p.energy}/100 and stress is {p.stress}/100",
            "Part-time work": f"¥{housing_debt:,} is still needed for housing",
            "Pay rent arrears": f"¥{p.rent_arrears:,} of overdue rent remains",
            "Study": f"knowledge is only {p.knowledge}",
            "Train": f"fitness is only {p.fitness}",
            "Guild patrol": f"safe hunter experience pays while readiness is {p.combat_readiness}/100",
            "Gate mission": (f"gate alert is {gate_alert}/3, readiness is "
                             f"{p.combat_readiness}/100, and a plan is {plan_state}"),
            "Seek treatment": (f"injury severity is {p.injury_severity}/5 and health is "
                               f"{p.health}/100"),
            "Prepare portal": (f"gate alert is {gate_alert}/3, planning knowledge is "
                               f"{p.knowledge}, and a plan is {plan_state}"),
            "Talk with Aiko": (f"stress is {p.stress}/100 and their familiarity is "
                               f"{aiko_familiarity.familiarity if aiko_familiarity else 0}/100"),
            "Visit hunter shop": (f"equipment is {p.equipped_weapon or 'no weapon'} and "
                                  f"{p.equipped_armor or 'no armor'}"),
        }
        return reasons[action]
