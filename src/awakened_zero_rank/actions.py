from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .models import Protagonist, TimeSlot
from .world import ITEMS, JOBS, travel_cost


Effect = Callable[[Protagonist], str]
Score = Callable[[Protagonist, TimeSlot, int], float]


@dataclass(frozen=True)
class Action:
    name: str
    score: Score
    apply: Effect


def _travel(p: Protagonist, destination: str) -> int:
    fare = min(p.money, travel_cost(p.location, destination))
    p.money -= fare
    p.location = destination
    return fare


def _work(p: Protagonist) -> str:
    job = JOBS["konbini"]
    fare = _travel(p, job.location)
    p.money += job.pay
    p.energy -= job.energy_cost
    p.hunger += 16
    p.stress += 10
    return f"Worked a konbini shift for ¥{job.pay:,}; train fare cost ¥{fare:,}."


def _patrol(p: Protagonist) -> str:
    job = JOBS["guild_patrol"]
    fare = _travel(p, job.location)
    p.money += job.pay
    p.energy -= job.energy_cost
    p.hunger += 18
    p.stress += 8
    p.combat_experience += 2
    p.reputation += 1
    return f"Completed a guild perimeter patrol for ¥{job.pay:,}; fare cost ¥{fare:,}."


def _mission_placeholder(_: Protagonist) -> str:
    return "Gate mission pending resolution."


def _shop(p: Protagonist) -> str:
    fare = _travel(p, "Kita-Senju Hunter Supply")
    priorities = (
        "Field Knife" if p.equipped_weapon is None else
        "Padded Jacket" if p.equipped_armor is None else
        "Healing Gel" if p.item_count("Healing Gel") < 2 else
        "Energy Drink"
    )
    item = ITEMS[priorities]
    if p.money < item.price:
        return f"Browsed hunter supplies but could not afford {item.name}; fare cost ¥{fare:,}."
    p.money -= item.price
    p.add_item(item.name)
    if item.kind == "weapon":
        p.equipped_weapon = item.name
    elif item.kind == "armor":
        p.equipped_armor = item.name
    p.stress -= 2
    return f"Bought {item.name} for ¥{item.price:,} and equipped it when possible; fare cost ¥{fare:,}."


def _socialize(p: Protagonist) -> str:
    fare = _travel(p, "Tokyo Hunter Guild")
    relationship = p.relationships["Aiko Sato"]
    relationship.change(trust=4, familiarity=6)
    p.energy -= 8
    p.stress -= 12
    p.reputation += 1
    return (f"Shared a break with Aiko Sato at the guild; trust is now "
            f"{relationship.trust} and familiarity {relationship.familiarity}. Fare cost ¥{fare:,}.")


def _eat(p: Protagonist) -> str:
    cost = 600 if p.money >= 600 else 0
    p.money -= cost
    p.hunger -= 45 if cost else 20
    p.energy += 8
    return "Bought a filling konbini meal." if cost else "Ate the last instant noodles at home."


def _rest(p: Protagonist) -> str:
    fare = _travel(p, "Adachi Apartment")
    p.energy += 42
    p.stress -= 20
    p.hunger += 8
    return f"Returned home and rested; travel cost ¥{fare:,}."


def _study(p: Protagonist) -> str:
    fare = _travel(p, "Ueno Library")
    p.knowledge += 2
    perception_gain = int(p.knowledge % 3 == 0)
    p.perception += perception_gain
    p.energy -= 13
    p.hunger += 7
    p.stress += 4
    return (f"Studied gate safety (+2 knowledge, +{perception_gain} perception); "
            f"travel cost ¥{fare:,}.")


def _train(p: Protagonist) -> str:
    fare = _travel(p, "Arakawa Riverbank")
    condition = min(p.health, p.energy)
    gain = 2 if condition >= 55 else 1
    focus = ("Strength", "Agility", "Endurance")[p.training_sessions % 3]
    repeated = p.recent_training[-2:].count(focus)
    attribute_gain = 0 if repeated >= 2 or condition < 30 else 1
    p.fitness += gain
    setattr(p, focus.lower(), getattr(p, focus.lower()) + attribute_gain)
    p.training_sessions += 1
    p.recent_training.append(focus)
    del p.recent_training[:-6]
    p.energy -= 20
    p.hunger += 12
    p.stress -= 5
    result = f"Trained {focus.lower()} beside the Arakawa (+{gain} fitness"
    result += f", +{attribute_gain} {focus.lower()}); travel cost ¥{fare:,}."
    return result


def available_actions(p: Protagonist) -> tuple[Action, ...]:
    actions = [
        Action("Eat", lambda p, _s, _a: p.hunger * 1.8 + (25 if p.health < 50 else 0), _eat),
        Action(
            "Rest",
            lambda p, slot, _a: (100 - p.energy) * 1.25 + p.stress * 0.45
            + (22 if slot is TimeSlot.LATE_NIGHT else 0),
            _rest,
        ),
        Action(
            "Part-time work",
            lambda p, slot, _a: (p.rent_arrears or max(0, p.rent_cost - p.money)) / 90
            + (18 if slot in (TimeSlot.MORNING, TimeSlot.AFTERNOON, TimeSlot.EVENING) else -30)
            - max(0, 35 - p.energy),
            _work,
        ),
        Action(
            "Study",
            lambda p, slot, _a: 32 - p.knowledge * 0.7
            + (10 if slot in (TimeSlot.AFTERNOON, TimeSlot.EVENING) else 0)
            - max(0, 30 - p.energy),
            _study,
        ),
        Action(
            "Train",
            lambda p, slot, _a: 30 - p.fitness * 0.7
            + (8 if slot in (TimeSlot.MORNING, TimeSlot.AFTERNOON) else 0)
            - max(0, 35 - p.energy),
            _train,
        ),
    ]
    if p.guild_registered:
        actions.append(Action(
            "Visit hunter shop",
            lambda p, slot, alert: (
                (48 if p.equipped_weapon is None and p.money >= ITEMS["Field Knife"].price + p.rent_cost else 0)
                + (42 if p.equipped_weapon and p.equipped_armor is None
                   and p.money >= ITEMS["Padded Jacket"].price + p.rent_cost else 0)
                + (28 if p.health < 75 and p.item_count("Healing Gel") == 0 and p.money >= 1_500 else 0)
                + (8 if slot in (TimeSlot.MORNING, TimeSlot.AFTERNOON) else -25)
                - alert * 5
            ),
            _shop,
        ))
        actions.append(Action(
            "Talk with Aiko",
            lambda p, slot, _a: 18 + p.stress * 0.45
            + (12 if p.relationships["Aiko Sato"].familiarity < 25 else 0)
            + (8 if slot is TimeSlot.EVENING else 0)
            - max(0, 25 - p.energy),
            _socialize,
        ))
        actions.append(Action(
            "Guild patrol",
            lambda p, slot, _a: 35 + p.rent_arrears / 100
            + (12 if slot is not TimeSlot.LATE_NIGHT else -25)
            - max(0, 42 - p.energy),
            _patrol,
        ))
        actions.append(Action(
            "Gate mission",
            lambda p, slot, alert: alert * 27 + p.combat_readiness * 0.35
            + (12 if slot in (TimeSlot.MORNING, TimeSlot.AFTERNOON) else -12)
            - max(0, 45 - p.health) - max(0, 40 - p.energy),
            _mission_placeholder,
        ))
    return tuple(actions)
