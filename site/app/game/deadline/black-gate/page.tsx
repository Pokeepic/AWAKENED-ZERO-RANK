"use client";

import Image from "next/image";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { verifyArtifacts } from "../../../observer-data";
import {
  loadRpgState,
  pendingStoryRoute,
  remainingDaySlots,
  takeRpgAction,
  type RpgState,
} from "../../game-state";
import {
  applyGamePreferences,
  loadGamePreferences,
} from "../../game-preferences";

const EVENT_ID = "black-gate-deadline-resolved";
const BEATS = [
  {
    speaker: "SYSTEM",
    line: "Day 365. The Black Gate has consumed every containment line between the plaza and central Tokyo.",
  },
  {
    speaker: "REN",
    line: "There is no victory here. Only the same residual cadence hidden beneath every breach this year.",
  },
  {
    speaker: "AIKO",
    line: "If you can still hear me—don't try to be stronger than it. Find the part that remembers before.",
  },
  {
    speaker: "BLACK GATE",
    line: "The core collapses inward. For one instant, its ending and Ren's beginning occupy the same place.",
  },
] as const;
type Outcome = { title: string; copy: string; survived: boolean };

export default function BlackGateDeadlinePage() {
  const [rpg, setRpg] = useState<RpgState | null>(null);
  const [beat, setBeat] = useState(0);
  const [outcome, setOutcome] = useState<Outcome | null>(null);
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    applyGamePreferences(loadGamePreferences());
    const controller = new AbortController();
    async function load() {
      try {
        const options = {
          cache: "no-store" as RequestCache,
          signal: controller.signal,
        };
        const [contract, snapshot] = await Promise.all([
          fetch("/data/observer-contract.json", options),
          fetch("/data/observer-snapshot.json", options),
        ]);
        if (!contract.ok || !snapshot.ok)
          throw new Error("artifacts unavailable");
        const verified = await verifyArtifacts(
          await contract.json(),
          await snapshot.json(),
        );
        const save = loadRpgState(verified.snapshot);
        if (pendingStoryRoute(save) !== "/game/deadline/black-gate")
          window.location.replace("/game");
        else if (!controller.signal.aborted) setRpg(save);
      } catch (error) {
        if (!(error instanceof DOMException && error.name === "AbortError"))
          setFailed(true);
      }
    }
    void load();
    return () => controller.abort();
  }, []);

  const resolve = useCallback(
    (choice: "fight" | "read") => {
      if (!rpg || outcome) return;
      const mastery = rpg.skillMastery["Residual Read"] ?? 0;
      const evidenceReady = [
        "arc-i-evidence",
        "arc-ii-evidence",
        "arc-iii-evidence",
      ].every((event) => rpg.completedEvents.includes(event));
      const strongestBond = Math.max(0, ...Object.values(rpg.bonds));
      const secondTimelineReady =
        rpg.timeline === 1 ||
        ((rpg.skillMastery["Vector Step"] ?? 0) === 100 &&
          rpg.completedEvents.includes("busan-signal-decoded") &&
          rpg.completedEvents.includes("residual-anchor-complete"));
      const prepared =
        mastery === 100 &&
        evidenceReady &&
        strongestBond >= 4 &&
        rpg.health >= 38 &&
        secondTimelineReady;
      const events = new Set(rpg.completedEvents);
      events.add(EVENT_ID);
      const bonds = { ...rpg.bonds };
      let health = rpg.health,
        energy = rpg.energy,
        action: string,
        result: Outcome;
      if (choice === "fight") {
        health = 0;
        energy = 0;
        events.add("black-gate-fought-and-lost");
        action = "Fought the impossible Black Gate";
        result = {
          survived: false,
          title: "Zero Rank cannot wound the dark.",
          copy: "Ren attacks the Gate as if this were a battle that could be won. The first counter-pulse erases him. Death ends this run; no loop is granted.",
        };
      } else if (prepared) {
        health -= 18;
        energy -= 30;
        events.add("black-gate-temporal-residue");
        events.add("read-the-collapsing-gate");
        const ally = Object.entries(bonds).sort((a, b) => b[1] - a[1])[0]?.[0];
        if (ally) bonds[ally] = Math.min(10, bonds[ally] + 2);
        action = "Read the collapsing Black Gate";
        result = {
          survived: true,
          title: "The Gate is not defeated.",
          copy: "Ren follows the residue instead of resisting it. The city still falls—but his evidence, mastery, and strongest bond hold one path open through the ending.",
        };
      } else {
        health = 0;
        energy = 0;
        events.add("black-gate-read-failed");
        action = "Lost himself inside the collapsing Gate";
        result = {
          survived: false,
          title: "The past does not answer.",
          copy: "Incomplete evidence, mastery, trust, or health turns the residual path into noise. Ren reaches the final day, but ordinary death still ends this run.",
        };
      }
      setRpg(
        takeRpgAction(
          rpg,
          action,
          {
            health,
            energy,
            location: "Black Gate Core",
            bonds,
            completedEvents: [...events],
          },
          remainingDaySlots(rpg),
        ),
      );
      setOutcome(result);
    },
    [outcome, rpg],
  );

  useEffect(() => {
    const key = (event: KeyboardEvent) => {
      if (outcome || event.altKey || event.ctrlKey || event.metaKey) return;
      if (beat < BEATS.length && (event.key === "Enter" || event.key === " ")) {
        event.preventDefault();
        setBeat((v) => Math.min(BEATS.length, v + 1));
      } else if (event.key === "Escape") setBeat(BEATS.length);
      else if (beat >= BEATS.length && event.code === "Digit1")
        resolve("fight");
      else if (beat >= BEATS.length && event.code === "Digit2") resolve("read");
    };
    window.addEventListener("keydown", key);
    return () => window.removeEventListener("keydown", key);
  }, [beat, outcome, resolve]);
  if (failed)
    return (
      <main className="game-loading">
        <p>CORE LINK LOST</p>
        <h1>The final-day record could not be verified.</h1>
        <Link href="/game">Return home</Link>
      </main>
    );
  if (!rpg)
    return (
      <main className="game-loading" aria-busy="true">
        <p>DAY 365 / BLACK GATE</p>
        <h1>Entering the residual core…</h1>
      </main>
    );
  const mastery = rpg.skillMastery["Residual Read"] ?? 0,
    evidence = ["arc-i-evidence", "arc-ii-evidence", "arc-iii-evidence"].filter(
      (event) => rpg.completedEvents.includes(event),
    ).length,
    strongestBond = Math.max(0, ...Object.values(rpg.bonds)),
    secondTimelineReady =
      rpg.timeline === 1 ||
      ((rpg.skillMastery["Vector Step"] ?? 0) === 100 &&
        rpg.completedEvents.includes("busan-signal-decoded") &&
        rpg.completedEvents.includes("residual-anchor-complete")),
    ready =
      mastery === 100 &&
      evidence === 3 &&
      strongestBond >= 4 &&
      rpg.health >= 38 &&
      secondTimelineReady,
    current = BEATS[Math.min(beat, BEATS.length - 1)];
  return (
    <main
      className="deadline-cutscene black-gate-deadline"
      aria-label="Arc IV Black Gate final deadline"
    >
      <Image
        className="deadline-bg"
        src="/game/cutscenes/black-gate-day365-core-v1.png"
        alt="The impossible Black Gate towering over a ruined Tokyo plaza"
        fill
        sizes="100vw"
        priority
      />
      <div className="deadline-shade" aria-hidden="true" />
      <Image
        className="deadline-ren"
        src="/game/visual-novel/ren-full.png"
        alt="Ren Takahashi facing the Black Gate"
        width={1024}
        height={1536}
        priority
      />
      <header className="deadline-caption">
        <span>ARC IV DEADLINE / TIMELINE {rpg.timeline} / DAY 365</span>
        <b>THE BLACK GATE</b>
        <small>
          EVIDENCE {evidence}/3 · BOND {strongestBond}/4 · HP {rpg.health}/38 ·
          RR {mastery}/100
        </small>
      </header>
      {!outcome && beat < BEATS.length && (
        <button className="deadline-skip" onClick={() => setBeat(BEATS.length)}>
          SKIP TO DECISION <span>ESC</span>
        </button>
      )}
      <section className="deadline-panel" aria-live="polite">
        {outcome ? (
          <div
            className={`deadline-result ${outcome.survived ? "success" : "failure"}`}
          >
            <small>
              {rpg.status === "year-ending" ? "YEAR ONE COMPLETE" : "GAME OVER"}
            </small>
            <h1>{outcome.title}</h1>
            <p>{outcome.copy}</p>
            <dl>
              <div>
                <dt>HP</dt>
                <dd>{rpg.health}</dd>
              </div>
              <div>
                <dt>GATE</dt>
                <dd>UNBEATEN</dd>
              </div>
              <div>
                <dt>NEXT</dt>
                <dd>{rpg.status === "year-ending" ? "LEDGER" : "RETRY"}</dd>
              </div>
            </dl>
            <Link href="/game">OPEN THE FINAL LEDGER</Link>
          </div>
        ) : beat < BEATS.length ? (
          <div className="deadline-beat" key={`${current.speaker}-${beat}`}>
            <small>
              {current.speaker} / {beat + 1} OF {BEATS.length}
            </small>
            <p>{current.line}</p>
            <button onClick={() => setBeat((v) => v + 1)}>
              CONTINUE <span>ENTER / SPACE</span>
            </button>
          </div>
        ) : (
          <div className="deadline-choice">
            <small>FINAL IRREVERSIBLE DECISION</small>
            <h1>The Black Gate cannot be beaten this year.</h1>
            <p>
              Ren can die fighting it, or trust everything he built and read the
              collapse. A read attempted without every preparation is still
              fatal.
            </p>
            <div>
              <button onClick={() => resolve("fight")}>
                <b>1</b>
                <span>FIGHT THE BLACK GATE</span>
                <small>IMPOSSIBLE · ORDINARY DEATH · NO LOOP</small>
              </button>
              <button onClick={() => resolve("read")}>
                <b>2</b>
                <span>READ THE COLLAPSING GATE</span>
                <small>
                  {ready
                    ? "ALL CONDITIONS READY · RESIDUAL PATH"
                    : rpg.timeline >= 2 && !secondTimelineReady
                      ? "VS 100% · BUSAN · ANCHOR REQUIRED"
                      : "PREPARATION INCOMPLETE · LETHAL"}
                </small>
              </button>
            </div>
          </div>
        )}
      </section>
    </main>
  );
}
