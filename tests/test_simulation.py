import unittest
from tempfile import TemporaryDirectory
from pathlib import Path

from awakened_zero_rank.journal import journal_entry
from awakened_zero_rank.dialogue import choose_intention, contextual_line, resolve_aiko_dialogue
from awakened_zero_rank.models import Relationship, TimeSlot
from awakened_zero_rank.persistence import load_simulation, save_simulation
from awakened_zero_rank.simulation import Simulation
from awakened_zero_rank.world import ITEMS
from awakened_zero_rank.content import dialogue_context_count, npc_context_count, portal_situation_count
from awakened_zero_rank.learning import ACTION_NAMES, LearningEnvironment


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
        self.assertEqual(len(environment.observe()), 14)
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
        simulation.run(28)
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


if __name__ == "__main__":
    unittest.main()
