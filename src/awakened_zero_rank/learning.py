"""Training episodes, tabular Q-learning, and utility-policy comparison.

The core adapter stays dependency-free. Installing the ``training`` extra upgrades
its compatible fallback spaces to Gymnasium's official Env, Discrete, and Box types.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass, field
import hashlib
import json
import math
import random
from pathlib import Path

try:
    import gymnasium as gym
    import numpy as np
except ImportError:  # The core simulation remains dependency-free.
    gym = None
    np = None

from .actions import available_actions
from .models import Relationship, SLOTS
from .simulation import Simulation


ACTION_NAMES = (
    "Eat", "Rest", "Part-time work", "Pay rent arrears", "Study", "Train",
    "Visit hunter shop",
    "Talk with Aiko", "Guild patrol", "Prepare portal", "Gate mission", "Seek treatment",
)
REWARD_COMPONENTS = ("survival", "stability", "progress", "social")
EVALUATION_CONDITIONS = ("standard", "financial_pressure", "injury_recovery",
                         "gate_crisis")
MAX_DOMINANCE_REGRESSION = 0.15


@dataclass(frozen=True)
class Transition:
    observation: tuple[float, ...]
    reward: float
    action: str
    valid_actions: tuple[str, ...]
    event_outcome: str
    reward_components: tuple[tuple[str, float], ...] = ()
    resolved_action: str = ""


class LearningEnvironment:
    """Small strategic interface suitable for accelerated agent experiments."""

    def __init__(self, seed: int = 42) -> None:
        self.simulation = Simulation(seed=seed)

    @property
    def valid_actions(self) -> tuple[str, ...]:
        names = {action.name for action in available_actions(self.simulation.state.protagonist)}
        return tuple(name for name in ACTION_NAMES if name in names)

    def observe(self) -> tuple[float, ...]:
        state, p = self.simulation.state, self.simulation.state.protagonist
        relationship = p.relationships.get("Aiko Sato")
        network_trust = sum(r.trust for r in p.relationships.values())
        return (
            p.health / 100, p.energy / 100, p.hunger / 100, p.stress / 100,
            min(p.money, 50_000) / 50_000, p.combat_readiness / 100,
            p.rank_points / 100, state.gate_alert_level / 3,
            SLOTS.index(state.clock.slot) / (len(SLOTS) - 1),
            (relationship.trust if relationship else 0) / 100,
            (relationship.tension if relationship else 0) / 100,
            p.morale / 100,
            max(-1, min(1, network_trust / 400)),
            len(state.discovered_portals) / 6,
            int(state.active_portal_plan is not None),
            min(1, sum(i.preparation_bonus for i in state.portal_investigations.values()) / 30),
            min(1, sum(i.joint_missions for i in state.portal_investigations.values()) / 10),
            min(1, sum(state.objective_scores.values()) / 400),
            p.injury_severity / 5,
            self.simulation.state.wage_modifier / 115,
            self.simulation.state.meal_cost / 800,
            min(1, sum(state.objective_progress.values()) / 9),
        )

    def action_mask(self) -> tuple[int, ...]:
        valid = set(self.valid_actions)
        return tuple(int(name in valid) for name in ACTION_NAMES)

    def step(self, action: str) -> Transition:
        if action not in self.valid_actions:
            raise ValueError(f"Invalid action {action!r}; valid actions: {self.valid_actions}")
        before = self.score_components()
        event = self.simulation.step(action)
        components = self._component_delta(before)
        reward = round(sum(value for _, value in components), 3)
        components = self._reconcile_components(components, reward)
        return Transition(self.observe(), reward, action, self.valid_actions,
                          event.outcome, components, event.action)

    def baseline_step(self) -> Transition:
        before = self.score_components()
        event = self.simulation.step()
        components = self._component_delta(before)
        reward = round(sum(value for _, value in components), 3)
        components = self._reconcile_components(components, reward)
        return Transition(self.observe(), reward, event.action, self.valid_actions,
                          event.outcome, components, event.action)

    def score_components(self) -> dict[str, float]:
        p = self.simulation.state.protagonist
        survival = p.health * 0.5 + p.energy * 0.12 - p.hunger * 0.12 - p.stress * 0.08
        stability = min(p.money, p.rent_cost * 2) / 350 - p.rent_arrears / 250
        progress = p.rank_points * 0.7 + p.missions_completed * 2 + p.ability_mastery * 0.2
        social = sum((r.trust - r.tension) * 0.08 for r in p.relationships.values())
        return {"survival": survival, "stability": stability,
                "progress": progress, "social": social}

    def _component_delta(self, before: dict[str, float]) -> tuple[tuple[str, float], ...]:
        after = self.score_components()
        return tuple((name, after[name] - before[name])
                     for name in REWARD_COMPONENTS)

    @staticmethod
    def _reconcile_components(components: tuple[tuple[str, float], ...],
                              reward: float) -> tuple[tuple[str, float], ...]:
        reconciled = list(components)
        name, value = reconciled[-1]
        reconciled[-1] = (name, value + reward - sum(item for _, item in reconciled))
        return tuple(reconciled)

    def _score(self) -> float:
        return sum(self.score_components().values())

class DiscreteSpace:
    def __init__(self, n: int, seed: int | None = None) -> None:
        self.n, self._rng = n, random.Random(seed)

    def seed(self, seed: int | None = None) -> list[int | None]:
        self._rng.seed(seed)
        return [seed]

    def sample(self, mask: tuple[int, ...] | None = None) -> int:
        choices = list(range(self.n) if mask is None else [i for i, valid in enumerate(mask) if valid])
        if not choices:
            raise ValueError("Cannot sample when no actions are valid")
        return self._rng.choice(choices)

    def contains(self, value: object) -> bool:
        return isinstance(value, int) and not isinstance(value, bool) and 0 <= value < self.n


class ObservationSpace:
    shape = (22,)

    @staticmethod
    def contains(value: object) -> bool:
        return (isinstance(value, (tuple, list)) and len(value) == 22 and
                all(isinstance(item, (int, float)) and math.isfinite(item) for item in value))


class TrainingEnvironment(gym.Env if gym else object):
    """Gymnasium-style fixed-horizon episodes with integer policy actions."""
    metadata = {"render_modes": []}

    def __init__(self, seed: int = 42, horizon: int = 120) -> None:
        if horizon < 1:
            raise ValueError("horizon must be at least 1")
        self.initial_seed, self.horizon = seed, horizon
        if gym:
            self.action_space = gym.spaces.Discrete(len(ACTION_NAMES), seed=seed)
            self.observation_space = gym.spaces.Box(
                low=-float("inf"), high=float("inf"), shape=(22,), dtype=np.float32
            )
        else:
            self.action_space = DiscreteSpace(len(ACTION_NAMES), seed)
            self.observation_space = ObservationSpace()
        self.environment = LearningEnvironment(seed)
        self.elapsed_steps, self._finished = 0, False

    @property
    def simulation(self) -> Simulation:
        return self.environment.simulation

    def action_masks(self) -> tuple[int, ...]:
        return self.environment.action_mask()

    def reset(self, *, seed: int | None = None, options: dict | None = None
              ) -> tuple[tuple[float, ...], dict]:
        del options
        if gym:
            super().reset(seed=seed)
        episode_seed = self.initial_seed if seed is None else seed
        self.environment = LearningEnvironment(episode_seed)
        self.action_space.seed(episode_seed)
        self.elapsed_steps, self._finished = 0, False
        observation = self.environment.observe()
        if np is not None:
            observation = np.asarray(observation, dtype=np.float32)
        return observation, {"action_mask": self.action_masks(), "seed": episode_seed}

    def step(self, action: int) -> tuple[tuple[float, ...], float, bool, bool, dict]:
        if self._finished:
            raise RuntimeError("Episode is finished; call reset() before step()")
        if not self.action_space.contains(action):
            raise ValueError(f"Action must be an integer from 0 to {len(ACTION_NAMES) - 1}")
        mask = self.action_masks()
        if not mask[action]:
            raise ValueError(f"Action {action} ({ACTION_NAMES[action]}) is currently invalid")
        transition = self.environment.step(ACTION_NAMES[action])
        self.elapsed_steps += 1
        terminated = self.simulation.state.protagonist.health <= 0
        truncated = self.elapsed_steps >= self.horizon and not terminated
        self._finished = terminated or truncated
        info = {"action_mask": self.action_masks(), "action_name": transition.action,
                "event_outcome": transition.event_outcome, "elapsed_steps": self.elapsed_steps,
                "reward_components": dict(transition.reward_components),
                "resolved_action": transition.resolved_action}
        observation = transition.observation
        if np is not None:
            observation = np.asarray(observation, dtype=np.float32)
        return observation, transition.reward, terminated, truncated, info


GymnasiumEnvironment = TrainingEnvironment


@dataclass(frozen=True)
class QLearningConfig:
    episodes: int = 40
    horizon: int = 120
    learning_rate: float = 0.15
    discount_factor: float = 0.95
    epsilon_start: float = 0.30
    epsilon_end: float = 0.05
    exploration_bonus: float = 0.40
    curriculum: bool = True

    def __post_init__(self) -> None:
        if self.episodes < 1 or self.horizon < 1:
            raise ValueError("episodes and horizon must be at least 1")
        if not 0 < self.learning_rate <= 1 or not 0 <= self.discount_factor <= 1:
            raise ValueError("learning_rate and discount_factor must be between 0 and 1")
        if not 0 <= self.epsilon_end <= self.epsilon_start <= 1:
            raise ValueError("epsilon must satisfy 0 <= end <= start <= 1")
        if self.exploration_bonus < 0:
            raise ValueError("exploration_bonus cannot be negative")


QTable = dict[tuple[int, ...], list[float]]


@dataclass(frozen=True)
class TrainingResult:
    training_seed: int
    config: QLearningConfig
    q_table: QTable = field(compare=True)
    episode_rewards: tuple[float, ...] = ()
    episode_seeds: tuple[int, ...] = ()
    training_rewards: tuple[float, ...] = ()
    state_count: int = 0


def abstract_state(observation) -> tuple[int, ...]:
    """Compress the 22-value observation into strategic categorical features."""
    indices = (0, 1, 2, 3, 4, 5, 6, 7, 8, 11, 13, 14, 18, 19, 20, 21)
    return tuple(max(0, min(3, math.floor(float(observation[index]) * 4)))
                 for index in indices)


def discretize(observation) -> tuple[int, ...]:
    """Backward-compatible name for the Milestone 18 state abstraction."""
    return abstract_state(observation)


def curriculum_reward(episode: int, episodes: int, reward: float,
                      components: dict[str, float], enabled: bool = True) -> float:
    """Apply phased shaping while retaining the environment reward for evaluation."""
    if not enabled:
        return reward
    progress = episode / max(1, episodes - 1)
    if progress < 1 / 3:
        adjustment = components["survival"] * 0.35 + components["stability"] * 0.25
    elif progress < 2 / 3:
        adjustment = components["stability"] * 0.20 + components["social"] * 0.10
    else:
        adjustment = components["progress"] * 0.35 + components["social"] * 0.10
    return round(reward + adjustment, 3)


def _greedy_action(values: list[float], mask: tuple[int, ...]) -> int:
    valid = [i for i, allowed in enumerate(mask) if allowed]
    return max(valid, key=lambda index: (values[index], -index))


def train_q_learning(training_seed: int, config: QLearningConfig | None = None) -> TrainingResult:
    """Train reproducible masked Q-learning with curriculum and count exploration."""
    config = config or QLearningConfig()
    rng, table = random.Random(training_seed), {}
    totals, shaped_totals, episode_seeds, visits = [], [], [], Counter()
    for episode in range(config.episodes):
        episode_seed = rng.randrange(2**31)
        episode_seeds.append(episode_seed)
        env = TrainingEnvironment(episode_seed, config.horizon)
        observation, info = env.reset(seed=episode_seed)
        total = shaped_total = 0.0
        epsilon = (config.epsilon_start if config.episodes == 1 else config.epsilon_start +
                   (config.epsilon_end - config.epsilon_start) * episode / (config.episodes - 1))
        while True:
            state = abstract_state(observation)
            values = table.setdefault(state, [0.0] * len(ACTION_NAMES))
            mask = info["action_mask"]
            valid = [index for index, allowed in enumerate(mask) if allowed]
            if rng.random() < epsilon:
                action = rng.choice(valid)
            else:
                action = max(valid, key=lambda index: (
                    values[index] + config.exploration_bonus /
                    math.sqrt(visits[(state, index)] + 1), -index))
            next_observation, reward, terminated, truncated, info = env.step(action)
            shaped = curriculum_reward(episode, config.episodes, reward,
                                       info["reward_components"], config.curriculum)
            next_state = abstract_state(next_observation)
            next_values = table.setdefault(next_state, [0.0] * len(ACTION_NAMES))
            future = 0.0 if terminated or truncated else next_values[
                _greedy_action(next_values, info["action_mask"])]
            visits[(state, action)] += 1
            values[action] += config.learning_rate * (
                shaped + config.discount_factor * future - values[action])
            observation, total, shaped_total = next_observation, total + reward, shaped_total + shaped
            if terminated or truncated:
                break
        totals.append(round(total, 3))
        shaped_totals.append(round(shaped_total, 3))
    return TrainingResult(training_seed, config, table, tuple(totals), tuple(episode_seeds),
                          tuple(shaped_totals), len(table))
CHECKPOINT_VERSION = 2


def _checkpoint_data(result: TrainingResult) -> dict:
    return {
        "checkpoint_version": CHECKPOINT_VERSION,
        "encoder": "strategic-v2",
        "action_names": ACTION_NAMES,
        "training_seed": result.training_seed,
        "config": asdict(result.config),
        "episode_rewards": result.episode_rewards,
        "episode_seeds": result.episode_seeds,
        "training_rewards": result.training_rewards,
        "state_count": result.state_count,
        "q_table": [
            {"state": state, "values": values}
            for state, values in sorted(result.q_table.items())
        ],
    }


def checkpoint_digest(result: TrainingResult) -> str:
    payload = json.dumps(_checkpoint_data(result), sort_keys=True,
                         separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def save_checkpoint(result: TrainingResult, path: str | Path) -> Path:
    """Write a deterministic, integrity-protected tabular policy checkpoint."""
    destination = Path(path)
    data = _checkpoint_data(result)
    data["sha256"] = checkpoint_digest(result)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    return destination


def load_checkpoint(path: str | Path) -> TrainingResult:
    """Load a checkpoint only when its schema, actions, and digest are intact."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    digest = data.pop("sha256", None)
    if data.get("checkpoint_version") != CHECKPOINT_VERSION:
        raise ValueError("Unsupported checkpoint version")
    if tuple(data.get("action_names", ())) != ACTION_NAMES or data.get("encoder") != "strategic-v2":
        raise ValueError("Checkpoint policy schema does not match this environment")
    table = {tuple(item["state"]): list(item["values"]) for item in data["q_table"]}
    result = TrainingResult(
        training_seed=data["training_seed"], config=QLearningConfig(**data["config"]),
        q_table=table, episode_rewards=tuple(data["episode_rewards"]),
        episode_seeds=tuple(data["episode_seeds"]),
        training_rewards=tuple(data["training_rewards"]), state_count=data["state_count"],
    )
    if digest != checkpoint_digest(result):
        raise ValueError("Checkpoint integrity verification failed")
    return result

