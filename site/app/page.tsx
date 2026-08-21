/* eslint-disable react/no-unescaped-entities */
"use client";

import { useEffect, useRef, useState } from "react";

import {
  RESOURCE_NAMES,
  verifyArtifacts,
  type ObserverSnapshot,
  type PresentationContract,
} from "./observer-data";

const REFRESH_INTERVAL_MS = 60_000;
const SLOT_NUMBER = { Morning: 0, Afternoon: 1, Evening: 2, "Late Night": 3 } as const;

function Metric({ name, value }: { name: string; value: number }) {
  return <div><b>{value}</b><small>{name}</small></div>;
}

export default function Home() {
  const [snapshot, setSnapshot] = useState<ObserverSnapshot | null>(null);
  const [contract, setContract] = useState<PresentationContract | null>(null);
  const [failed, setFailed] = useState(false);
  const [stale, setStale] = useState(false);
  const [updated, setUpdated] = useState(false);
  const [verifiedAt, setVerifiedAt] = useState<Date | null>(null);
  const previousDigest = useRef<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    let trusted = false;
    let refreshing = false;
    let updateTimer: number | undefined;

    async function refresh() {
      if (refreshing || document.visibilityState === "hidden") return;
      refreshing = true;
      try {
        const options = { cache: "no-store" as RequestCache, signal: controller.signal };
        const [contractResponse, snapshotResponse] = await Promise.all([
          fetch("/data/observer-contract.json", options),
          fetch("/data/observer-snapshot.json", options),
        ]);
        if (!contractResponse.ok || !snapshotResponse.ok) throw new Error("artifacts unavailable");
        const [contractValue, snapshotValue] = await Promise.all([
          contractResponse.json(), snapshotResponse.json(),
        ]);
        const { contract: nextContract, snapshot: nextSnapshot } =
          await verifyArtifacts(contractValue, snapshotValue);
        if (controller.signal.aborted) return;
        if (previousDigest.current !== null && previousDigest.current !== nextSnapshot.identity.digest) {
          setUpdated(true);
          window.clearTimeout(updateTimer);
          updateTimer = window.setTimeout(() => setUpdated(false), 1_800);
        }
        previousDigest.current = nextSnapshot.identity.digest;
        setContract(nextContract);
        setSnapshot(nextSnapshot);
        setVerifiedAt(new Date());
        setFailed(false);
        setStale(false);
        trusted = true;
      } catch (error) {
        if (error instanceof DOMException && error.name === "AbortError") return;
        if (trusted) setStale(true);
        else setFailed(true);
      } finally {
        refreshing = false;
      }
    }

    function refreshWhenVisible() {
      if (document.visibilityState === "visible") void refresh();
    }
    function markOffline() {
      if (trusted) setStale(true);
    }
    function refreshWhenOnline() {
      void refresh();
    }

    void refresh();
    const interval = window.setInterval(refresh, REFRESH_INTERVAL_MS);
    document.addEventListener("visibilitychange", refreshWhenVisible);
    window.addEventListener("offline", markOffline);
    window.addEventListener("online", refreshWhenOnline);
    return () => {
      controller.abort();
      window.clearInterval(interval);
      window.clearTimeout(updateTimer);
      document.removeEventListener("visibilitychange", refreshWhenVisible);
      window.removeEventListener("offline", markOffline);
      window.removeEventListener("online", refreshWhenOnline);
    };
  }, []);

  if (failed) {
    return <main id="chronicle" tabIndex={-1} className="loading"><div role="alert"><p>OBSERVER OFFLINE</p><h1>The chronicle could not be verified.</h1><small>No unverified world data has been rendered.</small></div></main>;
  }
  if (!snapshot || !contract) {
    return <main id="chronicle" tabIndex={-1} className="loading" aria-busy="true"><div role="status" aria-live="polite"><p>AUTHENTICATING CHRONICLE</p><h1>AWAKENED: ZERO RANK</h1></div></main>;
  }

  const p = snapshot.protagonist;
  const events = [...snapshot.activity.recent_events].reverse().slice(0, 8);
  const discovered = snapshot.portals.discovered;
  const investigations = snapshot.portals.investigations;
  const inventory = Object.entries(p.equipment.inventory);
  const storyProgress = Math.round((snapshot.story.completed_count / snapshot.story.total_anchors) * 100);
  const currentSlot = SLOT_NUMBER[snapshot.clock.slot as keyof typeof SLOT_NUMBER];
  const rentStatus = snapshot.economy.rent_arrears > 0
    ? `¥${snapshot.economy.rent_arrears.toLocaleString()} overdue`
    : snapshot.economy.rent_payments > 0
      ? "Paid"
      : `${Math.max(0, snapshot.economy.rent_due_day - snapshot.clock.day)} days away`;

  return <main id="chronicle" tabIndex={-1} className={updated ? "chronicle-updated" : undefined}>
    <header><b>AWAKENED <i>ZERO RANK</i></b><div className="verification"><span role="status" aria-live="polite" aria-atomic="true">{stale ? "REFRESH DELAYED / LAST VERIFIED" : updated ? "CHRONICLE ADVANCED / VERIFIED" : "AUTO REFRESH / READ ONLY"}</span>{verifiedAt&&<time dateTime={verifiedAt.toISOString()}>LAST VERIFIED {verifiedAt.toISOString().slice(11,19)} UTC</time>}</div></header>
    {stale && <aside className="stale-notice" role="status">The live pair is temporarily unavailable. Every value below remains from the last authenticated chronicle.</aside>}

    <section className="hero" aria-labelledby="chronicle-title"><div><small>REN'S CHRONICLE / TOKYO, JAPAN</small><h1 id="chronicle-title">A life unfolding<br />without your hand.</h1><p>Rent is due. Gates are opening. Ren chooses what comes next.</p><span className="hero-state">{p.location} / {p.mood} / RANK {p.hunter_rank}</span></div><aside aria-label={`Day ${snapshot.clock.day}, ${snapshot.clock.slot}`}>DAY<strong>{String(snapshot.clock.day).padStart(3, "0")}</strong><em>{snapshot.clock.slot}</em></aside></section>
    <nav aria-label="Current world status"><span>{snapshot.environment.weather} / {snapshot.environment.temperature_c} C</span><span>{snapshot.environment.season}</span><span>GATE ALERT {snapshot.environment.gate_alert_level}</span><span>SEED {snapshot.seed}</span></nav>

    <div className="grid">
      <section className="profile"><h2 className="section-label">CURRENT STATE <mark>RANK {p.hunter_rank}</mark></h2><h3>{p.name}</h3><p>{p.location} / {p.mood}</p><blockquote><small>ACTIVE INTENT</small><b>{p.current_goal}</b></blockquote>{RESOURCE_NAMES.map((k) => <div className="meter" key={k} role="progressbar" aria-label={k} aria-valuemin={0} aria-valuemax={100} aria-valuenow={p.resources[k]}><span>{k}<b>{p.resources[k]}</b></span><i><u style={{ width: `${p.resources[k]}%` }} /></i></div>)}<div className="money"><small>AVAILABLE</small><strong>JPY {p.resources.money.toLocaleString()}</strong></div></section>

      <section className="events"><h2 className="section-label">LATEST DECISIONS <span>{events.length} ENTRIES</span></h2>{events.length===0&&<p className="empty-state">Ren has not made a recorded decision yet.</p>}{events.map((event) => <article key={`${event.day}-${event.slot}-${event.action}`}><time>D{event.day} / {event.slot}</time><div><h3>{event.action}</h3><p>{event.outcome}</p><small>WHY / {event.reason}</small></div></article>)}</section>

      <section className="hunter"><h2 className="section-label">HUNTER RECORD <span>{p.ability}</span></h2><div className="stats"><Metric name="Readiness" value={p.progression.combat_readiness} /><Metric name="Rank points" value={p.progression.rank_points} /><Metric name="Mastery" value={p.progression.ability_mastery} /><Metric name="Knowledge" value={p.progression.knowledge} /></div><div className="record-line"><span>MISSIONS</span><b>{p.progression.missions_completed} / {p.progression.missions_attempted} CLEARED</b></div><div className="record-line"><span>WEAPON</span><b>{p.equipment.weapon ?? "None"}</b></div><div className="record-line"><span>ARMOR</span><b>{p.equipment.armor ?? "None"}</b></div><div className="inventory" aria-label="Inventory">{inventory.length === 0 ? <small>NO CARRIED EQUIPMENT</small> : inventory.map(([name, quantity]) => <span key={name}>{name}<b>x{quantity}</b></span>)}</div></section>

      <section className="economy"><h2 className="section-label">LIFE LEDGER <span>JPY</span></h2><strong className="ledger-balance">¥{p.resources.money.toLocaleString()}</strong><div className="record-line"><span>RENT / DAY {snapshot.economy.rent_due_day}</span><b>{rentStatus}</b></div><div className="record-line"><span>RENT COST</span><b>¥{snapshot.economy.rent_cost.toLocaleString()}</b></div><div className="record-line"><span>MEAL COST</span><b>¥{snapshot.economy.meal_cost.toLocaleString()}</b></div><div className="record-line"><span>SHOP VISITS</span><b>{snapshot.economy.shop_visits}</b></div></section>

      <section className="story"><h2 className="section-label">THREE-YEAR ARC <span>{snapshot.story.completed_count}/{snapshot.story.total_anchors}</span></h2><div className="arc-meter" role="progressbar" aria-label="Story arc progress" aria-valuemin={0} aria-valuemax={100} aria-valuenow={storyProgress}><i style={{ width: `${storyProgress}%` }} /></div>{snapshot.story.next ? <><h3>{snapshot.story.next.title}</h3><p>Fixed story anchor arrives on day {snapshot.story.next.day}.</p><strong>{snapshot.story.next.days_remaining}<small>DAYS REMAINING</small></strong></> : <><h3>{snapshot.story.ending?.title || "Ending reached"}</h3><p>{snapshot.story.ending?.summary || "Ren's three-year chronicle is complete."}</p><strong>ARC<small>COMPLETE</small></strong></>}{snapshot.story.completed.length > 0 && <ol className="completed-arcs">{snapshot.story.completed.map((arc) => <li key={arc.key}><time>DAY {arc.day}</time><b>{arc.title}</b><small>{arc.tier}</small></li>)}</ol>}</section>

      <section className="people"><h2 className="section-label">PEOPLE IN ORBIT <span>{snapshot.relationships.length} KNOWN</span></h2>{snapshot.relationships.length===0&&<p className="empty-state">No trusted relationships have formed yet.</p>}{snapshot.relationships.map((relationship) => <article key={relationship.name}><i aria-hidden="true">{relationship.name.split(" ").map((part) => part[0]).join("")}</i><div><b>{relationship.name}</b><small>{relationship.role}</small></div><dl><div><dt>TRUST</dt><dd>{relationship.trust}</dd></div><div><dt>FAMILIAR</dt><dd>{relationship.familiarity}</dd></div><div><dt>LOYAL</dt><dd>{relationship.loyalty}</dd></div><div><dt>TENSION</dt><dd>{relationship.tension}</dd></div></dl></article>)}</section>

      <section className="portals"><h2 className="section-label">PORTAL LEDGER <span>{discovered.length} FOUND</span></h2>{discovered.length===0&&<p className="empty-state">No portals have been discovered yet.</p>}{discovered.map((name) => { const investigation = investigations.find((item) => item.portal_name === name); return <article className="portal" key={name}><div><b>{name}</b>{snapshot.portals.active_plan === name && <mark>ACTIVE PLAN</mark>}</div>{investigation ? <><span>{investigation.progress}% investigated / risk {investigation.risk}</span><i aria-hidden="true"><u style={{ width: `${investigation.progress}%` }} /></i><small>{investigation.preparation_strategy}{investigation.cooperating_npc ? ` / with ${investigation.cooperating_npc}` : ""}</small></> : <small>DISCOVERED / NOT YET INVESTIGATED</small>}</article>; })}</section>

      <section className="memories"><h2 className="section-label">KEY MEMORIES <span>{snapshot.activity.key_memories.length} RETAINED</span></h2>{snapshot.activity.key_memories.length === 0 ? <p className="empty-state">No defining memories have formed yet.</p> : <ol>{snapshot.activity.key_memories.map((memory) => <li key={`${memory.day}-${memory.summary}`}><time>DAY {memory.day} / IMPACT {memory.importance}</time><p>{memory.summary}</p></li>)}</ol>}</section>
    </div>

    <section className="integrity" aria-label="Observer integrity"><div><small>WORLD POSITION</small><b>DAY {snapshot.clock.day} / SLOT {currentSlot + 1} OF 4</b></div><code>SNAPSHOT / {snapshot.identity.digest.slice(0, 16)}...<br />CONTRACT / {contract.contract_sha256.slice(0, 16)}...</code><small>AUTHENTICATED STATIC ARTIFACTS / NO CONTROL CAPABILITIES</small></section>
    <footer><b>AWAKENED: ZERO RANK</b><p>An autonomous life simulation. You watch. Ren decides.</p><small>OBSERVER / READ ONLY</small></footer>
  </main>;
}
