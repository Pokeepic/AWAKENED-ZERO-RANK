export type Identity = { algorithm: "sha256"; digest: string };
export type ResourceName =
  | "health"
  | "energy"
  | "hunger"
  | "stress"
  | "morale";
export type Resources = Record<ResourceName, number> & { money: number };
export type ActivityEvent = {
  action: string;
  day: number;
  outcome: string;
  reason: string;
  slot: string;
};
export type KeyMemory = {
  day: number;
  importance: number;
  summary: string;
};
export type Relationship = {
  affection: number;
  familiarity: number;
  loyalty: number;
  name: string;
  role: string;
  tension: number;
  trust: number;
};
export type PortalInvestigation = {
  cooperating_npc: string | null;
  joint_missions: number;
  portal_name: string;
  preparation_bonus: number;
  preparation_strategy: string;
  progress: number;
  risk: number;
};
export type StoryEnding = {
  id: string;
  isolated_count: number;
  prepared_count: number;
  resilient_count: number;
  summary: string;
  tier: string;
  title: string;
};
export type CompletedStory = {
  day: number;
  focus_npcs: string[];
  key: string;
  outcome: string;
  tier: string;
  title: string;
};
export type ObserverSnapshot = {
  schema_version: number;
  seed: number;
  identity: Identity;
  clock: { day: number; slot: string };
  economy: {
    meal_cost: number;
    rent_arrears: number;
    rent_cost: number;
    rent_due_day: number;
    rent_payments: number;
    shop_visits: number;
    wage_modifier: number;
  };
  environment: {
    weather: string;
    temperature_c: number;
    season: string;
    gate_alert_level: number;
  };
  protagonist: {
    name: string;
    hunter_rank: string;
    ability: string;
    location: string;
    mood: string;
    current_goal: string;
    equipment: {
      armor: string | null;
      inventory: Record<string, number>;
      weapon: string | null;
    };
    resources: Resources;
    progression: {
      ability_mastery: number;
      combat_readiness: number;
      rank_points: number;
      fitness: number;
      knowledge: number;
      missions_attempted: number;
      missions_completed: number;
    };
  };
  activity: { key_memories: KeyMemory[]; recent_events: ActivityEvent[] };
  story: {
    completed: CompletedStory[];
    schema_version: number;
    completed_count: number;
    total_anchors: number;
    ending: StoryEnding | null;
    ending_reached: boolean;
    next: { key: string; title: string; day: number; days_remaining: number } | null;
  };
  relationships: Relationship[];
  portals: {
    active_plan: string | null;
    discovered: string[];
    investigations: PortalInvestigation[];
  };
  path?: string;
};
export type PresentationContract = {
  animation_cues: string[];
  comparison_schema_version: number;
  contract_sha256: string;
  contract_schema_version: number;
  observer_schema_version: number;
  read_only: boolean;
  recent_activity_relations: string[];
  update_modes: string[];
  control_capabilities: unknown[];
};

