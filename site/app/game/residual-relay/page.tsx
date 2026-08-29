"use client";

import Image from "next/image";
import Link from "next/link";
import { useEffect, useState } from "react";
import { verifyArtifacts } from "../../observer-data";
import {
  loadRpgState,
  remainingDaySlots,
  takeRpgAction,
  type RpgState,
} from "../game-state";
import { GameHud } from "../game-hud";
import { applyGamePreferences, loadGamePreferences } from "../game-preferences";

const DRAW_RESULTS = [
  {
    title: "VECTOR CALIBRATION FILM",
    copy: "An obsolete motion-analysis reel maps cleanly onto Vector Step.",
    mastery: 20,
    money: 0,
    energy: 0,
  },
  {
    title: "GUILD RELIEF VOUCHER",
    copy: "The ticket resolves into emergency field funding.",
    mastery: 0,
    money: 5000,
    energy: 0,
  },
  {
    title: "MEDICAL PRIORITY CHIT",
    copy: "An unused airport clinic allocation restores Ren before the next relay pass.",
    mastery: 0,
    money: 0,
    energy: 24,
  },
] as const;

export default function ResidualRelayPage() {
  const [rpg, setRpg] = useState<RpgState | null>(null);
  const [failed, setFailed] = useState(false);
  const [result, setResult] = useState<{ title: string; copy: string } | null>(
    null,
  );
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
        if (save.timeline < 2) window.location.replace("/game/city");
        else if (!controller.signal.aborted) setRpg(save);
      } catch (error) {
        if (!(error instanceof DOMException && error.name === "AbortError"))
          setFailed(true);
      }
    }
    void load();
    return () => controller.abort();
  }, []);
  if (failed)
    return (
      <main className="game-loading">
        <p>RELAY OFFLINE</p>
        <h1>The second-timeline signal could not be verified.</h1>
        <Link href="/game/city">Return to Tokyo</Link>
      </main>
    );
  if (!rpg)
    return (
      <main className="game-loading" aria-busy="true">
        <p>SECOND-TIMELINE ROUTE</p>
        <h1>Tuning the Haneda relay…</h1>
      </main>
    );

  const finalTimeline = rpg.timeline === 3;
  const activeSkill = finalTimeline ? "Causal Sever" : "Vector Step";
  const mastery = rpg.skillMastery[activeSkill] ?? 0;
  const signalEvent = finalTimeline
    ? "causal-spine-mapped"
    : "busan-signal-decoded";
  const anchorEvent = finalTimeline
    ? "severance-key-complete"
    : "residual-anchor-complete";
  const signalDecoded = rpg.completedEvents.includes(signalEvent);
  const anchorBuilt = rpg.completedEvents.includes(anchorEvent);
  const strongestBond = Math.max(0, ...Object.values(rpg.bonds));
  function train() {
    const nextMastery = Math.min(100, mastery + 12);
    setRpg(
      takeRpgAction(rpg!, `Trained ${activeSkill} at the residual relay`, {
        energy: rpg!.energy - 10,
        location: "Haneda Residual Relay",
        skillMastery: { ...rpg!.skillMastery, [activeSkill]: nextMastery },
      }),
    );
    setResult({
      title: `${activeSkill.toUpperCase()} ${nextMastery}%`,
      copy: finalTimeline
        ? "Ren isolates one harmless cause at a time, learning to cut consequence without erasing the life around it."
        : "Ren repeats the remembered fracture path until displacement becomes deliberate instead of reflexive.",
    });
  }
  function drawLottery() {
    const draw =
      DRAW_RESULTS[
        (rpg!.day * 31 + rpg!.attempt * 17 + rpg!.turns) % DRAW_RESULTS.length
      ];
    setRpg(
      takeRpgAction(rpg!, `Redeemed lottery ticket: ${draw.title}`, {
        lotteryTickets: rpg!.lotteryTickets - 1,
        money: rpg!.money + draw.money,
        energy: rpg!.energy + draw.energy,
        location: "Haneda Residual Relay",
        skillMastery: {
          ...rpg!.skillMastery,
          [activeSkill]: Math.min(100, mastery + draw.mastery),
        },
      }),
    );
    setResult({ title: draw.title, copy: draw.copy });
  }
  function decodeSignal() {
    const completedEvents = [
      ...new Set([...rpg!.completedEvents, signalEvent]),
    ];
    setRpg(
      takeRpgAction(
        rpg!,
        finalTimeline
          ? "Mapped the Black Gate causal spine"
          : "Decoded the Busan residual signal",
        {
          energy: rpg!.energy - 18,
          location: "Haneda Residual Relay",
          completedEvents,
        },
      ),
    );
    setResult(
      finalTimeline
        ? {
            title: "CAUSAL SPINE MAPPED",
            copy: "Every yearly disaster converges on one load-bearing cause inside the Black Gate. Ren finally knows what must be cut.",
          }
        : {
            title: "BUSAN SIGNAL DECODED",
            copy: "The overseas pulse is not an echo from this year. It is a reply to a message Ren has not sent yet.",
          },
    );
  }
  function buildAnchor() {
    const completedEvents = [
      ...new Set([...rpg!.completedEvents, anchorEvent]),
    ];
    setRpg(
      takeRpgAction(
        rpg!,
        finalTimeline
          ? "Forged the severance key with a willing ally"
          : "Constructed the residual anchor with a willing ally",
        {
          energy: rpg!.energy - 25,
          location: "Haneda Residual Relay",
          completedEvents,
        },
        remainingDaySlots(rpg!),
      ),
    );
    setResult(
      finalTimeline
        ? {
            title: "SEVERANCE KEY COMPLETE",
            copy: "A trusted witness binds Ren to the world while Causal Sever targets the Gate's single fatal cause.",
          }
        : {
            title: "RESIDUAL ANCHOR COMPLETE",
            copy: "A trusted voice, the decoded overseas reply, and mastered movement now hold the second path in place.",
          },
    );
  }
  return (
    <main className="relay-shell">
      <Image
        className="relay-bg"
        src="/game/locations/haneda-residual-relay-v1.png"
        alt="Abandoned Haneda rooftop communications relay before dawn"
        fill
        sizes="100vw"
        priority
      />
      <div className="relay-shade" aria-hidden="true" />
      <Image
        className="relay-ren"
        src="/game/visual-novel/ren-full.png"
        alt="Ren Takahashi inside the residual relay"
        width={1024}
        height={1536}
        priority
      />
      <GameHud state={rpg} current="relay" />
      <section className="relay-copy">
        <small>TIMELINE {rpg.timeline} / HANEDA AIRPORT PERIMETER</small>
        <h1>The Residual Relay.</h1>
        <p>{finalTimeline ? "The relay now exposes the Black Gate's causal spine. This is Ren's last year, and there is no fourth path." : "This room was dead in the first year. Ren now remembers which frequency wakes it—and the overseas answer waiting beyond Tokyo."}</p>
      </section>
      <section className="relay-panel" aria-label={`${finalTimeline ? "Final" : "Second"}-timeline preparation`}>
        <div className="relay-status">
          <div>
            <small>{activeSkill.toUpperCase()}</small>
            <b>{mastery}%</b>
          </div>
          <div>
            <small>LOTTERY</small>
            <b>
              {rpg.lotteryTickets} TICKET{rpg.lotteryTickets === 1 ? "" : "S"}
            </b>
          </div>
          <div>
            <small>{finalTimeline ? "CAUSAL SPINE" : "BUSAN"}</small>
            <b>{signalDecoded ? (finalTimeline ? "MAPPED" : "DECODED") : "LOCKED"}</b>
          </div>
          <div>
            <small>{finalTimeline ? "KEY BOND" : "ANCHOR BOND"}</small>
            <b>{strongestBond} / 6</b>
          </div>
        </div>
        <div className="relay-actions">
          <button disabled={mastery >= 100 || rpg.energy < 10} onClick={train}>
            <i>1</i>
            <b>TRAIN {activeSkill.toUpperCase()}</b>
            <small>1 SLOT · −10 EN · +12% MASTERY</small>
          </button>
          <button disabled={rpg.lotteryTickets < 1} onClick={drawLottery}>
            <i>2</i>
            <b>REDEEM LOOP LOTTERY TICKET</b>
            <small>1 SLOT · DETERMINISTIC DRAW · TICKET −1</small>
          </button>
          <button
            disabled={signalDecoded || mastery < 40 || rpg.energy < 18}
            onClick={decodeSignal}
          >
            <i>3</i>
            <b>{finalTimeline ? "MAP THE BLACK GATE CAUSAL SPINE" : "DECODE THE BUSAN SIGNAL"}</b>
            <small>
              {mastery >= 40 ? "1 SLOT · −18 EN" : `${activeSkill.toUpperCase()} 40% REQUIRED`}
            </small>
          </button>
          <button
            disabled={
              anchorBuilt ||
              !signalDecoded ||
              mastery < 100 ||
              strongestBond < 6 ||
              rpg.energy < 25
            }
            onClick={buildAnchor}
          >
            <i>4</i>
            <b>{finalTimeline ? "FORGE THE SEVERANCE KEY" : "BUILD THE RESIDUAL ANCHOR"}</b>
            <small>
              {signalDecoded && mastery >= 100 && strongestBond >= 6
                ? "REST OF DAY · −25 EN"
                : finalTimeline ? "SPINE · CS 100% · BOND 6 REQUIRED" : "BUSAN · VS 100% · BOND 6 REQUIRED"}
            </small>
          </button>
        </div>
        {result && (
          <div className="relay-result" aria-live="polite">
            <b>{result.title}</b>
            <p>{result.copy}</p>
          </div>
        )}
        <Link href="/game/city">← RETURN TO TOKYO</Link>
      </section>
    </main>
  );
}
