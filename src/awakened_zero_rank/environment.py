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

AUTUMN_WEATHER = (
    Weather("Clear", 22, atmosphere="Dry light sharpens the edges of the city."),
    Weather("Cloudy", 19, atmosphere="A cool grey ceiling settles over Tokyo."),
    Weather("Rain", 17, 1.10, 3, 3, atmosphere="Autumn rain gathers along the platforms."),
    Weather("Mist", 16, 1.05, 4, 5, atmosphere="River mist erases the far side of the ward."),
    Weather("Typhoon", 21, 1.25, 8, 10, True,
            "Typhoon warnings close shutters across the city."),
)

WINTER_WEATHER = (
    Weather("Clear", 9, atmosphere="Cold sunlight flashes from the rails."),
    Weather("Cloudy", 6, atmosphere="A pale winter sky presses over Tokyo."),
    Weather("Rain", 7, 1.10, 4, 4, atmosphere="Cold rain empties the side streets."),
    Weather("Snow", 2, 1.15, 6, 7, atmosphere="Snow softens the city and hides Gate residue."),
    Weather("Cold Snap", -3, 1.15, 8, 9, True,
            "Emergency heaters hum through a dangerous cold snap."),
)

SPRING_WEATHER = (
    Weather("Clear", 18, atmosphere="Clear spring light reaches between the towers."),
    Weather("Cloudy", 16, atmosphere="Soft clouds drift above the waking city."),
    Weather("Rain", 14, 1.10, 3, 3, atmosphere="Spring rain carries petals into the gutters."),
    Weather("Blossom Wind", 20, 1.0, 2, 4,
            atmosphere="A strong blossom wind moves through the wards."),
    Weather("Thunderstorm", 17, 1.20, 6, 9, True,
            atmosphere="Spring thunder rolls above the Gate sirens."),
)

SEASON_WEATHER = {
    "Summer": SUMMER_WEATHER,
    "Autumn": AUTUMN_WEATHER,
    "Winter": WINTER_WEATHER,
    "Spring": SPRING_WEATHER,
}


def season_for_day(day: int) -> str:
    """Return the fixed Tokyo season for a one-based repeating calendar day."""
    day_of_year = ((max(1, day) - 1) % 365) + 1
    if day_of_year <= 91:
        return "Summer"
    if day_of_year <= 182:
        return "Autumn"
    if day_of_year <= 273:
        return "Winter"
    return "Spring"


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


def seasonal_weather(day: int, rng: "Random") -> Weather:
    """Choose repeatable weather from the day's fixed seasonal profile."""
    season = season_for_day(day)
    if season == "Summer":
        return summer_weather(rng)
    profile = SEASON_WEATHER[season]
    roll = rng.random()
    if roll < 0.34:
        return profile[0]
    if roll < 0.57:
        return profile[1]
    if roll < 0.82:
        return profile[2]
    if roll < 0.95:
        return profile[3]
    return profile[4]


def weather_for(season: str, name: str) -> Weather:
    """Resolve one canonical weather record from its season and name."""
    return next(weather for weather in SEASON_WEATHER[season] if weather.name == name)


from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from random import Random
