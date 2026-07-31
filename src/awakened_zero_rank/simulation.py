from __future__ import annotations

import random

from .agent import UtilityAgent
from .dialogue import contextual_line, resolve_aiko_dialogue
from .content import NPCS, PORTALS, scheduled_location
from .environment import SUMMER_WEATHER, summer_weather
from .models import (DelayedConsequence, Event, Memory, PortalInvestigation,
                     Relationship, WorldState)
from .world import GATE_ENCOUNTERS, ITEMS, travel_cost


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
        self._update_npc_schedules()
        special = self._special_event()
        if special is not None:
            self.state.events.append(special)
            self._remember(special)
            self._update_goal()
            clock.advance()
            return special
        if selected_action is None:
            action, reason = self.agent.choose(
                protagonist, clock.slot, self.state.gate_alert_level, self.state.weather
            )
        else:
            from .actions import available_actions
            choices = {candidate.name: candidate for candidate in available_actions(protagonist)}
            if selected_action not in choices:
                raise ValueError(f"Action {selected_action!r} is unavailable")
            action = choices[selected_action]
            reason = "a learning policy selected this valid strategy (policy action)"
        if action.name == "Visit hunter shop" and self._weather().shop_closed:
            outcome = "The hunter supply shop was closed under the severe-weather advisory."
        else:
            if action.name == "Gate mission":
                outcome = self._resolve_gate_mission()
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
        if action.name == "Visit hunter shop":
            self.state.shop_visits += 1
        self._apply_passive_needs()
        self._apply_weather_cost(action.name)
        self._develop_from_action(action.name)
        self._update_mood(action.name)
        protagonist.clamp()
        event = Event(clock.day, clock.slot, action.name, reason, outcome)
        self.state.events.append(event)
        self._remember(event)
        self._update_goal()
        self._update_gate_alert()
        clock.advance()
        return event

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

    def _special_event(self) -> Event | None:
        clock = self.state.clock
        p = self.state.protagonist

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

        consequence = next((item for item in self.state.delayed_consequences
                            if not item.resolved and item.due_day <= clock.day), None)
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
            return Event(clock.day, clock.slot, "Investigation consequence",
                         "an earlier portal decision finally affected other people (delayed event)",
                         f"{consequence.description} {'; '.join(reactions)}.")
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
            context = "portal" if action_name in {"Gate mission", "Guild patrol"} else "routine"
            line = contextual_line(name, context, relationship)
            trust_change = 2 if p.mood in {"Hopeful", "Steady"} else 1
            relationship.change(trust_change, 2)
            self.state.social_encounters_seen.append(key)
            return (f"At {location}, {name} chose to approach me: “{line}” "
                    f"The brief exchange made us more familiar.")
        return ""

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

    def _resolve_gate_mission(self) -> str:
        p = self.state.protagonist
        fare = min(p.money, travel_cost(p.location, "Adachi Gate Zone"))
        p.money -= fare
        p.location = "Adachi Gate Zone"
        p.missions_attempted += 1
        alert = self.state.gate_alert_level
        maximum_index = min(len(GATE_ENCOUNTERS) - 1, max(0, alert - 1))
        encounter = GATE_ENCOUNTERS[self.rng.randint(0, maximum_index)]
        portal = PORTALS[self.rng.randrange(len(PORTALS))]
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
        preparation = []
        if p.health < 68 and p.consume_item("Healing Gel"):
            healed = min(22, 100 - p.health)
            p.health += healed
            preparation.append(f"used Healing Gel (+{healed} health)")
        if p.energy < 48 and p.consume_item("Energy Drink"):
            restored = min(18, 100 - p.energy)
            p.energy += restored
            preparation.append(f"used Energy Drink (+{restored} energy)")
        roll = p.combat_readiness + self.rng.randint(-12, 12)
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
            p.reputation += 2
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
                    f"{investigation.progress}%.{social}{suffix}{echo}")
        armor_reduction = ITEMS[p.equipped_armor].combat_bonus if p.equipped_armor else 0
        damage = max(8, difficulty - roll + 8 + encounter.damage_bonus - armor_reduction)
        p.health -= damage
        p.injuries += 1
        p.combat_experience += 2
        p.ability_mastery += 1
        clue = f" Discovered {portal.name}: {portal.clue}." if newly_discovered else ""
        social = self._portal_social_reaction(portal.name)
        self._queue_portal_consequence(portal.name, investigation.progress)
        return (f"Retreated from {encounter.name} inside {portal.name} ({portal.environment}; "
                f"hazard: {portal.hazard}) in {weather.name.lower()} weather "
                f"(roll {roll} vs {difficulty}); suffered "
                f"{damage} damage and received no reward. Fare cost ¥{fare:,}.{prep_text}{clue} "
                f"Investigation reached {investigation.progress}%.{social}")

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
