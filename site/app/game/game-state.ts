import type { ObserverSnapshot } from "../observer-data";

export const RPG_SAVE_KEY = "awakened-zero-rank:rpg-save-v1";
export const RPG_SLOTS = ["Morning", "Afternoon", "Evening", "Late Night"] as const;
export const CAMPAIGN_ARCS = [
  { id: "worthless-awakening", title: "Worthless Awakening", starts: 1, deadline: 45 },
  { id: "adachi-countdown", title: "The Adachi Countdown", starts: 46, deadline: 120 },
  { id: "false-orders", title: "Tokyo's False Orders", starts: 121, deadline: 240 },
  { id: "black-gate", title: "The Black Gate", starts: 241, deadline: 365 },
] as const;
export type Timeline = 1 | 2 | 3;
export type CampaignStatus = "active" | "game-over" | "year-ending";
export type RpgJournalEntry = { day: number; slot: (typeof RPG_SLOTS)[number]; action: string; location: string };

export type RpgState = {
  saveVersion: 5;
  timeline: Timeline;
  attempt: number;
  status: CampaignStatus;
  skills: string[];
  legacyClues: string[];
  lotteryTickets: number;
  transmigrationEligible: boolean;
  day: number;
  slot: (typeof RPG_SLOTS)[number];
  health: number;
  energy: number;
  money: number;
  location: string;
  turns: number;
  lastAction: string;
  journal: RpgJournalEntry[];
  bonds: Record<string, number>;
  completedEvents: string[];
};

export function newRpgState(snapshot: ObserverSnapshot): RpgState {
  return {
    saveVersion: 5,
    timeline: 1,
    attempt: 1,
    status: "active",
    skills: ["Residual Read"],
    legacyClues: [],
    lotteryTickets: 0,
    transmigrationEligible: false,
    day: 1,
    slot: "Morning",
    health: snapshot.protagonist.resources.health,
    energy: snapshot.protagonist.resources.energy,
    money: snapshot.protagonist.resources.money,
    location: snapshot.protagonist.location,
    turns: 0,
    lastAction: "Campaign started",
    journal: [],
    bonds: {},
    completedEvents: [],
  };
}

export function loadRpgState(snapshot: ObserverSnapshot): RpgState {
  try {
    const saved = window.localStorage.getItem(RPG_SAVE_KEY);
    if (saved) {
      const candidate = JSON.parse(saved) as Partial<RpgState>;
      const migrated = {
        ...candidate,
        saveVersion: 5 as const,
        timeline: candidate.timeline ?? 1,
        attempt: candidate.attempt ?? 1,
        status: candidate.status ?? (candidate.health === 0 ? "game-over" : "active"),
        skills: Array.isArray(candidate.skills) ? candidate.skills : ["Residual Read"],
        legacyClues: Array.isArray(candidate.legacyClues) ? candidate.legacyClues : [],
        lotteryTickets: candidate.lotteryTickets ?? 0,
        transmigrationEligible: candidate.transmigrationEligible ?? false,
        journal: Array.isArray(candidate.journal) ? candidate.journal : [],
        bonds: candidate.bonds && typeof candidate.bonds === "object" && !Array.isArray(candidate.bonds) ? candidate.bonds : {},
        completedEvents: Array.isArray(candidate.completedEvents) ? candidate.completedEvents : [],
      };
      if (isRpgState(migrated)) { saveRpgState(migrated); return migrated; }
    }
  } catch { /* start from the authenticated world seed */ }
  const initial = newRpgState(snapshot);
  saveRpgState(initial);
  return initial;
}

