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

        const [contractValue, snapshotValue] = await Promise.all([
          contractResponse.json(),
          snapshotResponse.json(),
        ]);
        const { contract: nextContract, snapshot: nextSnapshot } =
          await verifyArtifacts(contractValue, snapshotValue);
        if (controller.signal.aborted) {
          return;
        }

        if (
          previousDigest.current !== null &&
          previousDigest.current !== nextSnapshot.identity.digest
        ) {
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

    function markOffline() {
      if (trusted) {
        setStale(true);
      }
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
    return <main id="chronicle" tabIndex={-1} className="loading"><div role="alert"><p>OBSERVER OFFLINE</p><h1>The chronicle could not be verified.</h1></div></main>;
  }
  if (!snapshot || !contract) {
    return <main id="chronicle" tabIndex={-1} className="loading" aria-busy="true"><div role="status" aria-live="polite"><p>AUTHENTICATING CHRONICLE</p><h1>AWAKENED: ZERO RANK</h1></div></main>;
  }

  const p = snapshot.protagonist;
  const events = [...snapshot.activity.recent_events].reverse().slice(0, 6);return <main id="chronicle" tabIndex={-1} className={updated?"chronicle-updated":undefined}><header><b>AWAKENED <i>ZERO RANK</i></b><div className="verification"><span role="status" aria-live="polite" aria-atomic="true">{stale?"REFRESH DELAYED / LAST VERIFIED":updated?"CHRONICLE ADVANCED / VERIFIED":"AUTO REFRESH / READ ONLY"}</span>{verifiedAt&&<time dateTime={verifiedAt.toISOString()}>LAST VERIFIED {verifiedAt.toISOString().slice(11,19)} UTC</time>}</div></header><section className="hero"><div><small>REN'S CHRONICLE / TOKYO, JAPAN</small><h1>A life unfolding<br/>without your hand.</h1><p>Rent is due. Gates are opening. Ren chooses what comes next.</p></div><aside>DAY<strong>{String(snapshot.clock.day).padStart(3,"0")}</strong><em>{snapshot.clock.slot}</em></aside></section><nav aria-label="Current world status"><span>{snapshot.environment.weather} / {snapshot.environment.temperature_c} C</span><span>{snapshot.environment.season}</span><span>GATE ALERT {snapshot.environment.gate_alert_level}</span><span>SEED {snapshot.seed}</span></nav><div className="grid"><section className="profile"><h2 className="section-label">CURRENT STATE <mark>RANK {p.hunter_rank}</mark></h2><h3>{p.name}</h3><p>{p.location} / {p.mood}</p><blockquote><small>ACTIVE INTENT</small><b>{p.current_goal}</b></blockquote>{RESOURCE_NAMES.map((k)=><div className="meter" key={k} role="progressbar" aria-label={k} aria-valuemin={0} aria-valuemax={100} aria-valuenow={p.resources[k]}><span>{k}<b>{p.resources[k]}</b></span><i><u style={{width:p.resources[k]+"%"}}/></i></div>)}<div className="money"><small>AVAILABLE</small><strong>JPY {p.resources.money.toLocaleString()}</strong></div></section><section className="events"><h2 className="section-label">LATEST DECISIONS <span>{events.length} ENTRIES</span></h2>{events.map((e)=><article key={e.day+e.slot+e.action}><time>D{e.day} / {e.slot}</time><div><h3>{e.action}</h3><p>{e.outcome}</p></div></article>)}</section><section><h2 className="section-label">HUNTER RECORD <span>{p.ability}</span></h2><div className="stats">{[["Readiness",p.progression.combat_readiness],["Rank points",p.progression.rank_points],["Fitness",p.progression.fitness],["Knowledge",p.progression.knowledge]].map(x=><div key={x[0]}><b>{x[1]}</b><small>{x[0]}</small></div>)}</div></section><section className="story"><h2 className="section-label">THREE-YEAR ARC <span>{snapshot.story.completed_count}/{snapshot.story.total_anchors}</span></h2>{snapshot.story.next?<><h3>{snapshot.story.next.title}</h3><p>Fixed story anchor arrives on day {snapshot.story.next.day}.</p><strong>{snapshot.story.next.days_remaining}<small>DAYS REMAINING</small></strong></>:<><h3>{snapshot.story.ending?.title||"Ending reached"}</h3><p>{snapshot.story.ending?.summary||"Ren's three-year chronicle is complete."}</p><strong>ARC<small>COMPLETE</small></strong></>}</section><section className="people"><h2 className="section-label">PEOPLE IN ORBIT <span>{snapshot.relationships.length} KNOWN</span></h2>{snapshot.relationships.slice(0,4).map((r)=><article key={r.name}><i>{r.name.split(" ").map((x:string)=>x[0]).join("")}</i><div><b>{r.name}</b><small>{r.role}</small></div><strong>{r.trust}<small>trust</small></strong></article>)}</section><section><h2 className="section-label">PORTAL LEDGER <span>{snapshot.portals.discovered.length} FOUND</span></h2>{snapshot.portals.discovered.map((x)=><p className="portal" key={x}>O {x}</p>)}<code>SNAPSHOT / {snapshot.identity.digest.slice(0,16)}...<br/>CONTRACT / {contract.contract_sha256.slice(0,16)}...</code></section></div><footer><b>AWAKENED: ZERO RANK</b><p>An autonomous life simulation. You watch. Ren decides.</p><small>NO CONTROL CAPABILITIES</small></footer></main>}
