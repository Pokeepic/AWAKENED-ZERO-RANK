from __future__ import annotations

import random

from .agent import UtilityAgent
from .dialogue import (
    contextual_line, resolve_aiko_dialogue, resolve_contextual_encounter,
)
from .content import NPCS, PORTALS, STORY_ANCHORS, StoryAnchor, scheduled_location
from .environment import SUMMER_WEATHER, summer_weather
from .models import (DelayedConsequence, Event, Memory, PortalInvestigation,
                     Relationship, TimeSlot, WorldState)
from .world import ITEMS, gate_encounters_for_rank, travel_cost


RANK_THRESHOLDS = ((90, "C"), (60, "D"), (30, "E"))


class Simulation:
    def __init__(self, seed: int = 42, state: WorldState | None = None) -> None:
        self.seed = seed
        self.state = state or WorldState()
        self.rng = random.Random(seed)
        self.agent = UtilityAgent(self.rng)

    def step(self, selected_action: str | None = None) -> Event:
        clock = self.state.clock
        protagonist = self.state.protagonist
        self._update_weather()
        self._update_economy()
        self._update_npc_schedules()
        special = self._special_event()
        if special is not None:
            self.state.events.append(special)
            self._remember(special)
            self._update_goal()
            clock.advance()
            return special
        background_consequence = self._resolve_due_consequence()
        if selected_action is None:
            action, reason = self.agent.choose(
                protagonist, clock.slot, self.state.gate_alert_level, self.state.weather,
                self.state.active_portal_plan is not None,
            )
        else:
            from .actions import available_actions
            choices = {candidate.name: candidate for candidate in available_actions(protagonist)}
            if selected_action not in choices:
                raise ValueError(f"Action {selected_action!r} is unavailable")
            action = choices[selected_action]
            reason = "a learning policy selected this valid strategy (policy action)"
        money_before = protagonist.money
        if action.name == "Visit hunter shop" and self._weather().shop_closed:
            outcome = "The hunter supply shop was closed under the severe-weather advisory."
        else:
            if action.name == "Gate mission":
                outcome = self._resolve_gate_mission()
            elif action.name == "Prepare portal":
                outcome = self._prepare_portal()
            elif action.name == "Seek treatment":
                outcome = self._seek_treatment()
            elif action.name == "Talk with Aiko":
                travel = action.apply(protagonist)
                exchange, social_reason = resolve_aiko_dialogue(protagonist, clock.day)
                outcome = (f'{travel} Ren: “{exchange.ren_line}” Aiko: “{exchange.npc_line}” '
                           f'She seemed {exchange.reaction}; {social_reason}.')
            else:
                outcome = action.apply(protagonist)
                social = self._scheduled_social_encounter(action.name)
                if social:
                    outcome += f" {social}"
        if background_consequence is not None:
            outcome += f" Delayed consequence: {background_consequence}"
        if action.name == "Visit hunter shop":
            self.state.shop_visits += 1
        self._apply_passive_needs()
        self._apply_weather_cost(action.name)
        self._apply_economic_variation(action.name, money_before)
        self._develop_from_action(action.name)
        self._update_objectives()
        self._update_mood(action.name)
        protagonist.clamp()
        event = Event(clock.day, clock.slot, action.name, reason, outcome)
        self.state.events.append(event)
        self._remember(event)
        self._update_goal()
        self._update_gate_alert()
        clock.advance()
        return event

    def _update_economy(self) -> None:
        """Set one deterministic daily cost-of-living condition."""
        day = self.state.clock.day
        if self.state.economy_day == day:
            return
        self.state.economy_day = day
        economy_rng = random.Random(self.seed * 65_537 + day)
        self.state.wage_modifier = economy_rng.choice((85, 95, 100, 105, 115))
        self.state.meal_cost = economy_rng.choice((500, 600, 700, 800))

    def _apply_economic_variation(self, action_name: str, money_before: int) -> None:
        p = self.state.protagonist
        if action_name == "Part-time work":
            p.money += 2_200 * (self.state.wage_modifier - 100) // 100
        elif action_name == "Eat" and money_before >= 600 and self.state.meal_cost != 600:
            difference = self.state.meal_cost - 600
            p.money = max(0, p.money - difference)

    def _seek_treatment(self) -> str:
        p = self.state.protagonist
        severity = p.injury_severity
        full_cost = 700 + severity * 550
        cost = min(p.money, full_cost)
        assistance = full_cost - cost
        p.money -= cost
        healed = min(35 + severity * 5, 100 - p.health)
        p.health += healed
        p.energy += 8
        p.stress -= 12
        p.injury_severity = max(0, severity - 2)
        p.injuries = max(0, p.injuries - 1)
        p.treatments_received += 1
        support = (f" Emergency assistance covered ¥{assistance:,}."
                   if assistance else "")
        return (f"Received clinic treatment for ¥{cost:,}; recovered {healed} health "
                f"and reduced injury severity to {p.injury_severity}.{support}")

    def _update_objectives(self) -> None:
        p = self.state.protagonist
        self.state.objective_progress["financial_buffer"] = min(3, p.money // p.rent_cost)
        self.state.objective_progress["recovery"] = min(3, p.treatments_received)
        steps = max((len(item.preparation_steps)
                     for item in self.state.portal_investigations.values()), default=0)
        self.state.objective_progress["portal_readiness"] = min(3, steps)
    def _weather(self):
        return next(weather for weather in SUMMER_WEATHER if weather.name == self.state.weather)

    def _update_weather(self) -> None:
        clock = self.state.clock
        if self.state.weather_day == clock.day:
            return
        weather = summer_weather(self.rng)
        self.state.weather = weather.name
        self.state.temperature_c = weather.temperature_c
        self.state.weather_day = clock.day

    def _apply_weather_cost(self, action_name: str) -> None:
        weather = self._weather()
        if action_name in {"Train", "Gate mission", "Guild patrol", "Part-time work"}:
            self.state.protagonist.energy -= weather.energy_modifier

    def _develop_from_action(self, action_name: str) -> None:
        """Apply small, explainable growth from relevant lived experience."""
        p = self.state.protagonist
        if action_name == "Guild patrol" and p.health >= 45:
            if p.combat_experience % 8 == 0:
                p.perception += 1
            if p.combat_experience % 12 == 0:
                p.endurance += 1
        elif action_name == "Gate mission":
            p.ability_mastery += 2 if p.health >= 40 else 1
        p.clamp()

    def run(self, steps: int) -> list[Event]:
        return [self.step() for _ in range(steps)]

    def _apply_passive_needs(self) -> None:
        p = self.state.protagonist
        if p.hunger >= 85:
            p.health -= 8
        if p.energy <= 10:
            p.health -= 5
            p.stress += 8

    def _update_mood(self, action_name: str) -> None:
        p = self.state.protagonist
        if action_name == "Gate mission":
            p.morale += 3 if p.health >= 55 else -7
        elif action_name == "Rent deadline":
            p.morale += 4 if p.rent_arrears == 0 else -12
        elif action_name in {"Rest", "Eat"}:
            p.morale += 2
        if p.health < 35 or p.stress >= 80:
            p.mood = "Overwhelmed"
        elif p.energy < 25:
            p.mood = "Exhausted"
        elif p.morale >= 70:
            p.mood = "Hopeful"
        elif p.morale >= 50:
            p.mood = "Steady"
        elif p.stress >= 55:
            p.mood = "Anxious"
        else:
            p.mood = "Uneasy"
        p.clamp()

    def _story_anchor_event(self, anchor: StoryAnchor) -> Event:
        """Resolve a fixed story beat through the world Ren has actually built."""
        state = self.state
        protagonist = state.protagonist
        rank_score = {"Unranked": 0, "F": 1, "E": 2, "D": 3, "C": 4}.get(
            protagonist.hunter_rank, 0)
        trusted_allies = sum(
            relationship.trust >= 15
            for relationship in protagonist.relationships.values())
        readiness = rank_score + trusted_allies + len(state.discovered_portals)
        if readiness >= 8:
            outcome_tier = "prepared"
        elif readiness >= 4:
            outcome_tier = "resilient"
        else:
            outcome_tier = "isolated"
        resolution = anchor.outcome(outcome_tier)
        resolution += f" Scene: {anchor.scene}"
        focused_allies = [
            name for name in anchor.focus_npcs
            if name in protagonist.relationships and
            protagonist.relationships[name].trust >= 15]
        if focused_allies:
            resolution += f" Trusted support: {', '.join(focused_allies)}."
        if state.discovered_portals:
            resolution += f" Latest portal evidence: {state.discovered_portals[-1]}."
            resolution += f" Consequence: {anchor.portal_consequence}"
        if anchor.international_link is not None:
            resolution += f" International link: {anchor.international_link}"
        if anchor.ending:
            resolution += " This became the ending of his three-year chronicle."
        state.calendar_events_seen.append(anchor.key)
        state.story_outcomes[anchor.key] = outcome_tier
        return Event(
            state.clock.day, state.clock.slot, anchor.title,
            "a fixed six-month story anchor arrived (world event)",
            f"{anchor.premise} {resolution}")

    def _special_event(self) -> Event | None:
        clock = self.state.clock
        p = self.state.protagonist

        story_anchor = next(
            (anchor for anchor in STORY_ANCHORS
             if anchor.day == clock.day and
             anchor.key not in self.state.calendar_events_seen),
            None)
        if story_anchor is not None and clock.slot is TimeSlot.MORNING:
            return self._story_anchor_event(story_anchor)

        if clock.day == 7 and clock.slot.value == "Evening" and "Tanabata" not in self.state.calendar_events_seen:
            self.state.calendar_events_seen.append("Tanabata")
            p.stress -= 8
            p.relationships.get("Aiko Sato") and p.relationships["Aiko Sato"].change(2, 3)
            p.clamp()
            return Event(clock.day, clock.slot, "Tanabata evening",
                         "the neighborhood festival arrived on the calendar (world event)",
                         "Stopped beneath the paper wishes and festival lights; the city felt hopeful for once.")

        if clock.day == 3 and clock.slot.value == "Afternoon" and not p.awakened:
            p.money -= min(p.money, 320)
            p.location = "Tokyo Awakening Bureau"
            p.awakened = True
            p.hunter_rank = "F"
            p.ability = "Threat Sense"
            p.ability_mastery = 1
            p.reputation += 1
            return Event(clock.day, clock.slot, "Awakening assessment",
                         "a city gate alert triggered Ren's mandatory screening (world event)",
                         "Awakened at Rank F with Threat Sense.")

        if clock.day == 4 and clock.slot.value == "Morning" and p.awakened and not p.guild_registered:
            fare = min(p.money, travel_cost(p.location, "Tokyo Hunter Guild"))
            p.money -= fare
            p.location = "Tokyo Hunter Guild"
            p.guild_registered = True
            p.relationships["Aiko Sato"] = Relationship(
                name="Aiko Sato", role="F-rank guild clerk", trust=3, familiarity=5, meetings=1,
                loyalty=4
            )
            self.state.relationship_network["Aiko Sato"] = {"Daichi Mori": 18, "Mei Kuroda": -8}
            p.reputation += 1
            self.state.gate_alert_level = 2
            event = Event(clock.day, clock.slot, "Guild registration",
                         "newly awakened citizens must register before accepting hunter work (world event)",
                         f"Aiko Sato issued an F-rank license; travel and filing cost ¥{fare:,}.")
            return event

        introductions = {
            (5, "Morning"): ("Daichi Mori", 4, 3,
                "Daichi Mori assessed Ren for patrol duty. “Be early, carry water, and follow the retreat call.”"),
            (6, "Afternoon"): ("Mei Kuroda", 1, 2,
                "Mei Kuroda noticed Threat Sense in Ren's report and asked him to document unusual portal clues."),
            (9, "Evening"): ("Haruto Ishikawa", 3, 3,
                "Haruto Ishikawa introduced himself at the supply counter and quietly explained which cheap gear fails."),
        }
        introduction = introductions.get((clock.day, clock.slot.value))
        if introduction and introduction[0] not in p.relationships:
            name, trust, familiarity, outcome = introduction
            profile = NPCS[name]
            p.relationships[name] = Relationship(name, profile.role, trust=trust,
                                                  familiarity=familiarity, meetings=1, loyalty=2)
            self.state.relationship_network.setdefault(name, {})
            if name == "Daichi Mori":
                self.state.relationship_network[name]["Aiko Sato"] = 18
            elif name == "Mei Kuroda":
                self.state.relationship_network[name]["Aiko Sato"] = -8
            else:
                self.state.relationship_network[name]["Daichi Mori"] = 7
            return Event(clock.day, clock.slot, f"Meet {name}",
                         "Ren's routine crossed another recurring life in Tokyo (world event)", outcome)

        if clock.day == p.rent_due_day and clock.slot.value == "Morning":
            paid = min(p.money, p.rent_cost)
            p.money -= paid
            unpaid = p.rent_cost - paid
            p.rent_arrears += unpaid
            p.stress += 5 if unpaid == 0 else 25
            p.clamp()
            self.state.rent_payments += int(unpaid == 0)
            outcome = (f"Paid ¥{paid:,} rent in full." if unpaid == 0 else
                       f"Paid ¥{paid:,}; ¥{unpaid:,} became rent arrears.")
            return Event(clock.day, clock.slot, "Rent deadline",
                         "the apartment payment was automatically due (world event)", outcome)

        return None

    def _resolve_due_consequence(self) -> str | None:
        """Apply one due world consequence without consuming Ren's action slot."""
        p = self.state.protagonist
        consequence = next((item for item in self.state.delayed_consequences
                            if not item.resolved and
                            item.due_day <= self.state.clock.day), None)
        if consequence is not None:
            index = self.state.delayed_consequences.index(consequence)
            self.state.delayed_consequences[index] = DelayedConsequence(
                consequence.due_day, consequence.source, consequence.people,
                consequence.description, True)
            reactions = []
            for name in consequence.people:
                relationship = p.relationships.get(name)
                if relationship is not None:
                    trust_change = 2 if "verified" in consequence.description else -2
                    relationship.change(trust_change, 1)
                    reactions.append(f"{name}'s trust {'rose' if trust_change > 0 else 'fell'}")
            reaction_text = (
                f" {'; '.join(reactions)}." if reactions else ".")
            return f"{consequence.description}{reaction_text}"
        return None

    def _update_npc_schedules(self) -> None:
        clock = self.state.clock
        self.state.npc_locations = {
            name: scheduled_location(name, clock.slot.value, clock.day)
            for name in NPCS
        }

    def _scheduled_social_encounter(self, action_name: str) -> str:
        """Resolve one autonomous conversation when Ren's routine overlaps an NPC schedule."""
        p = self.state.protagonist
        day = self.state.clock.day
        for name, location in self.state.npc_locations.items():
            key = f"{day}:{name}"
            relationship = p.relationships.get(name)
            if (relationship is None or location != p.location or
                    key in self.state.social_encounters_seen or action_name == "Rest"):
                continue
            context = self._social_context(action_name)
            trust_change = 2 if p.mood in {"Hopeful", "Steady"} else 1
            exchange = resolve_contextual_encounter(
                p, name, context, day, trust_change)
            self.state.social_encounters_seen.append(key)
            return (f"At {location}, {name} chose to approach me: “{exchange.npc_line}” "
                    f"Ren answered: “{exchange.ren_line}” {name} seemed "
                    f"{exchange.reaction}; the exchange made them more familiar.")
        return ""

    def _social_context(self, action_name: str) -> str:
        """Choose the authored conversation situation from Ren's lived state."""
        p = self.state.protagonist
        if p.health < 55 or p.injury_severity > 1:
            return "injury"
        if action_name == "Gate mission":
            return "portal"
        if action_name == "Guild patrol" or p.location == "Tokyo Hunter Guild":
            return "guild"
        return "routine"

    def _record_portal_investigation(self, portal) -> tuple[PortalInvestigation, bool]:
        investigation = self.state.portal_investigations.get(portal.name)
        created = investigation is None
        if investigation is None:
            investigation = PortalInvestigation(portal.name, risk=1)
            self.state.portal_investigations[portal.name] = investigation
        if portal.clue not in investigation.clues_found:
            investigation.clues_found.append(portal.clue)
            investigation.progress = min(100, investigation.progress + 25)
        else:
            investigation.progress = min(100, investigation.progress + 8)
        investigation.risk = min(100, investigation.risk + 4)
        investigation.last_investigated_day = self.state.clock.day
        return investigation, created

    def _queue_portal_consequence(self, portal_name: str, progress: int) -> None:
        if any(item.source == portal_name for item in self.state.delayed_consequences):
            return
        people = tuple(name for name in ("Mei Kuroda", "Daichi Mori", "Aiko Sato")
                       if name in self.state.protagonist.relationships)
        description = (f"Evidence from {portal_name} was verified and changed the guild patrol route"
                       if progress >= 25 else
                       f"An incomplete report from {portal_name} sent a patrol toward uncertain ground")
        self.state.delayed_consequences.append(DelayedConsequence(
            self.state.clock.day + 2, portal_name, people, description))

    def _remember(self, event: Event, importance: int | None = None) -> None:
        p = self.state.protagonist
        important_actions = {
            "Awakening assessment": 10, "Guild registration": 8,
            "Gate mission": 7, "Rent deadline": 8, "Talk with Aiko": 4,
        }
        rating = (importance if importance is not None else
                  6 if event.action.startswith("Meet ") else
                  important_actions.get(event.action))
        if rating is None:
            return
        p.memories.append(Memory(event.day, f"{event.action}: {event.outcome}", rating))
        p.memories.sort(key=lambda memory: (-memory.importance, -memory.day))
        del p.memories[12:]

    def _update_goal(self) -> None:
        p = self.state.protagonist
        if not p.awakened:
            p.current_goal = "Earn enough yen to pay rent"
        elif not p.guild_registered:
            p.current_goal = "Register with the Tokyo Hunter Guild"
        elif p.rent_arrears:
            p.current_goal = f"Clear ¥{p.rent_arrears:,} in rent arrears"
        elif p.hunter_rank == "F":
            p.current_goal = "Survive gate work and reach Rank E"
        else:
            p.current_goal = f"Build a stable life as a Rank {p.hunter_rank} hunter"

    def _resolve_gate_mission(self, use_preparation: bool = True) -> str:
        p = self.state.protagonist
        fare = min(p.money, travel_cost(p.location, "Adachi Gate Zone"))
        p.money -= fare
        p.location = "Adachi Gate Zone"
        p.missions_attempted += 1
        alert = self.state.gate_alert_level
        encounters = gate_encounters_for_rank(p.hunter_rank)
        rank_bonus = {"Unranked": 0, "F": 0, "E": 1, "D": 2, "C": 3}[p.hunter_rank]
        maximum_index = min(len(encounters) - 1, max(0, alert - 1) + rank_bonus)
        encounter = encounters[self.rng.randint(0, maximum_index)]
        portal = (next(item for item in PORTALS if item.name == self.state.active_portal_plan)
                  if self.state.active_portal_plan else
                  PORTALS[self.rng.randrange(len(PORTALS))])
        newly_discovered = portal.name not in self.state.discovered_portals
        if newly_discovered:
            self.state.discovered_portals.append(portal.name)
        investigation, _ = self._record_portal_investigation(portal)
        weather = self._weather()
        difficulty = encounter.difficulty + alert * 3 + weather.gate_difficulty
        environmental_difficulty = {
            "ice": 5, "swamp": 6, "underground": 3, "urban tower": 4,
            "forest": 3, "urban ruin": 4,
        }[portal.environment]
        difficulty += environmental_difficulty
        preparation_bonus = 0
        cooperation_text = ""
        used_preparation = (use_preparation and
                            self.state.active_portal_plan == portal.name)
        if used_preparation:
            p.prepared_missions_attempted += 1
            preparation_bonus = investigation.preparation_bonus
            if investigation.cooperating_npc:
                investigation.joint_missions += 1
                cooperation_text = f" {investigation.cooperating_npc} supported the prepared approach."
                self.state.objective_scores["relationships"] += 2
            investigation.preparation_bonus = 0
            investigation.preparation_strategy = "Used"
            investigation.cooperating_npc = None
            self.state.active_portal_plan = None
        preparation = []
        if p.health < 60 and p.consume_item("Trauma Foam"):
            healed = min(35, 100 - p.health)
            p.health += healed
            preparation.append(f"used Trauma Foam (+{healed} health)")
        if p.health < 68 and p.consume_item("Healing Gel"):
            healed = min(22, 100 - p.health)
            p.health += healed
            preparation.append(f"used Healing Gel (+{healed} health)")
        if p.energy < 38 and p.consume_item("Focus Ampoule"):
            restored = min(30, 100 - p.energy)
            p.energy += restored
            preparation.append(f"used Focus Ampoule (+{restored} energy)")
        if p.energy < 48 and p.consume_item("Energy Drink"):
            restored = min(18, 100 - p.energy)
            p.energy += restored
            preparation.append(f"used Energy Drink (+{restored} energy)")
        roll = p.combat_readiness + preparation_bonus + self.rng.randint(-12, 12)
        p.energy -= 28
        p.hunger += 18
        p.stress += 12
        self.state.gate_alert_level = max(0, alert - 2)
        prep_text = f" Preparation: {', '.join(preparation)}." if preparation else ""
        if roll >= difficulty:
            reward = encounter.reward
            points = encounter.rank_points
            p.money += reward
            p.rank_points += points
            p.combat_experience += 5
            p.missions_completed += 1
            if used_preparation:
                p.prepared_missions_completed += 1
            p.reputation += 2
            self.state.objective_scores["survival"] += 2
            self.state.objective_scores["stability"] += reward // 1000
            self.state.objective_scores["discovery"] += 3
            exposure = max(1, encounter.difficulty // 18)
            p.echo_fragments += exposure
            if p.missions_completed % 3 == 0:
                p.perception += 1
            p.ability_mastery += 3
            promotion = self._promote_if_eligible()
            suffix = f" Promoted to Rank {promotion}!" if promotion else ""
            echo = (" Echo Fragment awakened from varied survival experience!"
                    if p.echo_fragments >= 8 and p.ability == "Threat Sense" else "")
            if echo:
                p.ability = "Threat Sense / Echo Fragment"
            clue = f" Discovered {portal.name}: {portal.clue}." if newly_discovered else ""
            social = self._portal_social_reaction(portal.name)
            self._queue_portal_consequence(portal.name, investigation.progress)
            return (f"Cleared {encounter.name} inside {portal.name} ({portal.environment}; "
                    f"hazard: {portal.hazard}) in {weather.name.lower()} weather "
                    f"(roll {roll} vs {difficulty}) for ¥{reward:,} "
                    f"and {points} rank points; gained {exposure} ability exposure; "
                    f"fare cost ¥{fare:,}.{prep_text}{clue} Investigation reached "
                    f"{investigation.progress}%.{cooperation_text}{social}{suffix}{echo}")
        armor_reduction = ITEMS[p.equipped_armor].combat_bonus if p.equipped_armor else 0
        damage = max(8, difficulty - roll + 8 + encounter.damage_bonus - armor_reduction)
        p.health -= damage
        p.injuries += 1
        p.combat_experience += 2
        p.ability_mastery += 1
        self.state.objective_scores["survival"] -= 2
        clue = f" Discovered {portal.name}: {portal.clue}." if newly_discovered else ""
        social = self._portal_social_reaction(portal.name)
        self._queue_portal_consequence(portal.name, investigation.progress)
        return (f"Retreated from {encounter.name} inside {portal.name} ({portal.environment}; "
                f"hazard: {portal.hazard}) in {weather.name.lower()} weather "
                f"(roll {roll} vs {difficulty}); suffered "
                f"{damage} damage and received no reward. Fare cost ¥{fare:,}.{prep_text}{clue} "
                f"Investigation reached {investigation.progress}%.{cooperation_text}{social}")

    def _prepare_portal(self) -> str:
        """Create one hazard-aware plan, including a compatible available ally."""
        p = self.state.protagonist
        if self.state.portal_investigations:
            investigation = min(
                self.state.portal_investigations.values(),
                key=lambda item: (item.progress, -item.risk, item.portal_name),
            )
            portal = next(item for item in PORTALS if item.name == investigation.portal_name)
        else:
            portal = PORTALS[self.rng.randrange(len(PORTALS))]
            investigation, _ = self._record_portal_investigation(portal)
        strategies = {
            "ice": ("thermal route kit", 10), "swamp": ("sealed breathing kit", 11),
            "underground": ("escape-line mapping", 8), "urban tower": ("room-marking protocol", 9),
            "forest": ("trail-anchor protocol", 8), "urban ruin": ("cinder protection", 9),
        }
        strategy, bonus = strategies[portal.environment]
        stages = (strategy, "route rehearsal", "contingency cache")
        stage = stages[min(len(investigation.preparation_steps), len(stages) - 1)]
        if stage not in investigation.preparation_steps:
            investigation.preparation_steps.append(stage)
        bonus += (len(investigation.preparation_steps) - 1) * 3
        preferred = "Mei Kuroda" if investigation.progress < 60 else "Daichi Mori"
        ally = preferred if preferred in p.relationships else (
            "Aiko Sato" if "Aiko Sato" in p.relationships else None)
        conflict = ""
        if ally == "Mei Kuroda":
            bonus += 3
            self.state.objective_scores["discovery"] += 3
            conflict = " Mei prioritized evidence even when the guild preferred a quick clearance."
        elif ally == "Daichi Mori":
            bonus += 4
            self.state.objective_scores["survival"] += 3
            conflict = " Daichi insisted that team survival outranked collecting every clue."
        investigation.preparation_strategy = strategy
        investigation.preparation_bonus = bonus
        investigation.cooperating_npc = ally
        investigation.reported_to.extend([ally] if ally and ally not in investigation.reported_to else [])
        self.state.active_portal_plan = portal.name
        p.energy -= 10
        p.stress -= 3
        ally_text = f" with {ally}" if ally else " alone"
        return (f"Prepared {stage}{ally_text} for {portal.name} ({portal.environment}), "
                f"banking +{bonus} mission readiness.{conflict}")

    def _portal_social_reaction(self, portal_name: str) -> str:
        """Let discoveries change relationships and produce an in-world response."""
        p = self.state.protagonist
        if "Mei Kuroda" in p.relationships:
            relationship = p.relationships["Mei Kuroda"]
            relationship.change(2, 2)
            relationship.loyalty = min(100, relationship.loyalty + 1)
            line = contextual_line("Mei Kuroda", "portal", relationship)
            return f' Mei later reacted to the {portal_name} report: “{line}”'
        if "Daichi Mori" in p.relationships:
            relationship = p.relationships["Daichi Mori"]
            relationship.change(1, 1)
        return ""

    def _promote_if_eligible(self) -> str | None:
        p = self.state.protagonist
        order = {"F": 0, "E": 1, "D": 2, "C": 3}
        for threshold, rank in RANK_THRESHOLDS:
            if p.rank_points >= threshold and order.get(rank, 0) > order.get(p.hunter_rank, -1):
                p.hunter_rank = rank
                return rank
        return None

    def _update_gate_alert(self) -> None:
        if self.rng.random() < 0.12:
            self.state.gate_alert_level = min(3, self.state.gate_alert_level + 1)
            self.state.protagonist.gates_witnessed += 1
        elif self.state.gate_alert_level:
            self.state.gate_alert_level -= 1
