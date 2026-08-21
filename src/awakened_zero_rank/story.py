"""Read-only structured progress for the deterministic three-year story arc."""

from __future__ import annotations

from typing import Any

from .content import STORY_ANCHORS
from .models import WorldState


STORY_PROGRESS_SCHEMA_VERSION = 4


def _ending_summary(state: WorldState) -> dict[str, Any] | None:
    ending_anchor = next(anchor for anchor in STORY_ANCHORS if anchor.ending)
    if ending_anchor.key not in state.story_outcomes:
        return None
    tiers = tuple(state.story_outcomes.values())
    counts = {
        tier: tiers.count(tier)
        for tier in ("isolated", "resilient", "prepared")
    }
    final_tier = state.story_outcomes[ending_anchor.key]
    if "legacy-unavailable" in tiers:
        ending_id = "legacy-unavailable"
        title = "Legacy Ending Unavailable"
        summary = "This timeline predates authenticated story outcome evidence."
    elif final_tier == "isolated":
        ending_id = "unfinished-warning"
        title = "The Unfinished Warning"
        summary = "Ren survived, but the warning he carried remained unresolved."
    elif final_tier == "prepared" and counts["prepared"] >= 4:
        ending_id = "zero-rank-horizon"
        title = "The Zero-Rank Horizon"
        summary = "Ren's evidence and trusted circle changed what Tokyo valued in a hunter."
    else:
        ending_id = "quiet-guardian"
        title = "Tokyo's Quiet Guardian"
        summary = "Ren left Tokyo steadier through persistence rather than recognition."
    return {
        "id": ending_id,
        "isolated_count": counts["isolated"],
        "prepared_count": counts["prepared"],
        "resilient_count": counts["resilient"],
        "summary": summary,
        "tier": final_tier,
        "title": title,
    }


def story_progress(state: WorldState) -> dict[str, Any]:
    """Return a deterministic, JSON-ready story summary without mutating state."""
    completed = [
        {
            "day": anchor.day,
            "focus_npcs": list(anchor.focus_npcs),
            "international_link": anchor.international_link,
            "key": anchor.key,
            "outcome": (
                "Outcome tier unavailable in this legacy timeline."
                if state.story_outcomes[anchor.key] == "legacy-unavailable"
                else anchor.outcome(state.story_outcomes[anchor.key])),
            "portal_consequence": anchor.portal_consequence,
            "premise": anchor.premise,
            "scene": anchor.scene,
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
        "ending": _ending_summary(state),
        "ending_reached": ending_key in state.story_outcomes,
        "next": next_summary,
        "schema_version": STORY_PROGRESS_SCHEMA_VERSION,
        "total_anchors": len(STORY_ANCHORS),
    }
