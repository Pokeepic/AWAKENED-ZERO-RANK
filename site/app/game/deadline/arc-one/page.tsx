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

const EVENT_ID = "arc-i-deadline-resolved";
const EVIDENCE_ID = "arc-i-evidence";
const STORY_BEATS = [
  {
    speaker: "DISPATCH",
    line: "All Adachi patrols: synchronized pulse confirmed. Evacuation Route C is losing containment.",
  },
  {
    speaker: "AIKO",
    line: "The cleanup team is already burning Gate residue. Ren—if your trace is real, this is the last chance to prove it.",
  },
  {
    speaker: "REN",
    line: "Residual Read catches the same causal scar repeating beneath every pulse. The evidence and the evacuation route are splitting apart.",
  },
] as const;

type Result = { title: string; copy: string; success: boolean };

export default function ArcOneDeadlinePage() {
  const [rpg, setRpg] = useState<RpgState | null>(null);
  const [beat, setBeat] = useState(0);
  const [result, setResult] = useState<Result | null>(null);
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
        if (pendingStoryRoute(save) !== "/game/deadline/arc-one")
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
    (choice: "evidence" | "evacuation" | "force-read" | "vector") => {
      if (!rpg || result) return;
      const hasEvidence =
        rpg.completedEvents.includes(EVIDENCE_ID) ||
        rpg.legacyClues.includes(EVIDENCE_ID);
      const mastery = rpg.skillMastery["Residual Read"] ?? 0;
      const vector = rpg.skillMastery["Vector Step"] ?? 0;
      const completedEvents = new Set(rpg.completedEvents);
      completedEvents.add(EVENT_ID);
      const bonds = { ...rpg.bonds };
      let health = rpg.health;
      let energy = rpg.energy;
      let location = "Adachi Evacuation Route C";
      let action = "Arc I deadline failed";
      let outcome: Result;

      if (choice === "vector" && rpg.timeline >= 2 && vector >= 20) {
        health -= 4;
        energy -= 15;
        completedEvents.add(EVIDENCE_ID);
        completedEvents.add("arc-i-authenticated-trace");
        completedEvents.add("timeline-ii-arc-i-rescue");
        bonds["Aiko Sato"] = Math.min(10, (bonds["Aiko Sato"] ?? 0) + 1);
        action = "Vector Stepped through the first synchronized pulse";
        outcome = {
          success: true,
          title: "This time, Ren arrives first.",
          copy: "Memory reveals the pulse path and Vector Step carries Ren through its weakest point. Route C and the trace both survive at a fraction of last year's cost.",
        };
      } else if (choice === "evidence" && hasEvidence) {
        health -= 8;
        energy -= 12;
        location = "Tokyo Hunter Guild";
        completedEvents.add("arc-i-authenticated-trace");
        action = "Authenticated the synchronized Gate trace";
        outcome = {
          success: true,
          title: "The trace survives.",
          copy: "Ren reaches the Guild before cleanup destroys the causal record. Arc II opens with proof that the pulses are coordinated.",
        };
      } else if (choice === "evacuation") {
        health -= hasEvidence ? 14 : 12;
        energy -= hasEvidence ? 18 : 16;
        bonds["Aiko Sato"] = Math.min(
          10,
          (bonds["Aiko Sato"] ?? 0) + (hasEvidence ? 2 : 1),
        );
        if (hasEvidence) {
          completedEvents.add("arc-i-authenticated-trace");
          action = "Carried the trace through the evacuation";
          outcome = {
            success: true,
            title: "Nobody is left behind.",
            copy: "Aiko carries Ren's sealed trace while he holds Route C. The evidence reaches the Guild damaged, but authentic.",
          };
        } else {
          completedEvents.add("arc-i-deadline-failed");
          outcome = {
            success: false,
            title: "Lives saved. Evidence erased.",
            copy: "Route C survives, but the cleanup team destroys the final trace. Arc II will begin without proof of coordination.",
          };
        }
      } else if (choice === "force-read") {
        health -= mastery >= 20 ? 25 : rpg.health;
        energy -= 22;
        if (mastery >= 20) {
          completedEvents.add(EVIDENCE_ID);
          completedEvents.add("arc-i-authenticated-trace");
          action = "Forced a live read during the synchronized pulse";
          outcome = {
            success: true,
            title: "Pain becomes proof.",
            copy: "Residual Read burns the synchronized pattern into Ren's memory. He secures the trace late, at a severe physical cost.",
          };
        } else {
          completedEvents.add("arc-i-deadline-failed");
          action = "Was consumed by the synchronized pulse";
          outcome = {
            success: false,
            title: "Residual Read breaks first.",
            copy: "Ren reaches into a live pulse without enough mastery. Ordinary death offers no path back.",
          };
        }
      } else return;

      const next = takeRpgAction(
        rpg,
        action,
        {
          health,
          energy,
          location,
          bonds,
          completedEvents: [...completedEvents],
        },
        remainingDaySlots(rpg),
      );
      setRpg(next);
      setResult(outcome);
    },
    [result, rpg],
  );

  useEffect(() => {
    const keydown = (event: KeyboardEvent) => {
      if (result || event.altKey || event.ctrlKey || event.metaKey) return;
      if (
        beat < STORY_BEATS.length &&
        (event.key === "Enter" || event.key === " ")
      ) {
        event.preventDefault();
        setBeat((value) => Math.min(STORY_BEATS.length, value + 1));
        return;
      }
      if (event.key === "Escape") setBeat(STORY_BEATS.length);
      if (beat >= STORY_BEATS.length && /^Digit[1-3]$/.test(event.code)) {
        const hasEvidence =
          rpg?.completedEvents.includes(EVIDENCE_ID) ||
          rpg?.legacyClues.includes(EVIDENCE_ID);
        if (event.code === "Digit1")
          resolve(hasEvidence ? "evidence" : "evacuation");
        else if (event.code === "Digit2")
          resolve(hasEvidence ? "evacuation" : "force-read");
        else if (rpg?.timeline && rpg.timeline >= 2) resolve("vector");
      }
    };
    window.addEventListener("keydown", keydown);
    return () => window.removeEventListener("keydown", keydown);
  }, [beat, resolve, result, rpg]);

  if (failed)
    return (
      <main className="game-loading">
        <p>DEADLINE LINK OFFLINE</p>
        <h1>The Arc I record could not be verified.</h1>
        <Link href="/game">Return home</Link>
      </main>
    );
  if (!rpg)
    return (
      <main className="game-loading" aria-busy="true">
        <p>DAY 45 / SYNCHRONIZED PULSE</p>
        <h1>Opening Route C…</h1>
      </main>
    );

  const hasEvidence =
    rpg.completedEvents.includes(EVIDENCE_ID) ||
    rpg.legacyClues.includes(EVIDENCE_ID);
  const vector = rpg.skillMastery["Vector Step"] ?? 0;
  const current = STORY_BEATS[Math.min(beat, STORY_BEATS.length - 1)];
  return (
    <main
      className="deadline-cutscene"
      aria-label="Arc I deadline at Adachi evacuation route"
    >
      <Image
        className="deadline-bg"
        src="/game/cutscenes/adachi-day45-pulse-v1.png"
        alt="Rainy Adachi evacuation route facing a synchronized Gate pulse"
        fill
        sizes="100vw"
        priority
      />
      <div className="deadline-shade" aria-hidden="true" />
      <Image
        className="deadline-ren"
        src="/game/visual-novel/ren-full.png"
        alt="Ren Takahashi at the evacuation route"
        width={1024}
        height={1536}
        priority
      />
      <Image
        className="deadline-aiko"
        src="/game/visual-novel/aiko-full.png"
        alt="Aiko Sato coordinating the evacuation"
        width={1024}
        height={1536}
        priority
      />
      <header className="deadline-caption">
        <span>ARC I DEADLINE / DAY {rpg.day}</span>
        <b>THE FIRST SYNCHRONIZED PULSE</b>
        <small>
          {hasEvidence ? "TRACE SECURED" : "TRACE MISSING"} · RR MASTERY{" "}
          {rpg.skillMastery["Residual Read"] ?? 0}%
        </small>
      </header>
      {!result && beat < STORY_BEATS.length && (
        <button
          className="deadline-skip"
          onClick={() => setBeat(STORY_BEATS.length)}
        >
          SKIP TO DECISION <span>ESC</span>
        </button>
      )}
      <section className="deadline-panel" aria-live="polite">
        {result ? (
          <div
            className={`deadline-result ${result.success ? "success" : "failure"}`}
          >
            <small>
              {rpg.status === "game-over" ? "GAME OVER" : "ARC I RESOLVED"}
            </small>
            <h1>{result.title}</h1>
            <p>{result.copy}</p>
            <dl>
              <div>
                <dt>HP</dt>
                <dd>{rpg.health}</dd>
              </div>
              <div>
                <dt>ENERGY</dt>
                <dd>{rpg.energy}</dd>
              </div>
              <div>
                <dt>NEXT</dt>
                <dd>{rpg.status === "game-over" ? "RETRY" : "ARC II"}</dd>
              </div>
            </dl>
            <Link href="/game">
              {rpg.status === "game-over"
                ? "FACE THE CONSEQUENCE"
                : "CONTINUE TO ARC II"}
            </Link>
          </div>
        ) : beat < STORY_BEATS.length ? (
          <div className="deadline-beat" key={`${current.speaker}-${beat}`}>
            <small>
              {current.speaker} / {beat + 1} OF {STORY_BEATS.length}
            </small>
            <p>{current.line}</p>
            <button onClick={() => setBeat((value) => value + 1)}>
              CONTINUE <span>ENTER / SPACE</span>
            </button>
          </div>
        ) : (
          <div className="deadline-choice">
            <small>IRREVERSIBLE DECISION</small>
            <h1>
              {hasEvidence
                ? "Where does Ren carry the proof?"
                : "The trace is already disappearing."}
            </h1>
            <p>
              {hasEvidence
                ? "Both routes can preserve the evidence. Their costs—and who bears them—are different."
                : "Ren can protect the evacuation, or attempt a live read his current mastery may not survive."}
            </p>
            <div>
              <button
                onClick={() => resolve(hasEvidence ? "evidence" : "evacuation")}
              >
                <b>1</b>
                <span>
                  {hasEvidence
                    ? "RUN THE TRACE TO THE GUILD"
                    : "HOLD THE EVACUATION ROUTE"}
                </span>
                <small>
                  {hasEvidence
                    ? "−8 HP · −12 EN · AUTHENTICATE"
                    : "−12 HP · −16 EN · EVIDENCE LOST"}
                </small>
              </button>
              <button
                onClick={() =>
                  resolve(hasEvidence ? "evacuation" : "force-read")
                }
              >
                <b>2</b>
                <span>
                  {hasEvidence
                    ? "TRUST AIKO WITH THE TRACE"
                    : "FORCE A LIVE RESIDUAL READ"}
                </span>
                <small>
                  {hasEvidence
                    ? "−14 HP · −18 EN · AIKO BOND +2"
                    : "20% MASTERY REQUIRED · FAILURE IS LETHAL"}
                </small>
              </button>
              {rpg.timeline >= 2 && (
                <button
                  disabled={vector < 20}
                  onClick={() => resolve("vector")}
                >
                  <b>3</b>
                  <span>STEP THROUGH THE REMEMBERED PULSE</span>
                  <small>
                    {vector >= 20
                      ? "VS 20% · LOW COST · SAVE BOTH"
                      : "VECTOR STEP 20% REQUIRED"}
                  </small>
                </button>
              )}
            </div>
          </div>
        )}
      </section>
    </main>
  );
}
