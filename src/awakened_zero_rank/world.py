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


LOCATIONS = {
    "Adachi Apartment": Location("Adachi Apartment", 0, "home and recovery"),
    "Kita-Senju": Location("Kita-Senju", 180, "part-time work and shopping"),
    "Ueno Library": Location("Ueno Library", 220, "study and gate-safety research"),
    "Arakawa Riverbank": Location("Arakawa Riverbank", 160, "free physical training"),
    "Tokyo Awakening Bureau": Location("Tokyo Awakening Bureau", 320, "awakening assessments"),
    "Tokyo Hunter Guild": Location("Tokyo Hunter Guild", 280, "registration and hunter work"),
    "Adachi Gate Zone": Location("Adachi Gate Zone", 240, "regulated low-rank gates"),
}

JOBS = {
    "konbini": Job("Kita-Senju konbini shift", "Kita-Senju", 2_200, 22),
    "guild_patrol": Job("F-rank guild perimeter patrol", "Tokyo Hunter Guild", 3_200, 27),
}


def travel_cost(origin: str, destination: str) -> int:
    if origin == destination:
        return 0
    return max(LOCATIONS[origin].travel_cost, LOCATIONS[destination].travel_cost)
