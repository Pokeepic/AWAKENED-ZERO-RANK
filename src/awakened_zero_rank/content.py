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
