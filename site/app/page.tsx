/* eslint-disable react/no-unescaped-entities */
"use client";

import { useEffect, useState } from "react";

type Identity = { algorithm: "sha256"; digest: string };
type ResourceName = "health" | "energy" | "hunger" | "stress" | "morale";
type Resources = Record<ResourceName, number> & { money: number };
type ActivityEvent = {
  action: string;
  day: number;
  outcome: string;
  reason: string;
  slot: string;
};
type Relationship = {
  name: string;
  role: string;
  trust: number;
};
type ObserverSnapshot = {
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
    next: { title: string; day: number; days_remaining: number } | null;
  };
  relationships: Relationship[];
  portals: { discovered: string[] };
};
type PresentationContract = {
  contract_sha256: string;
  contract_schema_version: number;
  observer_schema_version: number;
  read_only: boolean;
  control_capabilities: unknown[];
};

const REFRESH_INTERVAL_MS = 60_000;
const RESOURCE_NAMES: ResourceName[] = [
  "health",
  "energy",
  "hunger",
  "stress",
  "morale",
];

function canonical(value: unknown): string {
  if (Array.isArray(value)) {
    return `[${value.map(canonical).join(",")}]`;
  }
  if (value !== null && typeof value === "object") {
    const record = value as Record<string, unknown>;
    return `{${Object.keys(record)
      .sort()
      .map((key) => `${JSON.stringify(key)}:${canonical(record[key])}`)
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

async function verifyArtifacts(
  contract: PresentationContract,
  snapshot: ObserverSnapshot,
): Promise<void> {
  const { contract_sha256: claimedContract, ...contractPayload } = contract;
  const snapshotPayload: Record<string, unknown> = { ...snapshot };
  const identity = snapshot.identity;
  delete snapshotPayload.identity;
  delete snapshotPayload.path;

  const contractDigest = await sha256(contractPayload);
  if (
    contractDigest !== claimedContract ||
    contract.contract_schema_version !== 2 ||
    contract.observer_schema_version !== snapshot.schema_version ||
    contract.read_only !== true ||
    !Array.isArray(contract.control_capabilities) ||
    contract.control_capabilities.length !== 0
  ) {
    throw new Error("unsupported observer contract");
  }

  const snapshotDigest = await sha256(snapshotPayload);
  if (
    identity.algorithm !== "sha256" ||
    !/^[0-9a-f]{64}$/.test(identity.digest) ||
    snapshotDigest !== identity.digest
  ) {
    throw new Error("invalid observer snapshot");
  }
}
export default function Home() {
  const [snapshot, setSnapshot] = useState<ObserverSnapshot | null>(null);
  const [contract, setContract] = useState<PresentationContract | null>(null);
  const [failed, setFailed] = useState(false);
  const [stale, setStale] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    let trusted = false;
    let refreshing = false;

    async function refresh() {
      if (refreshing || document.visibilityState === "hidden") {
        return;
      }
      refreshing = true;
      try {
        const options = {
          cache: "no-store" as RequestCache,
          signal: controller.signal,
        };
        const [contractResponse, snapshotResponse] = await Promise.all([
          fetch("/data/observer-contract.json", options),
          fetch("/data/observer-snapshot.json", options),
        ]);
        if (!contractResponse.ok || !snapshotResponse.ok) {
          throw new Error("artifacts unavailable");
        }

        const [nextContract, nextSnapshot] = (await Promise.all([
          contractResponse.json(),
          snapshotResponse.json(),
        ])) as [PresentationContract, ObserverSnapshot];
        await verifyArtifacts(nextContract, nextSnapshot);
        if (controller.signal.aborted) {
          return;
        }

        setContract(nextContract);
        setSnapshot(nextSnapshot);
        setFailed(false);
        setStale(false);
        trusted = true;
      } catch (error) {
        if (error instanceof DOMException && error.name === "AbortError") {
          return;
        }
        if (trusted) {
          setStale(true);
        } else {
          setFailed(true);
        }
      } finally {
        refreshing = false;
      }
    }

    function refreshWhenVisible() {
      if (document.visibilityState === "visible") {
        void refresh();
      }
    }

    void refresh();
    const interval = window.setInterval(refresh, REFRESH_INTERVAL_MS);
    document.addEventListener("visibilitychange", refreshWhenVisible);
    return () => {
      controller.abort();
      window.clearInterval(interval);
      document.removeEventListener("visibilitychange", refreshWhenVisible);
    };
  }, []);

  if (failed) {
    return <main className="loading"><p>OBSERVER OFFLINE</p><h1>The chronicle could not be verified.</h1></main>;
  }
  if (!snapshot || !contract) {
    return <main className="loading"><p>AUTHENTICATING CHRONICLE</p><h1>AWAKENED: ZERO RANK</h1></main>;
  }

  const p = snapshot.protagonist;
  const events = [...snapshot.activity.recent_events].reverse().slice(0, 6);return <main><header><b>AWAKENED <i>ZERO RANK</i></b><span aria-live="polite">{stale?"REFRESH DELAYED / LAST VERIFIED":"AUTO REFRESH / READ ONLY"}</span></header><section className="hero"><div><small>REN'S CHRONICLE / TOKYO, JAPAN</small><h1>A life unfolding<br/>without your hand.</h1><p>Rent is due. Gates are opening. Ren chooses what comes next.</p></div><aside>DAY<strong>{String(snapshot.clock.day).padStart(3,"0")}</strong><em>{snapshot.clock.slot}</em></aside></section><nav><span>{snapshot.environment.weather} / {snapshot.environment.temperature_c} C</span><span>{snapshot.environment.season}</span><span>GATE ALERT {snapshot.environment.gate_alert_level}</span><span>SEED {snapshot.seed}</span></nav><div className="grid"><section className="profile"><label>CURRENT STATE <mark>RANK {p.hunter_rank}</mark></label><h2>{p.name}</h2><p>{p.location} / {p.mood}</p><blockquote><small>ACTIVE INTENT</small><b>{p.current_goal}</b></blockquote>{RESOURCE_NAMES.map((k)=><div className="meter" key={k}><span>{k}<b>{p.resources[k]}</b></span><i><u style={{width:p.resources[k]+"%"}}/></i></div>)}<div className="money"><small>AVAILABLE</small><strong>JPY {p.resources.money.toLocaleString()}</strong></div></section><section className="events"><label>LATEST DECISIONS <span>{events.length} ENTRIES</span></label>{events.map((e)=><article key={e.day+e.slot+e.action}><time>D{e.day} / {e.slot}</time><div><h3>{e.action}</h3><p>{e.outcome}</p></div></article>)}</section><section><label>HUNTER RECORD <span>{p.ability}</span></label><div className="stats">{[["Readiness",p.progression.combat_readiness],["Rank points",p.progression.rank_points],["Fitness",p.progression.fitness],["Knowledge",p.progression.knowledge]].map(x=><div key={x[0]}><b>{x[1]}</b><small>{x[0]}</small></div>)}</div></section><section className="story"><label>THREE-YEAR ARC <span>{snapshot.story.completed_count}/{snapshot.story.total_anchors}</span></label><h2>{snapshot.story.next?.title||"Ending reached"}</h2><p>Fixed story anchor arrives on day {snapshot.story.next?.day}.</p><strong>{snapshot.story.next?.days_remaining}<small>DAYS REMAINING</small></strong></section><section className="people"><label>PEOPLE IN ORBIT <span>{snapshot.relationships.length} KNOWN</span></label>{snapshot.relationships.slice(0,4).map((r)=><article key={r.name}><i>{r.name.split(" ").map((x:string)=>x[0]).join("")}</i><div><b>{r.name}</b><small>{r.role}</small></div><strong>{r.trust}<small>trust</small></strong></article>)}</section><section><label>PORTAL LEDGER <span>{snapshot.portals.discovered.length} FOUND</span></label>{snapshot.portals.discovered.map((x)=><p className="portal" key={x}>O {x}</p>)}<code>SNAPSHOT / {snapshot.identity.digest.slice(0,16)}...<br/>CONTRACT / {contract.contract_sha256.slice(0,16)}...</code></section></div><footer><b>AWAKENED: ZERO RANK</b><p>An autonomous life simulation. You watch. Ren decides.</p><small>NO CONTROL CAPABILITIES</small></footer></main>}
