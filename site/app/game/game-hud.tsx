"use client";

import { useEffect, useRef, useState } from "react";

import { currentCampaignArc, pendingStoryRoute, restartRpgRun, transmigrationConditions, transmigrateRpgState, type RpgState } from "./game-state";
import { applyGamePreferences, loadGamePreferences } from "./game-preferences";

export function GameHud({ state, current, onNewGame }: { state: RpgState; current: "home" | "city" | "cases" | "field" | "evening" | "debrief"; onNewGame?: () => void }) {
  const [confirmingReset, setConfirmingReset] = useState(false);
  const cancelReset = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    applyGamePreferences(loadGamePreferences());
    const route = pendingStoryRoute(state);
    const alreadyShowing = (route === "/game/evening" && current === "evening") || (route === "/game/debrief" && current === "debrief");
    if (route && !alreadyShowing) window.location.assign(route);
  }, [current, state]);

  useEffect(() => {
    if (!confirmingReset) return;
    cancelReset.current?.focus();
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") setConfirmingReset(false);
    };
    window.addEventListener("keydown", closeOnEscape);
    return () => window.removeEventListener("keydown", closeOnEscape);
  }, [confirmingReset]);

  const resetCampaign = () => {
    setConfirmingReset(false);
    onNewGame?.();
  };

  const retryRun = () => {
    restartRpgRun(state);
    window.location.assign("/game");
  };

  const resolveTransmigration = () => {
    transmigrateRpgState(state);
    window.location.assign("/game");
  };

  const arc = currentCampaignArc(state.day);
  const timelineLabel = ["", "FIRST TIMELINE", "SECOND TIMELINE", "FINAL TIMELINE"][state.timeline];
  const finalConditions = state.status === "year-ending" ? transmigrationConditions(state) : [];

  return <><section className="rpg-hud" aria-label="Ren RPG status">
    <div><small>{timelineLabel} · RUN {state.attempt}</small><b>DAY {state.day} / 365</b><span>{state.slot}</span></div>
    <div><small>LOCATION</small><b>{state.location}</b><span>{state.turns} ACTION{state.turns === 1 ? "" : "S"}</span></div>
    <div><small>CONDITION</small><b>HP {state.health}</b><span>EN {state.energy}</span></div>
    <div><small>FUNDS</small><b>¥{state.money.toLocaleString()}</b><span>{state.lastAction}</span></div>
    {onNewGame && <button onClick={() => setConfirmingReset(true)} aria-haspopup="dialog">NEW GAME</button>}
  </section><section className="campaign-deadline" aria-label="Current story deadline"><span>ARC {arc.id === "worthless-awakening" ? "I" : arc.id === "adachi-countdown" ? "II" : arc.id === "false-orders" ? "III" : "IV"}</span><b>{arc.title}</b><small>DEADLINE · DAY {arc.deadline} · {Math.max(0, arc.deadline - state.day)} DAYS REMAIN</small></section><details className="rpg-journal">
    <summary>CAMPAIGN JOURNAL <span>LOCAL SAVE · {state.journal.length} / 12</span></summary>
    <div className="save-status"><b>AUTOSAVE ACTIVE</b><span>DAY {state.day} · {state.slot} · {state.location}</span><small>Every committed action is saved on this device.</small></div>
    {state.journal.length === 0 ? <p>No actions recorded yet. Ren&apos;s first committed choice will appear here.</p> : <ol>{[...state.journal].reverse().map((entry, index) => <li key={`${entry.day}-${entry.slot}-${index}`}><b>DAY {entry.day} / {entry.slot}</b><span>{entry.action}</span><small>{entry.location}</small></li>)}</ol>}
  </details>{state.status === "game-over" && <div className="reset-shade"><section className="reset-dialog game-over" role="alertdialog" aria-modal="true" aria-labelledby="game-over-title"><small>RUN TERMINATED</small><h2 id="game-over-title">Ren died.</h2><p>Death before Day 365 does not trigger transmigration. This run is over.</p><dl><div><dt>TIMELINE</dt><dd>{state.timeline} / 3</dd></div><div><dt>REACHED</dt><dd>Day {state.day}</dd></div></dl><button className="retry" onClick={retryRun}>RETRY TIMELINE · RUN {state.attempt + 1}</button></section></div>}{state.status === "year-ending" && <div className="reset-shade"><section className="reset-dialog year-ending" role="alertdialog" aria-modal="true" aria-labelledby="year-ending-title"><small>DAY 365 · TIMELINE {state.timeline}</small><h2 id="year-ending-title">{state.transmigrationEligible ? "A residual path opens." : state.timeline === 3 ? "No fourth path remains." : "The year ends here."}</h2><p>{state.transmigrationEligible ? "Ren met every condition. Transmigration is now a choice—not a rescue." : "Reaching the final day was not enough. The missing conditions close the path."}</p><ul>{finalConditions.map((condition) => <li className={condition.met ? "met" : "missed"} key={condition.id}><span>{condition.met ? "✓" : "×"}</span>{condition.label}</li>)}</ul>{state.transmigrationEligible ? <button className="retry" onClick={resolveTransmigration}>TRANSMIGRATE TO TIMELINE {state.timeline + 1}</button> : <button className="retry" onClick={retryRun}>RETRY TIMELINE · RUN {state.attempt + 1}</button>}</section></div>}{confirmingReset && <div className="reset-shade" role="presentation"><section className="reset-dialog" role="alertdialog" aria-modal="true" aria-labelledby="reset-title" aria-describedby="reset-copy"><small>LOCAL CAMPAIGN</small><h2 id="reset-title">Begin Ren&apos;s story again?</h2><p id="reset-copy">This replaces the RPG save on this device. The authenticated Observer timeline is never changed.</p><dl><div><dt>CURRENT SAVE</dt><dd>Day {state.day}, {state.slot}</dd></div><div><dt>RECORDED ACTIONS</dt><dd>{state.turns}</dd></div></dl><nav><button ref={cancelReset} onClick={() => setConfirmingReset(false)}>KEEP CURRENT SAVE</button><button className="danger" onClick={resetCampaign}>START NEW GAME</button></nav><small>PRESS ESCAPE TO CANCEL</small></section></div>}</>;
}
