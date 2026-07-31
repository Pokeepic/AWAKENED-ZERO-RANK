from __future__ import annotations

from .models import Event


ATMOSPHERE = {
    "Morning": "Morning light reaches the narrow apartment streets.",
    "Afternoon": "Tokyo is fully awake around me.",
    "Evening": "The city lights flicker on.",
    "Late Night": "The last trains and distant sirens break the quiet.",
}


def journal_entry(event: Event) -> str:
    """Render an event as a compact scene centered on Ren's experience."""
    opening = ATMOSPHERE[event.slot.value]
    thoughts = {
        "Part-time work": "Rent will not wait for me.",
        "Eat": "I cannot think clearly on an empty stomach.",
        "Rest": "Pushing any farther would be reckless.",
        "Study": "Knowledge may be the only advantage I can afford.",
        "Train": "If another gate opens nearby, I need to be ready.",
        "Awakening assessment": "Rank F. The lowest rank—but no longer nothing.",
        "Guild registration": "Aiko says my name as she hands me the license.",
        "Gate mission": "Threat Sense keeps whispering that danger is close.",
        "Rent deadline": "For one moment, the whole month comes down to a number.",
        "Talk with Aiko": "Her reaction tells me more than her words do.",
        "Visit hunter shop": "Every item costs money I may need for rent.",
        "Guild patrol": "It is safer than a gate, but danger still has a scent.",
    }
    thought = thoughts.get(event.action, "I chose the best path I could see.")
    return (
        f"Day {event.day} — {event.slot.value}\n"
        f"{opening} {thought}\n"
        f"{event.outcome}"
    )