@dataclass(frozen=True)
class BatchComparison:
    training_seed: int
    evaluation_seeds: tuple[int, ...]
    rl_rewards: tuple[float, ...]
    utility_rewards: tuple[float, ...]
    mean_difference: float
    verdict: str


def compare_utility_and_rl(result: TrainingResult, evaluation_seeds: tuple[int, ...],
                           horizon: int | None = None) -> BatchComparison:
    """Evaluate frozen RL and utility policies on identical held-out world seeds."""
    if not evaluation_seeds:
        raise ValueError("At least one evaluation seed is required")
    training_seeds = {result.training_seed, *result.episode_seeds}
    if training_seeds.intersection(evaluation_seeds):
        raise ValueError("Evaluation seeds must be held out from all training seeds")
    horizon = horizon or result.config.horizon
    rl_totals, utility_totals = [], []
    for seed in evaluation_seeds:
        rl_env = TrainingEnvironment(seed, horizon)
        observation, info = rl_env.reset(seed=seed)
        rl_total = 0.0
        while True:
            values = result.q_table.get(discretize(observation), [0.0] * len(ACTION_NAMES))
            action = _greedy_action(values, info["action_mask"])
            observation, reward, terminated, truncated, info = rl_env.step(action)
            rl_total += reward
            if terminated or truncated:
                break
        utility_env = LearningEnvironment(seed)
        utility_total = sum(utility_env.baseline_step().reward for _ in range(horizon))
        rl_totals.append(round(rl_total, 3))
        utility_totals.append(round(utility_total, 3))
    differences = [rl - utility for rl, utility in zip(rl_totals, utility_totals)]
    mean = sum(differences) / len(differences)
    if len(differences) < 2:
        verdict = "inconclusive"
    else:
        standard_error = math.sqrt(sum((value - mean) ** 2 for value in differences) /
                                   (len(differences) - 1)) / math.sqrt(len(differences))
        margin = 1.96 * standard_error
        verdict = ("promising" if mean - margin > 0 else
                   "baseline remains better" if mean + margin < 0 else "inconclusive")
    return BatchComparison(result.training_seed, tuple(evaluation_seeds), tuple(rl_totals),
                           tuple(utility_totals), round(mean, 3), verdict)
