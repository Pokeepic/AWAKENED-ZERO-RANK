from __future__ import annotations

from .models import Event


ATMOSPHERE = {
    "Morning": "Morning light reaches the narrow apartment streets.",
    "Afternoon": "Tokyo is fully awake around me.",
    "Evening": "The city lights flicker on.",
    "Late Night": "The last trains and distant sirens break the quiet.",
}


def journal_entry(event: Event, weather: str | None = None, temperature_c: int | None = None,
                  mood: str | None = None) -> str:
    """Render an event as a compact scene centered on Ren's experience."""
    opening = ATMOSPHERE[event.slot.value]
    if weather is not None:
        opening += f" It is {weather.lower()}"
        opening += f" and {temperature_c}°C." if temperature_c is not None else "."
    if mood is not None:
        opening += f" I feel {mood.lower()}."
    thoughts = {
        "Part-time work": "Rent will not wait for me.",
        "Eat": "I cannot think clearly on an empty stomach.",
        "Rest": "Pushing any farther would be reckless.",
        "Study": "Knowledge may be the only advantage I can afford.",
        "Train": "Growth only counts if my body can survive the next day.",
        "Awakening assessment": "Rank F. The lowest rank—but no longer nothing.",
        "Guild registration": "Aiko says my name as she hands me the license.",
        "Gate mission": "Threat Sense changes with every danger I survive.",
        "Rent deadline": "For one moment, the whole month comes down to a number.",
        "Talk with Aiko": "Her reaction tells me more than her words do.",
        "Visit hunter shop": "Every item costs money I may need for rent.",
        "Guild patrol": "It is safer than a gate, but danger still has a scent.",
        "Tanabata evening": "For tonight, wishes seem more real than ranks.",
    }
    thought = ("Another person has entered the part of my life shaped by gates."
               if event.action.startswith("Meet ") else
               thoughts.get(event.action, "I chose the best path I could see."))
    return (
        f"Day {event.day} — {event.slot.value}\n"
        f"{opening} {thought}\n"
        f"{event.outcome}"
    )
