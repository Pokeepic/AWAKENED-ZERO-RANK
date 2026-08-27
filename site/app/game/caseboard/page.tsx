/* eslint-disable react/no-unescaped-entities */
"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { gateReadiness, verifyArtifacts, type ObserverSnapshot } from "../../observer-data";

const RECOMMENDATIONS = [
  { id: "prepare", label: "Prepare before committing", tone: "DISCIPLINE" },
  { id: "investigate", label: "Investigate the weaker signal", tone: "CURIOSITY" },
  { id: "withdraw", label: "Leave both Gates alone", tone: "RESTRAINT" },
] as const;

function renResponse(snapshot: ObserverSnapshot, recommendation: string) {
  const readiness = gateReadiness(snapshot);
  if (recommendation === "prepare") return readiness.supplyCount > 0
    ? `Ren checks ${readiness.supplyCount} field supply${readiness.supplyCount === 1 ? "" : "ies"}. “Preparation is real. Commitment still waits for my call.”`
    : "Ren closes the file. “Good instinct. I don't have field supplies to pretend otherwise.”";
  if (recommendation === "investigate") {
    const lowest = [...snapshot.portals.investigations].sort((a, b) => a.risk - b.risk || a.portal_name.localeCompare(b.portal_name))[0];
    return lowest ? `Ren circles ${lowest.portal_name}, risk ${lowest.risk}. “A lead, not permission. I'll decide whether the evidence justifies proximity.”` : "Ren finds no authenticated Gate file to follow. “Then there is nothing to investigate.”";
  }
  return `Ren leaves both files open but untouched. “Restraint is information too. Gate alert ${snapshot.environment.gate_alert_level} doesn't make every risk mine.”`;
}

export default function CaseboardPage() {
  const [snapshot, setSnapshot] = useState<ObserverSnapshot | null>(null);
  const [failed, setFailed] = useState(false);
  const [opened, setOpened] = useState<string[]>([]);
  const [active, setActive] = useState<string | null>(null);
  const [recommendation, setRecommendation] = useState<(typeof RECOMMENDATIONS)[number] | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    async function load() {
      try {
        const options = { cache: "no-store" as RequestCache, signal: controller.signal };
        const [contractResponse, snapshotResponse] = await Promise.all([fetch("/data/observer-contract.json", options), fetch("/data/observer-snapshot.json", options)]);
        if (!contractResponse.ok || !snapshotResponse.ok) throw new Error("artifacts unavailable");
        const verified = await verifyArtifacts(await contractResponse.json(), await snapshotResponse.json());
        if (!controller.signal.aborted) setSnapshot(verified.snapshot);
      } catch (error) {
        if (!(error instanceof DOMException && error.name === "AbortError")) setFailed(true);
      }
    }
    void load();
    return () => controller.abort();
  }, []);

  function openFile(name: string) { setActive(name); setOpened((known) => known.includes(name) ? known : [...known, name]); }
  function replay() { setOpened([]); setActive(null); setRecommendation(null); }

  if (failed) return <main id="chronicle" className="game-loading"><p>CASEBOARD OFFLINE</p><h1>The chronicle could not be verified.</h1><Link href="/game/city">Return to Tokyo</Link></main>;
  if (!snapshot) return <main id="chronicle" className="game-loading" aria-busy="true"><p>AUTHENTICATING CASE FILES</p><h1>Checking the Gate ledger…</h1></main>;

  const cases = snapshot.portals.investigations;
  const activeCase = cases.find((item) => item.portal_name === active);
  const ready = cases.length > 0 && opened.length === cases.length;

  return <main id="chronicle" className="case-shell">
    <header className="game-header"><Link href="/game/city">← TOKYO BOARD</Link><b>AWAKENED <i>ZERO RANK</i></b><span>CHAPTER 03 / GATE CASEBOARD</span></header>
    <section className="case-intro"><small>GUILD EVIDENCE / DAY {snapshot.clock.day}</small><h1>Two Gates.<br />No clean answer.</h1><p>Open every authenticated file before offering a risk recommendation. Unknown evidence stays unknown.</p></section>

    {cases.length === 0 ? <section className="case-empty"><small>NO DISCOVERED CASES</small><h2>The board is blank.</h2><p>Ren has no authenticated portal investigation yet. The game will not invent one.</p><Link href="/">RETURN TO CHRONICLE</Link></section> : <section className="caseboard" aria-label="Gate investigation caseboard">
      <div className="case-files">{cases.map((item, index) => <button key={item.portal_name} onClick={() => openFile(item.portal_name)} className={opened.includes(item.portal_name) ? "opened" : undefined} aria-pressed={active === item.portal_name}><span>CASE {String(index + 1).padStart(2, "0")}</span><h2>{item.portal_name}</h2><small>{opened.includes(item.portal_name) ? "FILE OPENED" : "SEALED EVIDENCE"}</small></button>)}</div>
      <aside className="case-detail" aria-live="polite">{!activeCase ? <><small>CASEBOARD</small><h2>Open the evidence.</h2><p>Risk and progress remain hidden until you inspect each file.</p></> : <><small>{activeCase.preparation_strategy}</small><h2>{activeCase.portal_name}</h2><dl><div><dt>RISK</dt><dd>{activeCase.risk}</dd></div><div><dt>PROGRESS</dt><dd>{activeCase.progress}%</dd></div><div><dt>PREP BONUS</dt><dd>+{activeCase.preparation_bonus}</dd></div><div><dt>JOINT MISSIONS</dt><dd>{activeCase.joint_missions}</dd></div></dl><p>{activeCase.cooperating_npc ? `Cooperating with ${activeCase.cooperating_npc}.` : "No cooperating contact recorded."}</p></>}
        <div className="case-options"><small>OFFER A RISK RECOMMENDATION</small>{RECOMMENDATIONS.map((item) => <button key={item.id} disabled={!ready || recommendation !== null} onClick={() => setRecommendation(item)}>{item.label}</button>)}{!ready && <p>Open {cases.length - opened.length} remaining file{cases.length - opened.length === 1 ? "" : "s"}.</p>}</div>
      </aside>
    </section>}

    {recommendation && <section className="case-verdict"><small>{recommendation.tone} / ADVISORY ONLY</small><h2>Ren reads the margin note.</h2><blockquote>{renResponse(snapshot, recommendation.id)}</blockquote><div><span>ACTIVE PLAN</span><b>{snapshot.portals.active_plan ?? "NONE"}</b><span>CANON STATUS</span><b>UNCHANGED</b></div><nav><button onClick={replay}>REOPEN CASEBOARD</button><Link href="/">WATCH REN'S NEXT MOVE</Link></nav></section>}
    <footer className="game-footer"><b>LOCAL CASE SESSION</b><p>Recommendations do not begin investigations, consume a time slot, or modify Gate plans.</p><span>{cases.length} AUTHENTICATED CASES</span></footer>
  </main>;
}
