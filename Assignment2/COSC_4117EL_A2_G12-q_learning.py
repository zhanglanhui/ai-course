from __future__ import annotations

import argparse
import csv
import importlib
import json
import random
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Hashable, Protocol

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

State = Hashable


class WarehouseAdapter(Protocol):
    """Small bridge to the course-provided gridworld_domain.

    reset(seed): return (row, col, has_package, delivered, steps_remaining).
    step(action): return (next_state, reward, terminated, truncated).
    actions: sequence of allowable action names, same order across runs.
    successful: whether the LAST episode completed pickup, delivery, return.
    """

    actions: tuple[str, ...]
    successful: bool

    def reset(self, seed: int) -> State: ...

    def step(self, action: str) -> tuple[State, float, bool, bool]: ...


def freeze_state(value: Any) -> State:
    """Convert the adapter's state into a stable, hashable Q-table key."""
    if isinstance(value, (int, float, str, bool, type(None))):
        return value
    if isinstance(value, (list, tuple)):
        return tuple(freeze_state(x) for x in value)
    if isinstance(value, dict):
        return tuple(sorted((k, freeze_state(v)) for k, v in value.items()))
    raise TypeError(f"Unsupported state representation: {type(value).__name__}")


@dataclass(frozen=True)
class Settings:
    name: str
    alpha: float
    gamma: float
    epsilon_decay: float
    epsilon_start: float = 1.0
    epsilon_min: float = 0.05


CONFIGS = (
    Settings("A_fast_decay", alpha=0.20, gamma=0.95, epsilon_decay=0.995),
    Settings("B_slow_decay", alpha=0.10, gamma=0.99, epsilon_decay=0.999),
)


class QAgent:
    def __init__(self, actions: tuple[str, ...], alpha: float, gamma: float):
        if not actions or len(set(actions)) != len(actions):
            raise ValueError("Adapter must provide distinct action labels")
        self.actions, self.alpha, self.gamma = actions, alpha, gamma
        self.q: dict[State, list[float]] = defaultdict(lambda: [0.0] * len(actions))
        self.visits: dict[State, int] = defaultdict(int)
        self.action_visits: dict[State, list[int]] = defaultdict(
            lambda: [0] * len(actions)
        )

    def initialize_states(self, env):
        """Initialize valid (row, col, picked, delivered, remaining) states."""
        for r in range(env.world.size):
            for c in range(env.world.size):
                if not env.world.passable(r, c):
                    continue
                for picked, delivered in ((0, 0), (1, 0), (1, 1)):
                    for remaining in range(env.world.max_steps + 1):
                        self.q[(r, c, picked, delivered, remaining)] = [0.0] * len(
                            self.actions
                        )

    def greedy_index(self, state: State) -> int:
        values = self.q[state]
        return max(range(len(values)), key=lambda i: values[i])

    def choose(self, state: State, epsilon: float, rng: random.Random) -> int:
        if rng.random() < epsilon:
            return rng.randrange(len(self.actions))
        # Randomize ties to prevent zero-initialization action-order bias in training.
        vals = self.q[state]
        best = max(vals)
        candidates = [i for i, v in enumerate(vals) if v == best]
        return rng.choice(candidates)

    def update(
        self,
        state: State,
        action_index: int,
        reward: float,
        next_state: State,
        done: bool,
    ) -> None:
        self.visits[state] += 1
        self.action_visits[state][action_index] += 1
        future = 0.0 if done else max(self.q[next_state])
        target = reward + self.gamma * future
        old = self.q[state][action_index]
        self.q[state][action_index] = old + self.alpha * (target - old)

    def policy(self) -> dict[str, str]:
        return {
            repr(s): self.actions[self.greedy_index(s)]
            for s in self.q
            if self.visits.get(s, 0) > 0
        }


