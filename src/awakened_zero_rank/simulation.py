from __future__ import annotations

import random

from .agent import UtilityAgent
from .models import Event, WorldState
from .world import travel_cost


RANK_THRESHOLDS = ((90, "C"), (60, "D"), (30, "E"))


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
        action, reason = self.agent.choose(protagonist, clock.slot, self.state.gate_alert_level)
        outcome = self._resolve_gate_mission() if action.name == "Gate mission" else action.apply(protagonist)
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
            return Event(clock.day, clock.slot, "Awakening assessment",
                         "a city gate alert triggered Ren's mandatory screening (world event)",
                         "Awakened at Rank F with Threat Sense.")

        if clock.day == 4 and clock.slot.value == "Morning" and p.awakened and not p.guild_registered:
            fare = min(p.money, travel_cost(p.location, "Tokyo Hunter Guild"))
            p.money -= fare
            p.location = "Tokyo Hunter Guild"
            p.guild_registered = True
            p.reputation += 1
            self.state.gate_alert_level = 2
            return Event(clock.day, clock.slot, "Guild registration",
                         "newly awakened citizens must register before accepting hunter work (world event)",
                         f"Received an F-rank license; travel and filing cost ¥{fare:,}.")

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
            return Event(clock.day, clock.slot, "Rent deadline",
                         "the apartment payment was automatically due (world event)", outcome)
        return None

    def _resolve_gate_mission(self) -> str:
        p = self.state.protagonist
        fare = min(p.money, travel_cost(p.location, "Adachi Gate Zone"))
        p.money -= fare
        p.location = "Adachi Gate Zone"
        p.missions_attempted += 1
        difficulty = 43 + self.state.gate_alert_level * 6
        roll = p.combat_readiness + self.rng.randint(-12, 12)
        p.energy -= 28
        p.hunger += 18
        p.stress += 12
        self.state.gate_alert_level = max(0, self.state.gate_alert_level - 2)
        if roll >= difficulty:
            reward = 5_000 + difficulty * 40
            points = 10 + self.state.gate_alert_level * 2
            p.money += reward
            p.rank_points += points
            p.combat_experience += 5
            p.missions_completed += 1
            p.reputation += 2
            promotion = self._promote_if_eligible()
            suffix = f" Promoted to Rank {promotion}!" if promotion else ""
            return (f"Cleared a low-rank gate (roll {roll} vs {difficulty}) for ¥{reward:,} "
                    f"and {points} rank points; fare cost ¥{fare:,}.{suffix}")
        damage = max(8, difficulty - roll + 8)
        p.health -= damage
        p.injuries += 1
        p.combat_experience += 2
        return (f"Retreated from a low-rank gate (roll {roll} vs {difficulty}); suffered "
                f"{damage} damage and received no reward. Fare cost ¥{fare:,}.")

    def _promote_if_eligible(self) -> str | None:
        p = self.state.protagonist
        order = {"F": 0, "E": 1, "D": 2, "C": 3}
        for threshold, rank in RANK_THRESHOLDS:
            if p.rank_points >= threshold and order.get(rank, 0) > order.get(p.hunter_rank, -1):
                p.hunter_rank = rank
                return rank
        return None

    def _update_gate_alert(self) -> None:
        if self.rng.random() < 0.12:
            self.state.gate_alert_level = min(3, self.state.gate_alert_level + 1)
            self.state.protagonist.gates_witnessed += 1
        elif self.state.gate_alert_level:
            self.state.gate_alert_level -= 1
