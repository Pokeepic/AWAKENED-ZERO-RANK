"""Structured narrative content designed to scale without incoherent line dumps."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import product


@dataclass(frozen=True)
class PortalProfile:
    name: str
    environment: str
    hazard: str
    clue: str


@dataclass(frozen=True)
class NPCProfile:
    name: str
    role: str
    personality: str
    speaking_style: str
    loyalty: str


TOKYO_LOCATIONS = (
    "Adachi Apartment", "Kita-Senju Station", "Ueno Library",
    "Tokyo Hunter Guild", "Arakawa Riverbank", "Adachi Gate Zone",
    "Akihabara Market", "Asakusa Shrine District", "Shinjuku Guild Annex",
)

PORTALS = (
    PortalProfile("Flooded Service Tunnel", "underground", "rising water", "fresh claw marks"),
    PortalProfile("Ashen Shopping Arcade", "urban ruin", "cinder wind", "a working payphone"),
    PortalProfile("Moonlit Cedar Path", "forest", "false trails", "bells without a source"),
    PortalProfile("Frostbound Platform", "ice", "whiteout", "an arriving ghost train"),
    PortalProfile("Sunken Courtyard", "swamp", "toxic spores", "guild equipment in the reeds"),
    PortalProfile("Glass Office Labyrinth", "urban tower", "shifting rooms", "Ren's reflection moves late"),
)

NPCS = {
    "Aiko Sato": NPCProfile("Aiko Sato", "F-rank guild clerk", "observant and kind",
                             "careful, practical sentences", "protect novice hunters"),
    "Daichi Mori": NPCProfile("Daichi Mori", "Rank E patrol leader", "blunt and disciplined",
                               "short field instructions", "protect his patrol team"),
    "Mei Kuroda": NPCProfile("Mei Kuroda", "independent portal researcher", "curious and guarded",
                              "precise questions and dry humor", "discover portal truth"),
    "Haruto Ishikawa": NPCProfile("Haruto Ishikawa", "hunter supply owner", "warm but shrewd",
                                   "friendly merchant banter", "keep his shop independent"),
}

# Recurring weekly routines. NPCs can still deviate when a delayed consequence calls them away.
NPC_SCHEDULES = {
    "Aiko Sato": {"Morning": "Tokyo Hunter Guild", "Afternoon": "Tokyo Hunter Guild",
                   "Evening": "Kita-Senju Station", "Late Night": "Home"},
    "Daichi Mori": {"Morning": "Adachi Gate Zone", "Afternoon": "Tokyo Hunter Guild",
                     "Evening": "Arakawa Riverbank", "Late Night": "Home"},
    "Mei Kuroda": {"Morning": "Ueno Library", "Afternoon": "Adachi Gate Zone",
                    "Evening": "Ueno Library", "Late Night": "Shinjuku Guild Annex"},
    "Haruto Ishikawa": {"Morning": "Akihabara Market", "Afternoon": "Akihabara Market",
                         "Evening": "Kita-Senju Station", "Late Night": "Home"},
}


def scheduled_location(name: str, slot: str, day: int) -> str:
    """Return a stable routine location, including a weekly day off."""
    if day % 7 == 0 and name in {"Aiko Sato", "Haruto Ishikawa"}:
        return "Asakusa Shrine District"
    return NPC_SCHEDULES[name][slot]

DIALOGUE_COMPONENTS = {
    "intent": ("guidance", "gratitude", "support", "honesty", "apology", "humor", "warning"),
    "mood": ("uneasy", "exhausted", "hopeful", "anxious", "steady"),
    "relationship": ("strangers", "guarded", "familiar", "trusted", "tense"),
    "context": ("guild", "after a gate", "rain", "festival", "injury", "rent pressure"),
}


def dialogue_context_count() -> int:
    """Number of meaningful dialogue states before wording variants are added."""
    return len(tuple(product(*DIALOGUE_COMPONENTS.values())))


def portal_situation_count() -> int:
    """Portal/environment combinations available to future encounter generation."""
    approaches = ("enter", "investigate", "report", "avoid")
    weather_states = ("clear", "rain", "heatwave", "thunderstorm")
    return len(PORTALS) * len(approaches) * len(weather_states)


def npc_context_count() -> int:
    """Social states available once identity and personal voice matter."""
    return dialogue_context_count() * len(NPCS)
