from __future__ import annotations

import argparse
import json
import sys

from . import __version__
from .journal import journal_entry
from .persistence import load_simulation, save_simulation
from .simulation import Simulation


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Observe an autonomous zero-rank life.")
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}",
    )
    parser.add_argument("--days", type=int, default=7, help="days to simulate (default: 7)")
    parser.add_argument("--seed", type=int, default=42, help="reproducible seed")
    parser.add_argument("--load", metavar="FILE", help="continue an existing save")
    parser.add_argument("--save", metavar="FILE", help="save after this run")
    parser.add_argument("--technical-log", action="store_true", help="show decision reasons")
    bundle_modes = parser.add_mutually_exclusive_group()
    bundle_modes.add_argument(
        "--inspect-experiment-bundle", metavar="DIR",
        help="verify a published experiment bundle and print JSON metadata",
    )
    bundle_modes.add_argument(
        "--compare-experiment-bundles", nargs=2, metavar=("LEFT", "RIGHT"),
        help="verify and compare two published experiment bundles",
    )
    bundle_modes.add_argument(
        "--inspect-comparison-artifact", metavar="FILE",
        help="verify saved comparison JSON and print it canonically",
    )
    parser.add_argument(
        "--comparison-output", metavar="FILE",
        help="save verified comparison JSON without overwriting",
    )
    parser.add_argument(
        "--require-identical", action="store_true",
        help="exit 1 when compared bundles differ",
    )
    return parser


def main(argv: tuple[str, ...] | None = None) -> None:
    parser = build_parser()
    arguments = tuple(sys.argv[1:] if argv is None else argv)
    args = parser.parse_args(arguments)
    if args.require_identical and not args.compare_experiment_bundles:
        parser.error("--require-identical requires --compare-experiment-bundles")
    if args.comparison_output and not args.compare_experiment_bundles:
        parser.error(
            "--comparison-output requires --compare-experiment-bundles")
    if (args.inspect_experiment_bundle or args.compare_experiment_bundles or
            args.inspect_comparison_artifact):
        mode_name = (
            "--inspect-experiment-bundle" if args.inspect_experiment_bundle
            else "--compare-experiment-bundles"
            if args.compare_experiment_bundles
            else "--inspect-comparison-artifact")
        simulation_options = (
            "--days", "--seed", "--load", "--save", "--technical-log",
        )
        if any(
                argument == option or argument.startswith(f"{option}=")
                for argument in arguments for option in simulation_options):
            parser.error(f"{mode_name} cannot use simulation options")
        from .learning import (
            compare_experiment_bundles, experiment_bundle_comparison_json,
            experiment_bundle_summary_json, inspect_experiment_bundle,
            load_experiment_bundle_comparison_artifact,
            save_experiment_bundle_comparison,
        )
        try:
            if args.inspect_experiment_bundle:
                result = inspect_experiment_bundle(
                    args.inspect_experiment_bundle)
                output = experiment_bundle_summary_json(result)
            elif args.inspect_comparison_artifact:
                result = load_experiment_bundle_comparison_artifact(
                    args.inspect_comparison_artifact)
                output = json.dumps(result, indent=2, sort_keys=True)
            else:
                result = compare_experiment_bundles(
                    *args.compare_experiment_bundles)
                output = experiment_bundle_comparison_json(result)
                if args.comparison_output:
                    save_experiment_bundle_comparison(
                        result, args.comparison_output)
        except (OSError, ValueError) as error:
            parser.error(str(error))
        print(output)
        if args.require_identical and not result.identical:
            raise SystemExit(1)
        return
    if args.days < 1:
        raise SystemExit("--days must be at least 1")

    if args.load:
        try:
            simulation = load_simulation(args.load)
        except (OSError, ValueError, KeyError, TypeError, AttributeError) as error:
            parser.error(f"Cannot load timeline: {error}")
    else:
        simulation = Simulation(seed=args.seed)
    protagonist = simulation.state.protagonist
    print("AWAKENED ZERO RANK — Ren's Chronicle")
    print(f"{protagonist.name} | {protagonist.location}\n")
    for _ in range(args.days * 4):
        event = simulation.step()
        print(event if args.technical_log else journal_entry(
            event, simulation.state.weather, simulation.state.temperature_c,
            simulation.state.protagonist.mood
        ))
        print()

    p = simulation.state.protagonist
    print("\nFinal state")
    print(
        f"Money: ¥{p.money:,} | Health: {p.health} | Energy: {p.energy} | "
        f"Hunger: {p.hunger} | Stress: {p.stress} | Knowledge: {p.knowledge} | "
        f"Fitness: {p.fitness} | Rank: {p.hunter_rank} ({p.rank_points} RP) | "
        f"Readiness: {p.combat_readiness} | Missions: {p.missions_completed}/{p.missions_attempted} | "
        f"Injuries: {p.injuries} (severity {p.injury_severity}/5) | Ability: {p.ability} | Location: {p.location} | "
        f"Rent arrears: ¥{p.rent_arrears:,}"
    )
    print(f"Mood: {p.mood} | Morale: {p.morale}/100 | Social confidence: {p.social_confidence}")
    print(
        f"Hunter attributes: STR {p.strength} | AGI {p.agility} | END {p.endurance} | "
        f"PER {p.perception} | MANA {p.mana} | LUCK {p.luck} | "
        f"Ability mastery {p.ability_mastery}/100 | Echo exposure {p.echo_fragments}"
    )
    inventory = ", ".join(f"{name} x{count}" for name, count in sorted(p.inventory.items())) or "empty"
    print(f"Equipment: {p.equipped_weapon or 'none'} / {p.equipped_armor or 'none'} | Inventory: {inventory}")
    print(f"Weather: {simulation.state.weather}, {simulation.state.temperature_c}°C | Season: {simulation.state.season}")
    print(f"Current goal: {p.current_goal}")
    if p.relationships:
        print("Relationships: " + "; ".join(
            f"{person.name} ({person.role}) trust {person.trust}, familiarity {person.familiarity}, "
            f"affection {person.affection}, tension {person.tension}, loyalty {person.loyalty}"
            for person in p.relationships.values()
        ))
    if simulation.state.discovered_portals:
        print("Portals discovered: " + ", ".join(simulation.state.discovered_portals))
    if p.memories:
        print("Key memories:")
        for memory in p.memories[:5]:
            print(f"- Day {memory.day}: {memory.summary}")
    if args.save:
        try:
            save_simulation(simulation, args.save)
        except OSError as error:
            parser.error(f"Cannot save timeline: {error}")
        print(f"\nTimeline saved to {args.save}")