function isRpgState(value: Partial<RpgState>): value is RpgState {
  return value.saveVersion === 5
    && [1, 2, 3].includes(value.timeline as number)
    && Number.isSafeInteger(value.attempt) && value.attempt! > 0
    && ["active", "game-over", "year-ending"].includes(value.status as string)
    && Array.isArray(value.skills) && value.skills.length >= 1 && value.skills.length <= 2
    && value.skills.every((skill) => typeof skill === "string" && skill.length > 0)
    && Array.isArray(value.legacyClues) && value.legacyClues.length <= 12
    && value.legacyClues.every((clue) => typeof clue === "string" && clue.length > 0)
    && Number.isSafeInteger(value.lotteryTickets) && value.lotteryTickets! >= 0
    && typeof value.transmigrationEligible === "boolean"
    && Number.isSafeInteger(value.day) && value.day! > 0
    && RPG_SLOTS.includes(value.slot as RpgState["slot"])
    && [value.health, value.energy].every((item) => Number.isSafeInteger(item) && item! >= 0 && item! <= 100)
    && Number.isSafeInteger(value.money) && value.money! >= 0
    && Number.isSafeInteger(value.turns) && value.turns! >= 0
    && typeof value.location === "string" && value.location.length > 0
    && typeof value.lastAction === "string" && value.lastAction.length > 0
    && Array.isArray(value.journal) && value.journal.length <= 12
    && value.journal.every((entry) => Number.isSafeInteger(entry.day) && entry.day > 0
      && RPG_SLOTS.includes(entry.slot) && typeof entry.action === "string" && entry.action.length > 0
      && typeof entry.location === "string" && entry.location.length > 0)
    && value.bonds !== null && typeof value.bonds === "object" && !Array.isArray(value.bonds)
    && Object.entries(value.bonds).every(([name, level]) => name.length > 0 && Number.isSafeInteger(level) && level >= 0 && level <= 10)
    && Array.isArray(value.completedEvents) && value.completedEvents.length <= 24
    && new Set(value.completedEvents).size === value.completedEvents.length
    && value.completedEvents.every((event) => typeof event === "string" && event.length > 0);
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

export function pendingStoryRoute(state: RpgState): string | null {
  if (state.status !== "active") return null;
  const survivedFirstGate = state.journal.some((entry) => [
    "Cleared the fracture sentinel",
    "Retreated from the fracture sentinel",
    "Withdrew from the fracture sentinel",
  ].includes(entry.action));
  if (survivedFirstGate && !state.completedEvents.includes("after-the-gate-aiko")) return "/game/evening";
  if (state.completedEvents.includes("after-the-gate-aiko")
    && !state.completedEvents.includes("guild-debrief-daichi")
    && state.location === "Tokyo Hunter Guild") return "/game/debrief";
  return null;
}

export function remainingDaySlots(state: RpgState): number {
  return RPG_SLOTS.length - RPG_SLOTS.indexOf(state.slot);
}

export function currentCampaignArc(day: number) {
  return CAMPAIGN_ARCS.find((arc) => day >= arc.starts && day <= arc.deadline) ?? CAMPAIGN_ARCS.at(-1)!;
}

export function takeRpgAction(state: RpgState, action: string, effects: Partial<Pick<RpgState, "health" | "energy" | "money" | "location" | "bonds" | "completedEvents">>, timeSlots = 1): RpgState {
  if (state.status !== "active") return state;
  const slots = Math.max(1, Math.min(RPG_SLOTS.length, Math.trunc(timeSlots)));
  const index = RPG_SLOTS.indexOf(state.slot);
  const elapsed = index + slots;
  const next = {
    ...state,
    ...effects,
    day: Math.min(365, state.day + Math.floor(elapsed / RPG_SLOTS.length)),
    slot: RPG_SLOTS[elapsed % RPG_SLOTS.length],
    turns: state.turns + 1,
    lastAction: action,
    journal: [...state.journal, { day: state.day, slot: state.slot, action, location: effects.location ?? state.location }].slice(-12),
  };
  next.health = Math.max(0, Math.min(100, next.health));
  next.energy = Math.max(0, Math.min(100, next.energy));
  next.money = Math.max(0, next.money);
  if (next.health === 0) next.status = "game-over";
  else if (state.day === 365 && elapsed >= RPG_SLOTS.length) next.status = "year-ending";
  saveRpgState(next);
  return next;
}
