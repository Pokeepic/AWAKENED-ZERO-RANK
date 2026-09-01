import type { RpgState, Timeline } from "./game-state";

export type GameSeason = "Summer" | "Autumn" | "Winter" | "Spring";
export type GameWeather = "Clear" | "Cloudy" | "Rain" | "Snow";

export function gameSeason(day: number): GameSeason {
  const dayOfYear = ((Math.max(1, day) - 1) % 365) + 1;
  if (dayOfYear <= 91) return "Summer";
  if (dayOfYear <= 182) return "Autumn";
  if (dayOfYear <= 273) return "Winter";
  return "Spring";
}

export function gameWeather(day: number, timeline: Timeline): GameWeather {
  const season = gameSeason(day);
  const roll = (day * 37 + timeline * 19) % 100;
  if (season === "Winter") {
    if (roll < 24) return "Snow";
    if (roll < 34) return "Rain";
    return roll < 68 ? "Cloudy" : "Clear";
  }
  if (roll < 22) return "Rain";
  return roll < 48 ? "Cloudy" : "Clear";
}

export function snowAccumulation(day: number, timeline: Timeline): number {
  if (gameSeason(day) !== "Winter") return 0;
  let depth = 0;
  for (let offset = 0; offset < 6 && day - offset > 0; offset += 1) {
    if (gameWeather(day - offset, timeline) === "Snow") depth += 1;
  }
  return Math.min(3, depth);
}

export function gameAtmosphere(state: RpgState) {
  const season = gameSeason(state.day);
  const weather = gameWeather(state.day, state.timeline);
  const snowDepth = snowAccumulation(state.day, state.timeline);
  return {
    season,
    weather,
    snowDepth,
    label: `${state.slot}, ${weather.toLowerCase()} ${season.toLowerCase()} weather${snowDepth > 0 ? `, snow accumulation level ${snowDepth}` : ""}`,
  };
}

export function apartmentAtmosphere(state: RpgState) {
  const atmosphere = gameAtmosphere(state);
  const night = state.slot === "Late Night";
  return {
    ...atmosphere,
    image: atmosphere.snowDepth > 0
      ? "/game/ren-apartment-winter-v1.png"
      : night
        ? "/game/ren-apartment-night-v1.png"
        : "/game/ren-apartment.png",
  };
}
