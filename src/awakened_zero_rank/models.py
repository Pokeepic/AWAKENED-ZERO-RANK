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
    location: str = "Adachi Apartment"
    hunter_rank: str = "Unranked"
    awakened: bool = False
    ability: str = "None"
    guild_registered: bool = False
    money: int = 2_500
    health: int = 100
    energy: int = 65
    hunger: int = 25
    stress: int = 35
    knowledge: int = 5
    fitness: int = 4
    reputation: int = 0
    rank_points: int = 0
    combat_experience: int = 0
    missions_attempted: int = 0
    missions_completed: int = 0
    injuries: int = 0
    inventory: dict[str, int] = field(default_factory=dict)
    equipped_weapon: str | None = None
    equipped_armor: str | None = None
    rent_due_day: int = 8
    rent_cost: int = 8_000
    rent_arrears: int = 0
    gates_witnessed: int = 0
    current_goal: str = "Earn enough yen to pay rent"
    memories: list[Memory] = field(default_factory=list)
    relationships: dict[str, Relationship] = field(default_factory=dict)

    @property
    def combat_readiness(self) -> int:
        """A readable 0-100 estimate used by both the agent and mission system."""
        from .world import ITEMS

        equipment_bonus = sum(
            ITEMS[item].combat_bonus
            for item in (self.equipped_weapon, self.equipped_armor)
            if item is not None
        )
        raw = (self.health * 0.35 + self.energy * 0.25 + self.fitness * 2
               + self.knowledge + equipment_bonus)
        return max(0, min(100, round(raw)))

    def item_count(self, name: str) -> int:
        return self.inventory.get(name, 0)

    def add_item(self, name: str, quantity: int = 1) -> None:
        self.inventory[name] = self.item_count(name) + quantity

    def consume_item(self, name: str) -> bool:
        if self.item_count(name) <= 0:
            return False
        self.inventory[name] -= 1
        if self.inventory[name] == 0:
            del self.inventory[name]
        return True

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
            f"{self.action:<18} | {self.outcome} Why: {self.reason}"
        )


@dataclass(frozen=True)
class Memory:
    day: int
    summary: str
    importance: int


@dataclass
class Relationship:
    name: str
    role: str
    trust: int = 0
    familiarity: int = 0
    meetings: int = 0

    def change(self, trust: int, familiarity: int = 1) -> None:
        self.trust = max(-100, min(100, self.trust + trust))
        self.familiarity = max(0, min(100, self.familiarity + familiarity))
        self.meetings += 1


@dataclass
class WorldState:
    clock: Clock = field(default_factory=Clock)
    protagonist: Protagonist = field(default_factory=Protagonist)
    events: list[Event] = field(default_factory=list)
    gate_alert_level: int = 0
    rent_payments: int = 0
    shop_visits: int = 0
