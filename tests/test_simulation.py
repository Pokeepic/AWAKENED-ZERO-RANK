from contextlib import redirect_stderr, redirect_stdout
from dataclasses import replace
import hashlib
from io import StringIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from awakened_zero_rank.actions import _shop, _shop_score, available_actions
from awakened_zero_rank.journal import journal_entry
from awakened_zero_rank.dialogue import (
    choose_intention, contextual_line, contextual_reaction, contextual_response,
    resolve_aiko_dialogue,
    resolve_contextual_encounter,
)
from awakened_zero_rank.models import DelayedConsequence, Relationship, TimeSlot
from awakened_zero_rank.environment import SEASON_WEATHER, season_for_day
from awakened_zero_rank.persistence import load_simulation, save_simulation
from awakened_zero_rank.simulation import Simulation
from awakened_zero_rank.world import ITEMS, gate_encounters_for_rank
from awakened_zero_rank.content import (
    NPCS, PORTALS, SEASONAL_EVENTS, STORY_ANCHORS, available_portals, dialogue_context_count, npc_context_count,
    portal_situation_count)
from awakened_zero_rank.cli import main as cli_main
from awakened_zero_rank.learning import (
    ACTION_NAMES, EVALUATION_CONDITIONS, EnsembleConfig, LearningEnvironment,
    QLearningConfig, TrainingEnvironment,
    _apply_training_rent_reserve, _frozen_policy_action,
    EvaluationScenario,
    abstract_state, assess_policy_adoption, audit_ensemble_similarity_coverage,
    audit_similarity_coverage, build_experiment_catalog,
    checkpoint_digest,
    compare_experiment_bundles, compare_utility_and_ensemble,
    compare_utility_and_rl, curriculum_reward,
    experiment_bundle_comparison_digest, experiment_bundle_comparison_json,
    experiment_bundle_summary_json,
    experiment_catalog_digest,
    experiment_catalog_report, inspect_experiment_bundle,
    diagnose_batch,
    diagnose_episode, diagnostics_report, ensemble_policy_action, heuristic_action,
    is_low_need_recovery, utility_action,
    evaluate_preparation_counterfactual,
    evaluate_repeated_trials, evaluate_scenario, evaluate_scenario_suite,
    load_checkpoint, load_experiment_bundle_comparison_artifact,
    load_experiment_catalog, load_scenario_suite_report,
    load_similarity_audit_report,
    save_checkpoint, save_experiment_bundle, save_experiment_catalog,
    save_scenario_suite_report, save_similarity_audit_report,
    nearest_action_neighbors,
    scenario_suite_digest, scenario_suite_report, similarity_audit_digest,
    similarity_audit_report, summarize_action_safety_groups,
    summarize_pooled_training_recurrence, summarize_pooled_training_slice,
    summarize_ensemble_evaluations,
    summarize_state_projection,
    summarize_training_actions, summarize_training_recurrence,
    summarize_training_depth,
    summarize_training_feature_slice, summarize_training_state_features,
    summarize_preparation_plan_contexts,
    summarize_training_conditions, summarize_training_preparation_blockers,
    summarize_training_progression,
    train_q_learning, verify_experiment_catalog,
)


