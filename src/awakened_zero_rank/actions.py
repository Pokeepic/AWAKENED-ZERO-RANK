from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .models import Protagonist, TimeSlot
from .world import ITEMS, JOBS, rank_meets_requirement, travel_cost


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


def _pay_rent_arrears(p: Protagonist) -> str:
    payment = min(p.rent_arrears, max(0, p.money - 600))
    p.money -= payment
    p.rent_arrears -= payment
    cleared = p.rent_arrears == 0
    p.stress -= 15 if cleared else max(3, payment // 1_000 * 2)
    p.morale += 5 if cleared else 1
    status = "cleared the debt" if cleared else f"left ¥{p.rent_arrears:,} outstanding"
    return f"Paid ¥{payment:,} toward rent arrears and {status}."


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


def _treatment_placeholder(_: Protagonist) -> str:
    return "Treatment pending resolution."


def _prepare_placeholder(_: Protagonist) -> str:
    return "Portal preparation pending resolution."


def _shop_priority(p: Protagonist, available_money: int | None = None) -> str | None:
    """Return the next affordable, rank-legal purchase without risking rent."""
    budget = p.money if available_money is None else available_money

    def affordable(name: str, *, reserve_rent: bool = False) -> bool:
        reserve = p.rent_cost if reserve_rent else 0
        return budget >= ITEMS[name].price + reserve

    if p.equipped_weapon is None and affordable("Field Knife", reserve_rent=True):
        return "Field Knife"
    if p.equipped_armor is None and affordable("Padded Jacket", reserve_rent=True):
        return "Padded Jacket"
    if p.item_count("Healing Gel") < 2 and p.health < 80 and affordable("Healing Gel"):
        return "Healing Gel"
    if p.item_count("Energy Drink") < 2 and p.energy < 65 and affordable("Energy Drink"):
        return "Energy Drink"

    upgrades = (
        ("Reinforced Machete", p.equipped_weapon),
        ("Gateweave Vest", p.equipped_armor),
    )
    for name, equipped in upgrades:
        item = ITEMS[name]
        if (equipped != name and p.rent_arrears == 0 and
                rank_meets_requirement(p.hunter_rank, item.minimum_rank) and
                affordable(name, reserve_rent=True)):
            return name

    if p.item_count("Healing Gel") < 2 and affordable("Healing Gel"):
        return "Healing Gel"
    if p.item_count("Energy Drink") < 2 and affordable("Energy Drink"):
        return "Energy Drink"
    return None


def _shop_score(p: Protagonist, slot: TimeSlot, alert: int) -> float:
    """Value the exact purchase the shop action would make."""
    fare = travel_cost(p.location, "Kita-Senju Hunter Supply")
    priority = _shop_priority(p, p.money - fare)
    purchase_value = 0
    if priority == "Field Knife" and p.money >= ITEMS[priority].price + p.rent_cost:
        purchase_value = 48
    elif priority == "Padded Jacket" and p.money >= ITEMS[priority].price + p.rent_cost:
        purchase_value = 42
    elif priority == "Healing Gel" and p.health < 75 and p.money >= ITEMS[priority].price:
        purchase_value = 14 * (2 - p.item_count(priority))
    elif priority == "Energy Drink" and p.energy < 60 and p.money >= ITEMS[priority].price:
        purchase_value = 12 * (2 - p.item_count(priority))
    elif priority == "Reinforced Machete":
        purchase_value = 62
    elif priority == "Gateweave Vest":
        purchase_value = 56
    return purchase_value + (8 if slot in (TimeSlot.MORNING, TimeSlot.AFTERNOON) else -25) - alert * 5


def _shop(p: Protagonist) -> str:
    fare = _travel(p, "Kita-Senju Hunter Supply")
    priority = _shop_priority(p, p.money)
    if priority is None:
        return f"Browsed hunter supplies but already carried the planned field stock; fare cost ¥{fare:,}."
    item = ITEMS[priority]
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
    p.energy -= 8
    p.stress -= 12
    return f"Reached the guild break room; fare cost ¥{fare:,}."


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
    if p.rent_arrears > 0 and p.money > 600:
        actions.append(Action(
            "Pay rent arrears",
            lambda p, _slot, _alert: (
                70 + min(p.rent_arrears, p.money - 600) / 80 + p.rent_arrears / 200
                - p.injury_severity * 20 - max(0, 60 - p.health)
            ),
            _pay_rent_arrears,
        ))
    if p.injury_severity > 0:
        actions.append(Action(
            "Seek treatment",
            lambda p, _slot, _alert: 45 + p.injury_severity * 18 + (100 - p.health) * 0.5,
            _treatment_placeholder,
        ))
    if p.guild_registered:
        actions.append(Action(
            "Prepare portal",
            lambda p, slot, alert: 24 + alert * 11 + p.knowledge * 0.8
            + (10 if slot in (TimeSlot.MORNING, TimeSlot.AFTERNOON) else -8)
            - max(0, 30 - p.energy),
            _prepare_placeholder,
        ))
        actions.append(Action(
            "Visit hunter shop",
            _shop_score,
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