def train(
    make_env, settings: Settings, seed: int, episodes: int, p: float, max_steps: int
) -> tuple[QAgent, list[dict]]:
    """Train by sampled transitions; agent never sees probability p."""
    rng = random.Random(seed)
    env = make_env(p=p, max_steps=max_steps)
    agent = QAgent(tuple(env.actions), settings.alpha, settings.gamma)
    agent.initialize_states(env)
    history = []
    epsilon = settings.epsilon_start
    for ep in range(episodes):
        # Different deterministic seed for each episode and configuration.
        state = freeze_state(env.reset(seed=seed * 1000003 + ep))
        total_reward, steps, finished = 0.0, 0, False
        for steps in range(1, max_steps + 1):
            action_idx = agent.choose(state, epsilon, rng)
            new_state, reward, terminated, truncated = env.step(env.actions[action_idx])
            next_state = freeze_state(new_state)
            done = bool(terminated or truncated or steps == max_steps)
            agent.update(state, action_idx, float(reward), next_state, done)
            total_reward += float(reward)
            state = next_state
            if done:
                finished = True
                break
        history.append(
            {
                "configuration": settings.name,
                "p": p,
                "seed": seed,
                "episode": ep + 1,
                "reward": total_reward,
                "success": int(env.successful),
                "steps": steps,
                "epsilon": epsilon,
            }
        )
        epsilon = max(settings.epsilon_min, epsilon * settings.epsilon_decay)
    return agent, history


def evaluate(
    make_env, agent: QAgent, p: float, seed: int, num_episodes: int, max_steps: int
) -> tuple[list[dict], list[dict]]:
    """Greedy policy evaluation (epsilon=0); no learning updates."""
    env = make_env(p=p, max_steps=max_steps)
    outcome, example_path = [], []
    for ep in range(num_episodes):
        state = freeze_state(env.reset(seed=seed * 1000003 + 500000 + ep))
        total_reward = 0.0
        path = [{"step": 0, "state": repr(state), "action": "START"}]
        for steps in range(1, max_steps + 1):
            action = agent.actions[agent.greedy_index(state)]
            new_state, reward, terminated, truncated = env.step(action)
            state = freeze_state(new_state)
            total_reward += float(reward)
            path.append(
                {
                    "step": steps,
                    "state": repr(state),
                    "action": action,
                    "reward": float(reward),
                }
            )
            if terminated or truncated:
                break
        outcome.append(
            {
                "p": p,
                "seed": seed,
                "eval_episode": ep + 1,
                "reward": total_reward,
                "success": int(env.successful),
                "steps": steps,
            }
        )
        if ep == 0:
            example_path = path
    return outcome, example_path


def write_csv(path: Path, records: list[dict]) -> None:
    if not records:
        return
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f, fieldnames=list(dict.fromkeys(k for row in records for k in row))
        )
        writer.writeheader()
        writer.writerows(records)


def plot_training(rows: list[dict], path: Path, window: int = 100) -> None:
    fig, ax = plt.subplots(figsize=(10, 5))
    keys = sorted({(r["configuration"], r["p"]) for r in rows})
    for name, p in keys:
        subset = [r for r in rows if r["configuration"] == name and r["p"] == p]
        episode_means = defaultdict(list)
        for row in subset:
            episode_means[row["episode"]].append(row["reward"])
        xs = sorted(episode_means)
        ys = [sum(episode_means[x]) / len(episode_means[x]) for x in xs]
        rolling = [
            sum(ys[max(0, i - window + 1) : i + 1])
            / len(ys[max(0, i - window + 1) : i + 1])
            for i in range(len(ys))
        ]
        ax.plot(xs, rolling, label=f"{name}, p={p:.2f}")
    ax.set(
        title=f"Q-Learning training reward ({window}-episode trailing mean)",
        xlabel="Episode",
        ylabel="Mean cumulative reward",
    )
    ax.legend(fontsize=8)
    ax.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def plot_success(rows: list[dict], path: Path, window: int = 100) -> None:
    fig, ax = plt.subplots(figsize=(10, 5))
    keys = sorted({(r["configuration"], r["p"]) for r in rows})
    for name, p in keys:
        subset = [r for r in rows if r["configuration"] == name and r["p"] == p]
        episode_means = defaultdict(list)
        for row in subset:
            episode_means[row["episode"]].append(row["success"])
        xs = sorted(episode_means)
        ys = [sum(episode_means[x]) / len(episode_means[x]) for x in xs]
        rolling = [
            sum(ys[max(0, i - window + 1) : i + 1])
            / len(ys[max(0, i - window + 1) : i + 1])
            for i in range(len(ys))
        ]
        ax.plot(xs, rolling, label=f"{name}, p={p:.2f}")
    ax.set(
        title=f"Q-Learning task completion ({window}-episode trailing mean)",
        xlabel="Episode",
        ylabel="Success fraction",
        ylim=(-0.05, 1.05),
    )
    ax.legend(fontsize=8)
    ax.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def summarize(rows: list[dict]) -> list[dict]:
    groups = defaultdict(list)
    for r in rows:
        groups[(r["configuration"], r["p"], r["seed"])].append(r)
    out = []
    for (name, p, seed), records in sorted(groups.items()):
        out.append(
            {
                "configuration": name,
                "p": p,
                "seed": seed,
                "episodes": len(records),
                "mean_reward": round(
                    sum(r["reward"] for r in records) / len(records), 3
                ),
                "success_rate": round(
                    sum(r["success"] for r in records) / len(records), 4
                ),
                "mean_steps": round(sum(r["steps"] for r in records) / len(records), 2),
            }
        )
    return out


