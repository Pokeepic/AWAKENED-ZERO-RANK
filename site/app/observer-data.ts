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
export type Conversation = {
  day: number;
  intention: string;
  npc_line: string;
  npc_name: string;
  reaction: string;
  ren_line: string;
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
export type Whereabout = { location: string; name: string };
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
  international_link: string | null;
  key: string;
  outcome: string;
  portal_consequence: string;
  premise: string;
  scene: string;
  tier: string;
  title: string;
};
export type ObserverSnapshot = {
  schema_version: number;
  seed: number;
  identity: Identity;
  clock: { day: number; slot: string };
  conversations: Conversation[];
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
  whereabouts: Whereabout[];
  portals: {
    active_plan: string | null;
    discovered: string[];
    investigations: PortalInvestigation[];
  };
  path?: string;
};
export type EquipmentCatalogItem = {
  bonus: number;
  kind: "weapon" | "armor";
  minimumRank: "F" | "E" | "D" | "C";
  name: string;
  price: number;
};
export type SeasonalCalendarEvent = {
  dayOfYear: number;
  season: "Summer" | "Autumn" | "Winter" | "Spring";
  title: string;
  place: string;
};
export type TokyoLocationProfile = {
  name: string;
  purpose: string;
  ward: string;
};
export const TOKYO_LOCATION_CATALOG: readonly TokyoLocationProfile[] = [
  { name: "Adachi Apartment", purpose: "Ren's home and recovery base", ward: "Adachi" },
  { name: "Adachi Gate Zone", purpose: "Regulated low-rank Gate perimeter", ward: "Adachi" },
  { name: "Akihabara Market", purpose: "Independent equipment and electronics market", ward: "Chiyoda" },
  { name: "Arakawa Riverbank", purpose: "Training ground and neighborhood gathering place", ward: "Adachi" },
  { name: "Asakusa Shrine District", purpose: "Weekly community and seasonal gathering place", ward: "Taito" },
  { name: "Home", purpose: "A recurring character's private residence", ward: "Private" },
  { name: "Kita-Senju", purpose: "Konbini work and everyday errands", ward: "Adachi" },
  { name: "Kita-Senju Hunter Supply", purpose: "Budget equipment and field supplies", ward: "Adachi" },
  { name: "Kita-Senju Station", purpose: "Rail interchange and evening meeting point", ward: "Adachi" },
  { name: "Shinjuku Guild Annex", purpose: "Portal research and specialist records", ward: "Shinjuku" },
  { name: "Tokyo Awakening Bureau", purpose: "Mandatory awakening assessment office", ward: "Central Tokyo" },
  { name: "Tokyo Hunter Guild", purpose: "Registration, patrols, and hunter work", ward: "Central Tokyo" },
  { name: "Ueno Library", purpose: "Study and Gate-safety research", ward: "Taito" },
] as const;
export type CurrentScene = {
  atmosphere: string;
  place: TokyoLocationProfile;
  presence: string;
  pressure: string;
};
export function currentScene(snapshot: ObserverSnapshot): CurrentScene {
  const place = TOKYO_LOCATION_CATALOG.find(({ name }) =>
    name === snapshot.protagonist.location
  )!;
  const nearby = snapshot.whereabouts
    .filter(({ location }) => location === place.name)
    .map(({ name }) => name);
  const pressure = [
    "No active Gate pressure",
    "Gate activity under watch",
    "Elevated Gate pressure",
    "Critical Gate pressure",
  ][snapshot.environment.gate_alert_level];
  return {
    atmosphere: `${snapshot.clock.slot} / ${snapshot.environment.weather}, ${snapshot.environment.temperature_c} C`,
    place,
    presence: nearby.length > 0
      ? `Nearby: ${nearby.join(" / ")}`
      : "No known recurring character is nearby.",
    pressure,
  };
}
export const SEASONAL_EVENT_CATALOG: readonly SeasonalCalendarEvent[] = [
  { dayOfYear: 7, season: "Summer", title: "Tanabata evening", place: "Arakawa Riverbank" },
  { dayOfYear: 137, season: "Autumn", title: "Tsukimi river watch", place: "Arakawa Riverbank" },
  { dayOfYear: 228, season: "Winter", title: "Year-end ward patrol", place: "Adachi Gate Zone" },
  { dayOfYear: 319, season: "Spring", title: "Hanami morning", place: "Arakawa Riverbank" },
];
export function nextSeasonalEvent(day: number) {
  const year = Math.floor((day - 1) / 365) + 1;
  const candidates = SEASONAL_EVENT_CATALOG.map((event) => ({
    event, day: (year - 1) * 365 + event.dayOfYear,
  }));
  const next = candidates.find((candidate) => candidate.day >= day) ?? {
    event: SEASONAL_EVENT_CATALOG[0], day: year * 365 + SEASONAL_EVENT_CATALOG[0].dayOfYear,
  };
  return { ...next.event, day: next.day, daysRemaining: next.day - day };
}
export type DailyBriefItem = {
  label: string;
  value: string;
  detail: string;
  tone: "urgent" | "watch" | "steady";
};
export function dailyBriefing(snapshot: ObserverSnapshot): readonly DailyBriefItem[] {
  const resources = snapshot.protagonist.resources;
  let pressure: DailyBriefItem;
  if (snapshot.economy.rent_arrears > 0) {
    pressure = { label: "Immediate pressure", value: "Rent arrears", detail: `¥${snapshot.economy.rent_arrears.toLocaleString()} remains overdue.`, tone: "urgent" };
  } else if (resources.health < 60) {
    pressure = { label: "Immediate pressure", value: "Recovery", detail: `Health is ${resources.health}/100.`, tone: "urgent" };
  } else if (resources.energy < 35) {
    pressure = { label: "Immediate pressure", value: "Low energy", detail: `Energy is ${resources.energy}/100.`, tone: "watch" };
  } else if (resources.hunger > 65) {
    pressure = { label: "Immediate pressure", value: "Hunger", detail: `Hunger is ${resources.hunger}/100.`, tone: "watch" };
  } else if (resources.stress > 60) {
    pressure = { label: "Immediate pressure", value: "High stress", detail: `Stress is ${resources.stress}/100.`, tone: "watch" };
  } else if (snapshot.environment.gate_alert_level >= 2) {
    pressure = { label: "Immediate pressure", value: "Gate alert", detail: `Tokyo alert level is ${snapshot.environment.gate_alert_level}.`, tone: "watch" };
  } else {
    pressure = { label: "Immediate pressure", value: "Routine stable", detail: snapshot.protagonist.current_goal, tone: "steady" };
  }
  const story = snapshot.story.next
    ? { label: "Story horizon", value: snapshot.story.next.title, detail: `${snapshot.story.next.days_remaining} days until day ${snapshot.story.next.day}.`, tone: "steady" as const }
    : { label: "Story horizon", value: snapshot.story.ending?.title ?? "Arc complete", detail: "The three-year chronicle has reached its ending.", tone: "steady" as const };
  const seasonal = nextSeasonalEvent(snapshot.clock.day);
  const seasonalItem = { label: "Seasonal horizon", value: seasonal.title, detail: `${seasonal.daysRemaining} days until day ${seasonal.day}.`, tone: "steady" as const };
  const investigation = snapshot.portals.active_plan
    ? snapshot.portals.investigations.find((item) => item.portal_name === snapshot.portals.active_plan)
    : [...snapshot.portals.investigations].sort((left, right) => right.progress - left.progress)[0];
  const portal = investigation
    ? { label: "Portal priority", value: investigation.portal_name, detail: `${investigation.progress}% investigated / risk ${investigation.risk}.`, tone: investigation.risk >= 60 ? "watch" as const : "steady" as const }
    : { label: "Portal priority", value: "No active investigation", detail: "No unresolved portal evidence is currently tracked.", tone: "steady" as const };
  return [pressure, story, seasonalItem, portal];
}
export const EQUIPMENT_CATALOG: readonly EquipmentCatalogItem[] = [
  { bonus: 7, kind: "weapon", minimumRank: "F", name: "Field Knife", price: 2400 },
  { bonus: 5, kind: "armor", minimumRank: "F", name: "Padded Jacket", price: 3200 },
  { bonus: 11, kind: "weapon", minimumRank: "E", name: "Reinforced Machete", price: 7200 },
  { bonus: 9, kind: "armor", minimumRank: "E", name: "Gateweave Vest", price: 8400 },
  { bonus: 16, kind: "weapon", minimumRank: "D", name: "Mana-edge Saber", price: 14800 },
  { bonus: 14, kind: "armor", minimumRank: "D", name: "Barrier Coat", price: 16600 },
  { bonus: 23, kind: "weapon", minimumRank: "C", name: "Riftglass Katana", price: 26000 },
  { bonus: 20, kind: "armor", minimumRank: "C", name: "Aegis Longcoat", price: 28500 },
] as const;