@dataclass(frozen=True)
class DiagnosticStep:
    step: int
    action: str
    reward: float
    health: int
    energy: int
    money: int
    rent_arrears: int
    missions_completed: int


@dataclass(frozen=True)
class EpisodeDiagnostics:
    seed: int
    policy: str
    condition: str
    steps: int
    decision_steps: int
    total_reward: float
    reward_components: tuple[tuple[str, float], ...]
    action_counts: tuple[tuple[str, int], ...]
    masked_counts: tuple[tuple[str, int], ...]
    survived: bool
    rent_due_reached: bool
    rent_paid: bool
    missions_attempted: int
    missions_completed: int
    unique_actions: int
    dominant_action_share: float
    longest_action_streak: int
    exploit_flags: tuple[str, ...]
    trace: tuple[DiagnosticStep, ...]


@dataclass(frozen=True)
class DiagnosticBatch:
    training_seed: int
    evaluation_seeds: tuple[int, ...]
    rl_episodes: tuple[EpisodeDiagnostics, ...]
    utility_episodes: tuple[EpisodeDiagnostics, ...]
    random_episodes: tuple[EpisodeDiagnostics, ...]
    heuristic_episodes: tuple[EpisodeDiagnostics, ...]
    policy_ranking: tuple[str, ...]
    reward_difference: float
    verdict: str
    worst_rl_seeds: tuple[int, ...]
    condition: str = "standard"


