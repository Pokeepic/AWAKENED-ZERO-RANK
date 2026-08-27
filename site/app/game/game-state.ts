import type { ObserverSnapshot } from "../observer-data";

export const RPG_SAVE_KEY = "awakened-zero-rank:rpg-save-v1";
export const RPG_SLOTS = ["Morning", "Afternoon", "Evening", "Late Night"] as const;

export type RpgState = {
  saveVersion: 1;
  day: number;
  slot: (typeof RPG_SLOTS)[number];
  health: number;
  energy: number;
  money: number;
  location: string;
  turns: number;
  lastAction: string;
};

export function newRpgState(snapshot: ObserverSnapshot): RpgState {
  return {
    saveVersion: 1,
    day: snapshot.clock.day,
    slot: RPG_SLOTS.includes(snapshot.clock.slot as RpgState["slot"]) ? snapshot.clock.slot as RpgState["slot"] : "Morning",
    health: snapshot.protagonist.resources.health,
    energy: snapshot.protagonist.resources.energy,
    money: snapshot.protagonist.resources.money,
    location: snapshot.protagonist.location,
    turns: 0,
    lastAction: "Campaign started",
  };
}

export function loadRpgState(snapshot: ObserverSnapshot): RpgState {
  try {
    const saved = window.localStorage.getItem(RPG_SAVE_KEY);
    if (saved) {
      const candidate = JSON.parse(saved) as Partial<RpgState>;
      const migrated = { ...candidate, saveVersion: 1 as const };
      if (isRpgState(migrated)) { saveRpgState(migrated); return migrated; }
    }
  } catch { /* start from the authenticated world seed */ }
  const initial = newRpgState(snapshot);
  saveRpgState(initial);
  return initial;
}

function isRpgState(value: Partial<RpgState>): value is RpgState {
  return value.saveVersion === 1
    && Number.isSafeInteger(value.day) && value.day! > 0
    && RPG_SLOTS.includes(value.slot as RpgState["slot"])
    && [value.health, value.energy].every((item) => Number.isSafeInteger(item) && item! >= 0 && item! <= 100)
    && Number.isSafeInteger(value.money) && value.money! >= 0
    && Number.isSafeInteger(value.turns) && value.turns! >= 0
    && typeof value.location === "string" && value.location.length > 0
    && typeof value.lastAction === "string" && value.lastAction.length > 0;
}

export function saveRpgState(state: RpgState) {
  window.localStorage.setItem(RPG_SAVE_KEY, JSON.stringify(state));
}

export function resetRpgState(snapshot: ObserverSnapshot): RpgState {
  window.localStorage.removeItem(RPG_SAVE_KEY);
  const initial = newRpgState(snapshot);
  saveRpgState(initial);
  return initial;
}

export function takeRpgAction(state: RpgState, action: string, effects: Partial<Pick<RpgState, "health" | "energy" | "money" | "location">>): RpgState {
  const index = RPG_SLOTS.indexOf(state.slot);
  const wraps = index === RPG_SLOTS.length - 1;
  const next = {
    ...state,
    ...effects,
    day: state.day + (wraps ? 1 : 0),
    slot: RPG_SLOTS[(index + 1) % RPG_SLOTS.length],
    turns: state.turns + 1,
    lastAction: action,
  };
  next.health = Math.max(0, Math.min(100, next.health));
  next.energy = Math.max(0, Math.min(100, next.energy));
  next.money = Math.max(0, next.money);
  saveRpgState(next);
  return next;
}
