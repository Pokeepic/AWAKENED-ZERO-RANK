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
class StoryAnchor:
    key: str
    day: int
    title: str
    premise: str
    focus_npcs: tuple[str, ...]
    scene: str
    portal_consequence: str
    international_link: str | None
    isolated_outcome: str
    resilient_outcome: str
    prepared_outcome: str
    ending: bool = False

    def outcome(self, tier: str) -> str:
        return {
            "isolated": self.isolated_outcome,
            "resilient": self.resilient_outcome,
            "prepared": self.prepared_outcome,
        }[tier]


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

STORY_ANCHORS = (
    StoryAnchor(
        "arc_adachi_warning", 183, "The Adachi Warning",
        "A synchronized Gate pulse forces Tokyo to reassess its weakest districts.",
        ("Aiko Sato", "Daichi Mori"),
        "Aiko maps apartment residents while Daichi marks the patrol routes the guild abandoned.",
        "The newest portal record reveals which evacuation route will destabilize first.",
        None,
        "The warning reached Adachi before Ren had anyone ready to believe him.",
        "Ren helped hold one evacuation route while the district absorbed the shock.",
        "Ren's evidence let the guild clear Adachi before the synchronized breach."),
    StoryAnchor(
        "arc_tokyo_fracture", 365, "The Tokyo Fracture",
        "Conflicting guild orders divide the people responsible for civilian safety.",
        ("Daichi Mori", "Mei Kuroda"),
        "Daichi brings the disputed orders to Mei, who finds a portal signature hidden in their timestamps.",
        "The recorded portal pattern distinguishes the forged order from the real patrol signal.",
        "The forgery uses routing conventions later traced beyond Japan.",
        "The fracture left Ren outside both camps as patrol routes collapsed.",
        "Ren carried evidence between rivals, preserving an uneasy working truce.",
        "Ren's trusted coalition exposed the false order before Tokyo divided."),
    StoryAnchor(
        "arc_foreign_signal", 548, "The Foreign Signal",
        "A repeating portal signature links Japan to a disaster unfolding overseas.",
        ("Mei Kuroda", "Haruto Ishikawa"),
        "Mei decodes the signal at Haruto's shuttered shop while he inventories supplies for an unknown city.",
        "The latest portal record gives the foreign responders a matching hazard and a safe approach.",
        "Responders in Busan confirm the same signature and establish the chronicle's first overseas contact.",
        "The signal faded overseas with no one willing to stake resources on Ren's warning.",
        "Ren preserved enough of the signal to guide a limited international response.",
        "Ren matched the signal to his portal record and opened a verified aid corridor."),
    StoryAnchor(
        "arc_guild_reckoning", 730, "The Guild Reckoning",
        "Tokyo must decide whether rank or lived evidence defines a hunter's worth.",
        ("Aiko Sato", "Daichi Mori"),
        "Aiko reads overlooked incident reports into the record as Daichi names the patrols those reports saved.",
        "A documented portal hazard turns Ren's field notes into evidence the hearing cannot dismiss.",
        "The Busan contact submits corroborating records that make the reckoning larger than one guild.",
        "The hearing reduced Ren's life to a rank the guild could dismiss.",
        "Ren's record protected low-rank patrols, even as the old hierarchy survived.",
        "Ren's allies forced the guild to recognize survival evidence beside rank."),
    StoryAnchor(
        "arc_zero_rank_choice", 913, "The Zero-Rank Choice",
        "Ren's accumulated loyalties and discoveries converge around one final threat.",
        ("Aiko Sato", "Daichi Mori", "Mei Kuroda", "Haruto Ishikawa"),
        "Aiko coordinates civilians, Daichi holds the perimeter, Mei reads the breach, and Haruto keeps the route supplied.",
        "The newest portal record determines where the circle can interrupt the converging breach.",
        "The overseas corridor returns the warning, giving Tokyo time bought by people Ren never met.",
        "Ren confronted the final threat without a network strong enough to share its cost.",
        "Ren's incomplete circle held long enough to keep the threat from consuming Tokyo.",
        "Every bond and discovery converged into a coordinated answer to the final threat."),
    StoryAnchor(
        "arc_awakened_horizon", 1095, "The Awakened Horizon",
        "The three-year chronicle reaches an ending shaped by the life Ren built.",
        ("Aiko Sato", "Daichi Mori", "Mei Kuroda", "Haruto Ishikawa"),
        "At the Arakawa riverbank, Ren's circle compares the city they inherited with the one their records now protect.",
        "Every documented portal remains part of the public warning network rather than disappearing into a private file.",
        "Tokyo and Busan keep the corridor open as the first link in a wider civilian warning network.",
        "Ren survived three years, carrying an unfinished warning into an uncertain future.",
        "Ren left Tokyo steadier than he found it, though some fractures remained.",
        "Ren reached the horizon with a trusted circle and a record that changed Tokyo.", True),
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