def _episode_summary(seed: int, policy: str, condition: str,
                     environment: LearningEnvironment, transitions: list[Transition],
                     masks: list[tuple[int, ...]],
                     trace: list[DiagnosticStep]) -> EpisodeDiagnostics:
    actions = Counter(item.resolved_action or item.action for item in transitions)
    policy_actions = Counter(name for name, count in actions.items()
                             for _ in range(count) if name in ACTION_NAMES)
    masked = Counter()
    components = Counter()
    for mask in masks:
        for index, valid in enumerate(mask):
            if not valid:
                masked[ACTION_NAMES[index]] += 1
    for transition in transitions:
        components.update(dict(transition.reward_components))
    longest, current, previous = 0, 0, None
    for transition in transitions:
        action = transition.resolved_action or transition.action
        current = current + 1 if action == previous else 1
        longest, previous = max(longest, current), action
    steps = len(transitions)
    decision_steps = sum(policy_actions.values())
    dominant = (max(policy_actions.values(), default=0) / decision_steps
                if decision_steps else 0.0)
    flags = []
    if decision_steps >= 8 and len(policy_actions) <= 2:
        flags.append("low action diversity")
    if decision_steps >= 8 and longest >= max(8, math.ceil(decision_steps * 0.2)):
        flags.append("repeated-action loop")
    passive = sum(policy_actions[name] for name in ("Eat", "Rest", "Talk with Aiko"))
    if decision_steps >= 8 and passive / decision_steps >= 0.8:
        flags.append("passive-policy dominance")
    p = environment.simulation.state.protagonist
    due_reached = environment.simulation.state.clock.day > p.rent_due_day
    return EpisodeDiagnostics(
        seed=seed, policy=policy, condition=condition, steps=steps, decision_steps=decision_steps,
        total_reward=round(sum(item.reward for item in transitions), 3),
        reward_components=tuple((name, round(components[name], 3)) for name in REWARD_COMPONENTS),
        action_counts=tuple(sorted(actions.items())),
        masked_counts=tuple((name, masked[name]) for name in ACTION_NAMES),
        survived=p.health > 0, rent_due_reached=due_reached,
        rent_paid=due_reached and p.rent_arrears == 0,
        missions_attempted=p.missions_attempted, missions_completed=p.missions_completed,
        unique_actions=len(policy_actions), dominant_action_share=round(dominant, 3),
        longest_action_streak=longest, exploit_flags=tuple(flags), trace=tuple(trace),
    )


def heuristic_action(environment: LearningEnvironment, mask: tuple[int, ...]) -> int:
    """Choose from explicit safety and progression rules, independent of utility scores."""
    p, state = environment.simulation.state.protagonist, environment.simulation.state
    valid = {name for index, name in enumerate(ACTION_NAMES) if mask[index]}
    priorities = []
    if p.injury_severity >= 2 or (p.injury_severity and p.health < 65):
        priorities.append("Seek treatment")
    if p.hunger >= 65:
        priorities.append("Eat")
    if p.energy <= 28 or p.health < 45:
        priorities.append("Rest")
    if p.rent_arrears and p.money > 600:
        priorities.append("Pay rent arrears")
    if p.money < p.rent_cost and state.clock.day <= p.rent_due_day:
        priorities.append("Part-time work")
    if state.active_portal_plan and p.health >= 60 and p.energy >= 42:
        priorities.append("Gate mission")
    if p.guild_registered and state.gate_alert_level >= 2 and p.health >= 65:
        priorities.append("Prepare portal")
    if p.guild_registered and p.energy >= 45:
        priorities.append("Guild patrol")
    priorities.extend(("Study", "Train", "Part-time work", "Rest", "Eat"))
    choice = next(name for name in priorities if name in valid)
    return ACTION_NAMES.index(choice)