export const GATE_ENCOUNTER_CATALOG = [
  { difficulty: 42, minimumRank: "F", name: "Tunnel Slime Nest", reward: 5400 },
  { difficulty: 49, minimumRank: "F", name: "Goblin Scavenger Pack", reward: 6600 },
  { difficulty: 57, minimumRank: "F", name: "Armored Fang Boar", reward: 8200 },
  { difficulty: 64, minimumRank: "E", name: "Echo Wraith Corridor", reward: 10500 },
  { difficulty: 72, minimumRank: "D", name: "Rift Hound Matriarch", reward: 13800 },
  { difficulty: 82, minimumRank: "C", name: "Mirror Oni Vanguard", reward: 18000 },
] as const;

export const FIELD_SUPPLY_CATALOG = [
  { effect: "HEALTH +22", maximum: 2, minimumRank: "F", name: "Healing Gel", price: 900 },
  { effect: "ENERGY +18", maximum: 2, minimumRank: "F", name: "Energy Drink", price: 450 },
  { effect: "HEALTH +35", maximum: 1, minimumRank: "E", name: "Trauma Foam", price: 1800 },
  { effect: "ENERGY +30", maximum: 1, minimumRank: "E", name: "Focus Ampoule", price: 1200 },
] as const;

export const PORTAL_PROFILE_CATALOG = [
  { aftermath: "Ward crews seal the overflow route.", environment: "underground", hazard: "rising water", name: "Flooded Service Tunnel" },
  { aftermath: "The arcade closes before the cinder front.", environment: "urban ruin", hazard: "cinder wind", name: "Ashen Shopping Arcade" },
  { aftermath: "Trail anchors restore an evacuation route.", environment: "forest", hazard: "false trails", name: "Moonlit Cedar Path" },
  { aftermath: "Arrival intervals warn the platform patrol.", environment: "ice", hazard: "whiteout", name: "Frostbound Platform" },
  { aftermath: "Spore samples trigger a respirator advisory.", environment: "swamp", hazard: "toxic spores", name: "Sunken Courtyard" },
  { aftermath: "Room marks expose the mirror loop.", environment: "urban tower", hazard: "shifting rooms", name: "Glass Office Labyrinth" },
  { aftermath: "Pressure data coordinates a floodgate evacuation.", environment: "underground", hazard: "pressure surges", name: "Kawasaki Floodgate Labyrinth" },
  { aftermath: "Footprints reveal the living breach's migration.", environment: "forest", hazard: "razor vines", name: "Chiba Glasshouse Breach" },
] as const;

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
export const SEASON_TEMPERATURES: Record<string, Record<string, number>> = {
  Summer: { Clear: 29, Cloudy: 27, Rain: 25, Heatwave: 36, Thunderstorm: 26 },
  Autumn: { Clear: 22, Cloudy: 19, Rain: 17, Mist: 16, Typhoon: 21 },
  Winter: { Clear: 9, Cloudy: 6, Rain: 7, Snow: 2, "Cold Snap": -3 },
  Spring: { Clear: 18, Cloudy: 16, Rain: 14, "Blossom Wind": 20, Thunderstorm: 17 },
};

