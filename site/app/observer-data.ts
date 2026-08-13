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
export type Relationship = {
  name: string;
  role: string;
  trust: number;
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
export type ObserverSnapshot = {
  schema_version: number;
  seed: number;
  identity: Identity;
  clock: { day: number; slot: string };
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
    resources: Resources;
    progression: {
      combat_readiness: number;
      rank_points: number;
      fitness: number;
      knowledge: number;
    };
  };
  activity: { recent_events: ActivityEvent[] };
  story: {
    schema_version: number;
    completed_count: number;
    total_anchors: number;
    ending: StoryEnding | null;
    ending_reached: boolean;
    next: { title: string; day: number; days_remaining: number } | null;
  };
  relationships: Relationship[];
  portals: { discovered: string[] };
};
export type PresentationContract = {
  contract_sha256: string;
  contract_schema_version: number;
  observer_schema_version: number;
  read_only: boolean;
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
  { day: 183, title: "The Adachi Warning" },
  { day: 365, title: "The Tokyo Fracture" },
  { day: 548, title: "The Foreign Signal" },
  { day: 730, title: "The Guild Reckoning" },
  { day: 913, title: "The Zero-Rank Choice" },
  { day: 1095, title: "The Awakened Horizon" },
] as const;

function isRecord(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function isString(value: unknown): value is string {
  return typeof value === "string" && value.length > 0;
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
    isString(value.weather) &&
    value.season === "Summer" &&
    isInteger(value.gate_alert_level) &&
    value.gate_alert_level <= 3 &&
    Number.isSafeInteger(value.temperature_c) &&
    SUMMER_TEMPERATURES[value.weather] === value.temperature_c
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
    hasRenderedStrings(value, ["action", "outcome", "reason", "slot"]) &&
    isInteger(value.day, 1) &&
    TIME_SLOTS.includes(value.slot as (typeof TIME_SLOTS)[number])
  );
}

function isActivity(
  value: unknown,
  currentDay: number,
  currentSlot: string,
): value is ObserverSnapshot["activity"] {
  if (
    !isRecord(value) ||
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
  return (
    beforeCurrent &&
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
    hasRenderedStrings(value, ["name", "role"]) &&
    RELATIONSHIP_ROLES[value.name as string] === value.role &&
    Number.isSafeInteger(value.trust) &&
    (value.trust as number) >= -100 &&
    (value.trust as number) <= 100
  );
}

function isRelationships(value: unknown): value is Relationship[] {
  if (!Array.isArray(value) || !value.every(isRelationship)) {
    return false;
  }
  const names = value.map((relationship) => relationship.name);
  return names.every(
    (name, index) => index === 0 || names[index - 1] < name,
  );
}

function isPortals(value: unknown): value is ObserverSnapshot["portals"] {
  if (
    !isRecord(value) ||
    !Array.isArray(value.discovered) ||
    !value.discovered.every(
      (name) => isString(name) && PORTAL_NAMES.has(name),
    )
  ) {
    return false;
  }
  return new Set(value.discovered).size === value.discovered.length;
}
function isStoryNext(
  value: unknown,
): value is ObserverSnapshot["story"]["next"] {
  return (
    value === null ||
    (isRecord(value) &&
      isString(value.title) &&
      isInteger(value.day, 1) &&
      isInteger(value.days_remaining))
  );
}

function isStoryEnding(
  value: unknown,
): value is StoryEnding | null {
  return (
    value === null ||
    (isRecord(value) &&
      hasRenderedStrings(value, ["id", "summary", "tier", "title"]) &&
      isInteger(value.isolated_count) &&
      isInteger(value.prepared_count) &&
      isInteger(value.resilient_count))
  );
}

function isEndingConsistent(ending: StoryEnding, total: number): boolean {
  if (
    ending.isolated_count < 0 ||
    ending.isolated_count > total ||
    ending.prepared_count < 0 ||
    ending.prepared_count > total ||
    ending.resilient_count < 0 ||
    ending.resilient_count > total
  ) {
    return false;
  }
  const resolved =
    ending.isolated_count +
    ending.prepared_count +
    ending.resilient_count;
  if (ending.id === "legacy-unavailable") {
    return (
      resolved < total &&
      ["isolated", "resilient", "prepared", "legacy-unavailable"].includes(
        ending.tier,
      ) &&
      ending.title === "Legacy Ending Unavailable" &&
      ending.summary ===
        "This timeline predates authenticated story outcome evidence."
    );
  }
  if (resolved !== total) {
    return false;
  }
  if (ending.id === "unfinished-warning") {
    return (
      ending.tier === "isolated" &&
      ending.title === "The Unfinished Warning" &&
      ending.summary ===
        "Ren survived, but the warning he carried remained unresolved."
    );
  }
  if (ending.id === "zero-rank-horizon") {
    return (
      ending.tier === "prepared" &&
      ending.prepared_count >= 4 &&
      ending.title === "The Zero-Rank Horizon" &&
      ending.summary ===
        "Ren's evidence and trusted circle changed what Tokyo valued in a hunter."
    );
  }
  return (
    ending.id === "quiet-guardian" &&
    (ending.tier === "resilient" ||
      (ending.tier === "prepared" && ending.prepared_count < 4)) &&
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
    value.schema_version !== 3 ||
    !isInteger(value.completed_count) ||
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
      value.next.title === expected.title &&
      value.next.day === expected.day &&
      value.next.days_remaining === Math.max(0, value.next.day - currentDay)
    );
  }
  return (
    value.completed_count === value.total_anchors &&
    value.ending !== null &&
    isEndingConsistent(value.ending, value.total_anchors)
  );
}
export function isPresentationContract(
  value: unknown,
): value is PresentationContract {
  return (
    isRecord(value) &&
    typeof value.contract_sha256 === "string" &&
    /^[0-9a-f]{64}$/.test(value.contract_sha256) &&
    isInteger(value.contract_schema_version, 1) &&
    isInteger(value.observer_schema_version, 1) &&
    typeof value.read_only === "boolean" &&
    Array.isArray(value.control_capabilities)
  );
}

export function isObserverSnapshot(value: unknown): value is ObserverSnapshot {
  if (
    !isRecord(value) ||
    value.schema_version !== 4 ||
    !isInteger(value.seed) ||
    !isIdentity(value.identity) ||
    !isRecord(value.clock) ||
    !isInteger(value.clock.day, 1) ||
    !isString(value.clock.slot) ||
    !isEnvironment(value.environment) ||
    !isRecord(value.protagonist)
  ) {
    return false;
  }

  const protagonist = value.protagonist;
  if (
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
    !LOCATIONS.has(protagonist.location as string) ||
    !isRecord(protagonist.resources) ||
    !RESOURCE_NAMES.every((name) =>
      isIntegerInRange(protagonist.resources[name], 0, 100),
    ) ||
    !isInteger(protagonist.resources.money) ||
    !isRecord(protagonist.progression) ||
    !isIntegerInRange(protagonist.progression.combat_readiness, 0, 100) ||
    !["rank_points", "fitness", "knowledge"].every((name) =>
      isInteger(protagonist.progression[name]))
  ) {
    return false;
  }

  if (
    !isActivity(value.activity, value.clock.day, value.clock.slot) ||
        !isStory(value.story, value.clock.day) ||
    !isRelationships(value.relationships) ||
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