def _configure_evaluation_condition(environment: LearningEnvironment,
                                    condition: str) -> None:
    if condition not in EVALUATION_CONDITIONS:
        raise ValueError(f"Unknown evaluation condition {condition!r}")
    state, p = environment.simulation.state, environment.simulation.state.protagonist

    def establish_hunter_start() -> None:
        p.awakened, p.guild_registered = True, True
        p.hunter_rank, p.ability, p.ability_mastery = "F", "Threat Sense", 10
        p.relationships["Aiko Sato"] = Relationship(
            name="Aiko Sato", role="F-rank guild clerk", trust=3,
            familiarity=5, meetings=1, loyalty=4,
        )

    if condition == "financial_pressure":
        establish_hunter_start()
        state.clock.day = p.rent_due_day + 1
        p.money, p.rent_arrears, p.hunger, p.stress = 300, p.rent_cost, 55, 70
    elif condition == "injury_recovery":
        p.health, p.energy, p.injury_severity, p.injuries = 42, 30, 3, 1
        p.money, p.stress = 3_500, 65
    elif condition == "gate_crisis":
        establish_hunter_start()
        p.health, p.energy, p.stress = 75, 55, 60
        state.gate_alert_level = 3


def diagnose_episode(seed: int, horizon: int, policy: str,
                     result: TrainingResult | None = None,
                     condition: str = "standard") -> EpisodeDiagnostics:
    """Run one deterministic episode and retain evidence for failure analysis."""
    if horizon < 1:
        raise ValueError("horizon must be at least 1")
    if policy not in {"rl", "utility", "random", "heuristic"}:
        raise ValueError("unknown diagnostic policy")
    if policy == "rl" and result is None:
        raise ValueError("RL diagnostics require a training result")
    environment = LearningEnvironment(seed)
    _configure_evaluation_condition(environment, condition)
    policy_rng = random.Random(seed * 97_409 + 17)
    transitions, masks, trace = [], [], []
    for step in range(1, horizon + 1):
        mask = environment.action_mask()
        masks.append(mask)
        if policy == "utility":
            transition = environment.baseline_step()
        elif policy == "random":
            action = policy_rng.choice([index for index, valid in enumerate(mask) if valid])
            transition = environment.step(ACTION_NAMES[action])
        elif policy == "heuristic":
            action = heuristic_action(environment, mask)
            transition = environment.step(ACTION_NAMES[action])
        else:
            observation = environment.observe()
            values = result.q_table.get(discretize(observation), [0.0] * len(ACTION_NAMES))
            action = _greedy_action(values, mask)
            transition = environment.step(ACTION_NAMES[action])
        transitions.append(transition)
        p = environment.simulation.state.protagonist
        trace.append(DiagnosticStep(step, transition.resolved_action or transition.action,
                                    transition.reward, p.health,
                                    p.energy, p.money, p.rent_arrears,
                                    p.missions_completed))
        if p.health <= 0:
            break
    return _episode_summary(seed, policy, condition, environment, transitions, masks, trace)


def _honest_verdict(differences: list[float]) -> str:
    if len(differences) < 2:
        return "inconclusive"
    mean = sum(differences) / len(differences)
    standard_error = math.sqrt(sum((value - mean) ** 2 for value in differences) /
                               (len(differences) - 1)) / math.sqrt(len(differences))
    margin = 1.96 * standard_error
    if mean - margin > 0:
        return "promising"
    if mean + margin < 0:
        return "baseline remains better"
    return "inconclusive"


def diagnose_batch(result: TrainingResult, evaluation_seeds: tuple[int, ...],
                   horizon: int | None = None, worst_count: int = 3,
                   condition: str = "standard") -> DiagnosticBatch:
    """Compare policies and retain the weakest held-out RL episodes for inspection."""
    if not evaluation_seeds:
        raise ValueError("At least one evaluation seed is required")
    if worst_count < 1:
        raise ValueError("worst_count must be at least 1")
    training_seeds = {result.training_seed, *result.episode_seeds}
    if training_seeds.intersection(evaluation_seeds):
        raise ValueError("Evaluation seeds must be held out from all training seeds")
    horizon = horizon or result.config.horizon
    rl = tuple(diagnose_episode(seed, horizon, "rl", result, condition)
               for seed in evaluation_seeds)
    utility = tuple(diagnose_episode(seed, horizon, "utility", condition=condition)
                    for seed in evaluation_seeds)
    random_policy = tuple(diagnose_episode(seed, horizon, "random", condition=condition)
                          for seed in evaluation_seeds)
    heuristic = tuple(diagnose_episode(seed, horizon, "heuristic", condition=condition)
                      for seed in evaluation_seeds)
    policies = {"rl": rl, "utility": utility, "random": random_policy,
                "heuristic": heuristic}
    averages = {name: sum(item.total_reward for item in episodes) / len(episodes)
                for name, episodes in policies.items()}
    ranking = tuple(sorted(averages, key=lambda name: (-averages[name], name)))
    differences = [r.total_reward - u.total_reward for r, u in zip(rl, utility)]
    worst = sorted(rl, key=lambda episode: (episode.total_reward, episode.seed))[:worst_count]
    return DiagnosticBatch(
        training_seed=result.training_seed, evaluation_seeds=tuple(evaluation_seeds),
        rl_episodes=rl, utility_episodes=utility, random_episodes=random_policy,
        heuristic_episodes=heuristic, policy_ranking=ranking,
        reward_difference=round(sum(differences) / len(differences), 3),
        verdict=_honest_verdict(differences),
        worst_rl_seeds=tuple(episode.seed for episode in worst), condition=condition,
    )

