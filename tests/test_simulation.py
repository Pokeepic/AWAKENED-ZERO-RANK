import hashlib
import json
import unittest
from dataclasses import replace
from tempfile import TemporaryDirectory
from pathlib import Path

from awakened_zero_rank.actions import available_actions
from awakened_zero_rank.journal import journal_entry
from awakened_zero_rank.dialogue import choose_intention, contextual_line, resolve_aiko_dialogue
from awakened_zero_rank.models import Relationship, TimeSlot
from awakened_zero_rank.persistence import load_simulation, save_simulation
from awakened_zero_rank.simulation import Simulation
from awakened_zero_rank.world import ITEMS
from awakened_zero_rank.content import dialogue_context_count, npc_context_count, portal_situation_count
from awakened_zero_rank.learning import (
    ACTION_NAMES, LearningEnvironment, QLearningConfig, TrainingEnvironment,
    _apply_training_rent_reserve,
    EvaluationScenario,
    abstract_state, assess_policy_adoption, checkpoint_digest,
    compare_utility_and_rl, curriculum_reward,
    diagnose_batch,
    diagnose_episode, diagnostics_report, heuristic_action, is_low_need_recovery,
    evaluate_preparation_counterfactual,
    evaluate_repeated_trials, evaluate_scenario, evaluate_scenario_suite,
    load_checkpoint, load_scenario_suite_report, save_checkpoint,
    save_scenario_suite_report,
    scenario_suite_digest, scenario_suite_report, summarize_training_actions,
    summarize_training_conditions, summarize_training_preparation_blockers,
    summarize_training_progression,
    train_q_learning,
)


class SimulationTests(unittest.TestCase):
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

    def test_severe_weather_changes_agent_preferences(self) -> None:
        simulation = Simulation(seed=2)
        p = simulation.state.protagonist
        p.energy = 70
        clear = simulation.agent._weather_adjustment("Train", "Clear")
        storm = simulation.agent._weather_adjustment("Train", "Thunderstorm")
        self.assertLess(storm, clear)

    def test_tanabata_calendar_event_occurs_once(self) -> None:
        simulation = Simulation(seed=42)
        events = simulation.run(32)
        self.assertEqual(sum(event.action == "Tanabata evening" for event in events), 1)
        self.assertIn("Tanabata", simulation.state.calendar_events_seen)

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
        self.assertGreaterEqual(portal_situation_count(), 90)

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
                        if event.action == "Investigation consequence"]
        self.assertTrue(consequences)
        self.assertTrue(any("trust" in event.outcome for event in consequences))

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
        preventive = replace(
            empty, config=replace(empty.config, preventive_rest_threshold=100))
        preventive_episode = diagnose_episode(201, 1, "rl", preventive)
        injured = replace(
            safe, config=replace(safe.config, preventive_rest_threshold=100))
        injured_episode = diagnose_episode(
            201, 1, "rl", injured, condition="injury_recovery")
        self.assertEqual(historical.trace[0].action, "Eat")
        self.assertEqual(first.trace[0].action, "Part-time work")
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
        self.assertEqual(seen_override.replaced_action_q_value, 2.0)
        self.assertEqual(seen_override.rest_q_value, 0.5)
        self.assertEqual(seen_override.replaced_action_q_advantage, 1.5)
        self.assertEqual(injured_episode.trace[0].action, "Seek treatment")
        self.assertEqual(injured_episode.preventive_rest_override_count, 0)
        self.assertEqual(first, second)
        self.assertEqual(first.unseen_state_count, 1)

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
        self.assertIn("average_unseen_state_share", report["rl"])
        self.assertEqual(report["utility"]["average_unseen_state_count"], 0)
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
            legacy["checkpoint_version"] = 16
            legacy.pop("episode_portal_preparations")
            legacy.pop("episode_prepared_missions_attempted")
            legacy.pop("episode_prepared_missions_completed")
            canonical = json.dumps(legacy, sort_keys=True, separators=(",", ":"))
            legacy["sha256"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
            first.write_text(json.dumps(legacy), encoding="utf-8")
            legacy_plan = replace(
                trained, episode_portal_preparations=(),
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
