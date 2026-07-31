from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .models import Protagonist, TimeSlot
from .world import JOBS, travel_cost


Effect = Callable[[Protagonist], str]
Score = Callable[[Protagonist, TimeSlot], float]


@dataclass(frozen=True)
class Action:
    name: str
    score: Score
    apply: Effect


def _work(p: Protagonist) -> str:
    job = JOBS["konbini"]
    fare = min(p.money, travel_cost(p.location, job.location))
    pay = job.pay
    p.money -= fare
    p.money += pay
    p.energy -= job.energy_cost
    p.hunger += 16
    p.stress += 10
    p.location = job.location
    return f"Worked a konbini shift for ¥{pay:,}; train fare cost ¥{fare:,}."


def _eat(p: Protagonist) -> str:
    cost = 600 if p.money >= 600 else 0
    p.money -= cost
    p.hunger -= 45 if cost else 20
    p.energy += 8
    return "Bought a filling konbini meal." if cost else "Ate the last instant noodles at home."


def _rest(p: Protagonist) -> str:
    fare = min(p.money, travel_cost(p.location, "Adachi Apartment"))
    p.money -= fare
    p.location = "Adachi Apartment"
    p.energy += 42
    p.stress -= 20
    p.hunger += 8
    return f"Returned home and rested; travel cost ¥{fare:,}."


def _study(p: Protagonist) -> str:
    fare = min(p.money, travel_cost(p.location, "Ueno Library"))
    p.money -= fare
    p.location = "Ueno Library"
    p.knowledge += 2
    p.energy -= 13
    p.hunger += 7
    p.stress += 4
    return f"Studied gate safety at Ueno Library; travel cost ¥{fare:,}."


def _train(p: Protagonist) -> str:
    fare = min(p.money, travel_cost(p.location, "Arakawa Riverbank"))
    p.money -= fare
    p.location = "Arakawa Riverbank"
    p.fitness += 2
    p.energy -= 20
    p.hunger += 12
    p.stress -= 5
    return f"Trained beside the Arakawa; travel cost ¥{fare:,}."


def available_actions() -> tuple[Action, ...]:
    return (
        Action(
            "Eat",
            lambda p, _: p.hunger * 1.8 + (25 if p.health < 50 else 0),
            _eat,
        ),
        Action(
            "Rest",
            lambda p, slot: (100 - p.energy) * 1.25 + p.stress * 0.45
            + (22 if slot is TimeSlot.LATE_NIGHT else 0),
            _rest,
        ),
        Action(
            "Part-time work",
            lambda p, slot: (p.rent_arrears or max(0, p.rent_cost - p.money)) / 90
            + (18 if slot in (TimeSlot.MORNING, TimeSlot.AFTERNOON, TimeSlot.EVENING) else -30)
            - max(0, 35 - p.energy),
            _work,
        ),
        Action(
            "Study",
            lambda p, slot: 32 - p.knowledge * 0.7
            + (10 if slot in (TimeSlot.AFTERNOON, TimeSlot.EVENING) else 0)
            - max(0, 30 - p.energy),
            _study,
        ),
        Action(
            "Train",
            lambda p, slot: 30 - p.fitness * 0.7
            + (8 if slot in (TimeSlot.MORNING, TimeSlot.AFTERNOON) else 0)
            - max(0, 35 - p.energy),
            _train,
        ),
    )
