/* eslint-disable react/no-unescaped-entities */
"use client";

import { useEffect, useRef, useState } from "react";

import {
  EQUIPMENT_CATALOG,
  FIELD_SUPPLY_CATALOG,
  GATE_ENCOUNTER_CATALOG,
  PORTAL_PROFILE_CATALOG,
  RESOURCE_NAMES,
  SEASONAL_EVENT_CATALOG,
  TOKYO_LOCATION_CATALOG,
  currentScene,
  memoryArchive,
  peopleDossiers,
  portalCaseFiles,
  storyTimeline,
  dailyBriefing,
  nextSeasonalEvent,
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
  const inventory = Object.entries(p.equipment.inventory);
  const rankOrder = { Unranked: 0, F: 1, E: 2, D: 3, C: 4 } as const;
  const currentRank = rankOrder[p.hunter_rank as keyof typeof rankOrder];
  const equipmentStatus = (item: (typeof EQUIPMENT_CATALOG)[number]) => {
    if (p.equipment[item.kind] === item.name) return "EQUIPPED";
    if ((p.equipment.inventory[item.name] ?? 0) > 0) return "OWNED";
    if (currentRank < rankOrder[item.minimumRank]) return `LOCKED / RANK ${item.minimumRank}`;
    const shortfall = Math.max(0, item.price + snapshot.economy.rent_cost - p.resources.money);
    return shortfall > 0 ? `SAVE ¥${shortfall.toLocaleString()}` : "AVAILABLE";
  };
  const storyProgress = Math.round((snapshot.story.completed_count / snapshot.story.total_anchors) * 100);
  const currentSlot = SLOT_NUMBER[snapshot.clock.slot as keyof typeof SLOT_NUMBER];
  const calendarYear = Math.floor((snapshot.clock.day - 1) / 365) + 1;
  const dayOfYear = ((snapshot.clock.day - 1) % 365) + 1;
  const nextSeasonal = nextSeasonalEvent(snapshot.clock.day);
  const briefing = dailyBriefing(snapshot);
  const scene = currentScene(snapshot);
  const arcTimeline = storyTimeline(snapshot);
  const people = peopleDossiers(snapshot);
  const portalCases = portalCaseFiles(snapshot);
  const memories = memoryArchive(snapshot);
  const cityLocations = Array.from(
    snapshot.whereabouts.reduce((locations, person) => {
      const names = locations.get(person.location) ?? [];
      names.push(person.name);
      locations.set(person.location, names);
      return locations;
    }, new Map<string, string[]>()).entries(),
  ).sort(([left], [right]) => left.localeCompare(right));
  const rentStatus = snapshot.economy.rent_arrears > 0
    ? `¥${snapshot.economy.rent_arrears.toLocaleString()} overdue`
    : snapshot.economy.rent_payments > 0
      ? "Paid"
      : `${Math.max(0, snapshot.economy.rent_due_day - snapshot.clock.day)} days away`;

  return <main id="chronicle" tabIndex={-1} className={updated ? "chronicle-updated" : undefined}>
    <header><b>AWAKENED <i>ZERO RANK</i></b><div className="verification"><span role="status" aria-live="polite" aria-atomic="true">{stale ? "REFRESH DELAYED / LAST VERIFIED" : updated ? "CHRONICLE ADVANCED / VERIFIED" : "AUTO REFRESH / READ ONLY"}</span>{verifiedAt&&<time dateTime={verifiedAt.toISOString()}>LAST VERIFIED {verifiedAt.toISOString().slice(11,19)} UTC</time>}</div></header>
    {stale && <aside className="stale-notice" role="status">The live pair is temporarily unavailable. Every value below remains from the last authenticated chronicle.</aside>}

    <section className="hero" aria-labelledby="chronicle-title"><div><small>REN'S CHRONICLE / TOKYO, JAPAN</small><h1 id="chronicle-title">A life unfolding<br />without your hand.</h1><p>Rent is due. Gates are opening. Ren chooses what comes next.</p><span className="hero-state">{p.location} / {p.mood} / RANK {p.hunter_rank}</span></div><aside aria-label={`Day ${snapshot.clock.day}, ${snapshot.clock.slot}`}>DAY<strong>{String(snapshot.clock.day).padStart(3, "0")}</strong><em>{snapshot.clock.slot}</em></aside></section>
    <nav aria-label="Current world status"><span>{snapshot.environment.weather} / {snapshot.environment.temperature_c} C</span><span>YEAR {calendarYear} / {snapshot.environment.season} D{dayOfYear}</span><span>GATE ALERT {snapshot.environment.gate_alert_level}</span><span>SEED {snapshot.seed}</span></nav>
    <nav className="section-nav" aria-label="Chronicle sections"><a href="#current-life">CURRENT LIFE</a><a href="#progression">PROGRESSION</a><a href="#story-world">STORY & PEOPLE</a><a href="#world-records">WORLD RECORDS</a></nav>

    <div className="grid">
      <div className="chapter-label" id="current-life"><span>01</span><b>CURRENT LIFE</b><small>Condition, choices, and conversations</small></div>
      <section className="briefing" aria-labelledby="briefing-title"><h2 className="section-label" id="briefing-title">TODAY AT A GLANCE <span>AUTHENTICATED SUMMARY</span></h2><div className="briefing-grid">{briefing.map((item) => <article className={item.tone} key={item.label}><small>{item.label}</small><b>{item.value}</b><p>{item.detail}</p></article>)}</div></section>
      <section className="profile"><h2 className="section-label">CURRENT STATE <mark>RANK {p.hunter_rank}</mark></h2><h3>{p.name}</h3><p>{p.location} / {p.mood}</p><blockquote><small>ACTIVE INTENT</small><b>{p.current_goal}</b></blockquote>{RESOURCE_NAMES.map((k) => <div className="meter" key={k} role="progressbar" aria-label={k} aria-valuemin={0} aria-valuemax={100} aria-valuenow={p.resources[k]}><span>{k}<b>{p.resources[k]}</b></span><i><u style={{ width: `${p.resources[k]}%` }} /></i></div>)}<div className="money"><small>AVAILABLE</small><strong>JPY {p.resources.money.toLocaleString()}</strong></div></section>

      <section className="events"><h2 className="section-label">LATEST DECISIONS <span>{events.length} ENTRIES</span></h2>{events.length===0&&<p className="empty-state">Ren has not made a recorded decision yet.</p>}{events.map((event) => <article key={`${event.day}-${event.slot}-${event.action}`}><time>D{event.day} / {event.slot}</time><div><h3>{event.action}</h3><p>{event.outcome}</p><small>WHY / {event.reason}</small></div></article>)}</section>

      <section className="conversations"><h2 className="section-label">RECENT CONVERSATIONS <span>{snapshot.conversations.length} RETAINED</span></h2>{snapshot.conversations.length===0?<p className="empty-state">No recurring conversation has been recorded yet.</p>:snapshot.conversations.map((conversation)=><article key={`${conversation.day}-${conversation.npc_name}-${conversation.intention}`}><header><time>DAY {conversation.day}</time><b>{conversation.npc_name}</b><small>{conversation.reaction}</small></header><blockquote><p>“{conversation.npc_line}”</p><footer>REN / “{conversation.ren_line}”</footer></blockquote></article>)}</section>

      <div className="chapter-label" id="progression"><span>02</span><b>PROGRESSION</b><small>Hunter growth, equipment, and economy</small></div>
      <section className="hunter"><h2 className="section-label">HUNTER RECORD <span>{p.ability}</span></h2><div className="stats"><Metric name="Readiness" value={p.progression.combat_readiness} /><Metric name="Rank points" value={p.progression.rank_points} /><Metric name="Mastery" value={p.progression.ability_mastery} /><Metric name="Knowledge" value={p.progression.knowledge} /></div><div className="record-line"><span>MISSIONS</span><b>{p.progression.missions_completed} / {p.progression.missions_attempted} CLEARED</b></div><div className="record-line"><span>WEAPON</span><b>{p.equipment.weapon ?? "None"}</b></div><div className="record-line"><span>ARMOR</span><b>{p.equipment.armor ?? "None"}</b></div><div className="inventory" aria-label="Inventory">{inventory.length === 0 ? <small>NO CARRIED EQUIPMENT</small> : inventory.map(([name, quantity]) => <span key={name}>{name}<b>x{quantity}</b></span>)}</div></section>

      <section className="gear"><h2 className="section-label">EQUIPMENT PROGRESSION <span>RENT RESERVE PROTECTED</span></h2><p className="gear-intro">The shop reveals what Ren can equip next without spending the ¥{snapshot.economy.rent_cost.toLocaleString()} held for rent.</p><div className="gear-grid">{EQUIPMENT_CATALOG.map((item) => { const status = equipmentStatus(item); return <article key={item.name} className={status.startsWith("LOCKED") ? "locked" : ""}><header><small>RANK {item.minimumRank} / {item.kind.toUpperCase()}</small><b>{item.name}</b></header><dl><div><dt>COMBAT</dt><dd>+{item.bonus}</dd></div><div><dt>PRICE</dt><dd>¥{item.price.toLocaleString()}</dd></div></dl><strong>{status}</strong></article>; })}</div></section>

      <section className="threats"><h2 className="section-label">GATE THREAT LADDER <span>RANK-SCALED MISSIONS</span></h2>{GATE_ENCOUNTER_CATALOG.map((encounter) => <div className="record-line" key={encounter.name}><span>RANK {encounter.minimumRank} / DIFFICULTY {encounter.difficulty}</span><b>{currentRank >= rankOrder[encounter.minimumRank] ? `${encounter.name} / ¥${encounter.reward.toLocaleString()}` : `LOCKED / ${encounter.name}`}</b></div>)}</section>

      <section className="supplies"><h2 className="section-label">FIELD SUPPLIES <span>BOUNDED RESERVES</span></h2>{FIELD_SUPPLY_CATALOG.map((item) => { const count = p.equipment.inventory[item.name] ?? 0; const unlocked = currentRank >= rankOrder[item.minimumRank]; return <div className="record-line" key={item.name}><span>RANK {item.minimumRank} / {item.effect}</span><b>{unlocked ? `${item.name} / ${count} OF ${item.maximum} / ¥${item.price.toLocaleString()}` : `LOCKED / ${item.name}`}</b></div>; })}</section>

      <section className="economy"><h2 className="section-label">LIFE LEDGER <span>JPY</span></h2><strong className="ledger-balance">¥{p.resources.money.toLocaleString()}</strong><div className="record-line"><span>RENT / DAY {snapshot.economy.rent_due_day}</span><b>{rentStatus}</b></div><div className="record-line"><span>RENT COST</span><b>¥{snapshot.economy.rent_cost.toLocaleString()}</b></div><div className="record-line"><span>MEAL COST</span><b>¥{snapshot.economy.meal_cost.toLocaleString()}</b></div><div className="record-line"><span>SHOP VISITS</span><b>{snapshot.economy.shop_visits}</b></div></section>

      <div className="chapter-label" id="story-world"><span>03</span><b>STORY & PEOPLE</b><small>Long arcs, annual moments, and relationships</small></div>
      <section className="story"><h2 className="section-label">THREE-YEAR ARC <span>{snapshot.story.completed_count}/{snapshot.story.total_anchors}</span></h2><div className="arc-meter" role="progressbar" aria-label="Story arc progress" aria-valuemin={0} aria-valuemax={100} aria-valuenow={storyProgress}><i style={{ width: `${storyProgress}%` }} /></div>{snapshot.story.next ? <><h3>{snapshot.story.next.title}</h3><p>Fixed story anchor arrives on day {snapshot.story.next.day}.</p><strong>{snapshot.story.next.days_remaining}<small>DAYS REMAINING</small></strong></> : <><h3>{snapshot.story.ending?.title || "Ending reached"}</h3><p>{snapshot.story.ending?.summary || "Ren's three-year chronicle is complete."}</p><strong>ARC<small>COMPLETE</small></strong></>}<details className="arc-timeline"><summary>VIEW THREE-YEAR TIMELINE <span>SPOILER-LIGHT</span></summary><ol>{arcTimeline.map((anchor, index) => <li className={anchor.status} key={anchor.day}><i>{String(index + 1).padStart(2, "0")}</i><div><small>DAY {anchor.day} / {anchor.status.toUpperCase()}</small><b>{anchor.title}</b></div><span>{anchor.status === "completed" ? "ARCHIVED" : `${anchor.daysRemaining} DAYS`}</span></li>)}</ol></details>{snapshot.story.completed.length > 0 && <ol className="completed-arcs">{snapshot.story.completed.map((arc) => <li key={arc.key}><time>DAY {arc.day}</time><div><b>{arc.title}</b><p>{arc.scene}</p><p>{arc.outcome}</p>{arc.international_link && <small>WORLD LINK / {arc.international_link}</small>}</div><small>{arc.tier}</small></li>)}</ol>}</section>

      <section className="calendar"><h2 className="section-label">SEASONAL CALENDAR <span>REPEATS YEARLY</span></h2><div className="calendar-next"><small>NEXT MOMENT / DAY {nextSeasonal.day}</small><b>{nextSeasonal.title}</b><strong>{nextSeasonal.daysRemaining}<small>DAYS</small></strong></div><div className="calendar-grid">{SEASONAL_EVENT_CATALOG.map((event) => <article key={event.title} className={event.title === nextSeasonal.title ? "next" : undefined}><small>{event.season.toUpperCase()} / D{event.dayOfYear}</small><b>{event.title}</b><span>{event.place}</span></article>)}</div><p>These world events recur without giving the observer control. Ren's condition and known relationships shape who shares them.</p></section>

      <section className="people"><h2 className="section-label">PEOPLE IN ORBIT <span>{people.length} KNOWN</span></h2>{people.length===0&&<p className="empty-state">No trusted relationships have formed yet.</p>}{people.map(({ relationship, location, signal, lastConversation }) => <article key={relationship.name}><i aria-hidden="true">{relationship.name.split(" ").map((part) => part[0]).join("")}</i><div className="person-name"><b>{relationship.name}</b><small>{relationship.role}</small><span>{location} / {signal}</span></div><div className="last-contact">{lastConversation ? <><small>LAST EXCHANGE / DAY {lastConversation.day} / {lastConversation.reaction}</small><p>“{lastConversation.npc_line}”</p></> : <><small>LAST EXCHANGE</small><p>No complete exchange recorded yet.</p></>}</div><dl><div><dt>TRUST</dt><dd>{relationship.trust}</dd></div><div><dt>FAMILIAR</dt><dd>{relationship.familiarity}</dd></div><div><dt>LOYAL</dt><dd>{relationship.loyalty}</dd></div><div><dt>TENSION</dt><dd>{relationship.tension}</dd></div></dl></article>)}</section>

      <section className="whereabouts"><h2 className="section-label">TOKYO TODAY <span>{snapshot.whereabouts.length + 1} LIVES LOCATED</span></h2><article className="current-scene"><div><small>CURRENT SCENE / {scene.place.ward.toUpperCase()}</small><h3>{scene.place.name}</h3><p>{scene.place.purpose}</p></div><dl><div><dt>ATMOSPHERE</dt><dd>{scene.atmosphere}</dd></div><div><dt>LOCAL PRESENCE</dt><dd>{scene.presence}</dd></div><div><dt>PRESSURE</dt><dd>{scene.pressure}</dd></div></dl></article><div className="city-board"><article className="ren-location"><small>REN / CURRENT</small><b>{p.location}</b><span>{p.name}</span></article>{cityLocations.map(([location, names]) => <article key={location}><small>KNOWN WHEREABOUTS</small><b>{location}</b><span>{names.join(" / ")}</span></article>)}</div><details className="city-index"><summary>INSPECT {TOKYO_LOCATION_CATALOG.length} DOCUMENTED PLACES <span>READ ONLY</span></summary><div>{TOKYO_LOCATION_CATALOG.map((place) => { const names = cityLocations.find(([location]) => location === place.name)?.[1] ?? []; const renHere = p.location === place.name; return <article key={place.name} className={renHere || names.length > 0 ? "occupied" : undefined}><small>{place.ward.toUpperCase()}</small><b>{place.name}</b><p>{place.purpose}</p><span>{renHere ? `REN${names.length ? ` / ${names.join(" / ")}` : ""}` : names.length ? names.join(" / ") : "NO KNOWN PRESENCE"}</span></article>; })}</div></details></section>

      <div className="chapter-label" id="world-records"><span>04</span><b>WORLD RECORDS</b><small>Investigations, memories, and the portal atlas</small></div>
      <section className="portals"><h2 className="section-label">PORTAL CASE FILES <span>{portalCases.length} OPENED</span></h2>{portalCases.length===0&&<p className="empty-state">No portals have been discovered yet.</p>}{portalCases.map(({ active, collaborator, collaboratorLocation, investigation, profile, status }) => <article className={`portal-case${active ? " active" : ""}`} key={profile.name}><header><div><small>{profile.environment.toUpperCase()} / {status.toUpperCase()}</small><b>{profile.name}</b></div>{active && <mark>ACTIVE PLAN</mark>}</header><dl><div><dt>HAZARD</dt><dd>{profile.hazard}</dd></div><div><dt>VERIFIED EFFECT</dt><dd>{profile.aftermath}</dd></div></dl>{investigation ? <><div className="case-progress"><span>INVESTIGATION {investigation.progress}%</span><span>RISK {investigation.risk}</span></div><i aria-hidden="true"><u style={{ width: `${investigation.progress}%` }} /></i><p>{investigation.preparation_strategy}</p><footer>{collaborator ? `COLLABORATOR / ${collaborator}${collaboratorLocation ? ` / ${collaboratorLocation}` : ""} / ${investigation.joint_missions} JOINT MISSIONS` : "NO COLLABORATOR RECORDED"}</footer></> : <p>Discovered, but no investigation plan has been recorded.</p>}</article>)}</section>

      <section className="atlas"><h2 className="section-label">PORTAL ATLAS <span>{discovered.length}/{PORTAL_PROFILE_CATALOG.length} DOCUMENTED</span></h2><div className="atlas-grid">{PORTAL_PROFILE_CATALOG.map((portal) => { const known = discovered.includes(portal.name); return <article key={portal.name} className={known ? "known" : "unknown"}><small>{portal.environment.toUpperCase()} / {known ? "DOCUMENTED" : "UNDISCOVERED"}</small><b>{portal.name}</b><span>{known ? `HAZARD / ${portal.hazard}` : "HAZARD / CLASSIFIED"}</span><p>{known ? `VERIFIED EFFECT / ${portal.aftermath}` : "EFFECT / CLASSIFIED"}</p></article>; })}</div></section>

      <section className="memories"><h2 className="section-label">CONTINUITY ARCHIVE <span>{memories.length} KEY MEMORIES</span></h2>{memories.length === 0 ? <p className="empty-state">No defining memories have formed yet.</p> : <ol>{memories.map((memory, index) => <li className={memory.band} key={`${memory.day}-${memory.summary}`}><i aria-hidden="true">{String(index + 1).padStart(2, "0")}</i><div><time>DAY {memory.day} / {memory.ageDays === 0 ? "TODAY" : `${memory.ageDays} DAYS AGO`}</time><p>{memory.summary}</p></div><span>IMPACT {memory.importance}<small>{memory.band}</small></span></li>)}</ol>}</section>
    </div>

    <section className="integrity" aria-label="Observer integrity"><div><small>WORLD POSITION</small><b>DAY {snapshot.clock.day} / SLOT {currentSlot + 1} OF 4</b></div><code>SNAPSHOT / {snapshot.identity.digest.slice(0, 16)}...<br />CONTRACT / {contract.contract_sha256.slice(0, 16)}...</code><small>AUTHENTICATED STATIC ARTIFACTS / NO CONTROL CAPABILITIES</small></section>
    <footer><b>AWAKENED: ZERO RANK</b><p>An autonomous life simulation. You watch. Ren decides.</p><small>OBSERVER / READ ONLY</small></footer>
  </main>;
}