export const RESOURCE_NAMES: ResourceName[] = [
  "health",
  "energy",
  "hunger",
  "stress",
  "morale",
];
const TIME_SLOTS = ["Morning", "Afternoon", "Evening", "Late Night"] as const;
const SUMMER_TEMPERATURES: Record<string, number> = {
  Clear: 29,
  Cloudy: 27,
  Rain: 25,
  Heatwave: 36,
  Thunderstorm: 26,
};
const PORTAL_NAMES = new Set([
  "Flooded Service Tunnel",
  "Ashen Shopping Arcade",
  "Moonlit Cedar Path",
  "Frostbound Platform",
  "Sunken Courtyard",
  "Glass Office Labyrinth",
]);
const HUNTER_RANKS = new Set(["Unranked", "F", "E", "D", "C"]);
const ABILITIES = new Set([
  "None",
  "Threat Sense",
  "Threat Sense / Echo Fragment",
]);
const MOODS = new Set([
  "Uneasy",
  "Anxious",
  "Steady",
  "Hopeful",
  "Exhausted",
  "Overwhelmed",
]);
function isRankAbilityConsistent(rank: string, ability: string): boolean {
  return rank === "Unranked" ? ability === "None" : ability !== "None";
}
function isAwakeningChronologyConsistent(
  day: number,
  slot: string,
  rank: string,
): boolean {
  const awakened = day > 3 ||
    (day === 3 && TIME_SLOTS.indexOf(slot as (typeof TIME_SLOTS)[number]) >= 2);
  return (rank !== "Unranked") === awakened;
}
function expectedCurrentGoal(
  day: number,
  slot: string,
  rank: string,
  rentArrears: number,
): string {
  const slotIndex = TIME_SLOTS.indexOf(slot as (typeof TIME_SLOTS)[number]);
  if (day < 3 || (day === 3 && slotIndex < 2)) {
    return "Earn enough yen to pay rent";
  }
  if (day < 4 || (day === 4 && slotIndex < 1)) {
    return "Register with the Tokyo Hunter Guild";
  }
  if (rentArrears > 0) return `Clear ¥${rentArrears.toLocaleString("en-US")} in rent arrears`;
  if (rank === "F") return "Survive gate work and reach Rank E";
  return `Build a stable life as a Rank ${rank} hunter`;
}
function isRankPointsConsistent(rank: string, points: number): boolean {
  if (rank === "Unranked" || rank === "F") return points < 30;
  if (rank === "E") return points >= 30 && points < 60;
  if (rank === "D") return points >= 60 && points < 90;
  return rank === "C" && points >= 90;
}
function isMissionPointsConsistent(completed: number, points: number): boolean {
  if (completed === 0) return points === 0;
  const remainder = points - completed * 10;
  if (remainder < 0 || remainder > completed * 7) return false;
  const minimumSevens = Math.max(
    0,
    Math.ceil((remainder - completed * 3) / 4),
  );
  const maximumSevens = Math.min(completed, Math.floor(remainder / 7));
  const firstSevens = minimumSevens + ((remainder - minimumSevens) % 3);
  return firstSevens <= maximumSevens;
}
const RELATIONSHIP_ROLES: Record<string, string> = {
  "Aiko Sato": "F-rank guild clerk",
  "Daichi Mori": "Rank E patrol leader",
  "Haruto Ishikawa": "hunter supply owner",
  "Mei Kuroda": "independent portal researcher",
};
const LOCATIONS = new Set([
  "Adachi Apartment",
  "Kita-Senju",
  "Ueno Library",
  "Arakawa Riverbank",
  "Tokyo Awakening Bureau",
  "Tokyo Hunter Guild",
  "Adachi Gate Zone",
  "Kita-Senju Hunter Supply",
]);
const STORY_ANCHORS = [
  { day: 183, key: "arc_adachi_warning", title: "The Adachi Warning", focus_npcs: ["Aiko Sato", "Daichi Mori"], outcomes: { isolated: "The warning reached Adachi before Ren had anyone ready to believe him.", resilient: "Ren helped hold one evacuation route while the district absorbed the shock.", prepared: "Ren's evidence let the guild clear Adachi before the synchronized breach." } },
  { day: 365, key: "arc_tokyo_fracture", title: "The Tokyo Fracture", focus_npcs: ["Daichi Mori", "Mei Kuroda"], outcomes: { isolated: "The fracture left Ren outside both camps as patrol routes collapsed.", resilient: "Ren carried evidence between rivals, preserving an uneasy working truce.", prepared: "Ren's trusted coalition exposed the false order before Tokyo divided." } },
  { day: 548, key: "arc_foreign_signal", title: "The Foreign Signal", focus_npcs: ["Mei Kuroda", "Haruto Ishikawa"], outcomes: { isolated: "The signal faded overseas with no one willing to stake resources on Ren's warning.", resilient: "Ren preserved enough of the signal to guide a limited international response.", prepared: "Ren matched the signal to his portal record and opened a verified aid corridor." } },
  { day: 730, key: "arc_guild_reckoning", title: "The Guild Reckoning", focus_npcs: ["Aiko Sato", "Daichi Mori"], outcomes: { isolated: "The hearing reduced Ren's life to a rank the guild could dismiss.", resilient: "Ren's record protected low-rank patrols, even as the old hierarchy survived.", prepared: "Ren's allies forced the guild to recognize survival evidence beside rank." } },
  { day: 913, key: "arc_zero_rank_choice", title: "The Zero-Rank Choice", focus_npcs: ["Aiko Sato", "Daichi Mori", "Mei Kuroda", "Haruto Ishikawa"], outcomes: { isolated: "Ren confronted the final threat without a network strong enough to share its cost.", resilient: "Ren's incomplete circle held long enough to keep the threat from consuming Tokyo.", prepared: "Every bond and discovery converged into a coordinated answer to the final threat." } },
  { day: 1095, key: "arc_awakened_horizon", title: "The Awakened Horizon", focus_npcs: ["Aiko Sato", "Daichi Mori", "Mei Kuroda", "Haruto Ishikawa"], outcomes: { isolated: "Ren survived three years, carrying an unfinished warning into an uncertain future.", resilient: "Ren left Tokyo steadier than he found it, though some fractures remained.", prepared: "Ren reached the horizon with a trusted circle and a record that changed Tokyo." } },
] as const;
const LEGACY_STORY_OUTCOME = "Outcome tier unavailable in this legacy timeline.";
const ANIMATION_CUES = [
  "awakening", "consequence", "festival", "finance", "food", "mission",
  "other", "patrol", "portal_preparation", "registration", "rest",
  "shopping", "social", "story", "study", "train", "treatment", "work",
];
const RECENT_ACTIVITY_RELATIONS = ["append", "replace", "unchanged"];
const UPDATE_MODES = ["animate", "refresh", "replace", "unchanged"];