@dataclass(frozen=True)
class TrialSummary:
    training_seed: int
    evaluation_seeds: tuple[int, ...]
    rl_average_reward: float
    utility_average_reward: float
    mean_difference: float
    verdict: str
    checkpoint_sha256: str


@dataclass(frozen=True)
class RepeatedTrialResult:
    trials: tuple[TrialSummary, ...]
    pooled_mean_difference: float
    verdict: str
    neural_trial_ready: bool


def evaluate_repeated_trials(training_seeds: tuple[int, ...],
                              evaluation_seed_groups: tuple[tuple[int, ...], ...],
                              config: QLearningConfig) -> RepeatedTrialResult:
    """Run independent training/evaluation trials and pool paired held-out evidence."""
    if not training_seeds or len(training_seeds) != len(evaluation_seed_groups):
        raise ValueError("Each training seed requires one non-empty evaluation seed group")
    summaries, pooled = [], []
    for training_seed, evaluation_seeds in zip(training_seeds, evaluation_seed_groups):
        if not evaluation_seeds:
            raise ValueError("Evaluation seed groups cannot be empty")
        result = train_q_learning(training_seed, config)
        batch = diagnose_batch(result, evaluation_seeds, config.horizon, worst_count=1)
        rl_rewards = [item.total_reward for item in batch.rl_episodes]
        utility_rewards = [item.total_reward for item in batch.utility_episodes]
        differences = [rl - utility for rl, utility in zip(rl_rewards, utility_rewards)]
        pooled.extend(differences)
        summaries.append(TrialSummary(
            training_seed=training_seed, evaluation_seeds=evaluation_seeds,
            rl_average_reward=round(sum(rl_rewards) / len(rl_rewards), 3),
            utility_average_reward=round(sum(utility_rewards) / len(utility_rewards), 3),
            mean_difference=round(sum(differences) / len(differences), 3),
            verdict=_honest_verdict(differences), checkpoint_sha256=checkpoint_digest(result),
        ))
    verdict = _honest_verdict(pooled)
    ready = verdict == "promising" and all(item.verdict == "promising" for item in summaries)
    return RepeatedTrialResult(tuple(summaries), round(sum(pooled) / len(pooled), 3),
                               verdict, ready)

@dataclass(frozen=True)
class EvaluationScenario:
    """A named held-out evaluation slice with a horizon and starting condition."""
    name: str
    horizon: int
    evaluation_seeds: tuple[int, ...]
    condition: str = "standard"

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("Scenario name cannot be empty")
        if self.horizon < 1:
            raise ValueError("Scenario horizon must be at least 1")
        if not self.evaluation_seeds:
            raise ValueError("Scenario evaluation seeds cannot be empty")
        if len(set(self.evaluation_seeds)) != len(self.evaluation_seeds):
            raise ValueError("Scenario evaluation seeds must be unique")
        if self.condition not in EVALUATION_CONDITIONS:
            raise ValueError(f"Unknown evaluation condition {self.condition!r}")


@dataclass(frozen=True)
class ScenarioComparison:
    name: str
    horizon: int
    condition: str
    evaluation_seeds: tuple[int, ...]
    policy_ranking: tuple[str, ...]
    rl_average_reward: float
    utility_average_reward: float
    mean_difference: float
    rl_survival_rate: float
    utility_survival_rate: float
    rl_average_missions: float
    utility_average_missions: float
    verdict: str
    rl_rent_paid_rate: float = 0.0
    utility_rent_paid_rate: float = 0.0
    rl_dominant_action_share: float = 0.0
    utility_dominant_action_share: float = 0.0
    rl_exploit_flags: tuple[str, ...] = ()


@dataclass(frozen=True)
class ScenarioSuiteResult:
    training_seed: int
    checkpoint_sha256: str
    scenarios: tuple[ScenarioComparison, ...]
    total_episodes: int
    pooled_mean_difference: float
    verdict: str
    adoption_ready: bool


@dataclass(frozen=True)
class AdoptionDecision:
    ready: bool
    checkpoint_sha256: str
    report_sha256: str
    blockers: tuple[str, ...]


def _adoption_blockers(scenarios: tuple[ScenarioComparison, ...],
                       verdict: str) -> tuple[str, ...]:
    blockers = []
    if verdict != "promising":
        blockers.append(f"pooled verdict is {verdict}")
    for scenario in scenarios:
        if scenario.verdict != "promising":
            blockers.append(f"{scenario.name}: verdict is {scenario.verdict}")
        if scenario.rl_survival_rate < scenario.utility_survival_rate:
            blockers.append(f"{scenario.name}: survival regression")
        if scenario.rl_average_missions < scenario.utility_average_missions:
            blockers.append(f"{scenario.name}: mission regression")
        if scenario.rl_rent_paid_rate < scenario.utility_rent_paid_rate:
            blockers.append(f"{scenario.name}: rent recovery regression")
        if (scenario.rl_dominant_action_share - scenario.utility_dominant_action_share >
                MAX_DOMINANCE_REGRESSION):
            blockers.append(f"{scenario.name}: action dominance regression")
        if scenario.rl_exploit_flags:
            flags = ", ".join(scenario.rl_exploit_flags)
            blockers.append(f"{scenario.name}: behavioral exploit flags ({flags})")
    return tuple(blockers)