class SimulationTests(unittest.TestCase):
    def test_cli_reports_package_version(self) -> None:
        output = StringIO()
        with redirect_stdout(output), self.assertRaises(SystemExit) as context:
            cli_main(("--version",))
        self.assertEqual(context.exception.code, 0)
        self.assertTrue(output.getvalue().strip().endswith(" 0.430.0"))

    def test_four_actions_advance_exactly_one_day(self) -> None:
        simulation = Simulation(seed=1)
        simulation.run(4)
        self.assertEqual(simulation.state.clock.day, 2)
        self.assertEqual(simulation.state.clock.slot, TimeSlot.MORNING)

    def test_same_seed_produces_identical_log(self) -> None:
        first = [str(event) for event in Simulation(seed=77).run(60)]
        second = [str(event) for event in Simulation(seed=77).run(60)]
        self.assertEqual(first, second)

    def test_simulation_preserves_stat_bounds(self) -> None:
        simulation = Simulation(seed=12)
        simulation.run(400)
        p = simulation.state.protagonist
        for value in (p.health, p.energy, p.hunger, p.stress):
            self.assertGreaterEqual(value, 0)
            self.assertLessEqual(value, 100)

    def test_every_event_explains_the_decision(self) -> None:
        events = Simulation(seed=3).run(20)
        self.assertTrue(all(event.reason for event in events))
        self.assertTrue(all("utility" in event.reason for event in events if "world event" not in event.reason))

    def test_awakening_occurs_at_bureau_on_day_three(self) -> None:
        simulation = Simulation(seed=3)
        events = simulation.run(10)
        p = simulation.state.protagonist
        self.assertEqual(events[-1].action, "Awakening assessment")
        self.assertEqual((p.hunter_rank, p.ability), ("F", "Threat Sense"))

    def test_guild_registration_unlocks_hunter_work(self) -> None:
        simulation = Simulation(seed=3)
        events = simulation.run(13)
        self.assertEqual(events[-1].action, "Guild registration")
        self.assertTrue(simulation.state.protagonist.guild_registered)

    def test_gate_missions_track_outcomes_and_injuries(self) -> None:
        simulation = Simulation(seed=42)
        events = simulation.run(80)
        p = simulation.state.protagonist
        self.assertTrue(any(event.action == "Gate mission" for event in events))
        self.assertEqual(p.missions_attempted, p.missions_completed + p.injuries)
        self.assertGreaterEqual(p.combat_experience, p.missions_attempted * 2)

    def test_successful_missions_can_promote_hunter(self) -> None:
        simulation = Simulation(seed=42)
        simulation.run(240)
        p = simulation.state.protagonist
        self.assertGreater(p.missions_completed, 0)
        if p.rank_points >= 30:
            self.assertNotEqual(p.hunter_rank, "F")

    def test_rent_deadline_is_resolved_once(self) -> None:
        simulation = Simulation(seed=9)
        events = simulation.run(29)
        self.assertEqual(sum(event.action == "Rent deadline" for event in events), 1)
        resolved = simulation.state.rent_payments + int(simulation.state.protagonist.rent_arrears > 0)
        self.assertEqual(resolved, 1)

    def test_money_never_becomes_negative(self) -> None:
        simulation = Simulation(seed=18)
        simulation.run(100)
        self.assertGreaterEqual(simulation.state.protagonist.money, 0)

    def test_recurring_character_is_introduced_at_registration(self) -> None:
        simulation = Simulation(seed=3)
        simulation.run(13)
        relationship = simulation.state.protagonist.relationships["Aiko Sato"]
        self.assertEqual(relationship.role, "F-rank guild clerk")
        self.assertGreater(relationship.familiarity, 0)

    def test_social_actions_develop_relationships(self) -> None:
        simulation = Simulation(seed=42)
        events = simulation.run(120)
        relationship = simulation.state.protagonist.relationships["Aiko Sato"]
        self.assertTrue(any(event.action == "Talk with Aiko" for event in events))
        self.assertGreater(relationship.meetings, 1)
        self.assertGreater(relationship.trust, 3)

    def test_important_memories_are_bounded_and_prioritized(self) -> None:
        simulation = Simulation(seed=42)
        simulation.run(240)
        memories = simulation.state.protagonist.memories
        self.assertLessEqual(len(memories), 12)
        self.assertTrue(any("Awakening assessment" in memory.summary for memory in memories))
        self.assertEqual(memories, sorted(memories, key=lambda memory: (-memory.importance, -memory.day)))

    def test_goal_changes_with_life_stage(self) -> None:
        simulation = Simulation(seed=3)
        simulation.run(13)
        self.assertIn("Rank E", simulation.state.protagonist.current_goal)

    def test_shop_purchases_and_equips_hunter_gear(self) -> None:
        simulation = Simulation(seed=42)
        events = simulation.run(160)
        p = simulation.state.protagonist
        self.assertTrue(any(event.action == "Visit hunter shop" for event in events))
        self.assertGreater(simulation.state.shop_visits, 0)
        self.assertIsNotNone(p.equipped_weapon)
        self.assertIn(p.equipped_weapon, ITEMS)

    def test_shop_stops_buying_consumables_at_field_stock_limit(self) -> None:
        simulation = Simulation(seed=43)
        p = simulation.state.protagonist
        p.money = 20_000
        p.equipped_weapon = "Field Knife"
        p.equipped_armor = "Padded Jacket"
        p.add_item("Healing Gel", 2)
        p.add_item("Energy Drink", 2)
        expected_money = p.money - 180

        outcome = _shop(p)

        self.assertIn("already carried the planned field stock", outcome)
        self.assertEqual(p.money, expected_money)
        self.assertEqual(p.item_count("Healing Gel"), 2)
        self.assertEqual(p.item_count("Energy Drink"), 2)

    def test_shop_score_replenishes_partial_field_stock(self) -> None:
        simulation = Simulation(seed=47)
        p = simulation.state.protagonist
        p.money = 20_000
        p.equipped_weapon = "Field Knife"
        p.equipped_armor = "Padded Jacket"
        p.health = 50
        p.add_item("Healing Gel")
        p.add_item("Energy Drink", 2)
        self.assertEqual(_shop_score(p, TimeSlot.MORNING, 0), 22)

        p.health = 100
        p.energy = 40
        p.add_item("Healing Gel")
        p.consume_item("Energy Drink")
        self.assertEqual(_shop_score(p, TimeSlot.MORNING, 0), 20)

    def test_shop_buys_energy_for_low_energy_before_surplus_gel(self) -> None:
        simulation = Simulation(seed=53)
        p = simulation.state.protagonist
        p.money = 20_000
        p.health = 100
        p.energy = 40
        p.equipped_weapon = "Field Knife"
        p.equipped_armor = "Padded Jacket"

        outcome = _shop(p)

        self.assertIn("Energy Drink", outcome)
        self.assertEqual(p.item_count("Energy Drink"), 1)
        self.assertEqual(p.item_count("Healing Gel"), 0)

    def test_shop_reserves_rank_e_upgrades_for_eligible_hunters(self) -> None:
        simulation = Simulation(seed=59)
        p = simulation.state.protagonist
        p.money = 30_000
        p.equipped_weapon = "Field Knife"
        p.equipped_armor = "Padded Jacket"
        p.add_item("Field Knife")
        p.add_item("Padded Jacket")
        p.add_item("Healing Gel", 2)
        p.add_item("Energy Drink", 2)

        self.assertLess(_shop_score(p, TimeSlot.MORNING, 0), 10)
        p.hunter_rank = "E"
        self.assertEqual(_shop_score(p, TimeSlot.MORNING, 0), 70)

        outcome = _shop(p)

        self.assertIn("Reinforced Machete", outcome)
        self.assertEqual(p.equipped_weapon, "Reinforced Machete")
        self.assertEqual(p.item_count("Field Knife"), 1)
        self.assertEqual(p.item_count("Reinforced Machete"), 1)

    def test_shop_blocks_upgrades_when_rent_is_at_risk(self) -> None:
        simulation = Simulation(seed=61)
        p = simulation.state.protagonist
        p.hunter_rank = "E"
        p.money = ITEMS["Reinforced Machete"].price + p.rent_cost - 1
        p.equipped_weapon = "Field Knife"
        p.equipped_armor = "Padded Jacket"
        p.add_item("Healing Gel", 2)
        p.add_item("Energy Drink", 2)
        p.add_item("Trauma Foam")
        p.add_item("Focus Ampoule")

        outcome = _shop(p)

        self.assertIn("already carried the planned field stock", outcome)
        self.assertEqual(p.equipped_weapon, "Field Knife")

    def test_shop_prioritizes_urgent_supplies_before_rank_e_upgrades(self) -> None:
        simulation = Simulation(seed=67)
        p = simulation.state.protagonist
        p.hunter_rank = "E"
        p.money = 30_000
        p.health = 50
        p.equipped_weapon = "Field Knife"
        p.equipped_armor = "Padded Jacket"

        outcome = _shop(p)

        self.assertIn("Healing Gel", outcome)
        self.assertEqual(p.equipped_weapon, "Field Knife")

    def test_rank_e_shop_prioritizes_emergency_supplies_when_severe(self) -> None:
        simulation = Simulation(seed=69)
        p = simulation.state.protagonist
        p.hunter_rank = "E"
        p.money = 30_000
        p.health = 40
        p.equipped_weapon = "Field Knife"
        p.equipped_armor = "Padded Jacket"

        outcome = _shop(p)

        self.assertIn("Trauma Foam", outcome)
        self.assertEqual(p.item_count("Trauma Foam"), 1)
        self.assertEqual(p.equipped_weapon, "Field Knife")

    def test_emergency_supply_stock_is_bounded_to_one_each(self) -> None:
        simulation = Simulation(seed=70)
        p = simulation.state.protagonist
        p.hunter_rank = "C"
        p.money = 100_000
        p.equipped_weapon = "Riftglass Katana"
        p.equipped_armor = "Aegis Longcoat"
        p.add_item("Healing Gel", 2)
        p.add_item("Energy Drink", 2)
        p.add_item("Trauma Foam")
        p.add_item("Focus Ampoule")

        outcome = _shop(p)

        self.assertIn("already carried the planned field stock", outcome)
        self.assertEqual(p.item_count("Trauma Foam"), 1)
        self.assertEqual(p.item_count("Focus Ampoule"), 1)

    def test_gate_mission_uses_advanced_supplies_before_starter_items(self) -> None:
        simulation = Simulation(seed=72)
        p = simulation.state.protagonist
        p.guild_registered = True
        p.hunter_rank = "E"
        p.health = 40
        p.energy = 25
        p.add_item("Trauma Foam")
        p.add_item("Focus Ampoule")
        p.add_item("Healing Gel")
        p.add_item("Energy Drink")

        outcome = simulation._resolve_gate_mission()

        self.assertIn("used Trauma Foam (+35 health)", outcome)
        self.assertIn("used Focus Ampoule (+30 energy)", outcome)
        self.assertEqual(p.item_count("Trauma Foam"), 0)
        self.assertEqual(p.item_count("Focus Ampoule"), 0)
        self.assertEqual(p.item_count("Healing Gel"), 1)
        self.assertEqual(p.item_count("Energy Drink"), 1)

    def test_rank_e_catalog_upgrades_have_stronger_typed_bonuses(self) -> None:
        machete = ITEMS["Reinforced Machete"]
        vest = ITEMS["Gateweave Vest"]
        self.assertEqual((machete.kind, machete.minimum_rank), ("weapon", "E"))
        self.assertEqual((vest.kind, vest.minimum_rank), ("armor", "E"))
        self.assertGreater(machete.combat_bonus, ITEMS["Field Knife"].combat_bonus)
        self.assertGreater(vest.combat_bonus, ITEMS["Padded Jacket"].combat_bonus)

    def test_rank_d_shop_advances_through_each_equipment_tier(self) -> None:
        simulation = Simulation(seed=71)
        p = simulation.state.protagonist
        p.hunter_rank = "D"
        p.money = 100_000
        p.equipped_weapon = "Field Knife"
        p.equipped_armor = "Padded Jacket"
        p.add_item("Field Knife")
        p.add_item("Padded Jacket")
        p.add_item("Healing Gel", 2)
        p.add_item("Energy Drink", 2)

        outcomes = [_shop(p) for _ in range(4)]

        self.assertTrue(all(name in outcome for name, outcome in zip(
            ("Reinforced Machete", "Gateweave Vest", "Mana-edge Saber", "Barrier Coat"),
            outcomes)))
        self.assertEqual(p.equipped_weapon, "Mana-edge Saber")
        self.assertEqual(p.equipped_armor, "Barrier Coat")
        self.assertEqual(p.item_count("Reinforced Machete"), 1)
        self.assertEqual(p.item_count("Gateweave Vest"), 1)
        self.assertEqual(ITEMS["Mana-edge Saber"].minimum_rank, "D")
        self.assertEqual(ITEMS["Barrier Coat"].minimum_rank, "D")

    def test_rank_c_shop_completes_the_full_equipment_ladder(self) -> None:
        simulation = Simulation(seed=73)
        p = simulation.state.protagonist
        p.hunter_rank = "C"
        p.money = 200_000
        p.equipped_weapon = "Field Knife"
        p.equipped_armor = "Padded Jacket"
        p.add_item("Field Knife")
        p.add_item("Padded Jacket")
        p.add_item("Healing Gel", 2)
        p.add_item("Energy Drink", 2)

        outcomes = [_shop(p) for _ in range(6)]

        expected = ("Reinforced Machete", "Gateweave Vest", "Mana-edge Saber",
                    "Barrier Coat", "Riftglass Katana", "Aegis Longcoat")
        self.assertTrue(all(name in outcome for name, outcome in zip(expected, outcomes)))
        self.assertEqual(p.equipped_weapon, "Riftglass Katana")
        self.assertEqual(p.equipped_armor, "Aegis Longcoat")
        bonuses = [ITEMS[name].combat_bonus for name in (
            "Field Knife", "Reinforced Machete", "Mana-edge Saber", "Riftglass Katana")]
        self.assertEqual(bonuses, sorted(bonuses))

    def test_equipment_increases_combat_readiness(self) -> None:
        simulation = Simulation(seed=1)
        p = simulation.state.protagonist
        baseline = p.combat_readiness
        p.equipped_weapon = "Field Knife"
        p.equipped_armor = "Padded Jacket"
        self.assertEqual(p.combat_readiness, min(100, baseline + 12))

    def test_gate_logs_name_a_specific_encounter(self) -> None:
        events = Simulation(seed=42).run(160)
        mission_logs = [event.outcome for event in events if event.action == "Gate mission"]
        self.assertTrue(mission_logs)
        self.assertTrue(any(encounter in outcome for outcome in mission_logs for encounter in (
            "Tunnel Slime Nest", "Goblin Scavenger Pack", "Armored Fang Boar"
        )))

    def test_gate_encounter_ladder_unlocks_one_rank_band_at_a_time(self) -> None:
        expected = {
            "F": ("Tunnel Slime Nest", "Goblin Scavenger Pack", "Armored Fang Boar"),
            "E": ("Tunnel Slime Nest", "Goblin Scavenger Pack", "Armored Fang Boar",
                  "Echo Wraith Corridor"),
            "D": ("Tunnel Slime Nest", "Goblin Scavenger Pack", "Armored Fang Boar",
                  "Echo Wraith Corridor", "Rift Hound Matriarch"),
            "C": ("Tunnel Slime Nest", "Goblin Scavenger Pack", "Armored Fang Boar",
                  "Echo Wraith Corridor", "Rift Hound Matriarch", "Mirror Oni Vanguard"),
        }
        for rank, names in expected.items():
            self.assertEqual(tuple(item.name for item in gate_encounters_for_rank(rank)), names)
        self.assertEqual(gate_encounters_for_rank("Unranked"),
                         gate_encounters_for_rank("F"))

    def test_consumables_are_used_and_removed_safely(self) -> None:
        simulation = Simulation(seed=4)
        p = simulation.state.protagonist
        p.guild_registered = True
        p.health = 40
        p.energy = 35
        p.add_item("Healing Gel")
        p.add_item("Energy Drink")
        simulation.state.gate_alert_level = 2
        outcome = simulation._resolve_gate_mission()
        self.assertIn("Healing Gel", outcome)
        self.assertIn("Energy Drink", outcome)
        self.assertEqual(p.item_count("Healing Gel"), 0)
        self.assertEqual(p.item_count("Energy Drink"), 0)

    def test_save_load_restores_complete_state(self) -> None:
        simulation = Simulation(seed=42)
        simulation.run(53)
        with TemporaryDirectory() as directory:
            path = Path(directory) / "ren.json"
            save_simulation(simulation, path)
            restored = load_simulation(path)
        self.assertEqual(restored.state, simulation.state)

    def test_legacy_save_defaults_prepared_mission_counters(self) -> None:
        simulation = Simulation(seed=27)
        with TemporaryDirectory() as directory:
            path = Path(directory) / "legacy.json"
            save_simulation(simulation, path)
            data = json.loads(path.read_text(encoding="utf-8"))
            protagonist = data["state"]["protagonist"]
            protagonist.pop("prepared_missions_attempted")
            protagonist.pop("prepared_missions_completed")
            data["save_version"] = 1
            data.pop("save_digest")
            path.write_text(json.dumps(data), encoding="utf-8")
            restored = load_simulation(path)
        self.assertEqual(restored.state.protagonist.prepared_missions_attempted, 0)
        self.assertEqual(restored.state.protagonist.prepared_missions_completed, 0)

    def test_loaded_timeline_has_identical_future(self) -> None:
        uninterrupted = Simulation(seed=77)
        interrupted = Simulation(seed=77)
        uninterrupted.run(41)
        interrupted.run(41)
        with TemporaryDirectory() as directory:
            path = Path(directory) / "ren.json"
            save_simulation(interrupted, path)
            resumed = load_simulation(path)
        expected = [str(event) for event in uninterrupted.run(40)]
        actual = [str(event) for event in resumed.run(40)]
        self.assertEqual(actual, expected)
        self.assertEqual(resumed.state, uninterrupted.state)

    def test_journal_focuses_on_protagonist_without_utility_report(self) -> None:
        event = Simulation(seed=3).step()
        entry = journal_entry(event)
        self.assertIn("Day 1", entry)
        self.assertIn(event.outcome, entry)
        self.assertNotIn("utility", entry.lower())

    def test_weather_is_generated_once_per_day(self) -> None:
        simulation = Simulation(seed=42)
        simulation.step()
        first = (simulation.state.weather, simulation.state.temperature_c)
        simulation.run(3)
        self.assertEqual(first, (simulation.state.weather, simulation.state.temperature_c))
        simulation.step()
        self.assertEqual(simulation.state.weather_day, 2)

    def test_weather_is_deterministic_and_saved(self) -> None:
        first = Simulation(seed=88)
        second = Simulation(seed=88)
        first.run(45)
        second.run(45)
        self.assertEqual(first.state.weather, second.state.weather)
        with TemporaryDirectory() as directory:
            path = Path(directory) / "weather.json"
            save_simulation(first, path)
            restored = load_simulation(path)
        self.assertEqual(restored.state, first.state)

    def test_seasons_follow_fixed_repeating_calendar_boundaries(self) -> None:
        expected = {
            1: "Summer", 91: "Summer", 92: "Autumn", 182: "Autumn",
            183: "Winter", 273: "Winter", 274: "Spring", 365: "Spring",
            366: "Summer", 457: "Autumn",
        }
        self.assertEqual({day: season_for_day(day) for day in expected}, expected)

    def test_every_season_has_distinct_canonical_weather(self) -> None:
        self.assertEqual(set(SEASON_WEATHER), {"Summer", "Autumn", "Winter", "Spring"})
        self.assertTrue(all(len(profile) == 5 for profile in SEASON_WEATHER.values()))
        self.assertEqual(
            {weather.name for weather in SEASON_WEATHER["Winter"]},
            {"Clear", "Cloudy", "Rain", "Snow", "Cold Snap"},
        )

    def test_simulation_crosses_all_seasons_deterministically(self) -> None:
        first, second = Simulation(seed=211), Simulation(seed=211)
        for day, season in ((92, "Autumn"), (183, "Winter"), (274, "Spring"), (366, "Summer")):
            steps = (day - first.state.clock.day) * 4
            first.run(steps)
            second.run(steps)
            first.step()
            second.step()
            self.assertEqual(first.state.season, season)
            self.assertEqual(
                (first.state.weather, first.state.temperature_c),
                (second.state.weather, second.state.temperature_c),
            )

    def test_severe_weather_changes_agent_preferences(self) -> None:
        simulation = Simulation(seed=2)
        p = simulation.state.protagonist
        p.energy = 70
        clear = simulation.agent._weather_adjustment("Train", "Clear")
        storm = simulation.agent._weather_adjustment("Train", "Thunderstorm")
        self.assertLess(storm, clear)

    def test_story_anchors_span_three_years_and_end(self) -> None:
        self.assertEqual(len(STORY_ANCHORS), 6)
        self.assertEqual(STORY_ANCHORS[0].day, 183)
        self.assertEqual(STORY_ANCHORS[-1].day, 1095)
        self.assertTrue(STORY_ANCHORS[-1].ending)
        self.assertTrue(all(
            later.day - earlier.day in {182, 183}
            for earlier, later in zip(STORY_ANCHORS, STORY_ANCHORS[1:])))

    def test_story_anchors_have_distinct_authored_outcomes_and_valid_focus(self) -> None:
        outcomes = [
            anchor.outcome(tier)
            for anchor in STORY_ANCHORS
            for tier in ("isolated", "resilient", "prepared")]
        self.assertEqual(len(outcomes), 18)
        self.assertEqual(len(set(outcomes)), 18)
        self.assertTrue(all(outcomes))
        self.assertTrue(all(
            anchor.focus_npcs and set(anchor.focus_npcs).issubset(NPCS)
            for anchor in STORY_ANCHORS))
        self.assertTrue(all(anchor.scene for anchor in STORY_ANCHORS))
        self.assertTrue(all(anchor.portal_consequence for anchor in STORY_ANCHORS))
        self.assertTrue(all(
            anchor.international_link for anchor in STORY_ANCHORS[1:]))

    def test_story_anchor_resolution_reflects_accumulated_readiness(self) -> None:
        isolated = Simulation(seed=89)
        isolated.state.clock.day = 183
        isolated_event = isolated.step()

        prepared = Simulation(seed=89)
        prepared.state.clock.day = 183
        prepared.state.protagonist.hunter_rank = "D"
        prepared.state.protagonist.relationships = {
            name: Relationship(name, profile.role, trust=20)
            for name, profile in list(NPCS.items())[:3]
        }
        prepared.state.discovered_portals = [portal.name for portal in PORTALS[:2]]
        prepared_event = prepared.step()

        self.assertEqual(isolated_event.action, "The Adachi Warning")
        self.assertIn("before Ren had anyone ready to believe him", isolated_event.outcome)
        self.assertIn("clear Adachi before the synchronized breach", prepared_event.outcome)
        self.assertIn("Trusted support: Aiko Sato, Daichi Mori", prepared_event.outcome)
        self.assertIn("Latest portal evidence: Ashen Shopping Arcade", prepared_event.outcome)
        self.assertIn("Scene: Aiko maps apartment residents", prepared_event.outcome)
        self.assertIn("Consequence: The newest portal record", prepared_event.outcome)
        self.assertIn("arc_adachi_warning", prepared.state.calendar_events_seen)

    def test_story_outcome_ledger_survives_save_load(self) -> None:
        simulation = Simulation(seed=97)
        simulation.run(35)
        simulation.state.clock.day = 183
        simulation.state.clock.slot = TimeSlot.MORNING
        simulation.step()
        with TemporaryDirectory() as directory:
            path = Path(directory) / "story.json"
            save_simulation(simulation, path)
            restored = load_simulation(path)

        self.assertEqual(
            restored.state.story_outcomes,
            {"arc_adachi_warning": "isolated"})

    def test_cli_reports_story_arc_progress(self) -> None:
        simulation = Simulation(seed=101)
        simulation.run(35)
        simulation.state.clock.day = 183
        simulation.state.clock.slot = TimeSlot.MORNING
        simulation.step()
        output = StringIO()
        with TemporaryDirectory() as directory:
            path = Path(directory) / "story.json"
            save_simulation(simulation, path)
            with redirect_stdout(output):
                cli_main(("--load", str(path), "--days", "1"))

        self.assertIn(
            "Story arc: 1/6 anchors | Latest: The Adachi Warning (isolated)",
            output.getvalue())

    def test_tanabata_calendar_event_occurs_once(self) -> None:
        simulation = Simulation(seed=42)
        events = simulation.run(32)
        self.assertEqual(sum(event.action == "Tanabata evening" for event in events), 1)
        self.assertIn("Tanabata", simulation.state.calendar_events_seen)
        self.assertIn("seasonal:1:tanabata", simulation.state.calendar_events_seen)

    def test_seasonal_catalog_matches_the_fixed_calendar(self) -> None:
        self.assertEqual(len(SEASONAL_EVENTS), 4)
        self.assertEqual(len({event.key for event in SEASONAL_EVENTS}), 4)
        self.assertEqual(
            [season_for_day(event.day_of_year) for event in SEASONAL_EVENTS],
            [event.season for event in SEASONAL_EVENTS])

    def test_authored_seasonal_event_changes_life_and_known_relationship(self) -> None:
        simulation = Simulation(seed=42)
        simulation.run(28)
        p = simulation.state.protagonist
        before_trust = p.relationships["Daichi Mori"].trust
        p.energy, p.stress, p.morale = 50, 50, 50
        simulation.state.clock.day = 137
        simulation.state.clock.slot = TimeSlot.EVENING

        event = simulation.step()

        self.assertEqual(event.action, "Tsukimi river watch")
        self.assertEqual((p.energy, p.stress, p.morale), (53, 45, 55))
        self.assertEqual(p.relationships["Daichi Mori"].trust, before_trust + 1)
        self.assertIn("seasonal:1:tsukimi", simulation.state.calendar_events_seen)

    def test_seasonal_events_repeat_once_per_year(self) -> None:
        simulation = Simulation(seed=42)
        simulation.run(28)
        simulation.state.clock.day = 372
        simulation.state.clock.slot = TimeSlot.EVENING

        first = simulation.step()
        simulation.state.clock.day = 372
        simulation.state.clock.slot = TimeSlot.EVENING
        second = simulation.step()

        self.assertEqual(first.action, "Tanabata evening")
        self.assertNotEqual(second.action, "Tanabata evening")
        self.assertEqual(
            simulation.state.calendar_events_seen.count("seasonal:2:tanabata"), 1)

    def test_gate_log_includes_environment(self) -> None:
        events = Simulation(seed=42).run(180)
        missions = [event.outcome for event in events if event.action == "Gate mission"]
        self.assertTrue(missions)
        self.assertTrue(all("weather" in outcome for outcome in missions))

    def test_training_rotates_hunter_attributes(self) -> None:
        simulation = Simulation(seed=1)
        p = simulation.state.protagonist
        p.health = p.energy = 100
        from awakened_zero_rank.actions import _train
        _train(p)
        _train(p)
        _train(p)
        self.assertEqual((p.strength, p.agility, p.endurance), (4, 5, 5))
        self.assertEqual(p.training_sessions, 3)

    def test_exhaustion_reduces_training_growth(self) -> None:
        simulation = Simulation(seed=1)
        p = simulation.state.protagonist
        p.health = p.energy = 20
        from awakened_zero_rank.actions import _train
        _train(p)
        self.assertEqual(p.fitness, 5)
        self.assertEqual(p.strength, 3)

    def test_gate_experience_develops_ability(self) -> None:
        simulation = Simulation(seed=42)
        simulation.run(160)
        p = simulation.state.protagonist
        self.assertGreater(p.ability_mastery, 1)
        self.assertGreater(p.echo_fragments, 0)

    def test_echo_fragment_unlocks_from_survival_exposure(self) -> None:
        simulation = Simulation(seed=42)
        events = simulation.run(160)
        p = simulation.state.protagonist
        self.assertIn("Echo Fragment", p.ability)
        self.assertTrue(any("Echo Fragment awakened" in event.outcome for event in events))

    def test_expanded_stats_survive_save_and_load(self) -> None:
        simulation = Simulation(seed=42)
        simulation.run(80)
        with TemporaryDirectory() as directory:
            path = Path(directory) / "growth.json"
            save_simulation(simulation, path)
            restored = load_simulation(path)
        self.assertEqual(restored.state.protagonist, simulation.state.protagonist)

    def test_dialogue_intention_responds_to_ren_condition(self) -> None:
        simulation = Simulation(seed=1)
        p = simulation.state.protagonist
        relationship = Relationship("Aiko Sato", "F-rank guild clerk", trust=3, meetings=1)
        intention, reason = choose_intention(p, relationship)
        self.assertEqual(intention.name, "Ask for guidance")
        self.assertIn("survival", reason)
        p.health = 35
        intention, _ = choose_intention(p, relationship)
        self.assertEqual(intention.name, "Hide worry")

    def test_dialogue_shows_npc_reaction_and_changes_relationship(self) -> None:
        simulation = Simulation(seed=1)
        p = simulation.state.protagonist
        p.morale = 60
        p.relationships["Aiko Sato"] = Relationship("Aiko Sato", "F-rank guild clerk", trust=20,
                                                     familiarity=30, meetings=3)
        before = p.relationships["Aiko Sato"].trust
        exchange, _ = resolve_aiko_dialogue(p, day=5)
        self.assertEqual(exchange.intention, "Offer support")
        self.assertEqual(exchange.reaction, "quietly touched")
        self.assertGreater(p.relationships["Aiko Sato"].trust, before)
        self.assertGreater(p.relationships["Aiko Sato"].affection, 0)

    def test_hiding_injury_can_create_social_tension(self) -> None:
        simulation = Simulation(seed=1)
        p = simulation.state.protagonist
        p.health = 30
        p.relationships["Aiko Sato"] = Relationship("Aiko Sato", "F-rank guild clerk", trust=2)
        exchange, _ = resolve_aiko_dialogue(p, day=5)
        relationship = p.relationships["Aiko Sato"]
        self.assertEqual(exchange.reaction, "unconvinced")
        self.assertLess(relationship.trust, 2)
        self.assertGreater(relationship.tension, 0)

    def test_dialogue_history_is_bounded_and_saved(self) -> None:
        simulation = Simulation(seed=1)
        simulation.run(14)
        p = simulation.state.protagonist
        p.relationships["Aiko Sato"] = Relationship("Aiko Sato", "F-rank guild clerk", trust=20,
                                                     familiarity=30, meetings=3)
        for day in range(25):
            resolve_aiko_dialogue(p, day)
        self.assertEqual(len(p.dialogue_history), 20)
        with TemporaryDirectory() as directory:
            path = Path(directory) / "dialogue.json"
            save_simulation(simulation, path)
            restored = load_simulation(path)
        self.assertEqual(restored.state.protagonist, p)

    def test_journal_can_show_current_mood(self) -> None:
        event = Simulation(seed=3).step()
        entry = journal_entry(event, mood="Hopeful")
        self.assertIn("I feel hopeful.", entry)

    def test_content_system_scales_beyond_one_thousand_dialogue_states(self) -> None:
        self.assertGreaterEqual(dialogue_context_count(), 1_000)
        self.assertEqual(portal_situation_count(), 128)

    def test_portal_catalog_has_unique_authored_world_evidence(self) -> None:
        self.assertEqual(len(PORTALS), 8)
        self.assertEqual(len({portal.name for portal in PORTALS}), len(PORTALS))
        self.assertEqual(len({portal.hazard for portal in PORTALS}), len(PORTALS))
        self.assertEqual(len({portal.clue for portal in PORTALS}), len(PORTALS))
        self.assertEqual(
            len({portal.verified_consequence for portal in PORTALS}), len(PORTALS))
        self.assertEqual(
            len({portal.incomplete_consequence for portal in PORTALS}), len(PORTALS))
        self.assertEqual(
            {portal.consequence_focus for portal in PORTALS},
            {"survival", "stability", "discovery", "relationships"},
        )
        self.assertEqual(
            {portal.name for portal in PORTALS[-2:]},
            {"Kawasaki Floodgate Labyrinth", "Chiba Glasshouse Breach"},
        )
        self.assertEqual(available_portals(45), PORTALS[:6])
        self.assertEqual(available_portals(46), PORTALS)

    def test_fixed_seed_preparation_can_reach_every_portal_profile(self) -> None:
        prepared = set()
        for seed in range(100):
            simulation = Simulation(seed=seed)
            simulation.state.clock.day = 46
            outcome = simulation._prepare_portal()
            prepared.update(portal.name for portal in PORTALS if portal.name in outcome)
        self.assertEqual(prepared, {portal.name for portal in PORTALS})

    def test_verified_portal_aftermath_advances_its_world_focus(self) -> None:
        simulation = Simulation(seed=181)
        portal = PORTALS[-1]
        before = simulation.state.objective_scores[portal.consequence_focus]
        simulation._queue_portal_consequence(portal.name, verified=True)
        simulation.state.clock.day += 2

        outcome = simulation._resolve_due_consequence()

        self.assertIn(portal.verified_consequence, outcome)
        self.assertEqual(
            simulation.state.objective_scores[portal.consequence_focus], before + 3)

    def test_incomplete_portal_aftermath_harms_its_world_focus(self) -> None:
        simulation = Simulation(seed=191)
        portal = PORTALS[-2]
        before = simulation.state.objective_scores[portal.consequence_focus]
        simulation._queue_portal_consequence(portal.name, verified=False)
        simulation.state.clock.day += 2

        outcome = simulation._resolve_due_consequence()

        self.assertIn(portal.incomplete_consequence, outcome)
        self.assertEqual(
            simulation.state.objective_scores[portal.consequence_focus], before - 2)

    def test_mission_retreat_queues_an_incomplete_authored_aftermath(self) -> None:
        simulation = Simulation(seed=5)
        simulation.run(240)
        incomplete = [
            item for item in simulation.state.delayed_consequences
            if "incomplete" in item.description
        ]
        self.assertEqual(len(incomplete), 1)
        portal = next(item for item in PORTALS if item.name == incomplete[0].source)
        self.assertIn(portal.incomplete_consequence, incomplete[0].description)

    def test_learning_observation_and_action_mask_are_stable(self) -> None:
        environment = LearningEnvironment(seed=5)
        self.assertEqual(len(environment.observe()), 22)
        self.assertEqual(len(environment.action_mask()), len(ACTION_NAMES))
        self.assertEqual(sum(environment.action_mask()), len(environment.valid_actions))

    def test_learning_policy_can_select_a_valid_strategy(self) -> None:
        environment = LearningEnvironment(seed=5)
        transition = environment.step("Rest")
        self.assertEqual(transition.action, "Rest")
        self.assertIn("policy action", environment.simulation.state.events[-1].reason)
        self.assertIsInstance(transition.reward, float)

    def test_learning_environment_rejects_locked_actions(self) -> None:
        environment = LearningEnvironment(seed=5)
        with self.assertRaises(ValueError):
            environment.step("Gate mission")

    def test_baseline_adapter_remains_deterministic(self) -> None:
        first, second = LearningEnvironment(seed=19), LearningEnvironment(seed=19)
        a = [first.baseline_step() for _ in range(20)]
        b = [second.baseline_step() for _ in range(20)]
        self.assertEqual(a, b)

    def test_additional_recurring_characters_enter_ren_life(self) -> None:
        simulation = Simulation(seed=42)
        events = simulation.run(36)
        relationships = simulation.state.protagonist.relationships
        self.assertTrue({"Aiko Sato", "Daichi Mori", "Mei Kuroda", "Haruto Ishikawa"}
                        .issubset(relationships))
        self.assertTrue(any(event.action == "Meet Daichi Mori" for event in events))
        meeting = next(event for event in events if event.action == "Meet Daichi Mori")
        self.assertIn("Another person", journal_entry(meeting))
        self.assertTrue(any("Meet Daichi Mori" in memory.summary
                            for memory in simulation.state.protagonist.memories))

    def test_relationship_network_preserves_conflicting_loyalties(self) -> None:
        simulation = Simulation(seed=42)
        simulation.run(29)
        network = simulation.state.relationship_network
        self.assertGreater(network["Aiko Sato"]["Daichi Mori"], 0)
        self.assertLess(network["Aiko Sato"]["Mei Kuroda"], 0)

    def test_contextual_dialogue_uses_identity_and_trust(self) -> None:
        guarded = Relationship("Mei Kuroda", "independent portal researcher", trust=2)
        trusted = Relationship("Mei Kuroda", "independent portal researcher", trust=20)
        self.assertNotEqual(contextual_line("Mei Kuroda", "portal", guarded),
                            contextual_line("Mei Kuroda", "portal", trusted))

    def test_every_recurring_character_has_guarded_and_trusted_routine_voice(self) -> None:
        for name, profile in NPCS.items():
            guarded = Relationship(name, profile.role, trust=2)
            trusted = Relationship(name, profile.role, trust=20)
            self.assertNotEqual(
                contextual_line(name, "routine", guarded),
                contextual_line(name, "routine", trusted))

    def test_every_recurring_character_has_two_sided_contextual_voice(self) -> None:
        for name, profile in NPCS.items():
            guarded = Relationship(name, profile.role, trust=2)
            trusted = Relationship(name, profile.role, trust=20)
            for context in ("routine", "portal", "injury", "guild"):
                self.assertNotEqual(
                    contextual_line(name, context, guarded),
                    contextual_line(name, context, trusted))
                self.assertNotEqual(
                    contextual_response(name, context, guarded),
                    contextual_response(name, context, trusted))
                self.assertNotEqual(
                    contextual_reaction(name, context, guarded),
                    contextual_reaction(name, context, trusted))

    def test_recurring_characters_react_to_the_situation(self) -> None:
        for name, profile in NPCS.items():
            guarded = Relationship(name, profile.role, trust=2)
            trusted = Relationship(name, profile.role, trust=20)
            for relationship in (guarded, trusted):
                reactions = {
                    contextual_reaction(name, context, relationship)
                    for context in ("routine", "portal", "injury", "guild")
                }
                self.assertGreaterEqual(len(reactions), 3)

    def test_aiko_guild_voice_does_not_fall_back_to_routine(self) -> None:
        relationship = Relationship(
            "Aiko Sato", NPCS["Aiko Sato"].role, trust=20)
        self.assertNotEqual(
            contextual_line("Aiko Sato", "guild", relationship),
            contextual_line("Aiko Sato", "routine", relationship))
        self.assertNotEqual(
            contextual_response("Aiko Sato", "guild", relationship),
            contextual_response("Aiko Sato", "routine", relationship))

    def test_contextual_encounter_records_both_sides_and_reaction(self) -> None:
        simulation = Simulation(seed=173)
        p = simulation.state.protagonist
        p.relationships["Daichi Mori"] = Relationship(
            "Daichi Mori", NPCS["Daichi Mori"].role, trust=20)

        exchange = resolve_contextual_encounter(
            p, "Daichi Mori", "portal", day=12, trust_change=2)

        self.assertEqual(exchange.npc_name, "Daichi Mori")
        self.assertIn("outside line", exchange.ren_line)
        self.assertEqual(exchange.reaction, "approving")
        self.assertEqual(p.dialogue_history[-1], exchange)
        self.assertEqual(p.relationships["Daichi Mori"].trust, 22)

    def test_autonomous_schedule_encounter_enters_saved_dialogue_history(self) -> None:
        simulation = Simulation(seed=179)
        simulation.run(20)
        p = simulation.state.protagonist
        p.location = "Adachi Gate Zone"
        simulation._update_npc_schedules()

        outcome = simulation._scheduled_social_encounter("Guild patrol")

        self.assertIn("Ren answered", outcome)
        self.assertEqual(p.dialogue_history[-1].npc_name, "Daichi Mori")
        with TemporaryDirectory() as directory:
            path = Path(directory) / "recurring-dialogue.json"
            save_simulation(simulation, path)
            restored = load_simulation(path)
        self.assertEqual(
            restored.state.protagonist.dialogue_history,
            p.dialogue_history)

    def test_social_context_routes_authored_situations(self) -> None:
        simulation = Simulation(seed=181)
        p = simulation.state.protagonist
        p.location = "Adachi Gate Zone"
        self.assertEqual(simulation._social_context("Gate mission"), "portal")
        self.assertEqual(simulation._social_context("Guild patrol"), "guild")
        self.assertEqual(simulation._social_context("Study"), "routine")
        p.location = "Tokyo Hunter Guild"
        self.assertEqual(simulation._social_context("Study"), "guild")
        p.health = 40
        self.assertEqual(simulation._social_context("Gate mission"), "injury")

    def test_guild_patrol_uses_guild_specific_exchange(self) -> None:
        simulation = Simulation(seed=191)
        simulation.run(20)
        p = simulation.state.protagonist
        p.location = "Tokyo Hunter Guild"
        simulation.state.npc_locations["Aiko Sato"] = p.location

        outcome = simulation._scheduled_social_encounter("Guild patrol")

        self.assertIn("clean answers", outcome)
        self.assertEqual(p.dialogue_history[-1].intention, "Guild encounter")

    def test_gate_missions_discover_named_portals_and_clues(self) -> None:
        simulation = Simulation(seed=42)
        events = simulation.run(180)
        missions = [event.outcome for event in events if event.action == "Gate mission"]
        self.assertTrue(simulation.state.discovered_portals)
        self.assertTrue(any("Discovered" in outcome for outcome in missions))
        self.assertTrue(any("hazard:" in outcome for outcome in missions))

    def test_network_and_portal_discovery_survive_save_load(self) -> None:
        simulation = Simulation(seed=42)
        simulation.run(120)
        with TemporaryDirectory() as directory:
            path = Path(directory) / "social-world.json"
            save_simulation(simulation, path)
            restored = load_simulation(path)
        self.assertEqual(restored.state, simulation.state)

    def test_npc_content_scales_without_flat_line_dump(self) -> None:
        self.assertGreaterEqual(npc_context_count(), 4_000)

    def test_npc_schedules_change_with_time_and_weekly_day_off(self) -> None:
        from awakened_zero_rank.content import scheduled_location
        self.assertEqual(scheduled_location("Aiko Sato", "Morning", 6), "Tokyo Hunter Guild")
        self.assertEqual(scheduled_location("Aiko Sato", "Morning", 7),
                         "Asakusa Shrine District")

    def test_gate_work_creates_persistent_investigation_progress(self) -> None:
        simulation = Simulation(seed=42)
        simulation.run(180)
        self.assertTrue(simulation.state.portal_investigations)
        self.assertTrue(all(record.progress > 0 and record.clues_found
                            for record in simulation.state.portal_investigations.values()))

    def test_portal_decision_resolves_as_delayed_multi_character_consequence(self) -> None:
        simulation = Simulation(seed=42)
        events = simulation.run(220)
        consequences = [event for event in events
                        if "Delayed consequence:" in event.outcome]
        self.assertTrue(consequences)
        self.assertTrue(any("trust" in event.outcome for event in consequences))

    def test_investigation_consequence_does_not_consume_action_slot(self) -> None:
        simulation = Simulation(seed=163)
        p = simulation.state.protagonist
        p.relationships["Aiko Sato"] = Relationship(
            "Aiko Sato", NPCS["Aiko Sato"].role, trust=10)
        simulation.state.delayed_consequences.append(DelayedConsequence(
            due_day=1, source="Moonlit Cedar Path",
            people=("Aiko Sato",),
            description="Evidence was verified"))

        event = simulation.step("Rest")

        self.assertEqual(event.action, "Rest")
        self.assertEqual(simulation.state.clock.slot, TimeSlot.AFTERNOON)
        self.assertEqual(len(simulation.state.events), 1)
        self.assertIn("Delayed consequence: Evidence was verified", event.outcome)
        self.assertIn("Aiko Sato's trust rose", event.outcome)
        self.assertEqual(p.relationships["Aiko Sato"].trust, 12)
        self.assertTrue(simulation.state.delayed_consequences[0].resolved)

    def test_learning_action_executes_when_consequence_is_due(self) -> None:
        environment = LearningEnvironment(seed=167)
        environment.simulation.state.delayed_consequences.append(
            DelayedConsequence(
                due_day=1, source="Sunken Courtyard", people=(),
                description="An incomplete report reached the guild"))

        transition = environment.step("Rest")

        self.assertEqual(transition.action, "Rest")
        self.assertEqual(transition.resolved_action, "Rest")
        self.assertIn("Delayed consequence:", transition.event_outcome)
        self.assertEqual(
            environment.simulation.state.clock.slot, TimeSlot.AFTERNOON)

    def test_schedule_overlap_can_create_autonomous_social_encounter(self) -> None:
        simulation = Simulation(seed=42)
        events = simulation.run(160)
        self.assertTrue(any("chose to approach me" in event.outcome for event in events))
        self.assertTrue(simulation.state.social_encounters_seen)

    def test_investigations_schedules_and_consequences_survive_save(self) -> None:
        simulation = Simulation(seed=42)
        simulation.run(140)
        with TemporaryDirectory() as directory:
            path = Path(directory) / "milestone-12.json"
            save_simulation(simulation, path)
            restored = load_simulation(path)
        self.assertEqual(restored.state, simulation.state)

    def test_portal_preparation_is_hazard_aware_and_persistent(self) -> None:
        simulation = Simulation(seed=42)
        simulation.run(29)
        event = simulation.step("Prepare portal")
        plan = simulation.state.portal_investigations[simulation.state.active_portal_plan]
        self.assertIn(plan.preparation_strategy, {
            "thermal route kit", "sealed breathing kit", "escape-line mapping",
            "room-marking protocol", "trail-anchor protocol", "cinder protection",
        })
        self.assertGreater(plan.preparation_bonus, 0)
        self.assertIn("mission readiness", event.outcome)

    def test_prepared_gate_consumes_plan_and_records_cooperation(self) -> None:
        simulation = Simulation(seed=42)
        simulation.run(29)
        simulation.step("Prepare portal")
        portal_name = simulation.state.active_portal_plan
        ally = simulation.state.portal_investigations[portal_name].cooperating_npc
        p = simulation.state.protagonist
        attempts_before = p.prepared_missions_attempted
        prepared_before = p.prepared_missions_completed
        completed_before = p.missions_completed
        event = simulation.step("Gate mission")
        record = simulation.state.portal_investigations[portal_name]
        self.assertIsNone(simulation.state.active_portal_plan)
        self.assertEqual(p.prepared_missions_attempted, attempts_before + 1)
        self.assertEqual(p.prepared_missions_completed - prepared_before,
                         p.missions_completed - completed_before)
        self.assertEqual(record.preparation_strategy, "Used")
        self.assertEqual(record.joint_missions, int(ally is not None))
        if ally:
            self.assertIn(ally, event.outcome)

    def test_competing_objectives_change_scenario_scores(self) -> None:
        simulation = Simulation(seed=42)
        simulation.run(29)
        before = dict(simulation.state.objective_scores)
        simulation.step("Prepare portal")
        after = simulation.state.objective_scores
        self.assertNotEqual(after, before)
        self.assertTrue(after["discovery"] > before["discovery"] or
                        after["survival"] > before["survival"])

    def test_long_horizon_evaluation_is_deterministic(self) -> None:
        first = evaluate_scenario(seed=19, steps=120)
        second = evaluate_scenario(seed=19, steps=120)
        self.assertEqual(first, second)
        self.assertGreaterEqual(first.investigation_progress, 0)

    def test_milestone_13_state_survives_save_and_load(self) -> None:
        simulation = Simulation(seed=42)
        simulation.run(29)
        simulation.step("Prepare portal")
        self.assertIsNotNone(simulation.state.active_portal_plan)
        with TemporaryDirectory() as directory:
            path = Path(directory) / "milestone-13.json"
            save_simulation(simulation, path)
            restored = load_simulation(path)
        self.assertEqual(restored.state, simulation.state)

    def test_training_environment_uses_gymnasium_episode_contract(self) -> None:
        environment = TrainingEnvironment(seed=7, horizon=3)
        observation, info = environment.reset(seed=7)
        self.assertTrue(environment.observation_space.contains(observation))
        self.assertEqual(environment.action_space.n, len(ACTION_NAMES))
        self.assertEqual(len(info["action_mask"]), len(ACTION_NAMES))
        for step in range(3):
            action = next(i for i, valid in enumerate(info["action_mask"]) if valid)
            observation, reward, terminated, truncated, info = environment.step(action)
            self.assertIsInstance(reward, float)
            self.assertFalse(terminated)
            self.assertEqual(truncated, step == 2)
        with self.assertRaises(RuntimeError):
            environment.step(0)

    def test_training_reset_accepts_deterministic_condition_options(self) -> None:
        environment = TrainingEnvironment(seed=9, horizon=3)
        observation, info = environment.reset(
            seed=9, options={"condition": "compound_crisis"}
        )
        self.assertEqual(info["condition"], "compound_crisis")
        self.assertEqual(environment.simulation.state.protagonist.health, 42)
        self.assertTrue(environment.observation_space.contains(observation))
        with self.assertRaises(ValueError):
            environment.reset(options={"condition": "unknown"})

    def test_training_cycles_conditions_reproducibly(self) -> None:
        config = QLearningConfig(
            episodes=4, horizon=5, training_horizons=(3, 5),
            training_conditions=("standard", "compound_crisis"),
        )
        first = train_q_learning(109, config)
        second = train_q_learning(109, config)
        self.assertEqual(first, second)
        self.assertEqual(first.episode_conditions, (
            "standard", "standard", "compound_crisis", "compound_crisis",
        ))
        self.assertEqual(first.episode_horizons, (3, 5, 3, 5))
        self.assertEqual(set(zip(first.episode_conditions, first.episode_horizons)), {
            ("standard", 3), ("standard", 5),
            ("compound_crisis", 3), ("compound_crisis", 5),
        })
        with TemporaryDirectory() as directory:
            path = Path(directory) / "conditioned.json"
            save_checkpoint(first, path)
            self.assertEqual(load_checkpoint(path), first)
        with self.assertRaises(ValueError):
            QLearningConfig(training_horizons=(3, 0))
        with self.assertRaises(ValueError):
            QLearningConfig(training_horizons=(True,))
        with self.assertRaises(ValueError):
            QLearningConfig(training_conditions=())
        with self.assertRaises(ValueError):
            QLearningConfig(training_conditions=("unknown",))
        with self.assertRaises(ValueError):
            QLearningConfig(unseen_state_fallback="unknown")
        with self.assertRaises(ValueError):
            QLearningConfig(seen_recovery_utility_override=1)

    def test_training_replays_an_aligned_episode_seed_pool(self) -> None:
        config = QLearningConfig(
            episodes=8, horizon=4, training_horizons=(3, 4),
            training_conditions=("standard", "compound_crisis"),
            episode_seed_pool_size=4,
        )
        first = train_q_learning(127, config)
        second = train_q_learning(127, config)
        self.assertEqual(first, second)
        self.assertEqual(first.episode_seeds[:4], first.episode_seeds[4:])
        self.assertEqual(first.episode_conditions[:4], first.episode_conditions[4:])
        self.assertEqual(first.episode_horizons[:4], first.episode_horizons[4:])
        with self.assertRaises(ValueError):
            QLearningConfig(episode_seed_pool_size=True)
        with self.assertRaises(ValueError):
            QLearningConfig(episodes=4, episode_seed_pool_size=5)
        with self.assertRaises(ValueError):
            QLearningConfig(
                episodes=4, training_horizons=(3, 4),
                episode_seed_pool_size=3,
            )

    def test_training_condition_summary_is_auditable(self) -> None:
        trained = train_q_learning(113, QLearningConfig(
            episodes=4, horizon=4,
            training_conditions=("standard", "compound_crisis"),
        ))
        summaries = summarize_training_conditions(trained)
        self.assertEqual(tuple(item.condition for item in summaries),
                         ("standard", "compound_crisis"))
        self.assertEqual(tuple(item.episode_count for item in summaries), (2, 2))
        standard_rewards = trained.episode_rewards[::2]
        self.assertEqual(summaries[0].average_reward,
                         round(sum(standard_rewards) / 2, 3))
        self.assertEqual(summaries[0].average_training_reward,
                         round(sum(trained.training_rewards[::2]) / 2, 3))
        self.assertEqual(summaries[0].worst_reward,
                         round(min(standard_rewards), 3))
        standard_states = trained.episode_state_counts[::2]
        self.assertEqual(summaries[0].average_unique_states,
                         round(sum(standard_states) / 2, 3))
        self.assertEqual(summaries[0].minimum_unique_states,
                         min(standard_states))
        incomplete = replace(trained, episode_state_counts=())
        with self.assertRaises(ValueError):
            summarize_training_conditions(incomplete)

    def test_training_action_exposure_is_exact_and_auditable(self) -> None:
        trained = train_q_learning(127, QLearningConfig(episodes=3, horizon=8))
        exposures = summarize_training_actions(trained)
        self.assertEqual(tuple(item.action for item in exposures), ACTION_NAMES)
        self.assertEqual(sum(item.selection_count for item in exposures),
                         sum(sum(counts) for counts in trained.visit_table.values()))
        self.assertTrue(all(item.selection_count >= item.state_count
                            for item in exposures))
        self.assertAlmostEqual(sum(item.selection_share for item in exposures),
                               1.0, places=2)
        with self.assertRaises(ValueError):
            summarize_training_actions(replace(trained, visit_table={}))

    def test_training_recurrence_is_exact_and_auditable(self) -> None:
        trained = train_q_learning(128, QLearningConfig(episodes=3, horizon=8))
        summary = summarize_training_recurrence(trained)
        self.assertEqual(summary.state_count, len(trained.visit_table))
        self.assertEqual(
            summary.total_state_visits,
            sum(sum(counts) for counts in trained.visit_table.values()))
        self.assertEqual(
            summary.visited_state_count + summary.unvisited_state_count,
            summary.state_count)
        self.assertEqual(
            summary.singleton_state_count + summary.repeated_state_count,
            summary.visited_state_count)
        self.assertEqual(
            summary.singleton_state_action_pairs +
            summary.repeated_state_action_pairs,
            summary.visited_state_action_pairs)
        self.assertGreaterEqual(summary.maximum_state_visits, 1)
        self.assertGreaterEqual(summary.maximum_state_action_visits, 1)
        with self.assertRaises(ValueError):
            summarize_training_recurrence(replace(trained, visit_table={}))
        invalid = dict(trained.visit_table)
        state = next(iter(invalid))
        invalid[state] = [-1] + [0] * (len(ACTION_NAMES) - 1)
        with self.assertRaises(ValueError):
            summarize_training_recurrence(replace(trained, visit_table=invalid))

    def test_training_depth_summary_requires_replicated_matching_policies(self) -> None:
        trained = train_q_learning(149, QLearningConfig(episodes=3, horizon=8))
        replica = replace(trained, training_seed=150)
        summary = summarize_training_depth((trained, replica))
        recurrence = summarize_training_recurrence(trained)
        self.assertEqual(summary.training_seeds, (149, 150))
        self.assertEqual(summary.episodes_per_policy, 3)
        self.assertEqual(summary.total_selections, recurrence.total_state_visits * 2)
        self.assertEqual(summary.visited_state_evidence,
                         recurrence.visited_state_count * 2)
        with self.assertRaises(ValueError):
            summarize_training_depth((trained,))
        with self.assertRaises(ValueError):
            summarize_training_depth((trained, trained))
        mismatched = train_q_learning(151, QLearningConfig(episodes=2, horizon=8))
        with self.assertRaises(ValueError):
            summarize_training_depth((trained, mismatched))

    def test_pooled_training_recurrence_preserves_exact_states(self) -> None:
        trained = train_q_learning(134, QLearningConfig(episodes=3, horizon=8))
        replica = replace(trained, training_seed=135)
        summary = summarize_pooled_training_recurrence((trained, replica))
        recurrence = summarize_training_recurrence(trained)
        self.assertEqual(summary.training_seeds, (134, 135))
        self.assertEqual(summary.visited_state_count, recurrence.visited_state_count)
        self.assertEqual(summary.cross_run_state_count, summary.visited_state_count)
        self.assertEqual(summary.repeated_state_count, summary.visited_state_count)
        self.assertEqual(summary.conflicting_action_states, 0)
        state = next(state for state, counts in trained.visit_table.items()
                     if counts.count(max(counts)) == 1 and max(counts) > 0)
        conflicting_visits = {
            candidate: list(counts)
            for candidate, counts in trained.visit_table.items()
        }
        original = conflicting_visits[state]
        winner = original.index(max(original))
        replacement = (winner + 1) % len(ACTION_NAMES)
        conflicting_visits[state] = [0] * len(ACTION_NAMES)
        conflicting_visits[state][replacement] = sum(original)
        conflicting = replace(
            trained, training_seed=136, visit_table=conflicting_visits)
        conflict_summary = summarize_pooled_training_recurrence(
            (trained, conflicting))
        self.assertGreaterEqual(conflict_summary.conflicting_action_states, 1)
        with self.assertRaises(ValueError):
            summarize_pooled_training_recurrence((trained,))
        with self.assertRaises(ValueError):
            summarize_pooled_training_recurrence((trained, trained))
        mismatched = train_q_learning(137, QLearningConfig(episodes=2, horizon=8))
        with self.assertRaises(ValueError):
            summarize_pooled_training_recurrence((trained, mismatched))

    def test_pooled_training_slice_authenticates_episode_labels(self) -> None:
        trained = train_q_learning(138, QLearningConfig(
            episodes=2, horizon=8, training_conditions=("gate_crisis",)))
        replica = replace(trained, training_seed=139)
        summary = summarize_pooled_training_slice((trained, replica))
        self.assertEqual((summary.condition, summary.horizon), ("gate_crisis", 8))
        self.assertEqual(summary.recurrence.training_seeds, (138, 139))
        tampered = replace(replica, episode_conditions=("standard", "standard"))
        with self.assertRaises(ValueError):
            summarize_pooled_training_slice((trained, tampered))

    def test_training_state_feature_coverage_is_exact_and_auditable(self) -> None:
        trained = train_q_learning(131, QLearningConfig(episodes=3, horizon=8))
        coverage = summarize_training_state_features(trained)
        self.assertEqual(len(coverage), 16)
        self.assertEqual(tuple(item.state_index for item in coverage), tuple(range(16)))
        for item in coverage:
            self.assertEqual(sum(item.visited_state_counts), sum(
                sum(counts) > 0 for counts in trained.visit_table.values()))
            self.assertEqual(sum(item.selection_visit_counts), 24)
            self.assertEqual(item.constant, len(item.observed_categories) == 1)
        money = coverage[4]
        self.assertEqual(money.feature, "money")
        with self.assertRaises(ValueError):
            summarize_training_state_features(replace(trained, visit_table={}))

    def test_training_feature_slice_requires_single_authenticated_slice(self) -> None:
        config = QLearningConfig(
            episodes=2, horizon=8, training_conditions=("financial_pressure",))
        trained = train_q_learning(132, config)
        summary = summarize_training_feature_slice(trained)
        self.assertEqual((summary.condition, summary.horizon),
                         ("financial_pressure", 8))
        self.assertEqual(summary.episode_count, 2)
        self.assertEqual(summary.selection_visits, 16)
        self.assertTrue(all(len(item.observed_categories) <= 2
                            for item in summary.sparse_features))
        mixed = train_q_learning(133, QLearningConfig(
            episodes=2, horizon=8,
            training_conditions=("standard", "financial_pressure")))
        with self.assertRaises(ValueError):
            summarize_training_feature_slice(mixed)
        with self.assertRaises(ValueError):
            summarize_training_feature_slice(trained, max_categories=0)

    def test_state_projection_balances_recurrence_and_action_conflicts(self) -> None:
        trained = train_q_learning(130, QLearningConfig(episodes=3, horizon=8))
        exact = summarize_state_projection(trained, tuple(range(16)))
        projected = summarize_state_projection(
            trained, tuple(index for index in range(16) if index != 4))
        self.assertEqual(exact.original_visited_states, exact.projected_state_count)
        self.assertLessEqual(projected.projected_state_count, exact.projected_state_count)
        self.assertGreaterEqual(
            projected.projected_state_recurrence_share,
            exact.projected_state_recurrence_share)
        self.assertLessEqual(
            projected.conflicting_action_groups, projected.comparable_action_groups)
        with self.assertRaises(ValueError):
            summarize_state_projection(trained, (0, 1, 2))
        with self.assertRaises(ValueError):
            summarize_state_projection(trained, tuple(range(15)) + (14,))
        with self.assertRaises(ValueError):
            summarize_state_projection(replace(trained, visit_table={}), tuple(range(16)))

    def test_training_progression_coverage_is_exact_and_auditable(self) -> None:
        trained = train_q_learning(129, QLearningConfig(episodes=3, horizon=8))
        self.assertEqual(len(trained.episode_gate_priority_clear_steps), 3)
        self.assertEqual(len(trained.episode_preparation_priority_clear_steps), 3)
        self.assertEqual(len(trained.episode_preparation_ready_steps), 3)
        self.assertEqual(len(trained.episode_preparation_blocker_counts), 3)
        summarize_training_preparation_blockers(trained)
        summaries = summarize_training_progression(trained)
        self.assertEqual(tuple(item.action for item in summaries),
                         ("Gate mission", "Prepare portal"))
        self.assertTrue(all(item.selection_count <= item.priority_clear_steps
                            for item in summaries))
        measured = replace(
            trained,
            episode_gate_priority_clear_steps=(2, 1, 0),
            episode_gate_priority_clear_selections=(1, 1, 0),
            episode_preparation_priority_clear_steps=(0, 0, 0),
            episode_preparation_priority_clear_selections=(0, 0, 0),
            episode_preparation_ready_steps=(2, 1, 0),
            episode_preparation_blocker_counts=(
                (("urgent hunger", 2),), (("rent preparation", 1),), ()),
        )
        measured_summaries = summarize_training_progression(measured)
        self.assertEqual(measured_summaries[0].priority_clear_steps, 3)
        self.assertEqual(measured_summaries[0].selection_count, 2)
        self.assertEqual(measured_summaries[0].selection_rate, 0.667)
        self.assertIsNone(measured_summaries[1].selection_rate)
        self.assertEqual(
            summarize_training_preparation_blockers(measured),
            (("rent preparation", 1), ("urgent hunger", 2)))
        with self.assertRaises(ValueError):
            summarize_training_preparation_blockers(replace(
                measured, episode_preparation_blocker_counts=(
                    (("urgent hunger", 1),),
                    (("rent preparation", 1),), ())))
        with self.assertRaises(ValueError):
            summarize_training_progression(replace(
                trained, episode_gate_priority_clear_steps=()))
        with self.assertRaises(ValueError):
            summarize_training_progression(replace(
                trained, episode_gate_priority_clear_steps=(0, 2, 0),
                episode_gate_priority_clear_selections=(1, 0, 0)))

    def test_integer_actions_enforce_current_mask(self) -> None:
        environment = TrainingEnvironment(seed=5, horizon=4)
        _, info = environment.reset()
        locked_action = ACTION_NAMES.index("Gate mission")
        self.assertEqual(info["action_mask"][locked_action], 0)
        with self.assertRaises(ValueError):
            environment.step(locked_action)

    def test_tabular_q_learning_is_reproducible_at_small_scale(self) -> None:
        config = QLearningConfig(episodes=3, horizon=8)
        first = train_q_learning(training_seed=101, config=config)
        second = train_q_learning(training_seed=101, config=config)
        self.assertEqual(first, second)
        self.assertEqual(len(first.episode_rewards), 3)

    def test_training_visit_evidence_is_exact_and_reproducible(self) -> None:
        config = QLearningConfig(episodes=3, horizon=8)
        first = train_q_learning(103, config)
        second = train_q_learning(103, config)
        self.assertEqual(first.visit_table, second.visit_table)
        self.assertEqual(set(first.visit_table), set(first.q_table))
        self.assertTrue(all(len(counts) == len(ACTION_NAMES)
                            for counts in first.visit_table.values()))
        self.assertEqual(sum(sum(counts) for counts in first.visit_table.values()), 24)
        self.assertEqual(set(first.reward_table), set(first.q_table))
        self.assertEqual(
            round(sum(sum(rewards) for rewards in first.reward_table.values()), 3),
            round(sum(first.episode_rewards), 3))

    def test_preparation_returns_are_plan_bounded_and_reproducible(self) -> None:
        config = QLearningConfig(
            episodes=2, horizon=20, training_conditions=("gate_crisis",),
            progression_sampling_rate=1.0)
        first = train_q_learning(211, config)
        second = train_q_learning(211, config)
        self.assertEqual(first.preparation_return_samples,
                         second.preparation_return_samples)
        self.assertEqual(
            len(first.preparation_return_samples),
            sum(first.episode_portal_preparations))
        self.assertTrue(first.preparation_return_samples)
        self.assertTrue(all(sample.steps >= 1 and
                            len(sample.state) == 16
                            for sample in first.preparation_return_samples))
        self.assertEqual(first.preparation_plan_returns,
                         second.preparation_plan_returns)
        self.assertEqual(first.preparation_plan_contexts,
                         second.preparation_plan_contexts)
        self.assertEqual(len(first.preparation_plan_contexts),
                         len(first.preparation_plan_returns))
        self.assertTrue(all(context == ("gate_crisis", 20)
                            for context in first.preparation_plan_contexts))
        self.assertEqual(
            sum(sample.preparation_steps
                for sample in first.preparation_plan_returns),
            len(first.preparation_return_samples))
        self.assertTrue(all(sample.preparation_steps >= 1 and
                            sample.steps >= sample.preparation_steps and
                            len(sample.initial_state) == 16
                            for sample in first.preparation_plan_returns))
        summary = summarize_preparation_plan_contexts(first)
        self.assertEqual(len(summary), 1)
        self.assertEqual(
            (summary[0].condition, summary[0].horizon,
             summary[0].plan_count, summary[0].consumed_count,
             summary[0].positive_consumed_count, summary[0].censored_count),
            ("gate_crisis", 20, len(first.preparation_plan_returns),
             sum(sample.plan_consumed
                 for sample in first.preparation_plan_returns),
             sum(sample.plan_consumed and sample.discounted_return > 0
                 for sample in first.preparation_plan_returns),
             sum(not sample.plan_consumed
                 for sample in first.preparation_plan_returns)))
        with self.assertRaises(ValueError):
            summarize_preparation_plan_contexts(
                replace(first, preparation_plan_contexts=()))

    def test_one_step_discounted_returns_equal_realized_rewards(self) -> None:
        trained = train_q_learning(111, QLearningConfig(episodes=3, horizon=1))
        self.assertEqual(trained.discounted_return_table, trained.reward_table)
        self.assertEqual(set(trained.discounted_return_table), set(trained.q_table))

    def test_unseen_state_fallback_is_explicit_and_reproducible(self) -> None:
        trained = train_q_learning(101, QLearningConfig(episodes=1, horizon=2))
        empty = replace(trained, q_table={})
        historical = diagnose_episode(201, 1, "rl", empty)
        safe = replace(
            empty,
            config=replace(empty.config, unseen_state_fallback="heuristic"),
        )
        first = diagnose_episode(201, 1, "rl", safe)
        second = diagnose_episode(201, 1, "rl", safe)
        utility = replace(
            empty,
            config=replace(empty.config, unseen_state_fallback="utility"),
        )
        utility_first = diagnose_episode(201, 1, "rl", utility)
        utility_second = diagnose_episode(201, 1, "rl", utility)
        preventive = replace(
            empty, config=replace(empty.config, preventive_rest_threshold=100))
        preventive_episode = diagnose_episode(201, 1, "rl", preventive)
        injured = replace(
            safe, config=replace(safe.config, preventive_rest_threshold=100))
        injured_episode = diagnose_episode(
            201, 1, "rl", injured, condition="injury_recovery")
        self.assertEqual(historical.trace[0].action, "Eat")
        self.assertEqual(first.trace[0].action, "Part-time work")
        self.assertEqual(utility_first, utility_second)
        self.assertIn(utility_first.trace[0].action, LearningEnvironment(201).valid_actions)
        self.assertEqual(preventive_episode.trace[0].action, "Rest")
        self.assertEqual(preventive_episode.preventive_rest_override_count, 1)
        self.assertEqual(preventive_episode.preventive_rest_overrides[0].replaced_action,
                         "Eat")
        self.assertTrue(preventive_episode.preventive_rest_overrides[0].unseen_state)
        self.assertIsNone(
            preventive_episode.preventive_rest_overrides[0].replaced_action_q_advantage)
        seen_values = [0.0] * len(ACTION_NAMES)
        seen_values[ACTION_NAMES.index("Eat")] = 2.0
        seen_values[ACTION_NAMES.index("Rest")] = 0.5
        seen_state = abstract_state(LearningEnvironment(201).observe())
        seen = replace(
            preventive, q_table={seen_state: seen_values})
        seen_episode = diagnose_episode(201, 1, "rl", seen)
        seen_override = seen_episode.preventive_rest_overrides[0]
        self.assertFalse(seen_override.unseen_state)
        self.assertEqual(seen_episode.seen_state_decision_count, 1)
        self.assertIn(seen_episode.seen_utility_disagreement_count, (0, 1))
        self.assertEqual(
            seen_episode.seen_utility_disagreement_share,
            float(seen_episode.seen_utility_disagreement_count))
        self.assertEqual(len(seen_episode.seen_state_decision_outcomes), 1)
        seen_outcome = seen_episode.seen_state_decision_outcomes[0]
        self.assertEqual(seen_outcome.learned_action, "Eat")
        self.assertEqual(seen_outcome.selected_action, "Rest")
        self.assertEqual(seen_outcome.energy_before, 65)
        self.assertEqual(seen_outcome.energy_after, seen_episode.trace[0].energy)
        self.assertIn(seen_outcome.utility_action, ACTION_NAMES)
        self.assertEqual(seen_outcome.disagreed,
                         seen_outcome.learned_action != seen_outcome.utility_action)
        self.assertEqual(seen_outcome.reward, seen_episode.trace[0].reward)
        self.assertEqual(seen_outcome.reward_difference,
                         round(seen_outcome.reward - seen_outcome.utility_reward, 3))
        self.assertEqual(
            round(sum(dict(seen_outcome.reward_components).values()) -
                  sum(dict(seen_outcome.utility_reward_components).values()), 3),
            seen_outcome.reward_difference)
        self.assertEqual(seen_outcome.counterfactual_horizon, 4)
        self.assertEqual(
            seen_outcome.return_reward_difference,
            round(seen_outcome.return_reward - seen_outcome.utility_return_reward, 3))
        self.assertEqual(
            round(sum(dict(seen_outcome.return_reward_components).values()) -
                  sum(dict(seen_outcome.utility_return_reward_components).values()), 3),
            seen_outcome.return_reward_difference)
        self.assertEqual(seen_override.replaced_action_q_value, 2.0)
        self.assertEqual(seen_override.rest_q_value, 0.5)
        self.assertEqual(seen_override.replaced_action_q_advantage, 1.5)
        selective = replace(
            seen, config=replace(
                seen.config, preventive_rest_threshold=0,
                seen_recovery_utility_override=True))
        selective_first = diagnose_episode(201, 1, "rl", selective)
        selective_second = diagnose_episode(201, 1, "rl", selective)
        self.assertEqual(selective_first, selective_second)
        self.assertNotEqual(selective_first.trace[0].action, "Eat")
        self.assertEqual(selective_first.selective_recovery_override_count, 1)
        self.assertEqual(
            selective_first.selective_recovery_override_pairs,
            ((f"Eat -> {selective_first.trace[0].action}", 1),))
        urgent_environment = LearningEnvironment(201)
        urgent_environment.simulation.state.protagonist.hunger = 70
        urgent_state = abstract_state(urgent_environment.observe())
        urgent = replace(selective, q_table={urgent_state: seen_values})
        urgent_action = _frozen_policy_action(
            urgent, urgent_environment, urgent_environment.observe(),
            urgent_environment.action_mask())
        self.assertEqual(ACTION_NAMES[urgent_action[0]], "Eat")
        self.assertEqual(injured_episode.trace[0].action, "Seek treatment")
        self.assertEqual(injured_episode.preventive_rest_override_count, 0)
        self.assertEqual(first, second)
        self.assertEqual(first.unseen_state_count, 1)

    def test_return_evidence_ensemble_is_conservative_and_reproducible(self) -> None:
        trained = train_q_learning(140, QLearningConfig(episodes=2, horizon=8))
        environment = LearningEnvironment(300)
        state = abstract_state(environment.observe())
        mask = environment.action_mask()
        utility = utility_action(environment, mask)
        candidate = next(index for index, valid in enumerate(mask)
                         if valid and index != utility)
        visits = {key: list(values) for key, values in trained.visit_table.items()}
        returns = {
            key: list(values)
            for key, values in trained.discounted_return_table.items()
        }
        visits[state] = [0] * len(ACTION_NAMES)
        returns[state] = [0.0] * len(ACTION_NAMES)
        visits[state][utility] = visits[state][candidate] = 2
        returns[state][candidate] = 10.0
        evidenced = replace(
            trained, visit_table=visits, discounted_return_table=returns)
        policies = (evidenced, replace(evidenced, training_seed=141),
                    replace(evidenced, training_seed=142))
        action, overridden, advantage = ensemble_policy_action(
            policies, environment, environment.observe(), mask)
        self.assertEqual(action, candidate)
        self.assertTrue(overridden)
        self.assertEqual(advantage, 5.0)
        conservative = EnsembleConfig(minimum_return_advantage=6.0)
        action, overridden, advantage = ensemble_policy_action(
            policies, environment, environment.observe(), mask, conservative)
        self.assertEqual(action, utility)
        self.assertFalse(overridden)
        self.assertEqual(advantage, 5.0)
        blocked = EnsembleConfig(
            allowed_override_actions=(ACTION_NAMES[utility],))
        action, overridden, advantage = ensemble_policy_action(
            policies, environment, environment.observe(), mask, blocked)
        self.assertEqual(action, utility)
        self.assertFalse(overridden)
        self.assertEqual(advantage, 0.0)
        with self.assertRaises(ValueError):
            EnsembleConfig(allowed_override_actions=("Unknown",))
        guarded = EnsembleConfig(minimum_crisis_signals=1)
        action, overridden, _ = ensemble_policy_action(
            policies, environment, environment.observe(), mask, guarded)
        self.assertEqual(action, utility)
        self.assertFalse(overridden)
        environment.simulation.state.protagonist.rent_arrears = 1
        mask = environment.action_mask()
        crisis_utility = utility_action(environment, mask)
        self.assertNotEqual(crisis_utility, candidate)
        visits[state][crisis_utility] = 2
        returns[state][crisis_utility] = 0.0
        action, overridden, _ = ensemble_policy_action(
            policies, environment, environment.observe(), mask, guarded)
        self.assertEqual(action, candidate)
        self.assertTrue(overridden)
        with self.assertRaises(ValueError):
            EnsembleConfig(minimum_crisis_signals=8)
        first = compare_utility_and_ensemble(
            policies, (301, 302), horizon=4)
        second = compare_utility_and_ensemble(
            policies, (301, 302), horizon=4)
        self.assertEqual(first, second)
        self.assertGreaterEqual(first.override_count, 2)
        utility_only = compare_utility_and_ensemble(
            policies, (303, 304), horizon=8,
            config=EnsembleConfig(allowed_override_actions=()))
        self.assertEqual(utility_only.override_count, 0)
        self.assertEqual(utility_only.ensemble_rewards, utility_only.utility_rewards)
        self.assertEqual(
            utility_only.ensemble_survival_count,
            utility_only.utility_survival_count)
        self.assertEqual(
            utility_only.ensemble_mission_count,
            utility_only.utility_mission_count)
        with self.assertRaises(ValueError):
            EnsembleConfig(minimum_policy_support=1)
        with self.assertRaises(ValueError):
            compare_utility_and_ensemble(policies, (140,), horizon=4)

    def test_zero_override_ensemble_matches_utility_across_conditions(self) -> None:
        trained = train_q_learning(146, QLearningConfig(episodes=2, horizon=8))
        policies = (trained, replace(trained, training_seed=147),
                    replace(trained, training_seed=148))
        config = EnsembleConfig(allowed_override_actions=())
        for index, condition in enumerate(EVALUATION_CONDITIONS):
            comparison = compare_utility_and_ensemble(
                policies, (420 + index,), horizon=8,
                condition=condition, config=config)
            self.assertEqual(comparison.override_count, 0)
            self.assertEqual(
                comparison.ensemble_rewards, comparison.utility_rewards)
            self.assertEqual(
                comparison.ensemble_survival_count,
                comparison.utility_survival_count)
            self.assertEqual(
                comparison.ensemble_mission_count,
                comparison.utility_mission_count)

    def test_ensemble_evaluation_summary_is_conservative_and_auditable(self) -> None:
        trained = train_q_learning(143, QLearningConfig(episodes=2, horizon=8))
        policies = (trained, replace(trained, training_seed=144),
                    replace(trained, training_seed=145))
        first = compare_utility_and_ensemble(policies, (401, 402), horizon=4)
        second = compare_utility_and_ensemble(policies, (403, 404), horizon=4)
        summary = summarize_ensemble_evaluations((first, second))
        self.assertEqual(summary.total_episodes, 4)
        self.assertEqual(summary.training_seeds, (143, 144, 145))
        self.assertEqual(summary.override_count, first.override_count + second.override_count)
        self.assertEqual(summary.adoption_ready, not summary.blockers)
        with self.assertRaises(ValueError):
            summarize_ensemble_evaluations(())
        with self.assertRaises(ValueError):
            summarize_ensemble_evaluations((first, first))
    def test_batch_comparison_uses_held_out_seeds_and_honest_verdict(self) -> None:
        trained = train_q_learning(101, QLearningConfig(episodes=2, horizon=6))
        comparison = compare_utility_and_rl(trained, (201, 202, 203), horizon=6)
        self.assertEqual(comparison.evaluation_seeds, (201, 202, 203))
        self.assertIn(comparison.verdict,
                      {"promising", "inconclusive", "baseline remains better"})
        with self.assertRaises(ValueError):
            compare_utility_and_rl(trained, (101,), horizon=6)

    def test_reward_components_reconcile_with_transition_total(self) -> None:
        transition = LearningEnvironment(seed=5).step("Rest")
        self.assertEqual(tuple(name for name, _ in transition.reward_components),
                         ("survival", "stability", "progress", "social"))
        self.assertAlmostEqual(transition.reward,
                               sum(value for _, value in transition.reward_components), places=3)

    def test_low_need_recovery_thresholds_preserve_real_need(self) -> None:
        protagonist = Simulation(seed=5).state.protagonist
        protagonist.health, protagonist.hunger = 80, 20
        protagonist.energy, protagonist.stress, protagonist.injury_severity = 80, 20, 0
        self.assertTrue(is_low_need_recovery("Eat", protagonist, TimeSlot.MORNING))
        self.assertTrue(is_low_need_recovery("Rest", protagonist, TimeSlot.MORNING))
        protagonist.hunger = 70
        self.assertFalse(is_low_need_recovery("Eat", protagonist, TimeSlot.MORNING))
        protagonist.health, protagonist.hunger = 50, 20
        self.assertFalse(is_low_need_recovery("Eat", protagonist, TimeSlot.MORNING))
        protagonist.energy = 30
        self.assertFalse(is_low_need_recovery("Rest", protagonist, TimeSlot.MORNING))
        protagonist.energy, protagonist.stress = 80, 60
        self.assertFalse(is_low_need_recovery("Rest", protagonist, TimeSlot.MORNING))
        protagonist.stress = 20
        protagonist.energy, protagonist.injury_severity = 80, 2
        self.assertFalse(is_low_need_recovery("Rest", protagonist, TimeSlot.MORNING))
        protagonist.injury_severity = 0
        self.assertFalse(is_low_need_recovery("Rest", protagonist, TimeSlot.LATE_NIGHT))
        self.assertFalse(is_low_need_recovery("Study", protagonist, TimeSlot.MORNING))

    def test_preparation_counterfactual_is_paired_and_reproducible(self) -> None:
        first = evaluate_preparation_counterfactual(211)
        second = evaluate_preparation_counterfactual(211)
        self.assertEqual(first, second)
        self.assertTrue(first.portal)
        self.assertGreater(first.preparation_bonus, 0)
        self.assertGreaterEqual(first.prepared_rank_points, first.unprepared_rank_points)
        self.assertGreaterEqual(first.prepared_money_delta, first.unprepared_money_delta)

    def test_episode_diagnostics_count_actions_masks_and_outcomes(self) -> None:
        trained = train_q_learning(101, QLearningConfig(episodes=2, horizon=6))
        episode = diagnose_episode(201, 6, "rl", trained)
        self.assertEqual(sum(count for _, count in episode.action_counts), episode.steps)
        self.assertEqual(len(episode.trace), episode.steps)
        self.assertLessEqual(episode.decision_steps, episode.steps)
        self.assertTrue(all(0 <= count <= episode.steps for _, count in episode.masked_counts))
        utility = diagnose_episode(201, 12, "utility")
        self.assertEqual(sum(count for _, count in utility.action_counts), utility.steps)
        self.assertAlmostEqual(episode.total_reward,
                               sum(value for _, value in episode.reward_components), places=3)
        self.assertTrue(all(0 <= value <= 100 for value in (
            episode.end_health, episode.end_energy, episode.end_hunger,
            episode.end_stress)))
        self.assertTrue(all(0 <= value <= episode.steps for value in (
            episode.critical_energy_steps, episode.high_hunger_steps,
            episode.high_stress_steps)))
        self.assertTrue(all(
            entry.energy_before > 25 and entry.energy_after <= 25
            for entry in episode.critical_energy_entries))
        self.assertTrue(all(0 <= value <= 1 for value in (
            episode.critical_energy_share, episode.high_hunger_share,
            episode.high_stress_share)))
        self.assertEqual(len(episode.mission_outcomes), episode.missions_attempted)
        self.assertEqual(sum(item.completed for item in episode.mission_outcomes),
                         episode.missions_completed)
        self.assertEqual(sum(item.prepared for item in episode.mission_outcomes),
                         episode.prepared_missions_attempted)
        self.assertEqual(sum(item.completed for item in episode.mission_outcomes
                             if item.prepared),
                         episode.prepared_missions_completed)
        self.assertEqual(episode.critical_energy_decision_steps,
                         sum(count for _, count in episode.critical_energy_action_counts))
        self.assertGreaterEqual(episode.critical_energy_rest_count, 0)
        self.assertGreaterEqual(episode.critical_energy_rest_share, 0)
        self.assertLessEqual(episode.critical_energy_rest_share, 1)
        self.assertEqual(episode.strained_energy_decision_steps,
                         sum(count for _, count in episode.strained_energy_action_counts))
        self.assertGreaterEqual(episode.strained_energy_rest_count, 0)
        self.assertGreaterEqual(episode.strained_energy_rest_share, 0)
        self.assertLessEqual(episode.strained_energy_rest_share, 1)
        self.assertGreaterEqual(episode.dominant_action_share, 0)
        self.assertLessEqual(episode.dominant_action_share, 1)
        self.assertGreaterEqual(episode.low_need_recovery_count, 0)
        self.assertGreaterEqual(episode.low_need_recovery_share, 0)
        self.assertLessEqual(episode.low_need_recovery_share, 1)
        self.assertEqual(episode.social_action_count,
                         dict(episode.action_counts).get("Talk with Aiko", 0))
        self.assertGreaterEqual(episode.social_action_share, 0)
        self.assertLessEqual(episode.social_action_share, 1)
        self.assertGreaterEqual(episode.unseen_state_count, 0)
        self.assertGreaterEqual(episode.unseen_state_share, 0)
        self.assertLessEqual(episode.unseen_state_share, 1)
        self.assertGreaterEqual(episode.preventive_rest_override_count, 0)
        self.assertGreaterEqual(episode.preventive_rest_override_share, 0)
        self.assertLessEqual(episode.preventive_rest_override_share, 1)
        self.assertEqual(episode.preventive_rest_override_count,
                         len(episode.preventive_rest_overrides))
        self.assertGreaterEqual(episode.visit_evidence_steps, 0)
        self.assertGreaterEqual(episode.zero_visit_action_count, 0)
        self.assertGreaterEqual(episode.zero_visit_action_share, 0)
        self.assertLessEqual(episode.zero_visit_action_share, 1)
        self.assertGreaterEqual(episode.average_selected_action_visits, 0)
        self.assertGreaterEqual(episode.gate_mission_available_steps, 0)
        self.assertGreaterEqual(episode.gate_mission_ready_steps, 0)
        self.assertEqual(
            episode.gate_mission_ready_steps + sum(
                count for _, count in episode.gate_mission_readiness_blocker_counts),
            episode.gate_mission_available_steps)
        self.assertGreaterEqual(episode.gate_mission_selection_rate, 0)
        self.assertLessEqual(episode.gate_mission_selection_rate, 1)
        self.assertGreaterEqual(episode.portal_preparation_available_steps, 0)
        self.assertGreaterEqual(episode.portal_preparation_ready_steps, 0)
        self.assertEqual(
            episode.portal_preparation_ready_steps + sum(
                count for _, count in
                episode.portal_preparation_readiness_blocker_counts),
            episode.portal_preparation_available_steps)
        self.assertEqual(
            episode.portal_preparation_heuristic_clear_steps + sum(
                count for _, count in
                episode.portal_preparation_heuristic_displacement_counts),
            episode.portal_preparation_ready_steps)
        self.assertEqual(
            sum(count for _, count in
                episode.portal_preparation_heuristic_displacement_reason_counts),
            sum(count for _, count in
                episode.portal_preparation_heuristic_displacement_counts))
        self.assertGreaterEqual(episode.portal_preparation_selection_rate, 0)
        self.assertLessEqual(episode.portal_preparation_selection_rate, 1)
        self.assertGreaterEqual(episode.gate_mission_seen_opportunity_steps, 0)
        self.assertGreaterEqual(episode.gate_mission_greedy_steps, 0)
        self.assertLessEqual(episode.gate_mission_greedy_steps,
                             episode.gate_mission_seen_opportunity_steps)
        self.assertGreaterEqual(episode.gate_mission_greedy_rate, 0)
        self.assertLessEqual(episode.gate_mission_greedy_rate, 1)
        self.assertGreaterEqual(episode.gate_mission_q_gap_total, 0)
        self.assertGreaterEqual(episode.gate_mission_average_q_gap, 0)
        self.assertLessEqual(
            episode.gate_mission_priority_clear_seen_steps,
            episode.gate_mission_seen_opportunity_steps)
        self.assertLessEqual(
            episode.gate_mission_priority_clear_greedy_steps,
            episode.gate_mission_priority_clear_seen_steps)
        if episode.gate_mission_priority_clear_seen_steps:
            self.assertGreaterEqual(
                episode.gate_mission_priority_clear_greedy_rate, 0)
            self.assertLessEqual(
                episode.gate_mission_priority_clear_greedy_rate, 1)
            self.assertGreaterEqual(
                episode.gate_mission_priority_clear_average_q_gap, 0)
        else:
            self.assertIsNone(episode.gate_mission_priority_clear_greedy_rate)
            self.assertIsNone(
                episode.gate_mission_priority_clear_average_q_gap)
        self.assertGreaterEqual(episode.gate_mission_unseen_opportunity_steps, 0)
        self.assertGreaterEqual(episode.gate_mission_fallback_steps, 0)
        self.assertLessEqual(episode.gate_mission_fallback_steps,
                             episode.gate_mission_unseen_opportunity_steps)
        self.assertGreaterEqual(episode.gate_mission_fallback_rate, 0)
        self.assertLessEqual(episode.gate_mission_fallback_rate, 1)
        self.assertGreaterEqual(
            episode.gate_mission_ready_unseen_opportunity_steps, 0)
        self.assertLessEqual(
            episode.gate_mission_ready_unseen_opportunity_steps,
            episode.gate_mission_unseen_opportunity_steps)
        self.assertLessEqual(
            episode.gate_mission_ready_fallback_steps,
            episode.gate_mission_ready_unseen_opportunity_steps)
        self.assertGreaterEqual(episode.gate_mission_ready_fallback_rate, 0)
        self.assertLessEqual(episode.gate_mission_ready_fallback_rate, 1)
        self.assertEqual(
            sum(count for _, count in
                episode.gate_mission_ready_displacement_counts),
            episode.gate_mission_ready_unseen_opportunity_steps -
            episode.gate_mission_ready_fallback_steps)
        self.assertEqual(
            sum(count for _, count in
                episode.gate_mission_ready_displacement_reason_counts),
            sum(count for _, count in
                episode.gate_mission_ready_displacement_counts))
        self.assertLessEqual(
            episode.gate_mission_priority_clear_unseen_steps,
            episode.gate_mission_ready_unseen_opportunity_steps)
        self.assertLessEqual(
            episode.gate_mission_priority_clear_selection_steps,
            episode.gate_mission_priority_clear_unseen_steps)
        self.assertGreaterEqual(
            episode.gate_mission_priority_clear_selection_rate, 0)
        self.assertLessEqual(
            episode.gate_mission_priority_clear_selection_rate, 1)
        self.assertGreaterEqual(episode.portal_preparation_seen_opportunity_steps, 0)
        self.assertGreaterEqual(episode.portal_preparation_greedy_steps, 0)
        self.assertLessEqual(episode.portal_preparation_greedy_steps,
                             episode.portal_preparation_seen_opportunity_steps)
        self.assertGreaterEqual(episode.portal_preparation_greedy_rate, 0)
        self.assertLessEqual(episode.portal_preparation_greedy_rate, 1)
        self.assertGreaterEqual(episode.portal_preparation_q_gap_total, 0)
        self.assertGreaterEqual(episode.portal_preparation_average_q_gap, 0)
        self.assertLessEqual(
            episode.portal_preparation_priority_clear_seen_steps,
            episode.portal_preparation_seen_opportunity_steps)
        self.assertLessEqual(
            episode.portal_preparation_priority_clear_greedy_steps,
            episode.portal_preparation_priority_clear_seen_steps)
        if episode.portal_preparation_priority_clear_seen_steps:
            self.assertGreaterEqual(
                episode.portal_preparation_priority_clear_greedy_rate, 0)
            self.assertLessEqual(
                episode.portal_preparation_priority_clear_greedy_rate, 1)
            self.assertGreaterEqual(
                episode.portal_preparation_priority_clear_average_q_gap, 0)
        else:
            self.assertIsNone(
                episode.portal_preparation_priority_clear_greedy_rate)
            self.assertIsNone(
                episode.portal_preparation_priority_clear_average_q_gap)
        self.assertGreaterEqual(
            episode.portal_preparation_unseen_opportunity_steps, 0)
        self.assertGreaterEqual(episode.portal_preparation_fallback_steps, 0)
        self.assertLessEqual(
            episode.portal_preparation_fallback_steps,
            episode.portal_preparation_unseen_opportunity_steps)
        self.assertGreaterEqual(episode.portal_preparation_fallback_rate, 0)
        self.assertLessEqual(episode.portal_preparation_fallback_rate, 1)
        self.assertGreaterEqual(
            episode.portal_preparation_ready_unseen_opportunity_steps, 0)
        self.assertLessEqual(
            episode.portal_preparation_ready_unseen_opportunity_steps,
            episode.portal_preparation_unseen_opportunity_steps)
        self.assertLessEqual(
            episode.portal_preparation_ready_fallback_steps,
            episode.portal_preparation_ready_unseen_opportunity_steps)
        self.assertGreaterEqual(
            episode.portal_preparation_ready_fallback_rate, 0)
        self.assertLessEqual(episode.portal_preparation_ready_fallback_rate, 1)
        self.assertEqual(
            sum(count for _, count in
                episode.portal_preparation_ready_displacement_counts),
            episode.portal_preparation_ready_unseen_opportunity_steps -
            episode.portal_preparation_ready_fallback_steps)
        self.assertEqual(
            sum(count for _, count in
                episode.portal_preparation_ready_displacement_reason_counts),
            sum(count for _, count in
                episode.portal_preparation_ready_displacement_counts))
        self.assertLessEqual(
            episode.portal_preparation_priority_clear_unseen_steps,
            episode.portal_preparation_ready_unseen_opportunity_steps)
        self.assertLessEqual(
            episode.portal_preparation_priority_clear_selection_steps,
            episode.portal_preparation_priority_clear_unseen_steps)
        self.assertGreaterEqual(
            episode.portal_preparation_priority_clear_selection_rate, 0)
        self.assertLessEqual(
            episode.portal_preparation_priority_clear_selection_rate, 1)

    def test_diagnostic_batch_is_reproducible_and_ranks_worst_seeds(self) -> None:
        trained = train_q_learning(101, QLearningConfig(episodes=2, horizon=6))
        first = diagnose_batch(trained, (201, 202, 203), horizon=6, worst_count=2)
        second = diagnose_batch(trained, (201, 202, 203), horizon=6, worst_count=2)
        self.assertEqual(first, second)
        self.assertEqual(len(first.worst_rl_seeds), 2)
        self.assertEqual(tuple(name for name, _ in first.reward_component_differences),
                         ("survival", "stability", "progress", "social"))
        self.assertEqual(tuple(name for name, _ in first.terminal_wellbeing_differences),
                         ("health", "energy", "hunger", "stress"))
        self.assertEqual(tuple(name for name, _ in first.resource_burden_differences),
                         ("critical_energy_share", "high_hunger_share",
                          "high_stress_share"))
        rewards = {episode.seed: episode.total_reward for episode in first.rl_episodes}
        self.assertEqual(list(first.worst_rl_seeds),
                         sorted(rewards, key=lambda seed: (rewards[seed], seed))[:2])

    def test_diagnostics_report_contains_auditable_metrics_and_traces(self) -> None:
        trained = train_q_learning(101, QLearningConfig(episodes=2, horizon=6))
        batch = diagnose_batch(trained, (201, 202), horizon=6, worst_count=1)
        report = json.loads(diagnostics_report(batch))
        self.assertEqual(report["evaluation_seeds"], [201, 202])
        self.assertIn("reward_components", report["rl"])
        self.assertEqual(set(report["reward_component_differences"]),
                         {"survival", "stability", "progress", "social"})
        self.assertEqual(set(report["terminal_wellbeing_differences"]),
                         {"health", "energy", "hunger", "stress"})
        self.assertIn("average_end_health", report["rl"])
        self.assertIn("resource_burden_differences", report)
        self.assertIn("average_critical_energy_share", report["rl"])
        self.assertIn("critical_energy_action_counts", report["rl"])
        self.assertIn("critical_energy_entry_controller_counts", report["rl"])
        self.assertIn("critical_energy_entry_prior_sequence_counts", report["rl"])
        self.assertIn("critical_energy_action_frequencies", report["utility"])
        self.assertIn("critical_energy_rest_share", report["rl"])
        self.assertIn("strained_energy_action_counts", report["rl"])
        self.assertIn("strained_energy_action_frequencies", report["utility"])
        self.assertIn("strained_energy_rest_share", report["rl"])
        self.assertIn("action_counts", report["utility"])
        self.assertIn("masked_counts", report["rl"])
        self.assertIn("action_frequencies", report["rl"])
        self.assertIn("average_dominant_action_share", report["rl"])
        self.assertIn("mission_outcomes", report["rl"])
        self.assertEqual(
            report["rl"]["mission_outcomes"]["prepared"]["attempts"] +
            report["rl"]["mission_outcomes"]["unprepared"]["attempts"],
            report["rl"]["action_counts"].get("Gate mission", 0))
        self.assertIn("average_low_need_recovery_count", report["utility"])
        self.assertIn("average_low_need_recovery_share", report["utility"])
        self.assertIn("average_social_action_count", report["utility"])
        self.assertIn("average_social_action_share", report["utility"])
        self.assertIn("average_unseen_state_count", report["rl"])
        self.assertIn("seen_utility_disagreement_share", report["rl"])
        self.assertIn("seen_state_action_pair_counts", report["rl"])
        self.assertIn("seen_state_disagreement_average_reward", report["rl"])
        self.assertIn(
            "seen_state_disagreement_average_paired_reward_difference",
            report["rl"])
        self.assertIn("seen_state_disagreement_paired_component_differences",
                      report["rl"])
        self.assertEqual(report["rl"]['seen_state_counterfactual_horizon'], 4)
        self.assertIn(
            "seen_state_disagreement_average_paired_return_difference",
            report["rl"])
        self.assertIn("average_unseen_state_share", report["rl"])
        self.assertEqual(report["utility"]["average_unseen_state_count"], 0)
        self.assertIn("average_selective_recovery_override_count", report["rl"])
        self.assertIn("selective_recovery_override_pair_counts", report["rl"])
        self.assertIn("selective_recovery_critical_entry_count", report["rl"])
        self.assertIn("selective_recovery_critical_entry_action_counts", report["rl"])
        self.assertIn("selective_recovery_pre_action_energy_counts", report["rl"])
        self.assertIn("average_preventive_rest_override_count", report["rl"])
        self.assertEqual(report["utility"]["average_preventive_rest_override_count"], 0)
        self.assertIn("preventive_rest_replaced_action_counts", report["rl"])
        self.assertIn("preventive_rest_seen_override_count", report["rl"])
        self.assertIn("preventive_rest_unseen_override_count", report["rl"])
        self.assertIn("preventive_rest_average_replaced_q_advantage", report["rl"])
        self.assertIsNone(
            report["utility"]["preventive_rest_average_replaced_q_advantage"])
        self.assertIn("average_visit_evidence_steps", report["rl"])
        self.assertIn("average_zero_visit_action_share", report["rl"])
        self.assertIn("average_selected_action_visits", report["rl"])
        self.assertEqual(report["utility"]["average_visit_evidence_steps"], 0)
        self.assertIn("gate_mission_available_steps", report["rl"])
        self.assertIn("gate_mission_selection_rate", report["utility"])
        self.assertIn("gate_mission_ready_steps", report["rl"])
        self.assertIn("gate_mission_readiness_blocker_counts", report["rl"])
        self.assertEqual(
            report["rl"]["gate_mission_ready_steps"] + sum(
                report["rl"]["gate_mission_readiness_blocker_counts"].values()),
            report["rl"]["gate_mission_available_steps"])
        self.assertIn("portal_preparation_available_steps", report["rl"])
        self.assertIn("portal_preparation_selection_rate", report["utility"])
        self.assertIn("portal_preparation_ready_steps", report["rl"])
        self.assertIn("portal_preparation_readiness_blocker_counts", report["rl"])
        self.assertEqual(
            report["rl"]["portal_preparation_ready_steps"] + sum(
                report["rl"]["portal_preparation_readiness_blocker_counts"].values()),
            report["rl"]["portal_preparation_available_steps"])
        self.assertIn("portal_preparation_heuristic_clear_steps", report["rl"])
        self.assertIn("portal_preparation_heuristic_displacement_counts", report["rl"])
        self.assertIn(
            "portal_preparation_heuristic_displacement_reason_counts", report["rl"])
        self.assertEqual(
            report["rl"]["portal_preparation_heuristic_clear_steps"] + sum(
                report["rl"]["portal_preparation_heuristic_displacement_counts"].values()),
            report["rl"]["portal_preparation_ready_steps"])
        self.assertIn("gate_mission_seen_opportunity_steps", report["rl"])
        self.assertIn("gate_mission_greedy_steps", report["rl"])
        self.assertIn("gate_mission_greedy_rate", report["rl"])
        self.assertIn("gate_mission_average_q_gap", report["rl"])
        self.assertIn("gate_mission_priority_clear_seen_steps", report["rl"])
        self.assertIn("gate_mission_priority_clear_greedy_steps", report["rl"])
        self.assertIn("gate_mission_priority_clear_greedy_rate", report["rl"])
        self.assertIn("gate_mission_priority_clear_average_q_gap", report["rl"])
        self.assertIn("gate_mission_unseen_opportunity_steps", report["rl"])
        self.assertIn("gate_mission_fallback_steps", report["rl"])
        self.assertIn("gate_mission_fallback_rate", report["rl"])
        self.assertIn("gate_mission_ready_unseen_opportunity_steps",
                      report["rl"])
        self.assertIn("gate_mission_ready_fallback_steps", report["rl"])
        self.assertIn("gate_mission_ready_fallback_rate", report["rl"])
        self.assertIn("gate_mission_ready_displacement_counts", report["rl"])
        self.assertIn("gate_mission_ready_displacement_reason_counts",
                      report["rl"])
        self.assertIn("gate_mission_priority_clear_unseen_steps", report["rl"])
        self.assertIn("gate_mission_priority_clear_selection_steps",
                      report["rl"])
        self.assertIn("gate_mission_priority_clear_selection_rate",
                      report["rl"])
        self.assertIn("portal_preparation_seen_opportunity_steps", report["rl"])
        self.assertIn("portal_preparation_greedy_steps", report["rl"])
        self.assertIn("portal_preparation_greedy_rate", report["rl"])
        self.assertIn("portal_preparation_average_q_gap", report["rl"])
        self.assertIn("portal_preparation_priority_clear_seen_steps",
                      report["rl"])
        self.assertIn("portal_preparation_priority_clear_greedy_steps",
                      report["rl"])
        self.assertIn("portal_preparation_priority_clear_greedy_rate",
                      report["rl"])
        self.assertIn("portal_preparation_priority_clear_average_q_gap",
                      report["rl"])
        self.assertIn("portal_preparation_unseen_opportunity_steps",
                      report["rl"])
        self.assertIn("portal_preparation_fallback_steps", report["rl"])
        self.assertIn("portal_preparation_fallback_rate", report["rl"])
        self.assertIn("portal_preparation_ready_unseen_opportunity_steps",
                      report["rl"])
        self.assertIn("portal_preparation_ready_fallback_steps",
                      report["rl"])
        self.assertIn("portal_preparation_ready_fallback_rate", report["rl"])
        self.assertIn("portal_preparation_ready_displacement_counts",
                      report["rl"])
        self.assertIn("portal_preparation_ready_displacement_reason_counts",
                      report["rl"])
        self.assertIn("portal_preparation_priority_clear_unseen_steps",
                      report["rl"])
        self.assertIn("portal_preparation_priority_clear_selection_steps",
                      report["rl"])
        self.assertIn("portal_preparation_priority_clear_selection_rate",
                      report["rl"])
        self.assertEqual(report["utility"]["gate_mission_seen_opportunity_steps"], 0)
        self.assertIn("preparation_coverage", report["rl"])
        self.assertIn("prepared_success_rate", report["utility"])
        self.assertTrue(report["worst_rl_episodes"][0]["trace"])
        self.assertIn(report["verdict"],
                      {"promising", "inconclusive", "baseline remains better"})
    def test_daily_economy_is_seeded_and_changes_cash_flow(self) -> None:
        first, second = Simulation(seed=33), Simulation(seed=33)
        first.step("Part-time work")
        second.step("Part-time work")
        self.assertEqual((first.state.wage_modifier, first.state.meal_cost,
                          first.state.protagonist.money),
                         (second.state.wage_modifier, second.state.meal_cost,
                          second.state.protagonist.money))
        self.assertIn(first.state.wage_modifier, {85, 95, 100, 105, 115})
        self.assertIn(first.state.meal_cost, {500, 600, 700, 800})
        poor = Simulation(seed=33)
        poor.state.protagonist.money = 0
        poor.step("Eat")
        self.assertEqual(poor.state.protagonist.money, 0)

    def test_clinic_assistance_preserves_treatment_without_cash(self) -> None:
        simulation = Simulation(seed=5)
        protagonist = simulation.state.protagonist
        protagonist.money = 0
        protagonist.health, protagonist.injuries, protagonist.injury_severity = 35, 1, 3
        event = simulation.step("Seek treatment")
        self.assertEqual(protagonist.money, 0)
        self.assertGreater(protagonist.health, 35)
        self.assertEqual(protagonist.injury_severity, 1)
        self.assertIn("Emergency assistance covered ¥2,350", event.outcome)

    def test_injury_severity_unlocks_and_treatment_resolves_recovery(self) -> None:
        simulation = Simulation(seed=5)
        p = simulation.state.protagonist
        p.health, p.injuries, p.injury_severity = 45, 2, 3
        self.assertIn("Seek treatment", {action.name for action in available_actions(p)})
        event = simulation.step("Seek treatment")
        self.assertGreater(p.health, 45)
        self.assertLess(p.injury_severity, 3)
        self.assertEqual(p.treatments_received, 1)
        self.assertIn("clinic treatment", event.outcome)

    def test_portal_preparation_advances_multiple_persistent_stages(self) -> None:
        simulation = Simulation(seed=42)
        simulation.run(29)
        simulation.step("Prepare portal")
        portal = simulation.state.active_portal_plan
        first_bonus = simulation.state.portal_investigations[portal].preparation_bonus
        simulation.step("Prepare portal")
        investigation = simulation.state.portal_investigations[portal]
        self.assertGreaterEqual(len(investigation.preparation_steps), 2)
        self.assertGreater(investigation.preparation_bonus, first_bonus)
        self.assertGreaterEqual(simulation.state.objective_progress["portal_readiness"], 2)

    def test_milestone_16_state_and_expanded_observation_are_persistent(self) -> None:
        simulation = Simulation(seed=42)
        simulation.state.protagonist.injury_severity = 2
        simulation.step("Seek treatment")
        simulation.run(29)
        simulation.step("Prepare portal")
        with TemporaryDirectory() as directory:
            path = Path(directory) / "milestone-16.json"
            save_simulation(simulation, path)
            restored = load_simulation(path)
        self.assertEqual(restored.state, simulation.state)
        environment = LearningEnvironment(seed=9)
        self.assertEqual(len(environment.observe()), 22)
        self.assertEqual(len(environment.action_mask()), len(ACTION_NAMES))
    def test_masked_random_baseline_is_legal_and_reproducible(self) -> None:
        first = diagnose_episode(301, 12, "random")
        second = diagnose_episode(301, 12, "random")
        self.assertEqual(first, second)
        self.assertEqual(sum(count for _, count in first.action_counts), first.steps)
        self.assertTrue(all(step.action in ACTION_NAMES or step.action in {
            "Awakening assessment", "Guild registration", "Rent deadline",
            "Tanabata evening", "Investigation consequence",
        } or step.action.startswith("Meet ") for step in first.trace))

    def test_heuristic_baseline_prioritizes_severe_injury(self) -> None:
        environment = LearningEnvironment(seed=4)
        p = environment.simulation.state.protagonist
        p.health, p.injury_severity = 50, 3
        action = heuristic_action(environment, environment.action_mask())
        self.assertEqual(ACTION_NAMES[action], "Seek treatment")

    def test_utility_baseline_also_treats_severe_injury(self) -> None:
        simulation = Simulation(seed=4)
        p = simulation.state.protagonist
        p.health, p.injury_severity = 50, 3
        action, _ = simulation.agent.choose(p, simulation.state.clock.slot)
        self.assertEqual(action.name, "Seek treatment")

    def test_critical_entry_controller_labels_utility_sequence(self) -> None:
        episode = diagnose_episode(
            1013, 20, "utility", condition="gate_crisis")
        self.assertEqual(len(episode.critical_energy_entries), 1)
        entry = episode.critical_energy_entries[0]
        self.assertEqual(entry.controller, "utility")
        self.assertEqual(entry.action, "Gate mission")
        self.assertEqual(entry.prior_actions[-1], "Prepare portal")
        self.assertGreater(entry.energy_before, 25)
        self.assertLessEqual(entry.energy_after, 25)

    def test_multi_policy_batch_is_reproducible_and_ranked(self) -> None:
        trained = train_q_learning(101, QLearningConfig(episodes=2, horizon=6))
        first = diagnose_batch(trained, (201, 202), horizon=6, worst_count=1)
        second = diagnose_batch(trained, (201, 202), horizon=6, worst_count=1)
        self.assertEqual(first, second)
        self.assertEqual(set(first.policy_ranking), {"utility", "heuristic", "rl", "random"})
        report = json.loads(diagnostics_report(first))
        self.assertTrue({"utility", "heuristic", "rl", "random"}.issubset(report))
    def test_strategic_state_abstraction_is_compact_and_stable(self) -> None:
        observation = list(LearningEnvironment(seed=8).observe())
        state = abstract_state(observation)
        self.assertEqual(len(state), 16)
        observation[10] = 0.99  # Relationship tension is intentionally diagnostic-only.
        self.assertEqual(abstract_state(observation), state)
        self.assertTrue(all(0 <= value <= 3 for value in state))

    def test_action_neighbors_preserve_safety_and_require_visit_evidence(self) -> None:
        result = train_q_learning(101, QLearningConfig(episodes=2, horizon=6))
        action = "Prepare portal"
        action_index = ACTION_NAMES.index(action)
        target = next(iter(result.q_table))
        same_safety = list(target)
        same_safety[4] = (same_safety[4] + 1) % 4
        same_safety = tuple(same_safety)
        unsafe = list(same_safety)
        unsafe[1] = (unsafe[1] + 1) % 4
        unsafe = tuple(unsafe)
        q_table = dict(result.q_table)
        visit_table = dict(result.visit_table)
        for candidate, visits, value in ((same_safety, 3, 1.25),
                                         (unsafe, 9, 9.0)):
            q_table[candidate] = [0.0] * len(ACTION_NAMES)
            q_table[candidate][action_index] = value
            visit_table[candidate] = [0] * len(ACTION_NAMES)
            visit_table[candidate][action_index] = visits
        result = replace(result, q_table=q_table, visit_table=visit_table)
        evidence = nearest_action_neighbors(result, target, action)
        self.assertEqual(len(evidence), 1)
        self.assertEqual(evidence[0].state, same_safety)
        self.assertEqual((evidence[0].distance, evidence[0].action_visits,
                          evidence[0].q_value), (1, 3, 1.25))
        self.assertEqual(nearest_action_neighbors(
            result, target, action, max_distance=0), ())
        self.assertEqual(nearest_action_neighbors(
            result, target, action, min_action_visits=4), ())
        self.assertEqual(nearest_action_neighbors(
            result, target, action, min_q_value=1.5), ())

    def test_action_safety_groups_aggregate_repeated_comparable_evidence(self) -> None:
        result = train_q_learning(103, QLearningConfig(episodes=1, horizon=2))
        action_index = ACTION_NAMES.index("Prepare portal")
        first = next(iter(result.q_table))
        second = list(first)
        second[4] = (second[4] + 1) % 4
        second = tuple(second)
        q_table = dict(result.q_table)
        visit_table = dict(result.visit_table)
        for state, visits, value in ((first, 2, 1.0), (second, 3, -0.5)):
            q_table[state] = [0.0] * len(ACTION_NAMES)
            q_table[state][action_index] = value
            visit_table[state] = [0] * len(ACTION_NAMES)
            visit_table[state][action_index] = visits
        result = replace(result, q_table=q_table, visit_table=visit_table)
        groups = summarize_action_safety_groups(result, "Prepare portal")
        self.assertEqual(len(groups), 1)
        self.assertEqual((groups[0].state_count, groups[0].action_visits,
                          groups[0].positive_q_states,
                          groups[0].average_state_q_value), (2, 5, 1, 0.25))

    def test_action_safety_groups_validate_evidence(self) -> None:
        result = train_q_learning(104, QLearningConfig(episodes=1, horizon=2))
        with self.assertRaises(ValueError):
            summarize_action_safety_groups(result, "Unknown")
        with self.assertRaises(ValueError):
            summarize_action_safety_groups(
                result, "Prepare portal", (0, 0))

    def test_action_neighbors_validate_inputs_and_can_report_no_match(self) -> None:
        result = train_q_learning(102, QLearningConfig(episodes=1, horizon=2))
        state = next(iter(result.q_table))
        self.assertEqual(nearest_action_neighbors(result, state, "Prepare portal"), ())
        with self.assertRaises(ValueError):
            nearest_action_neighbors(result, state[:-1], "Prepare portal")
        with self.assertRaises(ValueError):
            nearest_action_neighbors(result, state, "Unknown")
        with self.assertRaises(ValueError):
            nearest_action_neighbors(result, state, "Prepare portal", (0, 0))
        for options in ({"max_distance": -1}, {"max_distance": True},
                        {"min_action_visits": 0}, {"min_action_visits": True},
                        {"min_q_value": float("inf")},
                        {"min_q_value": True}):
            with self.assertRaises(ValueError):
                nearest_action_neighbors(
                    result, state, "Prepare portal", **options)

    def test_similarity_coverage_is_held_out_and_conflict_safe(self) -> None:
        result = train_q_learning(107, QLearningConfig(episodes=1, horizon=2))
        environment = LearningEnvironment(207)
        target = abstract_state(environment.observe())
        visit_table = dict(result.visit_table)
        q_table = dict(result.q_table)
        visit_table.pop(target, None)
        q_table.pop(target, None)
        for offset, action in ((4, "Eat"), (6, "Rest")):
            candidate = list(target)
            candidate[offset] = (candidate[offset] + 1) % 4
            candidate = tuple(candidate)
            counts = [0] * len(ACTION_NAMES)
            counts[ACTION_NAMES.index(action)] = 2
            visit_table[candidate] = counts
            q_table[candidate] = [0.0] * len(ACTION_NAMES)
        result = replace(result, visit_table=visit_table, q_table=q_table)
        first = audit_similarity_coverage(
            result, (207,), horizon=1, max_distance=1)
        second = audit_similarity_coverage(
            result, (207,), horizon=1, max_distance=1)
        self.assertEqual(first, second)
        self.assertEqual((first.total_decisions, first.unseen_decisions,
                          first.conflicting_decisions,
                          first.supported_decisions), (1, 1, 1, 0))
        conflicts = dict(first.conflicting_feature_counts)
        self.assertEqual((conflicts["money"], conflicts["rank_points"]), (1, 1))
        self.assertEqual(sum(dict(
            first.supported_feature_distance_totals).values()), 0)
        agreement_visits = dict(visit_table)
        for offset in (4, 6):
            candidate = list(target)
            candidate[offset] = (candidate[offset] + 1) % 4
            counts = [0] * len(ACTION_NAMES)
            counts[ACTION_NAMES.index("Eat")] = 2
            agreement_visits[tuple(candidate)] = counts
        weights = [1] * 16
        weights[4] = weights[6] = 2
        agreement = audit_similarity_coverage(
            replace(result, visit_table=agreement_visits), (207,), horizon=1,
            max_distance=2, feature_weights=tuple(weights))
        self.assertEqual((agreement.supported_decisions,
                          agreement.average_supported_distance), (1, 2.0))
        self.assertEqual(sum(dict(
            agreement.supported_feature_distance_totals).values()), 2)
        self.assertEqual(agreement.feature_weights, tuple(weights))
        with self.assertRaises(ValueError):
            audit_similarity_coverage(result, (107,), horizon=1)
        with self.assertRaises(ValueError):
            audit_similarity_coverage(result, (207, 207), horizon=1)
        with self.assertRaises(ValueError):
            audit_similarity_coverage(result, (207,), horizon=0)
        with self.assertRaises(ValueError):
            audit_similarity_coverage(
                result, (207,), horizon=1, feature_weights=(1,) * 15)
        with self.assertRaises(ValueError):
            audit_similarity_coverage(
                result, (207,), horizon=1,
                feature_weights=(1,) * 15 + (True,))

    def test_ensemble_similarity_requires_cross_policy_action_agreement(self) -> None:
        trained = train_q_learning(108, QLearningConfig(episodes=1, horizon=2))
        environment = LearningEnvironment(208)
        target = abstract_state(environment.observe())
        candidate = list(target)
        candidate[4] = (candidate[4] + 1) % 4
        candidate = tuple(candidate)

        def policy(seed: int, action: str):
            counts = [0] * len(ACTION_NAMES)
            counts[ACTION_NAMES.index(action)] = 2
            return replace(
                trained, training_seed=seed,
                visit_table={candidate: counts},
                q_table={candidate: [0.0] * len(ACTION_NAMES)},
            )

        agreeing = (policy(108, "Eat"), policy(109, "Eat"),
                    policy(110, "Eat"))
        first = audit_ensemble_similarity_coverage(
            agreeing, (208,), horizon=1, max_distance=1,
            min_state_visits=2)
        second = audit_ensemble_similarity_coverage(
            agreeing, (208,), horizon=1, max_distance=1,
            min_state_visits=2)
        self.assertEqual(first, second)
        self.assertEqual((first.eligible_decisions, first.supported_decisions,
                          first.coverage_share), (1, 1, 1.0))
        self.assertEqual(first.supported_action_counts, (("Eat", 1),))
        self.assertEqual(
            first.supported_decisions +
            first.within_policy_conflict_decisions +
            first.cross_policy_conflict_decisions +
            first.invalid_consensus_decisions +
            first.insufficient_support_decisions,
            first.eligible_decisions,
        )
        disagreeing = agreeing[:2] + (policy(110, "Rest"),)
        conflict = audit_ensemble_similarity_coverage(
            disagreeing, (208,), horizon=1, max_distance=1,
            min_state_visits=2)
        self.assertEqual((conflict.supported_decisions,
                          conflict.cross_policy_conflict_decisions), (0, 1))
        with self.assertRaises(ValueError):
            audit_ensemble_similarity_coverage(
                agreeing, (108,), horizon=1, min_state_visits=2)
        with self.assertRaises(ValueError):
            audit_ensemble_similarity_coverage(
                agreeing, (208,), horizon=1, minimum_policy_support=4)

    def test_similarity_audit_report_is_canonical_and_tamper_evident(self) -> None:
        trained = train_q_learning(111, QLearningConfig(episodes=1, horizon=2))
        single = audit_similarity_coverage(
            trained, (211,), horizon=2, min_state_visits=1)
        policies = (trained, replace(trained, training_seed=112),
                    replace(trained, training_seed=113))
        ensemble = audit_ensemble_similarity_coverage(
            policies, (212,), horizon=2, min_state_visits=1)
        first = similarity_audit_report(single)
        self.assertEqual(first, similarity_audit_report(single))
        payload = json.loads(first)
        self.assertEqual(payload["report_version"], 1)
        self.assertEqual(payload["audit_type"], "single")
        self.assertEqual(payload["sha256"], similarity_audit_digest(single))
        with TemporaryDirectory() as directory:
            single_path = Path(directory) / "single.json"
            ensemble_path = Path(directory) / "ensemble.json"
            duplicate_path = Path(directory) / "duplicate.json"
            save_similarity_audit_report(single, single_path)
            save_similarity_audit_report(single, duplicate_path)
            save_similarity_audit_report(ensemble, ensemble_path)
            self.assertEqual(single_path.read_bytes(), duplicate_path.read_bytes())
            self.assertEqual(load_similarity_audit_report(single_path), single)
            self.assertEqual(load_similarity_audit_report(ensemble_path), ensemble)
            tampered = json.loads(single_path.read_text(encoding="utf-8"))
            tampered["summary"]["supported_decisions"] += 1
            single_path.write_text(json.dumps(tampered), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_similarity_audit_report(single_path)
            unsupported = json.loads(first)
            unsupported.pop("sha256")
            unsupported["report_version"] = 2
            canonical = json.dumps(
                unsupported, sort_keys=True, separators=(",", ":"))
            unsupported["sha256"] = hashlib.sha256(
                canonical.encode("utf-8")).hexdigest()
            single_path.write_text(json.dumps(unsupported), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_similarity_audit_report(single_path)
            invalid = json.loads(first)
            invalid.pop("sha256")
            invalid["summary"]["unsupported_decisions"] = -1
            canonical = json.dumps(
                invalid, sort_keys=True, separators=(",", ":"))
            invalid["sha256"] = hashlib.sha256(
                canonical.encode("utf-8")).hexdigest()
            single_path.write_text(json.dumps(invalid), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_similarity_audit_report(single_path)

    def test_experiment_catalog_is_portable_canonical_and_tamper_evident(self) -> None:
        trained = train_q_learning(114, QLearningConfig(episodes=2, horizon=3))
        suite = evaluate_scenario_suite(trained, (
            EvaluationScenario("standard", 3, (214, 215)),
        ))
        similarity = audit_similarity_coverage(
            trained, (216,), horizon=3, min_state_visits=1)
        catalog = build_experiment_catalog((
            ("Similarity coverage", "similarity/standard.json", similarity),
            ("Scenario baseline", "scenarios/baseline.json", suite),
        ))
        self.assertEqual(tuple(entry.filename for entry in catalog.entries), (
            "scenarios/baseline.json", "similarity/standard.json",
        ))
        first = experiment_catalog_report(catalog)
        self.assertEqual(first, experiment_catalog_report(catalog))
        payload = json.loads(first)
        self.assertEqual(payload["catalog_version"], 1)
        self.assertEqual(payload["sha256"], experiment_catalog_digest(catalog))
        self.assertEqual(payload["entries"][0]["status"], suite.verdict)
        self.assertEqual(payload["entries"][1]["status"], "diagnostic_only")
        with TemporaryDirectory() as directory:
            path = Path(directory) / "catalog.json"
            duplicate = Path(directory) / "duplicate.json"
            save_experiment_catalog(catalog, path)
            save_experiment_catalog(catalog, duplicate)
            self.assertEqual(path.read_bytes(), duplicate.read_bytes())
            self.assertEqual(load_experiment_catalog(path), catalog)
            with self.assertRaises(ValueError):
                verify_experiment_catalog(
                    catalog, Path(directory) / "missing-root")
            with self.assertRaises(ValueError):
                verify_experiment_catalog(catalog, directory)
            scenario_path = Path(directory) / "scenarios" / "baseline.json"
            similarity_path = Path(directory) / "similarity" / "standard.json"
            save_scenario_suite_report(suite, scenario_path)
            save_similarity_audit_report(similarity, similarity_path)
            self.assertEqual(
                verify_experiment_catalog(catalog, directory),
                (suite, similarity),
            )
            similarity_data = json.loads(
                similarity_path.read_text(encoding="utf-8"))
            similarity_data["summary"]["supported_decisions"] += 1
            similarity_path.write_text(
                json.dumps(similarity_data), encoding="utf-8")
            with self.assertRaises(ValueError):
                verify_experiment_catalog(catalog, directory)
            save_similarity_audit_report(similarity, similarity_path)
            save_similarity_audit_report(similarity, scenario_path)
            with self.assertRaises(ValueError):
                verify_experiment_catalog(catalog, directory)
            save_scenario_suite_report(suite, scenario_path)
            tampered = json.loads(path.read_text(encoding="utf-8"))
            tampered["entries"][0]["status"] = "promising"
            path.write_text(json.dumps(tampered), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_experiment_catalog(path)
            malformed = json.loads(first)
            malformed.pop("sha256")
            malformed["entries"][0]["filename"] = 7
            canonical = json.dumps(
                malformed, sort_keys=True, separators=(",", ":"))
            malformed["sha256"] = hashlib.sha256(
                canonical.encode("utf-8")).hexdigest()
            path.write_text(json.dumps(malformed), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_experiment_catalog(path)
        with self.assertRaises(ValueError):
            build_experiment_catalog((
                ("Unsafe", "../escape.json", similarity),
            ))
        with self.assertRaises(ValueError):
            build_experiment_catalog((
                ("Duplicate", "a.json", similarity),
                ("Duplicate", "b.json", suite),
            ))

    def test_experiment_bundle_is_staged_verified_and_non_overwriting(self) -> None:
        trained = train_q_learning(117, QLearningConfig(episodes=2, horizon=3))
        suite = evaluate_scenario_suite(trained, (
            EvaluationScenario("standard", 3, (217, 218)),
        ))
        similarity = audit_similarity_coverage(
            trained, (219,), horizon=3, min_state_visits=1)
        items = (
            ("Similarity", "similarity/standard.json", similarity),
            ("Scenarios", "scenarios/baseline.json", suite),
        )
        with TemporaryDirectory() as directory:
            first = Path(directory) / "first"
            second = Path(directory) / "second"
            self.assertEqual(save_experiment_bundle(items, first), first)
            self.assertEqual(save_experiment_bundle(items, second), second)
            first_catalog = load_experiment_catalog(first / "catalog.json")
            second_catalog = load_experiment_catalog(second / "catalog.json")
            self.assertEqual(first_catalog, second_catalog)
            self.assertEqual(
                verify_experiment_catalog(first_catalog, first),
                (suite, similarity),
            )
            for relative in (
                    "catalog.json", "scenarios/baseline.json",
                    "similarity/standard.json"):
                self.assertEqual(
                    (first / relative).read_bytes(),
                    (second / relative).read_bytes(),
                )
            with self.assertRaises(ValueError):
                save_experiment_bundle(items, first)
            reserved = Path(directory) / "reserved"
            with self.assertRaises(ValueError):
                save_experiment_bundle((
                    ("Reserved", "catalog.json", similarity),
                ), reserved)
            self.assertFalse(reserved.exists())

    def test_bundle_inspection_api_and_cli_emit_verified_json(self) -> None:
        trained = train_q_learning(120, QLearningConfig(episodes=2, horizon=3))
        suite = evaluate_scenario_suite(trained, (
            EvaluationScenario("standard", 3, (220, 221)),
        ))
        similarity = audit_similarity_coverage(
            trained, (222,), horizon=3, min_state_visits=1)
        items = (
            ("Similarity", "similarity/standard.json", similarity),
            ("Scenarios", "scenarios/baseline.json", suite),
        )
        with TemporaryDirectory() as directory:
            bundle = Path(directory) / "bundle"
            save_experiment_bundle(items, bundle)
            summary = inspect_experiment_bundle(bundle)
            payload = json.loads(experiment_bundle_summary_json(summary))
            self.assertEqual(payload["report_count"], 2)
            self.assertEqual(payload["training_seeds"], [120])
            self.assertEqual(payload["conditions"], ["standard"])
            self.assertEqual(payload["horizons"], [3])
            self.assertEqual(dict(payload["report_type_counts"]), {
                "scenario_suite": 1, "similarity_single": 1,
            })
            output = StringIO()
            with redirect_stdout(output):
                cli_main(("--inspect-experiment-bundle", str(bundle)))
            self.assertEqual(json.loads(output.getvalue()), payload)
            errors = StringIO()
            with redirect_stderr(errors), self.assertRaises(SystemExit):
                cli_main((
                    "--inspect-experiment-bundle", str(bundle),
                    "--save", "timeline.json",
                ))
            self.assertIn("cannot use simulation options", errors.getvalue())
            similarity_path = bundle / "similarity" / "standard.json"
            tampered = json.loads(similarity_path.read_text(encoding="utf-8"))
            tampered["summary"]["supported_decisions"] += 1
            similarity_path.write_text(json.dumps(tampered), encoding="utf-8")
            errors = StringIO()
            with redirect_stderr(errors), self.assertRaises(SystemExit):
                cli_main(("--inspect-experiment-bundle", str(bundle)))
            self.assertIn("integrity verification failed", errors.getvalue())

    def test_bundle_comparison_api_and_cli_report_verified_changes(self) -> None:
        config = QLearningConfig(episodes=2, horizon=3)
        left_training = train_q_learning(123, config)
        right_training = train_q_learning(124, config)
        stable = audit_similarity_coverage(
            left_training, (223,), horizon=3, min_state_visits=1)
        left_changed = audit_similarity_coverage(
            left_training, (224,), horizon=3, min_state_visits=1)
        right_changed = audit_similarity_coverage(
            right_training, (225,), horizon=4, min_state_visits=1)
        removed = evaluate_scenario_suite(left_training, (
            EvaluationScenario(
                "removed", 3, (226, 227), condition="injury_recovery"),
        ))
        added = evaluate_scenario_suite(right_training, (
            EvaluationScenario(
                "added", 4, (228, 229), condition="financial_pressure"),
        ))
        with TemporaryDirectory() as directory:
            left = Path(directory) / "left"
            right = Path(directory) / "right"
            save_experiment_bundle((
                ("Stable", "similarity/stable.json", stable),
                ("Current", "similarity/current.json", left_changed),
                ("Removed", "scenarios/removed.json", removed),
            ), left)
            save_experiment_bundle((
                ("Stable", "similarity/stable.json", stable),
                ("Current", "similarity/current.json", right_changed),
                ("Added", "scenarios/added.json", added),
            ), right)
            comparison = compare_experiment_bundles(left, right)
            payload = json.loads(
                experiment_bundle_comparison_json(comparison))
            self.assertEqual(payload["left_report_count"], 3)
            self.assertEqual(payload["right_report_count"], 3)
            self.assertEqual(payload["difference_count"], 3)
            self.assertFalse(payload["identical"])
            self.assertEqual(
                payload["comparison_sha256"],
                experiment_bundle_comparison_digest(comparison),
            )
            self.assertEqual(len(payload["comparison_sha256"]), 64)
            reverse = compare_experiment_bundles(right, left)
            self.assertNotEqual(
                experiment_bundle_comparison_digest(reverse),
                payload["comparison_sha256"],
            )
            self.assertEqual(payload["added_files"], ["scenarios/added.json"])
            self.assertEqual(
                payload["removed_files"], ["scenarios/removed.json"])
            self.assertEqual(
                payload["changed_files"], ["similarity/current.json"])
            self.assertEqual(
                payload["unchanged_files"], ["similarity/stable.json"])
            self.assertEqual(len(payload["added_reports"]), 1)
            added_record = payload["added_reports"][0]
            self.assertEqual(added_record["filename"], "scenarios/added.json")
            self.assertEqual(added_record["report"]["label"], "Added")
            self.assertEqual(
                added_record["report"]["report_type"], "scenario_suite")
            self.assertEqual(
                added_record["report"]["conditions"], ["financial_pressure"])
            self.assertEqual(len(payload["removed_reports"]), 1)
            removed_record = payload["removed_reports"][0]
            self.assertEqual(
                removed_record["filename"], "scenarios/removed.json")
            self.assertEqual(removed_record["report"]["label"], "Removed")
            self.assertEqual(
                removed_record["report"]["conditions"], ["injury_recovery"])
            self.assertEqual(len(payload["changed_reports"]), 1)
            report_change = payload["changed_reports"][0]
            self.assertEqual(
                report_change["filename"], "similarity/current.json")
            self.assertEqual(report_change["changed_fields"], [
                "sha256", "training_seeds", "horizons",
            ])
            self.assertEqual(report_change["left"]["training_seeds"], [123])
            self.assertEqual(report_change["right"]["training_seeds"], [124])
            self.assertEqual(report_change["left"]["horizons"], [3])
            self.assertEqual(report_change["right"]["horizons"], [4])
            self.assertEqual(payload["added_training_seeds"], [124])
            self.assertEqual(payload["removed_training_seeds"], [])
            self.assertEqual(
                payload["added_conditions"], ["financial_pressure"])
            self.assertEqual(
                payload["removed_conditions"], ["injury_recovery"])
            self.assertEqual(payload["added_horizons"], [4])
            self.assertEqual(payload["removed_horizons"], [])
            output = StringIO()
            with redirect_stdout(output):
                cli_main((
                    "--compare-experiment-bundles", str(left), str(right),
                ))
            self.assertEqual(json.loads(output.getvalue()), payload)
            artifact = Path(directory) / "comparison.json"
            artifact_output = StringIO()
            with redirect_stdout(artifact_output):
                cli_main((
                    "--compare-experiment-bundles", str(left), str(right),
                    "--comparison-output", str(artifact),
                ))
            self.assertEqual(json.loads(artifact_output.getvalue()), payload)
            self.assertEqual(
                load_experiment_bundle_comparison_artifact(artifact), payload)
            inspection_output = StringIO()
            with redirect_stdout(inspection_output):
                cli_main(("--inspect-comparison-artifact", str(artifact)))
            self.assertEqual(json.loads(inspection_output.getvalue()), payload)
            errors = StringIO()
            with redirect_stderr(errors), self.assertRaises(SystemExit):
                cli_main((
                    "--inspect-comparison-artifact", str(artifact),
                    "--seed", "1",
                ))
            self.assertIn("cannot use simulation options", errors.getvalue())
            errors = StringIO()
            with redirect_stderr(errors), self.assertRaises(SystemExit):
                cli_main((
                    "--compare-experiment-bundles", str(left), str(right),
                    "--comparison-output", str(artifact),
                ))
            self.assertIn("destination already exists", errors.getvalue())
            tampered_artifact = json.loads(artifact.read_text(encoding="utf-8"))
            tampered_artifact["added_files"].append("forged.json")
            artifact.write_text(json.dumps(tampered_artifact), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "integrity verification"):
                load_experiment_bundle_comparison_artifact(artifact)
            forged_artifact = json.loads(json.dumps(payload))
            forged_artifact["identical"] = True
            forged_artifact.pop("comparison_sha256")
            canonical = json.dumps(
                forged_artifact, sort_keys=True, separators=(",", ":"))
            forged_artifact["comparison_sha256"] = hashlib.sha256(
                canonical.encode("utf-8")).hexdigest()
            artifact.write_text(json.dumps(forged_artifact), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "semantic validation"):
                load_experiment_bundle_comparison_artifact(artifact)
            identical_output = StringIO()
            with redirect_stdout(identical_output):
                cli_main((
                    "--compare-experiment-bundles", str(left), str(left),
                    "--require-identical",
                ))
            identical_payload = json.loads(identical_output.getvalue())
            self.assertTrue(identical_payload["identical"])
            self.assertEqual(identical_payload["difference_count"], 0)
            self.assertEqual(identical_payload["changed_reports"], [])
            self.assertEqual(identical_payload["added_reports"], [])
            self.assertEqual(identical_payload["removed_reports"], [])
            different_output = StringIO()
            with (redirect_stdout(different_output),
                  self.assertRaises(SystemExit) as exit_context):
                cli_main((
                    "--compare-experiment-bundles", str(left), str(right),
                    "--require-identical",
                ))
            self.assertEqual(exit_context.exception.code, 1)
            self.assertEqual(json.loads(different_output.getvalue()), payload)
            errors = StringIO()
            with redirect_stderr(errors), self.assertRaises(SystemExit):
                cli_main((
                    "--compare-experiment-bundles", str(left), str(right),
                    "--days", "1",
                ))
            self.assertIn("cannot use simulation options", errors.getvalue())
            errors = StringIO()
            with redirect_stderr(errors), self.assertRaises(SystemExit):
                cli_main(("--require-identical",))
            self.assertIn(
                "requires a comparison mode", errors.getvalue())
            errors = StringIO()
            with redirect_stderr(errors), self.assertRaises(SystemExit):
                cli_main(("--comparison-output", "comparison.json"))
            self.assertIn(
                "requires --compare-experiment-bundles", errors.getvalue())
            changed_path = right / "similarity" / "current.json"
            tampered = json.loads(changed_path.read_text(encoding="utf-8"))
            tampered["summary"]["supported_decisions"] += 1
            changed_path.write_text(json.dumps(tampered), encoding="utf-8")
            errors = StringIO()
            with redirect_stderr(errors), self.assertRaises(SystemExit):
                cli_main((
                    "--compare-experiment-bundles", str(left), str(right),
                ))
            self.assertIn("integrity verification failed", errors.getvalue())

    def test_curriculum_reward_changes_focus_by_training_phase(self) -> None:
        components = {"survival": 4.0, "stability": 2.0, "progress": 6.0, "social": 1.0}
        early = curriculum_reward(0, 9, 1.0, components)
        late = curriculum_reward(8, 9, 1.0, components)
        self.assertEqual(early, 2.9)
        self.assertEqual(late, 3.2)
        self.assertEqual(curriculum_reward(8, 9, 1.0, components, False), 1.0)

    def test_count_exploration_configuration_is_validated(self) -> None:
        with self.assertRaises(ValueError):
            QLearningConfig(exploration_bonus=-0.1)
        with self.assertRaises(ValueError):
            QLearningConfig(progression_exploration_bonus=-0.1)
        with self.assertRaises(ValueError):
            QLearningConfig(progression_sampling_rate=1.1)
        with self.assertRaises(ValueError):
            QLearningConfig(priority_clear_progression_sampling_rate=1.1)
        with self.assertRaises(ValueError):
            QLearningConfig(progression_exploration_bonus=0.1,
                            progression_sampling_rate=0.1)
        with self.assertRaises(ValueError):
            QLearningConfig(progression_sampling_rate=0.1,
                            priority_clear_progression_sampling_rate=0.1)
        with self.assertRaises(ValueError):
            QLearningConfig(preventive_rest_threshold=101)
        with self.assertRaises(ValueError):
            QLearningConfig(preventive_rest_threshold=35.5)
        with self.assertRaises(ValueError):
            QLearningConfig(preventive_rest_threshold=True)
        with self.assertRaises(ValueError):
            QLearningConfig(preventive_rest_max_injury_severity=5)
        with self.assertRaises(ValueError):
            QLearningConfig(preventive_rest_max_injury_severity=True)
        with self.assertRaises(ValueError):
            QLearningConfig(training_rent_reserve=1)
        with self.assertRaises(ValueError):
            QLearningConfig(energy_preemption_floor=-1)
        with self.assertRaises(ValueError):
            QLearningConfig(energy_preemption_floor=True)
        config = QLearningConfig(episodes=2, horizon=5,
                                 progression_sampling_rate=0.1)
        self.assertEqual(train_q_learning(131, config), train_q_learning(131, config))
        clear_config = QLearningConfig(
            episodes=2, horizon=5,
            priority_clear_progression_sampling_rate=0.1)
        self.assertEqual(train_q_learning(133, clear_config),
                         train_q_learning(133, clear_config))
        reserve_config = QLearningConfig(
            episodes=2, horizon=5, training_rent_reserve=True)
        self.assertEqual(train_q_learning(135, reserve_config),
                         train_q_learning(135, reserve_config))

    def test_action_cost_energy_preemption_is_default_off_and_reproducible(self) -> None:
        trained = train_q_learning(141, QLearningConfig(episodes=1, horizon=2))
        environment = LearningEnvironment(241)
        p = environment.simulation.state.protagonist
        p.energy, p.hunger, p.injury_severity = 38, 20, 0
        observation, mask = environment.observe(), environment.action_mask()
        base = replace(
            trained, q_table={},
            config=replace(trained.config, unseen_state_fallback="heuristic"))
        action, _, overridden, replaced_action = _frozen_policy_action(
            base, environment, observation, mask)
        self.assertEqual(ACTION_NAMES[action], "Part-time work")
        self.assertFalse(overridden)
        guarded = replace(
            base, config=replace(base.config, energy_preemption_floor=25))
        first = _frozen_policy_action(
            guarded, environment, observation, mask)
        second = _frozen_policy_action(
            guarded, environment, observation, mask)
        self.assertEqual(first, second)
        self.assertEqual(ACTION_NAMES[first[0]], "Rest")
        self.assertTrue(first[2])
        self.assertEqual(ACTION_NAMES[first[3]], "Part-time work")

    def test_selective_recovery_and_energy_floor_compose_reproducibly(self) -> None:
        trained = train_q_learning(143, QLearningConfig(episodes=2, horizon=5))
        combined = replace(
            trained, config=replace(
                trained.config, unseen_state_fallback="utility",
                seen_recovery_utility_override=True, energy_preemption_floor=20))
        first = diagnose_episode(243, 8, "rl", combined, "gate_crisis")
        second = diagnose_episode(243, 8, "rl", combined, "gate_crisis")
        self.assertEqual(first, second)
        self.assertLessEqual(first.preventive_rest_override_count, first.decision_steps)
        self.assertLessEqual(
            first.selective_recovery_override_count, first.seen_state_decision_count)
        self.assertTrue(all(action in ACTION_NAMES or action.startswith((
            "Awakening", "Guild", "Rent", "Tanabata", "Investigation", "Meet "))
                            for action, _ in first.action_counts))

    def test_training_rent_reserve_preserves_arrears_conditions(self) -> None:
        standard = TrainingEnvironment(seed=7, horizon=3)
        standard.reset(seed=7)
        p = standard.simulation.state.protagonist
        self.assertLess(p.money, p.rent_cost)
        self.assertTrue(_apply_training_rent_reserve(standard))
        self.assertEqual(p.money, p.rent_cost)
        financial = TrainingEnvironment(seed=7, horizon=3)
        financial.reset(seed=7, options={"condition": "financial_pressure"})
        p = financial.simulation.state.protagonist
        before = (p.money, p.rent_arrears)
        self.assertFalse(_apply_training_rent_reserve(financial))
        self.assertEqual((p.money, p.rent_arrears), before)

    def test_training_records_environment_and_curriculum_returns(self) -> None:
        result = train_q_learning(18, QLearningConfig(episodes=3, horizon=8))
        self.assertEqual(len(result.episode_rewards), 3)
        self.assertEqual(len(result.training_rewards), 3)
        self.assertEqual(result.state_count, len(result.q_table))
        self.assertEqual(result.episode_horizons, (8, 8, 8))
        self.assertEqual(len(result.episode_state_counts), 3)
        self.assertEqual(len(result.episode_portal_preparations), 3)
        self.assertEqual(len(result.episode_prepared_missions_attempted), 3)
        self.assertEqual(len(result.episode_prepared_missions_completed), 3)
        self.assertTrue(all(completed <= attempted
                            for attempted, completed in zip(
                                result.episode_prepared_missions_attempted,
                                result.episode_prepared_missions_completed)))
        self.assertTrue(all(1 <= count <= 9 for count in result.episode_state_counts))
        self.assertNotEqual(result.episode_rewards, result.training_rewards)
    def test_q_checkpoint_round_trip_is_exact_and_stable(self) -> None:
        trained = train_q_learning(19, QLearningConfig(episodes=2, horizon=5))
        with TemporaryDirectory() as directory:
            first = Path(directory) / "first.json"
            second = Path(directory) / "second.json"
            save_checkpoint(trained, first)
            restored = load_checkpoint(first)
            save_checkpoint(restored, second)
            self.assertEqual(first.read_bytes(), second.read_bytes())
            legacy = json.loads(first.read_text(encoding="utf-8"))
            legacy.pop("sha256")
            legacy["checkpoint_version"] = 25
            legacy["config"].pop("episode_seed_pool_size")
            canonical = json.dumps(legacy, sort_keys=True, separators=(",", ":"))
            legacy["sha256"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
            first.write_text(json.dumps(legacy), encoding="utf-8")
            self.assertEqual(load_checkpoint(first), trained)
            legacy.pop("sha256")
            legacy["checkpoint_version"] = 24
            legacy["config"].pop("seen_recovery_utility_override")
            canonical = json.dumps(legacy, sort_keys=True, separators=(",", ":"))
            legacy["sha256"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
            first.write_text(json.dumps(legacy), encoding="utf-8")
            self.assertEqual(load_checkpoint(first), trained)
            legacy.pop("sha256")
            legacy["checkpoint_version"] = 23
            canonical = json.dumps(legacy, sort_keys=True, separators=(",", ":"))
            legacy["sha256"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
            first.write_text(json.dumps(legacy), encoding="utf-8")
            self.assertEqual(load_checkpoint(first), trained)
            legacy.pop("sha256")
            legacy["checkpoint_version"] = 22
            legacy["config"].pop("energy_preemption_floor")
            canonical = json.dumps(legacy, sort_keys=True, separators=(",", ":"))
            legacy["sha256"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
            first.write_text(json.dumps(legacy), encoding="utf-8")
            legacy_energy = replace(
                trained, config=replace(
                    trained.config, energy_preemption_floor=0))
            self.assertEqual(load_checkpoint(first), legacy_energy)
            legacy.pop("sha256")
            legacy["checkpoint_version"] = 21
            legacy.pop("preparation_plan_contexts")
            canonical = json.dumps(legacy, sort_keys=True, separators=(",", ":"))
            legacy["sha256"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
            first.write_text(json.dumps(legacy), encoding="utf-8")
            legacy_plan_context = replace(
                legacy_energy, preparation_plan_contexts=())
            self.assertEqual(load_checkpoint(first), legacy_plan_context)
            legacy.pop("sha256")
            legacy["checkpoint_version"] = 20
            legacy.pop("preparation_plan_returns")
            canonical = json.dumps(legacy, sort_keys=True, separators=(",", ":"))
            legacy["sha256"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
            first.write_text(json.dumps(legacy), encoding="utf-8")
            legacy_plan_return = replace(
                legacy_plan_context, preparation_plan_returns=())
            self.assertEqual(load_checkpoint(first), legacy_plan_return)
            legacy.pop("sha256")
            legacy["checkpoint_version"] = 19
            legacy.pop("preparation_return_samples")
            canonical = json.dumps(legacy, sort_keys=True, separators=(",", ":"))
            legacy["sha256"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
            first.write_text(json.dumps(legacy), encoding="utf-8")
            legacy_preparation_return = replace(
                legacy_plan_return, preparation_return_samples=())
            self.assertEqual(load_checkpoint(first), legacy_preparation_return)
            legacy.pop("sha256")
            legacy["checkpoint_version"] = 18
            legacy.pop("discounted_return_table")
            canonical = json.dumps(legacy, sort_keys=True, separators=(",", ":"))
            legacy["sha256"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
            first.write_text(json.dumps(legacy), encoding="utf-8")
            legacy_return = replace(
                legacy_preparation_return, discounted_return_table={})
            self.assertEqual(load_checkpoint(first), legacy_return)
            legacy.pop("sha256")
            legacy["checkpoint_version"] = 17
            legacy.pop("reward_table")
            canonical = json.dumps(legacy, sort_keys=True, separators=(",", ":"))
            legacy["sha256"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
            first.write_text(json.dumps(legacy), encoding="utf-8")
            legacy_reward = replace(legacy_return, reward_table={})
            self.assertEqual(load_checkpoint(first), legacy_reward)
            legacy.pop("sha256")
            legacy["checkpoint_version"] = 16
            legacy.pop("episode_portal_preparations")
            legacy.pop("episode_prepared_missions_attempted")
            legacy.pop("episode_prepared_missions_completed")
            canonical = json.dumps(legacy, sort_keys=True, separators=(",", ":"))
            legacy["sha256"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
            first.write_text(json.dumps(legacy), encoding="utf-8")
            legacy_plan = replace(
                legacy_reward, episode_portal_preparations=(),
                episode_prepared_missions_attempted=(),
                episode_prepared_missions_completed=())
            self.assertEqual(load_checkpoint(first), legacy_plan)
            legacy.pop("sha256")
            legacy["checkpoint_version"] = 15
            canonical = json.dumps(legacy, sort_keys=True, separators=(",", ":"))
            legacy["sha256"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
            first.write_text(json.dumps(legacy), encoding="utf-8")
            self.assertEqual(load_checkpoint(first), legacy_plan)
            legacy.pop("sha256")
            legacy["checkpoint_version"] = 14
            legacy["config"].pop("training_horizons")
            legacy.pop("episode_horizons")
            canonical = json.dumps(legacy, sort_keys=True, separators=(",", ":"))
            legacy["sha256"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
            first.write_text(json.dumps(legacy), encoding="utf-8")
            self.assertEqual(load_checkpoint(first), legacy_plan)
            legacy.pop("sha256")
            legacy["checkpoint_version"] = 13
            legacy["config"].pop("training_rent_reserve")
            canonical = json.dumps(legacy, sort_keys=True, separators=(",", ":"))
            legacy["sha256"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
            first.write_text(json.dumps(legacy), encoding="utf-8")
            self.assertEqual(load_checkpoint(first), legacy_plan)
            legacy.pop("sha256")
            legacy["checkpoint_version"] = 12
            legacy.pop("episode_preparation_ready_steps")
            legacy.pop("episode_preparation_blocker_counts")
            canonical = json.dumps(legacy, sort_keys=True, separators=(",", ":"))
            legacy["sha256"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
            first.write_text(json.dumps(legacy), encoding="utf-8")
            legacy_blockers = replace(
                legacy_plan, episode_preparation_ready_steps=(),
                episode_preparation_blocker_counts=())
            migrated_v12 = load_checkpoint(first)
            self.assertEqual(migrated_v12, legacy_blockers)
            with self.assertRaises(ValueError):
                summarize_training_preparation_blockers(migrated_v12)
            legacy.pop("sha256")
            legacy["checkpoint_version"] = 11
            legacy["config"].pop("priority_clear_progression_sampling_rate")
            canonical = json.dumps(legacy, sort_keys=True, separators=(",", ":"))
            legacy["sha256"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
            first.write_text(json.dumps(legacy), encoding="utf-8")
            self.assertEqual(load_checkpoint(first), legacy_blockers)
            legacy.pop("sha256")
            legacy["checkpoint_version"] = 10
            legacy.pop("episode_gate_priority_clear_steps")
            legacy.pop("episode_gate_priority_clear_selections")
            legacy.pop("episode_preparation_priority_clear_steps")
            legacy.pop("episode_preparation_priority_clear_selections")
            canonical = json.dumps(legacy, sort_keys=True, separators=(",", ":"))
            legacy["sha256"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
            first.write_text(json.dumps(legacy), encoding="utf-8")
            legacy_training = replace(
                legacy_blockers, episode_gate_priority_clear_steps=(),
                episode_gate_priority_clear_selections=(),
                episode_preparation_priority_clear_steps=(),
                episode_preparation_priority_clear_selections=())
            migrated_v10 = load_checkpoint(first)
            self.assertEqual(migrated_v10, legacy_training)
            with self.assertRaises(ValueError):
                summarize_training_progression(migrated_v10)
            legacy.pop("sha256")
            legacy["checkpoint_version"] = 9
            legacy["config"].pop("preventive_rest_max_injury_severity")
            canonical = json.dumps(legacy, sort_keys=True, separators=(",", ":"))
            legacy["sha256"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
            first.write_text(json.dumps(legacy), encoding="utf-8")
            migrated_v9 = load_checkpoint(first)
            self.assertEqual(
                migrated_v9.config.preventive_rest_max_injury_severity, 1)
            legacy.pop("sha256")
            legacy["checkpoint_version"] = 5
            legacy.pop("visit_table")
            legacy["config"].pop("progression_exploration_bonus")
            legacy["config"].pop("progression_sampling_rate")
            legacy["config"].pop("preventive_rest_threshold")
            legacy["config"].pop("preventive_rest_max_injury_severity", None)
            canonical = json.dumps(legacy, sort_keys=True, separators=(",", ":"))
            legacy["sha256"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
            first.write_text(json.dumps(legacy), encoding="utf-8")
            migrated_v5 = load_checkpoint(first)
            self.assertEqual(migrated_v5, replace(legacy_training, visit_table={}))
            legacy.pop("sha256")
            legacy["checkpoint_version"] = 4
            legacy["config"].pop("unseen_state_fallback")
            canonical = json.dumps(legacy, sort_keys=True, separators=(",", ":"))
            legacy["sha256"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
            first.write_text(json.dumps(legacy), encoding="utf-8")
            self.assertEqual(load_checkpoint(first), replace(legacy_training, visit_table={}))
            legacy.pop("sha256")
            legacy["checkpoint_version"] = 3
            legacy.pop("episode_state_counts")
            canonical = json.dumps(legacy, sort_keys=True, separators=(",", ":"))
            legacy["sha256"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
            first.write_text(json.dumps(legacy), encoding="utf-8")
            migrated = load_checkpoint(first)
            self.assertEqual(migrated, replace(
                legacy_training, episode_state_counts=(), visit_table={}))
            with self.assertRaises(ValueError):
                summarize_training_conditions(migrated)
            legacy.pop("sha256")
            legacy["checkpoint_version"] = 2
            legacy.pop("episode_conditions")
            legacy["config"].pop("training_conditions")
            canonical = json.dumps(legacy, sort_keys=True, separators=(",", ":"))
            legacy["sha256"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
            first.write_text(json.dumps(legacy), encoding="utf-8")
            self.assertEqual(load_checkpoint(first), replace(
                legacy_training, episode_state_counts=(), visit_table={}))
        self.assertEqual(restored, trained)
        self.assertEqual(len(checkpoint_digest(restored)), 64)

    def test_q_checkpoint_rejects_tampering(self) -> None:
        trained = train_q_learning(19, QLearningConfig(episodes=2, horizon=5))
        with TemporaryDirectory() as directory:
            path = Path(directory) / "tampered.json"
            save_checkpoint(trained, path)
            data = json.loads(path.read_text(encoding="utf-8"))
            data["q_table"][0]["values"][0] += 1
            path.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_checkpoint(path)
            save_checkpoint(trained, path)
            data = json.loads(path.read_text(encoding="utf-8"))
            data["reward_table"][0]["rewards"][0] += 1
            path.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_checkpoint(path)
            save_checkpoint(trained, path)
            data = json.loads(path.read_text(encoding="utf-8"))
            data["discounted_return_table"][0]["returns"][0] += 1
            path.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_checkpoint(path)
            save_checkpoint(trained, path)
            data = json.loads(path.read_text(encoding="utf-8"))
            data["preparation_return_samples"].append({
                "state": [0] * 16, "discounted_return": 1.0,
                "steps": 1, "plan_consumed": True})
            path.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_checkpoint(path)
            save_checkpoint(trained, path)
            data = json.loads(path.read_text(encoding="utf-8"))
            data["preparation_plan_returns"].append({
                "initial_state": [0] * 16, "preparation_steps": 1,
                "discounted_return": 1.0, "steps": 1,
                "plan_consumed": True})
            path.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_checkpoint(path)
            save_checkpoint(trained, path)
            data = json.loads(path.read_text(encoding="utf-8"))
            data["preparation_plan_contexts"].append(["standard", 999])
            path.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_checkpoint(path)

    def test_repeated_trials_are_reproducible_and_conservative(self) -> None:
        config = QLearningConfig(episodes=2, horizon=5)
        args = ((21, 22), ((121, 122), (221, 222)), config)
        first = evaluate_repeated_trials(*args)
        second = evaluate_repeated_trials(*args)
        self.assertEqual(first, second)
        self.assertFalse(first.neural_trial_ready)
        self.assertEqual(len({trial.checkpoint_sha256 for trial in first.trials}), 2)

    def test_repeated_trials_require_matching_nonempty_seed_groups(self) -> None:
        config = QLearningConfig(episodes=2, horizon=5)
        with self.assertRaises(ValueError):
            evaluate_repeated_trials((1, 2), ((101,),), config)
        with self.assertRaises(ValueError):
            evaluate_repeated_trials((1,), ((),), config)

    def test_gate_crisis_utility_prepares_before_mission_attempts(self) -> None:
        episode = diagnose_episode(501, 40, "utility", condition="gate_crisis")
        actions = dict(episode.action_counts)
        self.assertGreater(actions.get("Gate mission", 0), 0)
        self.assertGreater(actions.get("Prepare portal", 0), 0)
        trace = [step.action for step in episode.trace]
        self.assertLess(trace.index("Prepare portal"), trace.index("Gate mission"))
        self.assertGreater(episode.prepared_missions_attempted, 0)
        self.assertLessEqual(episode.prepared_missions_completed,
                             episode.prepared_missions_attempted)
        self.assertTrue(episode.survived)

    def test_rent_arrears_can_be_repaid_without_spending_emergency_cash(self) -> None:
        simulation = Simulation(seed=25)
        p = simulation.state.protagonist
        p.money, p.rent_arrears, p.stress = 3_500, 8_000, 70
        self.assertIn("Pay rent arrears", {action.name for action in available_actions(p)})
        event = simulation.step("Pay rent arrears")
        self.assertEqual((p.money, p.rent_arrears), (600, 5_100))
        self.assertLess(p.stress, 70)
        self.assertIn("¥2,900", event.outcome)
        p.money = 600
        self.assertNotIn("Pay rent arrears", {action.name for action in available_actions(p)})

    def test_financial_pressure_policy_can_clear_rent_arrears(self) -> None:
        episode = diagnose_episode(501, 40, "utility", condition="financial_pressure")
        self.assertTrue(episode.rent_paid)
        self.assertIn("Pay rent arrears", dict(episode.action_counts))

    def test_compound_crisis_prioritizes_treatment_reproducibly(self) -> None:
        first = diagnose_episode(61, 8, "utility", condition="compound_crisis")
        second = diagnose_episode(61, 8, "utility", condition="compound_crisis")
        heuristic = diagnose_episode(61, 8, "heuristic", condition="compound_crisis")
        self.assertEqual(first, second)
        self.assertEqual(first.condition, "compound_crisis")
        self.assertEqual(first.trace[0].action, "Seek treatment")
        self.assertEqual(heuristic.trace[0].action, "Seek treatment")
        self.assertTrue(first.survived)

    def test_conditioned_diagnostics_are_reproducible_and_auditable(self) -> None:
        first = diagnose_episode(51, 4, "utility", condition="injury_recovery")
        second = diagnose_episode(51, 4, "utility", condition="injury_recovery")
        self.assertEqual(first, second)
        self.assertEqual(first.condition, "injury_recovery")
        self.assertEqual(first.trace[0].action, "Seek treatment")
        financial = diagnose_episode(52, 1, "utility", condition="financial_pressure")
        self.assertIn(financial.trace[0].action, ACTION_NAMES)
        with self.assertRaises(ValueError):
            diagnose_episode(51, 4, "utility", condition="unknown")

    def test_scenario_suite_propagates_stress_conditions_to_every_policy(self) -> None:
        trained = train_q_learning(35, QLearningConfig(episodes=2, horizon=5))
        suite = evaluate_scenario_suite(trained, (
            EvaluationScenario("financial", 5, (136, 137), "financial_pressure"),
            EvaluationScenario("gate", 7, (236, 237), "gate_crisis"),
        ))
        self.assertEqual(tuple(item.condition for item in suite.scenarios),
                         ("financial_pressure", "gate_crisis"))
        self.assertEqual(tuple(item.training_condition_covered
                               for item in suite.scenarios), (False, False))
        self.assertFalse(suite.adoption_ready)
        decision = assess_policy_adoption(trained, suite)
        self.assertIn("financial: training condition coverage is absent",
                      decision.blockers)
        thin = train_q_learning(36, QLearningConfig(
            episodes=2, horizon=5,
            training_conditions=("financial_pressure", "gate_crisis"),
        ))
        thin_suite = evaluate_scenario_suite(thin, (
            EvaluationScenario("financial", 5, (138, 139), "financial_pressure"),
            EvaluationScenario("gate", 7, (238, 239), "gate_crisis"),
        ))
        self.assertEqual(tuple(item.training_condition_episodes
                               for item in thin_suite.scenarios), (1, 1))
        self.assertTrue(any("training condition exposure is 1" in blocker
                            for blocker in assess_policy_adoption(
                                thin, thin_suite).blockers))
        covered = train_q_learning(37, QLearningConfig(
            episodes=8, horizon=5, training_horizons=(5, 7),
            training_conditions=("financial_pressure", "gate_crisis"),
        ))
        covered_suite = evaluate_scenario_suite(covered, (
            EvaluationScenario("financial", 5, (140, 141), "financial_pressure"),
            EvaluationScenario("gate", 7, (240, 241), "gate_crisis"),
        ))
        self.assertTrue(all(item.training_condition_covered
                            for item in covered_suite.scenarios))
        self.assertEqual(tuple(item.training_condition_episodes
                               for item in covered_suite.scenarios), (4, 4))
        self.assertEqual(tuple(item.training_scenario_episodes
                               for item in covered_suite.scenarios), (2, 2))
        covered_blockers = assess_policy_adoption(covered, covered_suite).blockers
        self.assertFalse(any("training condition" in blocker
                             for blocker in covered_blockers))
        self.assertFalse(any("joint training" in blocker
                             for blocker in covered_blockers))
        crossed = evaluate_scenario_suite(covered, (
            EvaluationScenario("crossed", 7, (340, 341), "financial_pressure"),
        ))
        self.assertEqual(crossed.scenarios[0].training_condition_episodes, 4)
        self.assertTrue(crossed.scenarios[0].training_horizon_matches)
        self.assertEqual(crossed.scenarios[0].training_scenario_episodes, 2)
        sparse_pairs = replace(
            covered,
            episode_conditions=("financial_pressure", "gate_crisis") * 4,
            episode_horizons=(5, 7) * 4,
        )
        missed = evaluate_scenario_suite(sparse_pairs, (
            EvaluationScenario("missed pair", 7, (342, 343), "financial_pressure"),
        ))
        self.assertEqual(missed.scenarios[0].training_condition_episodes, 4)
        self.assertTrue(missed.scenarios[0].training_horizon_matches)
        self.assertEqual(missed.scenarios[0].training_scenario_episodes, 0)
        self.assertIn("missed pair: joint training exposure is 0; require 2",
                      assess_policy_adoption(sparse_pairs, missed).blockers)

    def test_scenario_suite_is_reproducible_across_horizons(self) -> None:
        trained = train_q_learning(31, QLearningConfig(episodes=2, horizon=5))
        scenarios = (
            EvaluationScenario("early survival", 5, (131, 132)),
            EvaluationScenario("longer stability", 9, (231, 232)),
        )
        first = evaluate_scenario_suite(trained, scenarios)
        second = evaluate_scenario_suite(trained, scenarios)
        self.assertEqual(first, second)
        self.assertEqual(tuple(item.horizon for item in first.scenarios), (5, 9))
        self.assertEqual(tuple(item.training_horizon_matches for item in first.scenarios),
                         (True, False))
        self.assertIn("longer stability: training horizon alignment is mismatched",
                      assess_policy_adoption(trained, first).blockers)
        self.assertEqual(first.total_episodes, 4)
        self.assertIn(first.verdict, {"promising", "inconclusive", "baseline remains better"})

    def test_adoption_decision_is_explainable_and_checkpoint_bound(self) -> None:
        trained = train_q_learning(33, QLearningConfig(episodes=2, horizon=5))
        suite = evaluate_scenario_suite(trained, (
            EvaluationScenario("early survival", 5, (134, 135)),
            EvaluationScenario("longer stability", 9, (234, 235)),
        ))
        decision = assess_policy_adoption(trained, suite)
        self.assertEqual(decision.ready, suite.adoption_ready)
        self.assertEqual(decision.checkpoint_sha256, checkpoint_digest(trained))
        self.assertEqual(decision.report_sha256, scenario_suite_digest(suite))
        self.assertEqual(decision.ready, not decision.blockers)
        if not decision.ready:
            self.assertTrue(any("verdict" in blocker or "regression" in blocker
                                for blocker in decision.blockers))

        other = train_q_learning(34, QLearningConfig(episodes=2, horizon=5))
        mismatch = assess_policy_adoption(other, suite)
        self.assertFalse(mismatch.ready)
        self.assertEqual(mismatch.blockers[0], "checkpoint mismatch")

    def test_adoption_decision_blocks_balance_regressions(self) -> None:
        trained = train_q_learning(36, QLearningConfig(episodes=2, horizon=5))
        suite = evaluate_scenario_suite(trained, (
            EvaluationScenario("balance audit", 5, (138, 139)),
        ))
        scenario = replace(
            suite.scenarios[0], verdict="promising",
            rl_survival_rate=1.0, utility_survival_rate=1.0,
            rl_average_missions=1.0, utility_average_missions=1.0,
            rl_rent_paid_rate=0.0, utility_rent_paid_rate=1.0,
            rl_dominant_action_share=0.8, utility_dominant_action_share=0.3,
            rl_exploit_flags=("low action diversity",),
        )
        audited = replace(suite, scenarios=(scenario,), verdict="promising",
                          adoption_ready=False)
        decision = assess_policy_adoption(trained, audited)
        self.assertFalse(decision.ready)
        self.assertIn("balance audit: rent recovery regression", decision.blockers)
        self.assertIn("balance audit: action dominance regression", decision.blockers)
        self.assertIn("balance audit: behavioral exploit flags (low action diversity)",
                      decision.blockers)

    def test_scenario_suite_report_is_canonical_and_policy_bound(self) -> None:
        trained = train_q_learning(32, QLearningConfig(episodes=2, horizon=5))
        suite = evaluate_scenario_suite(trained, (
            EvaluationScenario("early survival", 5, (132, 133)),
            EvaluationScenario("longer stability", 9, (232, 233)),
        ))
        first = scenario_suite_report(suite)
        second = scenario_suite_report(suite)
        payload = json.loads(first)
        self.assertEqual(first, second)
        self.assertEqual(payload["report_version"], 8)
        self.assertEqual(payload["checkpoint_sha256"], checkpoint_digest(trained))
        self.assertEqual(payload["sha256"], scenario_suite_digest(suite))
        self.assertEqual(payload["total_episodes"], 4)
        self.assertEqual(payload["scenarios"][1]["horizon"], 9)
        self.assertIn("rl_survival_rate", payload["scenarios"][0])
        self.assertIn("rl_rent_paid_rate", payload["scenarios"][0])
        self.assertIn("rl_dominant_action_share", payload["scenarios"][0])
        self.assertIn("rl_exploit_flags", payload["scenarios"][0])
        self.assertIn("rl_preparation_coverage", payload["scenarios"][0])
        self.assertIn("rl_prepared_success_rate", payload["scenarios"][0])
        self.assertTrue(payload["scenarios"][0]["training_condition_covered"])
        self.assertEqual(payload["scenarios"][0]["training_condition_episodes"], 2)
        self.assertTrue(payload["scenarios"][0]["training_horizon_matches"])
        self.assertEqual(payload["scenarios"][0]["training_scenario_episodes"], 2)
        with TemporaryDirectory() as directory:
            first_path = Path(directory) / "first.json"
            second_path = Path(directory) / "second.json"
            save_scenario_suite_report(suite, first_path)
            save_scenario_suite_report(suite, second_path)
            self.assertEqual(first_path.read_bytes(), second_path.read_bytes())
            self.assertEqual(first_path.read_text(encoding="utf-8"), first)
            self.assertEqual(load_scenario_suite_report(first_path), suite)
            legacy = json.loads(first_path.read_text(encoding="utf-8"))
            legacy.pop("sha256")
            legacy["report_version"] = 7
            for scenario in legacy["scenarios"]:
                scenario.pop("training_scenario_episodes")
            canonical = json.dumps(legacy, sort_keys=True, separators=(",", ":"))
            legacy["sha256"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
            first_path.write_text(json.dumps(legacy), encoding="utf-8")
            restored_v7 = load_scenario_suite_report(first_path)
            self.assertTrue(all(item.training_condition_covered
                                for item in restored_v7.scenarios))
            self.assertTrue(restored_v7.scenarios[0].training_horizon_matches)
            self.assertTrue(all(item.training_scenario_episodes is None
                                for item in restored_v7.scenarios))
            self.assertTrue(any("joint training exposure is unknown" in blocker
                                for blocker in assess_policy_adoption(
                                    trained, restored_v7).blockers))
            legacy = json.loads(first)
            legacy.pop("sha256")
            legacy["report_version"] = 1
            for scenario in legacy["scenarios"]:
                scenario.pop("condition")
                for field in ("rl_rent_paid_rate", "utility_rent_paid_rate",
                              "rl_dominant_action_share", "utility_dominant_action_share",
                              "rl_exploit_flags", "rl_preparation_coverage",
                              "utility_preparation_coverage", "rl_prepared_success_rate",
                              "utility_prepared_success_rate",
                              "training_condition_covered",
                              "training_condition_episodes",
                              "training_horizon_matches",
                              "training_scenario_episodes"):
                    scenario.pop(field)
            canonical = json.dumps(legacy, sort_keys=True, separators=(",", ":"))
            legacy["sha256"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
            first_path.write_text(json.dumps(legacy), encoding="utf-8")
            restored_legacy = load_scenario_suite_report(first_path)
            self.assertTrue(all(item.condition == "standard"
                                for item in restored_legacy.scenarios))
            self.assertTrue(all(item.rl_dominant_action_share == 0.0
                                for item in restored_legacy.scenarios))
            self.assertTrue(all(item.training_condition_covered is None
                                for item in restored_legacy.scenarios))
            self.assertTrue(all(item.training_condition_episodes is None
                                for item in restored_legacy.scenarios))
            self.assertTrue(all(item.training_horizon_matches is None
                                for item in restored_legacy.scenarios))
            self.assertTrue(all(item.training_scenario_episodes is None
                                for item in restored_legacy.scenarios))
            legacy_decision = assess_policy_adoption(trained, restored_legacy)
            self.assertTrue(any("training condition coverage is unknown" in blocker
                                for blocker in legacy_decision.blockers))
            first_path.write_text(first, encoding="utf-8")
            tampered = json.loads(first_path.read_text(encoding="utf-8"))
            tampered["scenarios"][0]["rl_average_reward"] += 1
            first_path.write_text(json.dumps(tampered), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_scenario_suite_report(first_path)
    def test_scenario_suite_validates_names_horizons_and_held_out_seeds(self) -> None:
        trained = train_q_learning(41, QLearningConfig(episodes=2, horizon=5))
        with self.assertRaises(ValueError):
            EvaluationScenario("", 5, (141,))
        with self.assertRaises(ValueError):
            EvaluationScenario("invalid", 0, (141,))
        with self.assertRaises(ValueError):
            evaluate_scenario_suite(trained, (
                EvaluationScenario("duplicate", 5, (141,)),
                EvaluationScenario("duplicate", 7, (241,)),
            ))
        with self.assertRaises(ValueError):
            evaluate_scenario_suite(trained, (
                EvaluationScenario("leaked", 5, (41,)),
            ))
        with self.assertRaises(ValueError):
            evaluate_scenario_suite(trained, (
                EvaluationScenario("first", 5, (141,)),
                EvaluationScenario("reused seed", 7, (141,)),
            ))

if __name__ == "__main__":
    unittest.main()
