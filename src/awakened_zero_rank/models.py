from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class TimeSlot(str, Enum):
    MORNING = "Morning"
    AFTERNOON = "Afternoon"
    EVENING = "Evening"
    LATE_NIGHT = "Late Night"


SLOTS = tuple(TimeSlot)


@dataclass
class Clock:
    day: int = 1
    slot: TimeSlot = TimeSlot.MORNING

    def advance(self) -> None:
        index = SLOTS.index(self.slot)
        if index == len(SLOTS) - 1:
            self.day += 1
            self.slot = SLOTS[0]
        else:
            self.slot = SLOTS[index + 1]


@dataclass
class Protagonist:
    name: str = "Ren Takahashi"
    location: str = "Adachi, Tokyo"
    hunter_rank: str = "Unranked"
    money: int = 2_500
    health: int = 100
    energy: int = 65
    hunger: int = 25
    stress: int = 35
    knowledge: int = 5
    fitness: int = 4
    reputation: int = 0
    rent_due_day: int = 8
    rent_cost: int = 8_000

    def clamp(self) -> None:
        for stat in ("health", "energy", "hunger", "stress"):
            setattr(self, stat, max(0, min(100, getattr(self, stat))))


@dataclass(frozen=True)
class Event:
    day: int
    slot: TimeSlot
    action: str
    reason: str
    outcome: str

    def __str__(self) -> str:
        return (
            f"Day {self.day:02d} | {self.slot.value:<10} | "
            f"{self.action:<14} | {self.outcome} Why: {self.reason}"
        )


@dataclass
class WorldState:
    clock: Clock = field(default_factory=Clock)
    protagonist: Protagonist = field(default_factory=Protagonist)
    events: list[Event] = field(default_factory=list)

