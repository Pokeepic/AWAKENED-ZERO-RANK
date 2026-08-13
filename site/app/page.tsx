/* eslint-disable react/no-unescaped-entities */
"use client";

import { useEffect, useState } from "react";

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

        const [contractValue, snapshotValue] = await Promise.all([
          contractResponse.json(),
          snapshotResponse.json(),
        ]);
        const { contract: nextContract, snapshot: nextSnapshot } =
          await verifyArtifacts(contractValue, snapshotValue);
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
