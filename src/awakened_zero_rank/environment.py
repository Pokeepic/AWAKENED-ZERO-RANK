from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Weather:
    name: str
    temperature_c: int
    travel_fare_multiplier: float = 1.0
    energy_modifier: int = 0
    gate_difficulty: int = 0
    shop_closed: bool = False
    atmosphere: str = ""


SUMMER_WEATHER = (
    Weather("Clear", 29, atmosphere="Hard summer light reflects from the rails."),
    Weather("Cloudy", 27, atmosphere="Low clouds soften Tokyo's skyline."),
    Weather("Rain", 25, 1.10, 3, 3, atmosphere="Rain darkens the streets and train platforms."),
    Weather("Heatwave", 36, 1.0, 7, 5, atmosphere="Heat shimmers above the pavement."),
    Weather("Thunderstorm", 26, 1.20, 6, 9, True,
            "Thunder rolls over the wards as emergency alerts sound."),
)


def summer_weather(rng: "Random") -> Weather:
    """Choose repeatable Tokyo summer weather with rare severe conditions."""
    roll = rng.random()
    if roll < 0.34:
        return SUMMER_WEATHER[0]
    if roll < 0.57:
        return SUMMER_WEATHER[1]
    if roll < 0.82:
        return SUMMER_WEATHER[2]
    if roll < 0.95:
        return SUMMER_WEATHER[3]
    return SUMMER_WEATHER[4]


from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from random import Random