function isRecord(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function isString(value: unknown): value is string {
  return typeof value === "string" && value.length > 0;
}

function hasExactKeys(value: Record<string, unknown>, keys: string[]): boolean {
  const actual = Object.keys(value).sort();
  return actual.length === keys.length && keys.every((key, index) => key === actual[index]);
}

function hasExactStrings(value: unknown, expected: string[]): value is string[] {
  return Array.isArray(value) &&
    value.length === expected.length &&
    value.every((item, index) => item === expected[index]);
}

function isInteger(value: unknown, minimum = 0): value is number {
  return Number.isSafeInteger(value) && (value as number) >= minimum;
}

function isIntegerInRange(
  value: unknown,
  minimum: number,
  maximum: number,
): value is number {
  return (
    Number.isSafeInteger(value) &&
    (value as number) >= minimum &&
    (value as number) <= maximum
  );
}

function isIdentity(value: unknown): value is Identity {
  return (
    isRecord(value) &&
    hasExactKeys(value, ["algorithm", "digest"]) &&
    value.algorithm === "sha256" &&
    typeof value.digest === "string" &&
    /^[0-9a-f]{64}$/.test(value.digest)
  );
}

function isEnvironment(
  value: unknown,
): value is ObserverSnapshot["environment"] {
  return (
    isRecord(value) &&
    hasExactKeys(value, ["gate_alert_level", "season", "temperature_c", "weather"]) &&
    isString(value.weather) &&
    value.season === "Summer" &&
    isInteger(value.gate_alert_level) &&
    value.gate_alert_level <= 3 &&
    Number.isSafeInteger(value.temperature_c) &&
    SUMMER_TEMPERATURES[value.weather] === value.temperature_c
  );
}

function isEconomy(
  value: unknown,
  day: number,
  slot: string,
): value is ObserverSnapshot["economy"] {
  if (
    !isRecord(value) ||
    !hasExactKeys(value, [
      "meal_cost", "rent_arrears", "rent_cost", "rent_due_day",
      "rent_payments", "shop_visits", "wage_modifier",
    ]) ||
    !["rent_arrears", "rent_cost", "rent_payments", "shop_visits"].every(
      (name) => isInteger(value[name]),
    ) ||
    !isInteger(value.rent_due_day, 1) ||
    !Number.isSafeInteger(value.meal_cost) ||
    !Number.isSafeInteger(value.wage_modifier)
  ) {
    return false;
  }
  return (
    [500, 600, 700, 800].includes(value.meal_cost as number) &&
    [85, 95, 100, 105, 115].includes(value.wage_modifier as number) &&
    value.rent_due_day === 8 &&
    value.rent_cost === 8000 &&
    (value.rent_arrears as number) <= 8000 &&
    (value.rent_payments as number) <= 1 &&
    !(value.rent_payments === 1 && (value.rent_arrears as number) > 0) &&
    !(
      (day < 8 || (day === 8 && slot === "Morning")) &&
      (value.rent_payments !== 0 || value.rent_arrears !== 0)
    )
  );
}

function isEquipment(
  value: unknown,
): value is ObserverSnapshot["protagonist"]["equipment"] {
  if (
    !isRecord(value) ||
    !hasExactKeys(value, ["armor", "inventory", "weapon"]) ||
    !(value.weapon === null || value.weapon === "Field Knife") ||
    !(value.armor === null || value.armor === "Padded Jacket") ||
    !isRecord(value.inventory)
  ) {
    return false;
  }
  const names = Object.keys(value.inventory);
  return (
    names.every((name) => name.length > 0) &&
    names.every((name, index) => index === 0 || names[index - 1] < name) &&
    names.every((name) => isInteger(value.inventory[name], 1))
  );
}

function hasRenderedStrings(
  value: Record<string, unknown>,
  keys: string[],
): boolean {
  return keys.every((key) => isString(value[key]));
}

function isActivityEvent(value: unknown): value is ActivityEvent {
  return (
    isRecord(value) &&
    hasExactKeys(value, ["action", "day", "outcome", "reason", "slot"]) &&
    hasRenderedStrings(value, ["action", "outcome", "reason", "slot"]) &&
    isInteger(value.day, 1) &&
    TIME_SLOTS.includes(value.slot as (typeof TIME_SLOTS)[number])
  );
}

function isKeyMemory(value: unknown, currentDay: number): value is KeyMemory {
  return (
    isRecord(value) &&
    hasExactKeys(value, ["day", "importance", "summary"]) &&
    isIntegerInRange(value.day, 1, currentDay) &&
    isIntegerInRange(value.importance, 1, 10) &&
    isString(value.summary)
  );
}

function isActivity(
  value: unknown,
  currentDay: number,
  currentSlot: string,
): value is ObserverSnapshot["activity"] {
  if (
    !isRecord(value) ||
    !hasExactKeys(value, ["key_memories", "recent_events"]) ||
    !Array.isArray(value.key_memories) ||
    value.key_memories.length > 5 ||
    !value.key_memories.every((memory) => isKeyMemory(memory, currentDay)) ||
    !Array.isArray(value.recent_events) ||
    value.recent_events.length > 12 ||
    !value.recent_events.every(isActivityEvent)
  ) {
    return false;
  }
  const currentSlotIndex = TIME_SLOTS.indexOf(
    currentSlot as (typeof TIME_SLOTS)[number],
  );
  if (currentSlotIndex < 0) {
    return false;
  }
  const positions = value.recent_events.map((event) => [
    event.day,
    TIME_SLOTS.indexOf(event.slot as (typeof TIME_SLOTS)[number]),
  ]);
  const beforeCurrent = positions.every(
    ([day, slot]) =>
      day < currentDay || (day === currentDay && slot < currentSlotIndex),
  );
  const memories = value.key_memories;
  const memoriesCanonical = memories.every(
    (memory, index) =>
      index === 0 ||
      memories[index - 1].importance > memory.importance ||
      (memories[index - 1].importance === memory.importance &&
        memories[index - 1].day >= memory.day),
  );
  return (
    beforeCurrent &&
    memoriesCanonical &&
    positions.every(
      (position, index) =>
        index === 0 ||
        positions[index - 1][0] < position[0] ||
        (positions[index - 1][0] === position[0] &&
          positions[index - 1][1] < position[1]),
    )
  );
}
function isRelationship(value: unknown): value is Relationship {
  return (
    isRecord(value) &&
    hasExactKeys(value, ["affection", "familiarity", "loyalty", "name", "role", "tension", "trust"]) &&
    hasRenderedStrings(value, ["name", "role"]) &&
    RELATIONSHIP_ROLES[value.name as string] === value.role &&
    ["affection", "trust"].every((name) =>
      isIntegerInRange(value[name], -100, 100)) &&
    ["familiarity", "loyalty", "tension"].every((name) =>
      isIntegerInRange(value[name], 0, 100))
  );
}

function isRelationships(
  value: unknown,
  day: number,
  slot: string,
): value is Relationship[] {
  if (!Array.isArray(value) || !value.every(isRelationship)) {
    return false;
  }
  const names = value.map((relationship) => relationship.name);
  const registered = day > 4 ||
    (day === 4 && TIME_SLOTS.indexOf(slot as (typeof TIME_SLOTS)[number]) >= 1);
  const position = day * TIME_SLOTS.length +
    TIME_SLOTS.indexOf(slot as (typeof TIME_SLOTS)[number]);
  const introductions = [
    ["Daichi Mori", 5 * TIME_SLOTS.length + 1],
    ["Mei Kuroda", 6 * TIME_SLOTS.length + 2],
    ["Haruto Ishikawa", 9 * TIME_SLOTS.length + 3],
  ] as const;
  return names.every(
    (name, index) => index === 0 || names[index - 1] < name,
  ) && names.includes("Aiko Sato") === registered && introductions.every(
    ([name, introduced]) => names.includes(name) === (position >= introduced),
  );
}

function isPortals(value: unknown): value is ObserverSnapshot["portals"] {
  if (
    !isRecord(value) ||
    !hasExactKeys(value, ["active_plan", "discovered", "investigations"]) ||
    !(value.active_plan === null || isString(value.active_plan)) ||
    !Array.isArray(value.investigations) ||
    !Array.isArray(value.discovered) ||
    !value.discovered.every(
      (name) => isString(name) && PORTAL_NAMES.has(name),
    )
  ) {
    return false;
  }
  const investigations = value.investigations;
  if (!investigations.every((investigation) =>
    isRecord(investigation) &&
    hasExactKeys(investigation, [
      "cooperating_npc", "joint_missions", "portal_name",
      "preparation_bonus", "preparation_strategy", "progress", "risk",
    ]) &&
    isString(investigation.portal_name) &&
    PORTAL_NAMES.has(investigation.portal_name) &&
    isString(investigation.preparation_strategy) &&
    investigation.preparation_strategy.length > 0 &&
    (investigation.cooperating_npc === null ||
      (isString(investigation.cooperating_npc) &&
        investigation.cooperating_npc in RELATIONSHIP_ROLES)) &&
    isIntegerInRange(investigation.progress, 0, 100) &&
    isIntegerInRange(investigation.risk, 0, 100) &&
    isInteger(investigation.preparation_bonus, 0) &&
    isInteger(investigation.joint_missions, 0)
  )) {
    return false;
  }
  const investigationNames = investigations.map(
    (investigation) => investigation.portal_name as string,
  );
  return (
    new Set(value.discovered).size === value.discovered.length &&
    investigationNames.every(
      (name, index) => index === 0 || investigationNames[index - 1] < name,
    ) &&
    investigationNames.every((name) => value.discovered.includes(name)) &&
    (value.active_plan === null || investigationNames.includes(value.active_plan))
  );
}
function isStoryNext(
  value: unknown,
): value is ObserverSnapshot["story"]["next"] {
  return (
    value === null ||
    (isRecord(value) &&
      hasExactKeys(value, ["day", "days_remaining", "key", "title"]) &&
      isString(value.key) &&
      isString(value.title) &&
      isInteger(value.day, 1) &&
      isInteger(value.days_remaining))
  );
}

function isCompletedStory(
  value: unknown,
  index: number,
  currentDay: number,
): value is CompletedStory {
  const anchor = STORY_ANCHORS[index];
  if (anchor === undefined || !isRecord(value)) {
    return false;
  }
  const tier = isString(value.tier) ? value.tier : "";
  const expectedOutcome = tier === "legacy-unavailable"
    ? LEGACY_STORY_OUTCOME
    : (anchor.outcomes as Record<string, string>)[tier];
  return (
    hasExactKeys(value, ["day", "focus_npcs", "key", "outcome", "tier", "title"]) &&
    value.day === anchor.day &&
    value.day <= currentDay &&
    value.key === anchor.key &&
    value.title === anchor.title &&
    value.outcome === expectedOutcome &&
    ["isolated", "resilient", "prepared", "legacy-unavailable"].includes(
      value.tier as string,
    ) &&
    Array.isArray(value.focus_npcs) &&
    value.focus_npcs.length === anchor.focus_npcs.length &&
    value.focus_npcs.every((name, focusIndex) =>
      name === anchor.focus_npcs[focusIndex])
  );
}

function isStoryEnding(
  value: unknown,
): value is StoryEnding | null {
  return (
    value === null ||
    (isRecord(value) &&
      hasExactKeys(value, ["id", "isolated_count", "prepared_count", "resilient_count", "summary", "tier", "title"]) &&
      hasRenderedStrings(value, ["id", "summary", "tier", "title"]) &&
      isInteger(value.isolated_count) &&
      isInteger(value.prepared_count) &&
      isInteger(value.resilient_count))
  );
}

function isEndingConsistent(
  ending: StoryEnding,
  completed: CompletedStory[],
): boolean {
  const tiers = completed.map((entry) => entry.tier);
  const isolatedCount = tiers.filter((tier) => tier === "isolated").length;
  const preparedCount = tiers.filter((tier) => tier === "prepared").length;
  const resilientCount = tiers.filter((tier) => tier === "resilient").length;
  const finalTier = tiers.at(-1);
  if (
    ending.isolated_count !== isolatedCount ||
    ending.prepared_count !== preparedCount ||
    ending.resilient_count !== resilientCount ||
    ending.tier !== finalTier
  ) {
    return false;
  }
  if (tiers.includes("legacy-unavailable")) {
    return (
      ending.id === "legacy-unavailable" &&
      ending.title === "Legacy Ending Unavailable" &&
      ending.summary ===
        "This timeline predates authenticated story outcome evidence."
    );
  }
  if (finalTier === "isolated") {
    return (
      ending.id === "unfinished-warning" &&
      ending.title === "The Unfinished Warning" &&
      ending.summary ===
        "Ren survived, but the warning he carried remained unresolved."
    );
  }
  if (finalTier === "prepared" && preparedCount >= 4) {
    return (
      ending.id === "zero-rank-horizon" &&
      ending.title === "The Zero-Rank Horizon" &&
      ending.summary ===
        "Ren's evidence and trusted circle changed what Tokyo valued in a hunter."
    );
  }
  return (
    ending.id === "quiet-guardian" &&
    ending.title === "Tokyo's Quiet Guardian" &&
    ending.summary ===
      "Ren left Tokyo steadier through persistence rather than recognition."
  );
}
function isStory(
  value: unknown,
  currentDay: number,
): value is ObserverSnapshot["story"] {
  if (
    !isRecord(value) ||
    !hasExactKeys(value, [
      "completed", "completed_count", "ending", "ending_reached", "next",
      "schema_version", "total_anchors",
    ]) ||
    !Array.isArray(value.completed) ||
    value.schema_version !== 3 ||
    !isInteger(value.completed_count) ||
    value.completed_count !== value.completed.length ||
    !value.completed.every((entry, index) =>
      isCompletedStory(entry, index, currentDay)) ||
    value.total_anchors !== STORY_ANCHORS.length ||
    value.completed_count > value.total_anchors ||
    typeof value.ending_reached !== "boolean" ||
    !isStoryEnding(value.ending) ||
    !isStoryNext(value.next) ||
    (value.next === null) !== value.ending_reached ||
    (value.ending !== null) !== value.ending_reached
  ) {
    return false;
  }
  const lastCompleted = STORY_ANCHORS[value.completed_count - 1];
  if (lastCompleted !== undefined && lastCompleted.day > currentDay) {
    return false;
  }
  if (value.next !== null) {
    const expected = STORY_ANCHORS[value.completed_count];
    return (
      value.completed_count < value.total_anchors &&
      expected !== undefined &&
      value.next.key === expected.key &&
      value.next.title === expected.title &&
      value.next.day === expected.day &&
      value.next.days_remaining === Math.max(0, value.next.day - currentDay)
    );
  }
  return (
    value.completed_count === value.total_anchors &&
    value.ending !== null &&
    isEndingConsistent(value.ending, value.completed)
  );
}
export function isPresentationContract(
  value: unknown,
): value is PresentationContract {
  return (
    isRecord(value) &&
    hasExactKeys(value, [
      "animation_cues", "comparison_schema_version", "contract_schema_version",
      "contract_sha256", "control_capabilities", "observer_schema_version",
      "read_only", "recent_activity_relations", "update_modes",
    ]) &&
    hasExactStrings(value.animation_cues, ANIMATION_CUES) &&
    value.comparison_schema_version === 8 &&
    typeof value.contract_sha256 === "string" &&
    /^[0-9a-f]{64}$/.test(value.contract_sha256) &&
    isInteger(value.contract_schema_version, 1) &&
    isInteger(value.observer_schema_version, 1) &&
    typeof value.read_only === "boolean" &&
    Array.isArray(value.control_capabilities) &&
    hasExactStrings(value.recent_activity_relations, RECENT_ACTIVITY_RELATIONS) &&
    hasExactStrings(value.update_modes, UPDATE_MODES)
  );
}

export function isObserverSnapshot(value: unknown): value is ObserverSnapshot {
  if (!isRecord(value)) {
    return false;
  }
  const snapshotKeys = [
    "activity", "clock", "economy", "environment", "identity", "portals",
    "protagonist", "relationships", "schema_version", "seed", "story",
  ];
  const hasValidEnvelope =
    hasExactKeys(value, snapshotKeys) ||
    (hasExactKeys(value, [...snapshotKeys, "path"].sort()) &&
      typeof value.path === "string");
  if (
    !hasValidEnvelope ||
    value.schema_version !== 4 ||
    !Number.isSafeInteger(value.seed) ||
    !isIdentity(value.identity) ||
    !isRecord(value.clock) ||
    !hasExactKeys(value.clock, ["day", "slot"]) ||
    !isInteger(value.clock.day, 1) ||
    !isString(value.clock.slot) ||
    !isEnvironment(value.environment) ||
    !isEconomy(value.economy, value.clock.day as number, value.clock.slot as string) ||
    !isRecord(value.protagonist)
  ) {
    return false;
  }

  const protagonist = value.protagonist;
  if (
    !hasExactKeys(protagonist, [
      "ability", "current_goal", "equipment", "hunter_rank", "location",
      "mood", "name", "progression", "resources",
    ]) ||
    !hasRenderedStrings(protagonist, [
      "name",
      "hunter_rank",
      "ability",
      "location",
      "mood",
      "current_goal",
    ]) ||
    protagonist.name !== "Ren Takahashi" ||
    !ABILITIES.has(protagonist.ability as string) ||
    !MOODS.has(protagonist.mood as string) ||
    !HUNTER_RANKS.has(protagonist.hunter_rank as string) ||
    !isRankAbilityConsistent(
      protagonist.hunter_rank as string,
      protagonist.ability as string,
    ) ||
    !isAwakeningChronologyConsistent(
      value.clock.day as number,
      value.clock.slot as string,
      protagonist.hunter_rank as string,
    ) ||
    protagonist.current_goal !== expectedCurrentGoal(
      value.clock.day as number,
      value.clock.slot as string,
      protagonist.hunter_rank as string,
      (value.economy as ObserverSnapshot["economy"]).rent_arrears,
    ) ||
    !LOCATIONS.has(protagonist.location as string) ||
    !isEquipment(protagonist.equipment) ||
    !isRecord(protagonist.resources) ||
    !hasExactKeys(protagonist.resources, [
      "energy", "health", "hunger", "money", "morale", "stress",
    ]) ||
    !RESOURCE_NAMES.every((name) =>
      isIntegerInRange(protagonist.resources[name], 0, 100),
    ) ||
    !isInteger(protagonist.resources.money) ||
    !isRecord(protagonist.progression) ||
    !hasExactKeys(protagonist.progression, [
      "ability_mastery", "combat_readiness", "fitness", "knowledge",
      "missions_attempted", "missions_completed", "rank_points",
    ]) ||
    !["ability_mastery", "combat_readiness"].every((name) =>
      isIntegerInRange(protagonist.progression[name], 0, 100)) ||
    ![
      "rank_points", "fitness", "knowledge", "missions_attempted",
      "missions_completed",
    ].every((name) => isInteger(protagonist.progression[name])) ||
    !isRankPointsConsistent(
      protagonist.hunter_rank as string,
      protagonist.progression.rank_points as number,
    ) ||
    !isMissionPointsConsistent(
      protagonist.progression.missions_completed as number,
      protagonist.progression.rank_points as number,
    ) ||
    (protagonist.progression.missions_completed as number) >
      (protagonist.progression.missions_attempted as number)
  ) {
    return false;
  }

  if (
    !isActivity(value.activity, value.clock.day, value.clock.slot) ||
        !isStory(value.story, value.clock.day) ||
    !isRelationships(
      value.relationships,
      value.clock.day as number,
      value.clock.slot as string,
    ) ||
    !isPortals(value.portals)
  ) {
    return false;
  }

  return true;
}

export function canonical(value: unknown): string {
  if (Array.isArray(value)) {
    return `[${value.map(canonical).join(",")}]`;
  }
  if (isRecord(value)) {
    return `{${Object.keys(value)
      .sort()
      .map((key) => `${JSON.stringify(key)}:${canonical(value[key])}`)
      .join(",")}}`;
  }
  return JSON.stringify(value) ?? "null";
}

async function sha256(value: unknown): Promise<string> {
  const bytes = new TextEncoder().encode(canonical(value));
  const digest = await crypto.subtle.digest("SHA-256", bytes);
  return Array.from(new Uint8Array(digest))
    .map((item) => item.toString(16).padStart(2, "0"))
    .join("");
}

export async function verifyArtifacts(
  contractValue: unknown,
  snapshotValue: unknown,
): Promise<{
  contract: PresentationContract;
  snapshot: ObserverSnapshot;
}> {
  if (
    !isPresentationContract(contractValue) ||
    !isObserverSnapshot(snapshotValue)
  ) {
    throw new Error("malformed observer artifacts");
  }

  const contract = contractValue;
  const snapshot = snapshotValue;
  const { contract_sha256: claimedContract, ...contractPayload } = contract;
  const snapshotPayload: Record<string, unknown> = { ...snapshot };
  delete snapshotPayload.identity;
  delete snapshotPayload.path;

  const contractDigest = await sha256(contractPayload);
  if (
    contractDigest !== claimedContract ||
    contract.contract_schema_version !== 2 ||
    contract.observer_schema_version !== snapshot.schema_version ||
    contract.read_only !== true ||
    contract.control_capabilities.length !== 0
  ) {
    throw new Error("unsupported observer contract");
  }

  const snapshotDigest = await sha256(snapshotPayload);
  if (snapshotDigest !== snapshot.identity.digest) {
    throw new Error("invalid observer snapshot");
  }

  return { contract, snapshot };
}