def load_factory(module_name: str, callable_name: str):
    try:
        module = importlib.import_module(module_name)
    except ImportError as exc:
        raise SystemExit(
            f"Cannot import {module_name!r}. The course-provided gridworld_domain "
            "and its compatible adapter must be supplied. Original error: " + str(exc)
        )
    factory = getattr(module, callable_name, None)
    if not callable(factory):
        raise SystemExit(
            f"{module_name}.{callable_name} is not a callable factory. "
            "See README and warehouse_bridge.py for the required adapter interface."
        )
    return factory


def main():
    parser = argparse.ArgumentParser(description="Q-Learning warehouse experiments")
    parser.add_argument(
        "--adapter",
        default="warehouse_bridge:create_env",
        help="Python module:callable returning an adapter around gridworld_domain",
    )
    parser.add_argument("--episodes", type=int, default=5000)
    parser.add_argument("--eval-episodes", type=int, default=100)
    parser.add_argument("--max-steps", type=int, default=120)
    parser.add_argument("--seeds", type=int, nargs="+", default=[11, 42, 99])
    parser.add_argument(
        "--probabilities", type=float, nargs="+", default=[1.0, 0.9, 0.8]
    )
    parser.add_argument("--output", type=Path, default=Path("results_q_learning"))
    args = parser.parse_args()
    if args.episodes <= 0 or args.eval_episodes <= 0 or args.max_steps <= 0:
        parser.error("Episodes, evaluation episodes, and max steps must be positive")
    if any(not 0 <= p <= 1 for p in args.probabilities):
        parser.error("Each intended-action probability must be between 0 and 1")
    module, sep, func = args.adapter.partition(":")
    if not sep:
        parser.error("--adapter must use module:callable syntax")
    make_env = load_factory(module, func)
    args.output.mkdir(parents=True, exist_ok=True)
    train_rows, eval_rows = [], []
    for p in args.probabilities:
        for config in CONFIGS:
            for seed in args.seeds:
                agent, history = train(
                    make_env, config, seed, args.episodes, p, args.max_steps
                )
                train_rows.extend(history)
                eval_result, example = evaluate(
                    make_env, agent, p, seed, args.eval_episodes, args.max_steps
                )
                for record in eval_result:
                    record["configuration"] = config.name
                eval_rows.extend(eval_result)
                stem = f"{config.name}_p{p:.2f}_seed{seed}"
                (args.output / f"policy_{stem}.json").write_text(
                    json.dumps(agent.policy(), indent=2), encoding="utf-8"
                )
                (args.output / f"action_visits_{stem}.json").write_text(
                    json.dumps(
                        {repr(k): v for k, v in agent.action_visits.items()}, indent=2
                    ),
                    encoding="utf-8",
                )
                (args.output / f"visits_{stem}.json").write_text(
                    json.dumps({repr(k): v for k, v in agent.visits.items()}, indent=2),
                    encoding="utf-8",
                )
                write_csv(args.output / f"example_greedy_run_{stem}.csv", example)
                print(
                    f"Finished {stem}: evaluation success "
                    f"{sum(x['success'] for x in eval_result)}/{len(eval_result)}"
                )
    write_csv(args.output / "training_episodes.csv", train_rows)
    write_csv(args.output / "evaluation_episodes.csv", eval_rows)
    write_csv(args.output / "training_summary_by_seed.csv", summarize(train_rows))
    write_csv(args.output / "evaluation_summary_by_seed.csv", summarize(eval_rows))
    plot_training(train_rows, args.output / "training_reward.png")
    plot_success(train_rows, args.output / "training_success.png")
    (args.output / "settings.json").write_text(
        json.dumps(
            {
                "configs": [asdict(c) for c in CONFIGS],
                "seeds": args.seeds,
                "p": args.probabilities,
                "episodes": args.episodes,
                "eval_episodes": args.eval_episodes,
                "max_steps": args.max_steps,
                "adapter": args.adapter,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"Results written to {args.output}")


if __name__ == "__main__":
    main()