export function seasonForDay(day: number): string {
  const dayOfYear = ((Math.max(1, day) - 1) % 365) + 1;
  if (dayOfYear <= 91) return "Summer";
  if (dayOfYear <= 182) return "Autumn";
  if (dayOfYear <= 273) return "Winter";
  return "Spring";
}
const PORTAL_NAMES = new Set([
  "Flooded Service Tunnel",
  "Ashen Shopping Arcade",
  "Moonlit Cedar Path",
  "Frostbound Platform",
  "Sunken Courtyard",
  "Glass Office Labyrinth",
  "Kawasaki Floodgate Labyrinth",
  "Chiba Glasshouse Breach",
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
const NPC_SCHEDULES: Record<string, Record<string, string>> = {
  "Aiko Sato": { Morning: "Tokyo Hunter Guild", Afternoon: "Tokyo Hunter Guild", Evening: "Kita-Senju Station", "Late Night": "Home" },
  "Daichi Mori": { Morning: "Adachi Gate Zone", Afternoon: "Tokyo Hunter Guild", Evening: "Arakawa Riverbank", "Late Night": "Home" },
  "Haruto Ishikawa": { Morning: "Akihabara Market", Afternoon: "Akihabara Market", Evening: "Kita-Senju Station", "Late Night": "Home" },
  "Mei Kuroda": { Morning: "Ueno Library", Afternoon: "Adachi Gate Zone", Evening: "Ueno Library", "Late Night": "Shinjuku Guild Annex" },
};
function scheduledLocation(name: string, slot: string, day: number): string | undefined {
  if (day % 7 === 0 && ["Aiko Sato", "Haruto Ishikawa"].includes(name)) {
    return "Asakusa Shrine District";
  }
  return NPC_SCHEDULES[name]?.[slot];
}
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
export const STORY_ANCHORS = [
  { day: 183, key: "arc_adachi_warning", title: "The Adachi Warning", focus_npcs: ["Aiko Sato", "Daichi Mori"], outcomes: { isolated: "The warning reached Adachi before Ren had anyone ready to believe him.", resilient: "Ren helped hold one evacuation route while the district absorbed the shock.", prepared: "Ren's evidence let the guild clear Adachi before the synchronized breach." } },
  { day: 365, key: "arc_tokyo_fracture", title: "The Tokyo Fracture", focus_npcs: ["Daichi Mori", "Mei Kuroda"], outcomes: { isolated: "The fracture left Ren outside both camps as patrol routes collapsed.", resilient: "Ren carried evidence between rivals, preserving an uneasy working truce.", prepared: "Ren's trusted coalition exposed the false order before Tokyo divided." } },
  { day: 548, key: "arc_foreign_signal", title: "The Foreign Signal", focus_npcs: ["Mei Kuroda", "Haruto Ishikawa"], outcomes: { isolated: "The signal faded overseas with no one willing to stake resources on Ren's warning.", resilient: "Ren preserved enough of the signal to guide a limited international response.", prepared: "Ren matched the signal to his portal record and opened a verified aid corridor." } },
  { day: 730, key: "arc_guild_reckoning", title: "The Guild Reckoning", focus_npcs: ["Aiko Sato", "Daichi Mori"], outcomes: { isolated: "The hearing reduced Ren's life to a rank the guild could dismiss.", resilient: "Ren's record protected low-rank patrols, even as the old hierarchy survived.", prepared: "Ren's allies forced the guild to recognize survival evidence beside rank." } },
  { day: 913, key: "arc_zero_rank_choice", title: "The Zero-Rank Choice", focus_npcs: ["Aiko Sato", "Daichi Mori", "Mei Kuroda", "Haruto Ishikawa"], outcomes: { isolated: "Ren confronted the final threat without a network strong enough to share its cost.", resilient: "Ren's incomplete circle held long enough to keep the threat from consuming Tokyo.", prepared: "Every bond and discovery converged into a coordinated answer to the final threat." } },
  { day: 1095, key: "arc_awakened_horizon", title: "The Awakened Horizon", focus_npcs: ["Aiko Sato", "Daichi Mori", "Mei Kuroda", "Haruto Ishikawa"], outcomes: { isolated: "Ren survived three years, carrying an unfinished warning into an uncertain future.", resilient: "Ren left Tokyo steadier than he found it, though some fractures remained.", prepared: "Ren reached the horizon with a trusted circle and a record that changed Tokyo." } },
] as const;
export type StoryTimelineEntry = {
  day: number;
  daysRemaining: number;
  status: "completed" | "next" | "locked";
  title: string;
};
export function storyTimeline(snapshot: ObserverSnapshot): StoryTimelineEntry[] {
  return STORY_ANCHORS.map((anchor, index) => {
    const status = index < snapshot.story.completed_count
      ? "completed" as const
      : index === snapshot.story.completed_count && !snapshot.story.ending_reached
        ? "next" as const
        : "locked" as const;
    const title = status === "completed"
      ? snapshot.story.completed[index].title
      : status === "next"
        ? snapshot.story.next!.title
        : "Unrevealed chapter";
    return {
      day: anchor.day,
      daysRemaining: Math.max(0, anchor.day - snapshot.clock.day),
      status,
      title,
    };
  });
}
const STORY_DETAILS = [
  { premise: "A synchronized Gate pulse forces Tokyo to reassess its weakest districts.", scene: "Aiko maps apartment residents while Daichi marks the patrol routes the guild abandoned.", portal_consequence: "The newest portal record reveals which evacuation route will destabilize first.", international_link: null },
  { premise: "Conflicting guild orders divide the people responsible for civilian safety.", scene: "Daichi brings the disputed orders to Mei, who finds a portal signature hidden in their timestamps.", portal_consequence: "The recorded portal pattern distinguishes the forged order from the real patrol signal.", international_link: "The forgery uses routing conventions later traced beyond Japan." },
  { premise: "A repeating portal signature links Japan to a disaster unfolding overseas.", scene: "Mei decodes the signal at Haruto's shuttered shop while he inventories supplies for an unknown city.", portal_consequence: "The latest portal record gives the foreign responders a matching hazard and a safe approach.", international_link: "Responders in Busan confirm the same signature and establish the chronicle's first overseas contact." },
  { premise: "Tokyo must decide whether rank or lived evidence defines a hunter's worth.", scene: "Aiko reads overlooked incident reports into the record as Daichi names the patrols those reports saved.", portal_consequence: "A documented portal hazard turns Ren's field notes into evidence the hearing cannot dismiss.", international_link: "The Busan contact submits corroborating records that make the reckoning larger than one guild." },
  { premise: "Ren's accumulated loyalties and discoveries converge around one final threat.", scene: "Aiko coordinates civilians, Daichi holds the perimeter, Mei reads the breach, and Haruto keeps the route supplied.", portal_consequence: "The newest portal record determines where the circle can interrupt the converging breach.", international_link: "The overseas corridor returns the warning, giving Tokyo time bought by people Ren never met." },
  { premise: "The three-year chronicle reaches an ending shaped by the life Ren built.", scene: "At the Arakawa riverbank, Ren's circle compares the city they inherited with the one their records now protect.", portal_consequence: "Every documented portal remains part of the public warning network rather than disappearing into a private file.", international_link: "Tokyo and Busan keep the corridor open as the first link in a wider civilian warning network." },
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
  day: number,
  slot: string,
): value is ObserverSnapshot["environment"] {
  if (!isRecord(value) || !isString(value.season) || !isString(value.weather)) return false;
  const expectedSeasons = new Set([seasonForDay(day)]);
  if (slot === "Morning" && day > 1) expectedSeasons.add(seasonForDay(day - 1));
  return (
    hasExactKeys(value, ["gate_alert_level", "season", "temperature_c", "weather"]) &&
    expectedSeasons.has(value.season) &&
    isInteger(value.gate_alert_level) &&
    value.gate_alert_level <= 3 &&
    !(day === 4 && slot === "Afternoon" && value.gate_alert_level !== 2) &&
    Number.isSafeInteger(value.temperature_c) &&
    SEASON_TEMPERATURES[value.season]?.[value.weather] === value.temperature_c
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
    !(
      (day < 4 || (day === 4 && ["Morning", "Afternoon"].includes(slot))) &&
      value.shop_visits !== 0
    ) &&
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
    !(
      value.weapon === null ||
      ["Field Knife", "Reinforced Machete", "Mana-edge Saber", "Riftglass Katana"].includes(value.weapon as string)
    ) ||
    !(
      value.armor === null ||
      ["Padded Jacket", "Gateweave Vest", "Barrier Coat", "Aegis Longcoat"].includes(value.armor as string)
    ) ||
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
  const currentPosition = currentDay * TIME_SLOTS.length + currentSlotIndex;
  const awakeningPosition = 3 * TIME_SLOTS.length +
    TIME_SLOTS.indexOf("Evening");
  const registrationPosition = 4 * TIME_SLOTS.length +
    TIME_SLOTS.indexOf("Afternoon");
  const latest = value.recent_events.at(-1);
  const fixedEventValid = currentPosition === awakeningPosition
    ? latest?.action === "Awakening assessment" && latest.day === 3 &&
      latest.slot === "Afternoon" &&
      latest.reason ===
        "a city gate alert triggered Ren's mandatory screening (world event)" &&
      latest.outcome === "Awakened at Rank F with Threat Sense."
    : currentPosition === registrationPosition
      ? latest?.action === "Guild registration" && latest.day === 4 &&
        latest.slot === "Morning" &&
        latest.reason ===
          "newly awakened citizens must register before accepting hunter work (world event)" &&
        /^Aiko Sato issued an F-rank license; travel and filing cost ¥(?:0|[1-9]\d{0,2}(?:,\d{3})*)\.$/.test(
          latest.outcome,
        )
      : true;
  const awakeningMemoryCount = memories.filter((memory) =>
    memory.day === 3 && memory.importance === 10 &&
    memory.summary ===
      "Awakening assessment: Awakened at Rank F with Threat Sense."
  ).length;
  const registrationMemoryCount = memories.filter((memory) =>
    memory.day === 4 && memory.importance === 8 &&
    /^Guild registration: Aiko Sato issued an F-rank license; travel and filing cost ¥(?:0|[1-9]\d{0,2}(?:,\d{3})*)\.$/.test(
      memory.summary,
    )
  ).length;
  const fixedMemoryValid =
    awakeningMemoryCount === Number(currentPosition >= awakeningPosition) &&
    registrationMemoryCount === Number(currentPosition >= registrationPosition);
  return (
    beforeCurrent &&
    memoriesCanonical &&
    fixedEventValid &&
    fixedMemoryValid &&
    positions.every(
      (position, index) =>
        index === 0 ||
        positions[index - 1][0] < position[0] ||
        (positions[index - 1][0] === position[0] &&
          positions[index - 1][1] < position[1]),
    )
  );
}

function isConversations(
  value: unknown,
  currentDay: number,
): value is Conversation[] {
  if (!Array.isArray(value) || value.length > 6) return false;
  const introductionDays: Record<string, number> = {
    "Aiko Sato": 4,
    "Daichi Mori": 5,
    "Mei Kuroda": 6,
    "Haruto Ishikawa": 9,
  };
  return value.every((conversation, index) =>
    isRecord(conversation) &&
    hasExactKeys(conversation, [
      "day", "intention", "npc_line", "npc_name", "reaction", "ren_line",
    ]) &&
    hasRenderedStrings(conversation, [
      "intention", "npc_line", "npc_name", "reaction", "ren_line",
    ]) &&
    ["intention", "npc_line", "npc_name", "reaction", "ren_line"].every(
      (key) => (conversation[key] as string).trim().length > 0,
    ) &&
    conversation.npc_name in RELATIONSHIP_ROLES &&
    isIntegerInRange(
      conversation.day,
      introductionDays[conversation.npc_name as string],
      currentDay,
    ) &&
    (index === 0 ||
      (value[index - 1] as Conversation).day <= conversation.day)
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
  const canonical = names.every(
    (name, index) => index === 0 || names[index - 1] < name,
  ) && names.includes("Aiko Sato") === registered && introductions.every(
    ([name, introduced]) => names.includes(name) === (position >= introduced),
  );
  if (!canonical) {
    return false;
  }
  const initialEvidence = [
    ["Aiko Sato", 4 * TIME_SLOTS.length + 1, 3, 5, 4],
    ["Daichi Mori", 5 * TIME_SLOTS.length + 1, 4, 3, 2],
    ["Mei Kuroda", 6 * TIME_SLOTS.length + 2, 1, 2, 2],
    ["Haruto Ishikawa", 9 * TIME_SLOTS.length + 3, 3, 3, 2],
  ] as const;
  return initialEvidence.every(([name, introduced, trust, familiarity, loyalty]) => {
    if (position !== introduced) {
      return true;
    }
    const relationship = value.find((item) => item.name === name)!;
    return relationship.trust === trust &&
      relationship.familiarity === familiarity &&
      relationship.loyalty === loyalty &&
      relationship.affection === 0 && relationship.tension === 0;
  });
}

function isWhereabouts(
  value: unknown,
  relationships: Relationship[],
  day: number,
  slot: string,
): value is Whereabout[] {
  if (!Array.isArray(value) || value.length !== relationships.length) return false;
  return value.every((item, index) =>
    isRecord(item) &&
    hasExactKeys(item, ["location", "name"]) &&
    item.name === relationships[index].name &&
    item.location === scheduledLocation(item.name as string, slot, day)
  );
}

function isPortals(
  value: unknown,
  day: number,
  slot: string,
): value is ObserverSnapshot["portals"] {
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
  const beforeHunterWorkUnlock =
    day < 4 || (day === 4 && ["Morning", "Afternoon"].includes(slot));
  return (
    new Set(value.discovered).size === value.discovered.length &&
    investigationNames.every(
      (name, index) => index === 0 || investigationNames[index - 1] < name,
    ) &&
    investigationNames.every((name) => value.discovered.includes(name)) &&
    (value.active_plan === null || investigationNames.includes(value.active_plan)) &&
    !(beforeHunterWorkUnlock &&
      (value.discovered.length > 0 || investigations.length > 0 ||
       value.active_plan !== null))
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
  const details = STORY_DETAILS[index];
  if (anchor === undefined || details === undefined || !isRecord(value)) {
    return false;
  }
  const tier = isString(value.tier) ? value.tier : "";
  const expectedOutcome = tier === "legacy-unavailable"
    ? LEGACY_STORY_OUTCOME
    : (anchor.outcomes as Record<string, string>)[tier];
  return (
    hasExactKeys(value, ["day", "focus_npcs", "international_link", "key", "outcome", "portal_consequence", "premise", "scene", "tier", "title"]) &&
    value.day === anchor.day &&
    value.day <= currentDay &&
    value.key === anchor.key &&
    value.title === anchor.title &&
    value.outcome === expectedOutcome &&
    value.premise === details.premise &&
    value.scene === details.scene &&
    value.portal_consequence === details.portal_consequence &&
    value.international_link === details.international_link &&
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
  if (finalTier === "prepared") {
    return (
      ending.id === "open-corridor" &&
      ending.title === "The Open Corridor" &&
      ending.summary ===
        "Ren ended the chronicle by keeping Tokyo connected to allies beyond Japan."
    );
  }
  if (isolatedCount >= 3) {
    return (
      ending.id === "scarred-watch" &&
      ending.title === "The Scarred Watch" &&
      ending.summary ===
        "Tokyo endured, and Ren's remaining circle kept watch over its unresolved wounds."
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
    value.schema_version !== 4 ||
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
    value.comparison_schema_version === 9 &&
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
    "activity", "clock", "conversations", "economy", "environment", "identity",
    "portals", "protagonist", "relationships", "schema_version", "seed", "story", "whereabouts",
  ];
  const hasValidEnvelope =
    hasExactKeys(value, snapshotKeys) ||
    (hasExactKeys(value, [...snapshotKeys, "path"].sort()) &&
      typeof value.path === "string");
  if (
    !hasValidEnvelope ||
    value.schema_version !== 6 ||
    !Number.isSafeInteger(value.seed) ||
    !isIdentity(value.identity) ||
    !isRecord(value.clock) ||
    !hasExactKeys(value.clock, ["day", "slot"]) ||
    !isInteger(value.clock.day, 1) ||
    !isString(value.clock.slot) ||
    !isEnvironment(
      value.environment,
      value.clock.day as number,
      value.clock.slot as string,
    ) ||
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
    (value.clock.day === 3 && value.clock.slot === "Evening" &&
      protagonist.location !== "Tokyo Awakening Bureau") ||
    (value.clock.day === 4 && value.clock.slot === "Afternoon" &&
      protagonist.location !== "Tokyo Hunter Guild") ||
    protagonist.current_goal !== expectedCurrentGoal(
      value.clock.day as number,
      value.clock.slot as string,
      protagonist.hunter_rank as string,
      (value.economy as ObserverSnapshot["economy"]).rent_arrears,
    ) ||
    !LOCATIONS.has(protagonist.location as string) ||
    !isEquipment(protagonist.equipment) ||
    (
      !["E", "D", "C"].includes(protagonist.hunter_rank as string) &&
      (
        protagonist.equipment.weapon === "Reinforced Machete" ||
        protagonist.equipment.armor === "Gateweave Vest"
      )
    ) ||
    (
      !["D", "C"].includes(protagonist.hunter_rank as string) &&
      (
        protagonist.equipment.weapon === "Mana-edge Saber" ||
        protagonist.equipment.armor === "Barrier Coat"
      )
    ) ||
    (
      protagonist.hunter_rank !== "C" &&
      (
        protagonist.equipment.weapon === "Riftglass Katana" ||
        protagonist.equipment.armor === "Aegis Longcoat"
      )
    ) ||
    (
      (value.clock.day < 4 ||
        (value.clock.day === 4 && ["Morning", "Afternoon"].includes(value.clock.slot))) &&
      (
        protagonist.equipment.weapon !== null ||
        protagonist.equipment.armor !== null ||
        Object.keys(protagonist.equipment.inventory).length > 0
      )
    ) ||
    ((((value.clock.day === 3 && value.clock.slot === "Evening") ||
      (value.clock.day === 4 && value.clock.slot === "Afternoon"))) &&
      ((protagonist.equipment as ObserverSnapshot["protagonist"]["equipment"]).weapon !== null ||
       (protagonist.equipment as ObserverSnapshot["protagonist"]["equipment"]).armor !== null ||
       Object.keys((protagonist.equipment as ObserverSnapshot["protagonist"]["equipment"]).inventory).length !== 0)) ||
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
    ((value.clock.day < 4 ||
      (value.clock.day === 4 && ["Morning", "Afternoon"].includes(value.clock.slot))) &&
      ["rank_points", "missions_attempted", "missions_completed"].some(
        (name) => protagonist.progression[name] !== 0,
      )) ||
    (value.clock.day === 3 && value.clock.slot === "Evening" &&
      protagonist.progression.ability_mastery !== 1) ||
    ((value.clock.day < 3 ||
      (value.clock.day === 3 && ["Morning", "Afternoon"].includes(value.clock.slot))) &&
      protagonist.progression.ability_mastery !== 0) ||
    ((value.clock.day > 3 ||
      (value.clock.day === 3 && value.clock.slot === "Late Night")) &&
      protagonist.progression.ability_mastery === 0) ||
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
    !isConversations(value.conversations, value.clock.day) ||
        !isStory(value.story, value.clock.day) ||
    !isRelationships(
      value.relationships,
      value.clock.day as number,
      value.clock.slot as string,
    ) ||
    !isWhereabouts(
      value.whereabouts,
      value.relationships as Relationship[],
      value.clock.day as number,
      value.clock.slot as string,
    ) ||
    !isPortals(
      value.portals,
      value.clock.day as number,
      value.clock.slot as string,
    )
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
