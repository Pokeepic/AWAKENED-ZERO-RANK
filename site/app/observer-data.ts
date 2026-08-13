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

function isRecord(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function isString(value: unknown): value is string {
  return typeof value === "string" && value.length > 0;
}

function isInteger(value: unknown, minimum = 0): value is number {
  return Number.isInteger(value) && (value as number) >= minimum;
}

function isNumberInRange(
  value: unknown,
  minimum: number,
  maximum: number,
): value is number {
  return (
    typeof value === "number" &&
    Number.isFinite(value) &&
    value >= minimum &&
    value <= maximum
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
    isInteger(value.day, 1)
  );
}

function isRelationship(value: unknown): value is Relationship {
  return (
    isRecord(value) &&
    hasRenderedStrings(value, ["name", "role"]) &&
    isNumberInRange(value.trust, 0, 100)
  );
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
function isStory(
  value: unknown,
  currentDay: number,
): value is ObserverSnapshot["story"] {
  if (
    !isRecord(value) ||
    !isInteger(value.completed_count) ||
    !isInteger(value.total_anchors, 1) ||
    value.completed_count > value.total_anchors ||
    typeof value.ending_reached !== "boolean" ||
    !isStoryEnding(value.ending) ||
    !isStoryNext(value.next) ||
    (value.next === null) !== value.ending_reached ||
    (value.ending !== null) !== value.ending_reached
  ) {
    return false;
  }
  if (value.next !== null) {
    return (
      value.completed_count < value.total_anchors &&
      value.next.days_remaining === Math.max(0, value.next.day - currentDay)
    );
  }
  return (
    value.completed_count === value.total_anchors &&
    value.ending !== null &&
    value.ending.isolated_count +
      value.ending.prepared_count +
      value.ending.resilient_count ===
      value.total_anchors
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
    !isInteger(value.schema_version, 1) ||
    !isInteger(value.seed) ||
    !isIdentity(value.identity) ||
    !isRecord(value.clock) ||
    !isInteger(value.clock.day, 1) ||
    !isString(value.clock.slot) ||
    !isRecord(value.environment) ||
    !hasRenderedStrings(value.environment, ["weather", "season"]) ||
    !isInteger(value.environment.gate_alert_level) ||
    !isNumberInRange(value.environment.temperature_c, -100, 100) ||
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
    !isRecord(protagonist.resources) ||
    !RESOURCE_NAMES.every((name) =>
      isNumberInRange(protagonist.resources[name], 0, 100),
    ) ||
    !isInteger(protagonist.resources.money) ||
    !isRecord(protagonist.progression) ||
    !["combat_readiness", "rank_points", "fitness", "knowledge"].every((name) =>
      isInteger(protagonist.progression[name]),
    )
  ) {
    return false;
  }

  if (
    !isRecord(value.activity) ||
    !Array.isArray(value.activity.recent_events) ||
    value.activity.recent_events.length > 12 ||
    !value.activity.recent_events.every(isActivityEvent) ||
        !isStory(value.story, value.clock.day) ||
    !Array.isArray(value.relationships) ||
    !value.relationships.every(isRelationship) ||
    !isRecord(value.portals) ||
    !Array.isArray(value.portals.discovered) ||
    !value.portals.discovered.every(isString) ||
    new Set(value.portals.discovered).size !== value.portals.discovered.length
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