def assess_policy_adoption(result: TrainingResult,
                           suite: ScenarioSuiteResult) -> AdoptionDecision:
    """Verify policy identity and explain every blocker to offline adoption."""
    digest = checkpoint_digest(result)
    blockers = list(_adoption_blockers(suite.scenarios, suite.verdict))
    if digest != suite.checkpoint_sha256:
        blockers.insert(0, "checkpoint mismatch")
    return AdoptionDecision(
        ready=not blockers, checkpoint_sha256=digest,
        report_sha256=scenario_suite_digest(suite), blockers=tuple(blockers),
    )


def evaluate_scenario_suite(result: TrainingResult,
                            scenarios: tuple[EvaluationScenario, ...]
                            ) -> ScenarioSuiteResult:
    """Evaluate one frozen policy across named, held-out fixed-horizon scenarios."""
    if not scenarios:
        raise ValueError("At least one evaluation scenario is required")
    names = [scenario.name for scenario in scenarios]
    if len(set(names)) != len(names):
        raise ValueError("Evaluation scenario names must be unique")
    evaluation_seeds = [seed for scenario in scenarios for seed in scenario.evaluation_seeds]
    if len(set(evaluation_seeds)) != len(evaluation_seeds):
        raise ValueError("Evaluation seeds must be unique across scenarios")
    summaries, pooled = [], []
    for scenario in scenarios:
        batch = diagnose_batch(result, scenario.evaluation_seeds,
                               horizon=scenario.horizon, worst_count=1,
                               condition=scenario.condition)
        rl_rewards = [episode.total_reward for episode in batch.rl_episodes]
        utility_rewards = [episode.total_reward for episode in batch.utility_episodes]
        differences = [rl - utility for rl, utility in zip(rl_rewards, utility_rewards)]
        pooled.extend(differences)
        count = len(scenario.evaluation_seeds)
        rl_due = sum(episode.rent_due_reached for episode in batch.rl_episodes)
        utility_due = sum(episode.rent_due_reached for episode in batch.utility_episodes)
        rl_flags = tuple(sorted({flag for episode in batch.rl_episodes
                                 for flag in episode.exploit_flags}))
        summaries.append(ScenarioComparison(
            name=scenario.name, horizon=scenario.horizon, condition=scenario.condition,
            evaluation_seeds=scenario.evaluation_seeds,
            policy_ranking=batch.policy_ranking,
            rl_average_reward=round(sum(rl_rewards) / count, 3),
            utility_average_reward=round(sum(utility_rewards) / count, 3),
            mean_difference=round(sum(differences) / count, 3),
            rl_survival_rate=round(sum(e.survived for e in batch.rl_episodes) / count, 3),
            utility_survival_rate=round(
                sum(e.survived for e in batch.utility_episodes) / count, 3),
            rl_average_missions=round(
                sum(e.missions_completed for e in batch.rl_episodes) / count, 3),
            utility_average_missions=round(
                sum(e.missions_completed for e in batch.utility_episodes) / count, 3),
            verdict=batch.verdict,
            rl_rent_paid_rate=round(
                sum(e.rent_paid for e in batch.rl_episodes) / max(1, rl_due), 3),
            utility_rent_paid_rate=round(
                sum(e.rent_paid for e in batch.utility_episodes) / max(1, utility_due), 3),
            rl_dominant_action_share=round(
                sum(e.dominant_action_share for e in batch.rl_episodes) / count, 3),
            utility_dominant_action_share=round(
                sum(e.dominant_action_share for e in batch.utility_episodes) / count, 3),
            rl_exploit_flags=rl_flags,
        ))
    verdict = _honest_verdict(pooled)
    adoption_ready = not _adoption_blockers(tuple(summaries), verdict)
    return ScenarioSuiteResult(
        training_seed=result.training_seed, checkpoint_sha256=checkpoint_digest(result),
        scenarios=tuple(summaries), total_episodes=len(pooled),
        pooled_mean_difference=round(sum(pooled) / len(pooled), 3),
        verdict=verdict, adoption_ready=adoption_ready,
    )

SCENARIO_REPORT_VERSION = 3


def _scenario_suite_data(suite: ScenarioSuiteResult) -> dict:
    return {
        "report_version": SCENARIO_REPORT_VERSION,
        "training_seed": suite.training_seed,
        "checkpoint_sha256": suite.checkpoint_sha256,
        "scenarios": [asdict(scenario) for scenario in suite.scenarios],
        "total_episodes": suite.total_episodes,
        "pooled_mean_difference": suite.pooled_mean_difference,
        "verdict": suite.verdict,
        "adoption_ready": suite.adoption_ready,
    }


