/* eslint-disable react/no-unescaped-entities */
"use client";

import Image from "next/image";
import Link from "../../game-link";
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

const EVENT_ID = "arc-iii-deadline-resolved";
const BEATS = [
  {
    speaker: "DAICHI",
    line: "Every district received a different retreat order under the same command signature. Tokyo's response grid is tearing itself apart.",
  },
  {
    speaker: "REN",
    line: "The forged orders repeat the cadence from Adachi. Whoever synchronized the Gates is now writing through the emergency network.",
  },
  {
    speaker: "SYSTEM",
    line: "Command purge begins in ninety seconds. The proof can be published—or read directly from the live core.",
  },
] as const;
type Outcome = { title: string; copy: string; success: boolean };

export default function ArcThreeDeadlinePage() {
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
        if (pendingStoryRoute(save) !== "/game/deadline/arc-three")
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
    (choice: "publish" | "core" | "vector" | "causal") => {
      if (!rpg || outcome) return;
      const trusted = (rpg.bonds["Daichi Mori"] ?? 0) >= 2;
      const mastery = rpg.skillMastery["Residual Read"] ?? 0;
      const vector = rpg.skillMastery["Vector Step"] ?? 0;
      const causal = rpg.skillMastery["Causal Sever"] ?? 0;
      const priorEvidence = rpg.completedEvents.includes("arc-ii-evidence");
      const events = new Set(rpg.completedEvents);
      events.add(EVENT_ID);
      const bonds = { ...rpg.bonds };
      let health = rpg.health,
        energy = rpg.energy,
        action: string,
        result: Outcome;
      if (choice === "causal" && rpg.timeline === 3 && causal >= 85) {
        health -= 3;
        energy -= 28;
        events.add("arc-iii-evidence");
        events.add("false-orders-exposed");
        events.add("timeline-iii-command-forgery-severed");
        bonds["Daichi Mori"] = Math.min(10, (bonds["Daichi Mori"] ?? 0) + 2);
        action = "Severed the forged orders from emergency command";
        result = { success: true, title: "The false orders lose their authority.", copy: "Ren cuts the causal link that makes the forgery executable. Daichi preserves the proof while Tokyo's real responders regain command." };
      } else if (choice === "vector" && rpg.timeline >= 2 && vector >= 80) {
        health -= 6;
        energy -= 22;
        events.add("arc-iii-evidence");
        events.add("false-orders-exposed");
        events.add("timeline-ii-command-purge-outrun");
        bonds["Daichi Mori"] = Math.min(10, (bonds["Daichi Mori"] ?? 0) + 2);
        action = "Vector Stepped the proof beyond the command purge";
        result = {
          success: true,
          title: "The purge deletes an empty room.",
          copy: "Ren crosses the remembered blind interval and carries the signed dispatch chain outside command before deletion begins. Daichi publishes proof the system can no longer reach.",
        };
      } else if (choice === "publish") {
        health -= priorEvidence ? 8 : 14;
        energy -= 20;
        if (priorEvidence && trusted) {
          events.add("arc-iii-evidence");
          events.add("false-orders-exposed");
          bonds["Daichi Mori"] = Math.min(10, (bonds["Daichi Mori"] ?? 0) + 2);
          action = "Published the forged orders with Daichi";
          result = {
            success: true,
            title: "Tokyo receives one true order.",
            copy: "Daichi signs the Adachi chain and pushes it through every surviving channel. The divided response grid reunites before the purge.",
          };
        } else {
          events.add("arc-iii-deadline-failed");
          action = "Published an incomplete dispatch accusation";
          result = {
            success: false,
            title: "The truth arrives without authority.",
            copy: "Without the Adachi chain and a trusted Guild signature, command labels Ren's warning counterfeit. The forged orders survive the night.",
          };
        }
      } else {
        energy -= 32;
        if (mastery >= 65) {
          health -= priorEvidence ? 25 : 34;
          events.add("arc-iii-evidence");
          events.add("command-core-residue-read");
          action = "Read the forged command core";
          result = {
            success: true,
            title: "The forgery leaves a voiceprint.",
            copy: "Ren reads the live purge backward and extracts the causal signature behind every false order. The Black Gate now has an author.",
          };
        } else {
          health = 0;
          events.add("arc-iii-deadline-failed");
          action = "Was erased by the command-core purge";
          result = {
            success: false,
            title: "The purge reaches Ren first.",
            copy: "Below 65% mastery, Residual Read cannot separate the live command core from Ren's own memory. Ordinary death ends this run.",
          };
        }
      }
      setRpg(
        takeRpgAction(
          rpg,
          action,
          {
            health,
            energy,
            location: "Tokyo Emergency Command",
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
        resolve("publish");
      else if (beat >= BEATS.length && event.code === "Digit2") resolve("core");
      else if (
        beat >= BEATS.length &&
        event.code === "Digit3" &&
        rpg?.timeline &&
        rpg.timeline >= 2
      )
        resolve(rpg.timeline === 3 ? "causal" : "vector");
    };
    window.addEventListener("keydown", key);
    return () => window.removeEventListener("keydown", key);
  }, [beat, outcome, resolve, rpg]);
  if (failed)
    return (
      <main className="game-loading">
        <p>COMMAND LINK OFFLINE</p>
        <h1>The Arc III record could not be verified.</h1>
        <Link href="/game">Return home</Link>
      </main>
    );
  if (!rpg)
    return (
      <main className="game-loading" aria-busy="true">
        <p>DAY 240 / FALSE ORDERS</p>
        <h1>Entering emergency command…</h1>
      </main>
    );
  const trusted = (rpg.bonds["Daichi Mori"] ?? 0) >= 2,
    mastery = rpg.skillMastery["Residual Read"] ?? 0,
    vector = rpg.skillMastery["Vector Step"] ?? 0,
    causal = rpg.skillMastery["Causal Sever"] ?? 0,
    priorEvidence = rpg.completedEvents.includes("arc-ii-evidence"),
    current = BEATS[Math.min(beat, BEATS.length - 1)];
  return (
    <main
      className="deadline-cutscene arc-three-deadline"
      aria-label="Arc III Tokyo's False Orders deadline"
    >
      <Image
        className="deadline-bg"
        src="/game/cutscenes/tokyo-day240-false-orders-v1.png"
        alt="Compromised underground Tokyo emergency command concourse"
        fill
        sizes="100vw"
        priority
      />
      <div className="deadline-shade" aria-hidden="true" />
      <Image
        className="deadline-ren"
        src="/game/visual-novel/ren-full.png"
        alt="Ren Takahashi facing the command purge"
        width={1024}
        height={1536}
        priority
      />
      <Image
        className="deadline-aiko"
        src="/game/visual-novel/daichi-full.png"
        alt="Daichi Mori holding the authenticated dispatch record"
        width={1024}
        height={1536}
        priority
      />
      <header className="deadline-caption">
        <span>
          ARC III DEADLINE / TIMELINE {rpg.timeline} / DAY {rpg.day}
        </span>
        <b>TOKYO'S FALSE ORDERS</b>
        <small>
          {priorEvidence ? "ADACHI CHAIN SECURED" : "ADACHI CHAIN MISSING"} ·
          DAICHI BOND {rpg.bonds["Daichi Mori"] ?? 0} · RR {mastery}%
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
            className={`deadline-result ${outcome.success ? "success" : "failure"}`}
          >
            <small>
              {rpg.status === "game-over" ? "GAME OVER" : "ARC III RESOLVED"}
            </small>
            <h1>{outcome.title}</h1>
            <p>{outcome.copy}</p>
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
                <dd>{rpg.status === "game-over" ? "RETRY" : "ARC IV"}</dd>
              </div>
            </dl>
            <Link href="/game">
              {rpg.status === "game-over"
                ? "FACE THE CONSEQUENCE"
                : "CONTINUE TO THE BLACK GATE"}
            </Link>
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
            <small>IRREVERSIBLE DECISION</small>
            <h1>Ninety seconds before the record disappears.</h1>
            <p>
              Evidence and trust were earned before the purge. Mastery decides
              whether Ren can survive reading it directly.
            </p>
            <div>
              <button onClick={() => resolve("publish")}>
                <b>1</b>
                <span>PUBLISH THROUGH DAICHI</span>
                <small>
                  {priorEvidence && trusted
                    ? "CHAIN + BOND READY · EXPOSE ORDERS"
                    : "CHAIN OR BOND MISSING · COVER-UP"}
                </small>
              </button>
              <button onClick={() => resolve("core")}>
                <b>2</b>
                <span>READ THE LIVE COMMAND CORE</span>
                <small>
                  {mastery >= 65
                    ? "65% MASTERY READY · SEVERE COST"
                    : "65% MASTERY REQUIRED · LETHAL"}
                </small>
              </button>
              {rpg.timeline >= 2 && (
                <button disabled={rpg.timeline === 3 ? causal < 85 : vector < 80} onClick={() => resolve(rpg.timeline === 3 ? "causal" : "vector")}>
                  <b>3</b>
                  <span>{rpg.timeline === 3 ? "SEVER THE FORGERY FROM COMMAND" : "STEP THE PROOF BEYOND THE PURGE"}</span>
                  <small>
                    {rpg.timeline === 3 ? (causal >= 85 ? "CS 85% · RESTORE TRUE COMMAND" : "CAUSAL SEVER 85% REQUIRED") : vector >= 80 ? "VS 80% · PRESERVE PROOF + TRUST" : "VECTOR STEP 80% REQUIRED"}
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
