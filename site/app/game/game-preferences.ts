export const RPG_SESSION_KEY = "awakened-zero-rank:rpg-session-v1";
export const RPG_PREFERENCES_KEY = "awakened-zero-rank:rpg-preferences-v1";

export type GamePreferences = {
  motion: "full" | "reduced";
  textSize: "normal" | "large";
};

export const DEFAULT_GAME_PREFERENCES: GamePreferences = { motion: "full", textSize: "normal" };

export function loadGamePreferences(): GamePreferences {
  try {
    const candidate = JSON.parse(window.localStorage.getItem(RPG_PREFERENCES_KEY) ?? "null") as Partial<GamePreferences> | null;
    return {
      motion: candidate?.motion === "reduced" ? "reduced" : "full",
      textSize: candidate?.textSize === "large" ? "large" : "normal",
    };
  } catch {
    return DEFAULT_GAME_PREFERENCES;
  }
}

export function applyGamePreferences(preferences: GamePreferences) {
  document.documentElement.dataset.gameMotion = preferences.motion;
  document.documentElement.dataset.gameText = preferences.textSize;
}

export function saveGamePreferences(preferences: GamePreferences) {
  window.localStorage.setItem(RPG_PREFERENCES_KEY, JSON.stringify(preferences));
  applyGamePreferences(preferences);
}