def scenario_suite_digest(suite: ScenarioSuiteResult) -> str:
    """Return the stable identity of a scenario-suite evaluation payload."""
    payload = json.dumps(_scenario_suite_data(suite), sort_keys=True,
                         separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def scenario_suite_report(suite: ScenarioSuiteResult) -> str:
    """Render a deterministic, integrity-identified scenario-suite JSON report."""
    data = _scenario_suite_data(suite)
    data["sha256"] = scenario_suite_digest(suite)
    return json.dumps(data, indent=2, sort_keys=True)


def save_scenario_suite_report(suite: ScenarioSuiteResult, path: str | Path) -> Path:
    """Save a canonical scenario-suite report for audits and observer tooling."""
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(scenario_suite_report(suite), encoding="utf-8")
    return destination

def load_scenario_suite_report(path: str | Path) -> ScenarioSuiteResult:
    """Load a scenario-suite report only when its version and digest are intact."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    digest = data.pop("sha256", None)
    if data.get("report_version") not in (1, 2, SCENARIO_REPORT_VERSION):
        raise ValueError("Unsupported scenario report version")
    payload = json.dumps(data, sort_keys=True, separators=(",", ":")).encode("utf-8")
    if digest != hashlib.sha256(payload).hexdigest():
        raise ValueError("Scenario report integrity verification failed")
    try:
        scenarios = tuple(ScenarioComparison(
            name=item["name"], horizon=item["horizon"],
            condition=item.get("condition", "standard"),
            evaluation_seeds=tuple(item["evaluation_seeds"]),
            policy_ranking=tuple(item["policy_ranking"]),
            rl_average_reward=item["rl_average_reward"],
            utility_average_reward=item["utility_average_reward"],
            mean_difference=item["mean_difference"],
            rl_survival_rate=item["rl_survival_rate"],
            utility_survival_rate=item["utility_survival_rate"],
            rl_average_missions=item["rl_average_missions"],
            utility_average_missions=item["utility_average_missions"],
            verdict=item["verdict"],
            rl_rent_paid_rate=item.get("rl_rent_paid_rate", 0.0),
            utility_rent_paid_rate=item.get("utility_rent_paid_rate", 0.0),
            rl_dominant_action_share=item.get("rl_dominant_action_share", 0.0),
            utility_dominant_action_share=item.get("utility_dominant_action_share", 0.0),
            rl_exploit_flags=tuple(item.get("rl_exploit_flags", ())),
        ) for item in data["scenarios"])
        suite = ScenarioSuiteResult(
            training_seed=data["training_seed"],
            checkpoint_sha256=data["checkpoint_sha256"], scenarios=scenarios,
            total_episodes=data["total_episodes"],
            pooled_mean_difference=data["pooled_mean_difference"],
            verdict=data["verdict"], adoption_ready=data["adoption_ready"],
        )
    except (KeyError, TypeError) as error:
        raise ValueError("Invalid scenario report schema") from error
    return suite


def diagnostics_report(batch: DiagnosticBatch) -> str:
    """Render a deterministic JSON report suitable for versioned experiment records."""
    def aggregate(episodes: tuple[EpisodeDiagnostics, ...]) -> dict:
        count = len(episodes)
        actions = Counter()
        masked = Counter()
        components = Counter()
        flags = Counter()
        for episode in episodes:
            actions.update(dict(episode.action_counts))
            masked.update(dict(episode.masked_counts))
            components.update(dict(episode.reward_components))
            flags.update(episode.exploit_flags)
        return {
            "average_reward": round(sum(e.total_reward for e in episodes) / count, 3),
            "average_missions": round(sum(e.missions_completed for e in episodes) / count, 3),
            "survival_rate": round(sum(e.survived for e in episodes) / count, 3),
            "rent_paid_rate_when_due": round(
                sum(e.rent_paid for e in episodes) /
                max(1, sum(e.rent_due_reached for e in episodes)), 3),
            "average_decision_steps": round(sum(e.decision_steps for e in episodes) / count, 3),
            "average_unique_actions": round(sum(e.unique_actions for e in episodes) / count, 3),
            "average_dominant_action_share": round(
                sum(e.dominant_action_share for e in episodes) / count, 3),
            "maximum_action_streak": max(e.longest_action_streak for e in episodes),
            "action_counts": dict(actions),
            "action_frequencies": {name: round(value / sum(actions.values()), 3)
                                   for name, value in actions.items()},
            "masked_counts": dict(masked),
            "masked_frequencies": {
                name: round(value / sum(e.steps for e in episodes), 3)
                for name, value in masked.items()
            },
            "reward_components": {name: round(components[name] / count, 3)
                                  for name in REWARD_COMPONENTS},
            "exploit_flags": dict(flags),
        }
    worst = []
    for seed in batch.worst_rl_seeds:
        episode = next(item for item in batch.rl_episodes if item.seed == seed)
        worst.append({
            "seed": seed, "reward": episode.total_reward,
            "exploit_flags": episode.exploit_flags,
            "trace": [step.__dict__ for step in episode.trace],
        })
    payload = {
        "training_seed": batch.training_seed,
        "condition": batch.condition,
        "evaluation_seeds": batch.evaluation_seeds,
        "rl": aggregate(batch.rl_episodes),
        "utility": aggregate(batch.utility_episodes),
        "random": aggregate(batch.random_episodes),
        "heuristic": aggregate(batch.heuristic_episodes),
        "policy_ranking": batch.policy_ranking,
        "mean_reward_difference": batch.reward_difference,
        "verdict": batch.verdict,
        "worst_rl_episodes": worst,
    }
    return json.dumps(payload, indent=2, sort_keys=True)

@dataclass(frozen=True)
class ScenarioResult:
    seed: int
    steps: int
    total_reward: float
    survived: bool
    rent_arrears: int
    missions_completed: int
    investigation_progress: int
    network_trust: int


def evaluate_scenario(seed: int, steps: int = 240) -> ScenarioResult:
    """Run a complete deterministic baseline scenario for later RL comparison."""
    environment = LearningEnvironment(seed)
    total = 0.0
    for _ in range(steps):
        total += environment.baseline_step().reward
    state, p = environment.simulation.state, environment.simulation.state.protagonist
    return ScenarioResult(
        seed=seed, steps=steps, total_reward=round(total, 3), survived=p.health > 0,
        rent_arrears=p.rent_arrears, missions_completed=p.missions_completed,
        investigation_progress=sum(i.progress for i in state.portal_investigations.values()),
        network_trust=sum(r.trust for r in p.relationships.values()),
    )
