import type { ObserverSnapshot } from "../observer-data";

export const RPG_SAVE_KEY = "awakened-zero-rank:rpg-save-v1";
export const RPG_SLOTS = ["Morning", "Afternoon", "Evening", "Late Night"] as const;

export type RpgState = {
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
    if (saved) return JSON.parse(saved) as RpgState;
  } catch { /* start from the authenticated world seed */ }
  const initial = newRpgState(snapshot);
  saveRpgState(initial);
  return initial;
}

export function saveRpgState(state: RpgState) {
  window.localStorage.setItem(RPG_SAVE_KEY, JSON.stringify(state));
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
