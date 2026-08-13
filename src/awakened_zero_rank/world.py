from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Location:
    name: str
    travel_cost: int
    purpose: str


@dataclass(frozen=True)
class Job:
    name: str
    location: str
    pay: int
    energy_cost: int


@dataclass(frozen=True)
class Item:
    name: str
    kind: str
    price: int
    combat_bonus: int = 0
    description: str = ""


@dataclass(frozen=True)
class GateEncounter:
    name: str
    difficulty: int
    reward: int
    rank_points: int
    damage_bonus: int = 0


LOCATIONS = {
    "Adachi Apartment": Location("Adachi Apartment", 0, "home and recovery"),
    "Kita-Senju": Location("Kita-Senju", 180, "part-time work and shopping"),
    "Ueno Library": Location("Ueno Library", 220, "study and gate-safety research"),
    "Arakawa Riverbank": Location("Arakawa Riverbank", 160, "free physical training"),
    "Tokyo Awakening Bureau": Location("Tokyo Awakening Bureau", 320, "awakening assessments"),
    "Tokyo Hunter Guild": Location("Tokyo Hunter Guild", 280, "registration and hunter work"),
    "Adachi Gate Zone": Location("Adachi Gate Zone", 240, "regulated low-rank gates"),
    "Kita-Senju Hunter Supply": Location("Kita-Senju Hunter Supply", 180, "budget hunter equipment"),
}

ITEMS = {
    "Field Knife": Item("Field Knife", "weapon", 2_400, 7, "A legal beginner hunter weapon."),
    "Padded Jacket": Item("Padded Jacket", "armor", 3_200, 5, "Basic protection against claws and debris."),
    "Healing Gel": Item("Healing Gel", "consumable", 900, description="Restores 22 health."),
    "Energy Drink": Item("Energy Drink", "consumable", 450, description="Restores 18 energy."),
}

GATE_ENCOUNTERS = (
    GateEncounter("Tunnel Slime Nest", 42, 5_400, 10),
    GateEncounter("Goblin Scavenger Pack", 49, 6_600, 13, 3),
    GateEncounter("Armored Fang Boar", 57, 8_200, 17, 7),
)
MISSION_RANK_POINT_AWARDS = (10, 13, 17)


def mission_rank_points_are_possible(completed: int, points: int) -> bool:
    """Return whether points can be composed from authored mission awards."""
    if completed == 0:
        return points == 0
    remainder = points - completed * MISSION_RANK_POINT_AWARDS[0]
    if remainder < 0 or remainder > 7 * completed:
        return False
    minimum_sevens = max(0, (remainder - 3 * completed + 3) // 4)
    maximum_sevens = min(completed, remainder // 7)
    first_sevens = minimum_sevens + (remainder - minimum_sevens) % 3
    return first_sevens <= maximum_sevens

JOBS = {
    "konbini": Job("Kita-Senju konbini shift", "Kita-Senju", 2_200, 22),
    "guild_patrol": Job("F-rank guild perimeter patrol", "Tokyo Hunter Guild", 3_200, 27),
}


def travel_cost(origin: str, destination: str) -> int:
    if origin == destination:
        return 0
    return max(LOCATIONS[origin].travel_cost, LOCATIONS[destination].travel_cost)
