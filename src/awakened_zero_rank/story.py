"""Read-only structured progress for the deterministic three-year story arc."""

from __future__ import annotations

from typing import Any

from .content import STORY_ANCHORS
from .models import WorldState


STORY_PROGRESS_SCHEMA_VERSION = 1


def story_progress(state: WorldState) -> dict[str, Any]:
    """Return a deterministic, JSON-ready story summary without mutating state."""
    completed = [
        {
            "day": anchor.day,
            "focus_npcs": list(anchor.focus_npcs),
            "key": anchor.key,
            "outcome": anchor.outcome(state.story_outcomes[anchor.key]),
            "tier": state.story_outcomes[anchor.key],
            "title": anchor.title,
        }
        for anchor in STORY_ANCHORS
        if anchor.key in state.story_outcomes
    ]
    next_anchor = next(
        (anchor for anchor in STORY_ANCHORS
         if anchor.key not in state.story_outcomes),
        None)
    next_summary = None if next_anchor is None else {
        "day": next_anchor.day,
        "days_remaining": max(0, next_anchor.day - state.clock.day),
        "key": next_anchor.key,
        "title": next_anchor.title,
    }
    ending_key = next(anchor.key for anchor in STORY_ANCHORS if anchor.ending)
    return {
        "completed": completed,
        "completed_count": len(completed),
        "ending_reached": ending_key in state.story_outcomes,
        "next": next_summary,
        "schema_version": STORY_PROGRESS_SCHEMA_VERSION,
        "total_anchors": len(STORY_ANCHORS),
    }