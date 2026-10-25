# -*- coding: utf-8 -*-
from __future__ import annotations

import csv
import math
import random
from pathlib import Path
from typing import Dict, List, Tuple

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

import warehouse_gridworld_domain_random as domain

State = Tuple[int, int, int, int]  # row, col, has_package, delivered

GAMMA = 0.95
THETA = 1e-6
MAX_ITERATIONS = 20_000
LAYOUT_SEED = 42
EVALUATION_EPISODES = 500
PROBABILITIES = (1.00, 0.90, 0.80)

ACTIONS = tuple(domain.ACTIONS)
ACTION_DELTA = domain.ACTION_TO_DELTA
PERPENDICULAR = {
    "up": ("left", "right"),
    "down": ("left", "right"),
    "left": ("up", "down"),
    "right": ("up", "down"),
}
ARROWS = {"up": "↑", "down": "↓", "left": "←", "right": "→"}
PHASES = ((0, 0, "Before pickup"), (1, 0, "Carrying package"), (1, 1, "After delivery"))


def is_goal_state(state: State, dock_pos: Tuple[int, int]) -> bool:
    row, col, _has_package, delivered = state
    return (row, col) == dock_pos and delivered == 1


def build_states(grid) -> List[State]:
    """Build reachable-form state tuples on all non-shelf cells."""
    states: List[State] = []
    for row in range(grid.shape[0]):
        for col in range(grid.shape[1]):
            if int(grid[row, col]) == domain.SHELF:
                continue
            states.extend(((row, col, 0, 0), (row, col, 1, 0), (row, col, 1, 1)))
    return states


def transition_for_actual_action(
        state: State,
        actual_action: str,
        world,
) -> Tuple[State, float, bool]:
    """Apply one actual direction and return (next_state, reward, terminal)."""
    row, col, has_package, delivered = state
    dr, dc = ACTION_DELTA[actual_action]
    next_row, next_col = row + dr, col + dc
    reward = float(domain.STEP_PENALTY)

    # Blocked movement leaves the robot in place and incurs the extra penalty.
    if not world.in_bounds(next_row, next_col) or not world.passable(
            next_row, next_col
    ):
        next_row, next_col = row, col
        reward += domain.INVALID_MOVE_PENALTY

    cell = int(world.grid[next_row, next_col])
    # Mirrors the supplied environment's reward check on the resulting cell.
    if cell == domain.CONGESTION:
        reward += domain.CONGESTION_PENALTY

    if (next_row, next_col) == world.pickup_pos and not has_package:
        has_package = 1
        reward += domain.PICKUP_REWARD

    if (next_row, next_col) == world.packing_pos and has_package and not delivered:
        delivered = 1
        reward += domain.DELIVERY_REWARD

    if (next_row, next_col) == world.dock_pos and delivered:
        reward += domain.DOCK_REWARD
        done = True
    else:
        done = False

    next_state: State = (next_row, next_col, int(has_package), int(delivered))
    return next_state, reward, done


def stochastic_outcomes(state: State, intended_action: str, p: float, world):
    """Yield probability, next state, reward, done for each possible direction."""
    if not (0.0 <= p <= 1.0):
        raise ValueError("p must be between 0 and 1")
    outcomes = [(intended_action, p)]
    side_probability = (1.0 - p) / 2.0
    left_side, right_side = PERPENDICULAR[intended_action]
    outcomes.extend(((left_side, side_probability), (right_side, side_probability)))
    for actual_action, probability in outcomes:
        if probability <= 0:
            continue
        next_state, reward, done = transition_for_actual_action(
            state, actual_action, world
        )
        yield probability, next_state, reward, done


def value_iteration(world, p: float, gamma: float = GAMMA, theta: float = THETA):
    """Solve the known-model MDP using the Bellman optimality update."""
    states = build_states(world.grid)
    state_set = set(states)
    values: Dict[State, float] = {state: 0.0 for state in states}
    terminal_states = {s for s in states if is_goal_state(s, world.dock_pos)}
    iterations = 0

    for iteration in range(1, MAX_ITERATIONS + 1):
        delta = 0.0
        new_values = values.copy()
        for state in states:
            if state in terminal_states:
                new_values[state] = 0.0
                continue

            best_value = -math.inf
            for action in ACTIONS:
                action_value = 0.0
                for (
                        probability,
                        next_state,
                        reward,
                        terminal_after_step,
                ) in stochastic_outcomes(state, action, p, world):
                    # All next states are valid/passable because collision leaves
                    # the robot in its current cell. Guard protects future edits.
                    if next_state not in state_set:
                        next_value = 0.0
                    elif terminal_after_step or next_state in terminal_states:
                        next_value = 0.0
                    else:
                        next_value = values[next_state]
                    action_value += probability * (reward + gamma * next_value)
                if action_value > best_value:
                    best_value = action_value
            new_values[state] = best_value
            delta = max(delta, abs(new_values[state] - values[state]))

        values = new_values
        iterations = iteration
        if delta < theta:
            break
    else:
        raise RuntimeError(
            f"Value Iteration did not converge within {MAX_ITERATIONS} iterations for p={p}."
        )

    policy: Dict[State, str] = {}
    for state in states:
        if state in terminal_states:
            policy[state] = "done"
            continue
        best_action = ACTIONS[0]
        best_value = -math.inf
        for action in ACTIONS:
            action_value = 0.0
            for (
                    probability,
                    next_state,
                    reward,
                    terminal_after_step,
            ) in stochastic_outcomes(state, action, p, world):
                if (
                        next_state not in state_set
                        or terminal_after_step
                        or next_state in terminal_states
                ):
                    next_value = 0.0
                else:
                    next_value = values[next_state]
                action_value += probability * (reward + gamma * next_value)
            if action_value > best_value:
                best_value = action_value
                best_action = action
        policy[state] = best_action

    return values, policy, iterations


def evaluate_policy(
        world, policy: Dict[State, str], p: float, episodes: int, seed: int
):
    """Monte Carlo evaluation under the same stochastic movement probability."""
    reward_totals: List[float] = []
    lengths: List[int] = []
    successes = 0

    for episode in range(episodes):
        rng = random.Random(seed + episode)
        state: State = (world.dock_pos[0], world.dock_pos[1], 0, 0)
        total_reward = 0.0
        steps = 0
        success = False

        while steps < world.max_steps:
            if is_goal_state(state, world.dock_pos):
                success = True
                break
            intended_action = policy.get(state)
            if intended_action is None or intended_action == "done":
                break

            draw = rng.random()
            if draw < p:
                actual_action = intended_action
            else:
                side_actions = PERPENDICULAR[intended_action]
                actual_action = (
                    side_actions[0] if rng.random() < 0.5 else side_actions[1]
                )

            state, reward, done = transition_for_actual_action(
                state, actual_action, world
            )
            total_reward += reward
            steps += 1
            if done:
                success = True
                break

        reward_totals.append(total_reward)
        lengths.append(steps)
        successes += int(success)

    return {
        "episodes": episodes,
        "average_cumulative_reward": sum(reward_totals) / episodes,
        "success_rate": successes / episodes,
        "average_steps": sum(lengths) / episodes,
    }


def plot_policy(world, policy: Dict[State, str], p: float, output_path: Path):
    """Save three phase-specific policy maps so task progress is visible."""
    fig, axes = plt.subplots(1, 3, figsize=(17, 6), constrained_layout=True)
    cell_colors = {
        domain.EMPTY: "#f5f5f5",
        domain.SHELF: "#222222",
        domain.CONGESTION: "#e13c3c",
        domain.PICKUP: "#4682ff",
        domain.PACKING: "#fadc28",
        domain.DOCK: "#3cc878",
    }
    station_labels = {
        domain.PICKUP: "P",
        domain.PACKING: "D",
        domain.DOCK: "C",
        domain.CONGESTION: "!",
        domain.SHELF: "#",
    }

    for ax, (has_package, delivered, phase_name) in zip(axes, PHASES):
        ax.set_title(phase_name, fontsize=12)
        ax.set_xlim(0, world.size)
        ax.set_ylim(world.size, 0)
        ax.set_aspect("equal")
        ax.set_xticks(range(world.size + 1))
        ax.set_yticks(range(world.size + 1))
        ax.set_xticklabels([])
        ax.set_yticklabels([])
        ax.grid(True, color="#b8b8b8", linewidth=0.5)

        for row in range(world.size):
            for col in range(world.size):
                cell = int(world.grid[row, col])
                ax.add_patch(
                    Rectangle(
                        (col, row), 1, 1, facecolor=cell_colors[cell], edgecolor="none"
                    )
                )
                state = (row, col, has_package, delivered)
                if cell == domain.SHELF:
                    ax.text(
                        col + 0.5,
                        row + 0.5,
                        "#",
                        ha="center",
                        va="center",
                        color="white",
                        fontsize=10,
                    )
                    continue
                if cell in station_labels:
                    ax.text(
                        col + 0.15,
                        row + 0.20,
                        station_labels[cell],
                        ha="left",
                        va="top",
                        color="black",
                        fontsize=8,
                        weight="bold",
                    )
                if is_goal_state(state, world.dock_pos):
                    ax.text(
                        col + 0.5,
                        row + 0.58,
                        "✓",
                        ha="center",
                        va="center",
                        color="black",
                        fontsize=14,
                        weight="bold",
                    )
                    continue
                action = policy.get(state)
                if action and action in ARROWS:
                    ax.text(
                        col + 0.5,
                        row + 0.57,
                        ARROWS[action],
                        ha="center",
                        va="center",
                        color="black",
                        fontsize=13,
                        weight="bold",
                    )

    fig.suptitle(
        f"Value Iteration Policy (intended-action probability p={p:.2f})", fontsize=14
    )
    fig.savefig(output_path, dpi=180, bbox_inches="tight")
    plt.close(fig)


def main():
    output_dir = Path(__file__).resolve().parent / "value_iteration_results"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Fix the layout seed so policy comparisons across p use the same map.
    world = domain.WarehouseGridWorld(seed=LAYOUT_SEED)
    print("Warehouse layout fixed for fair comparison")
    print(f"Layout seed: {LAYOUT_SEED}")
    print(f"Pickup position: {world.pickup_pos}")
    print(f"Packing position: {world.packing_pos}")
    print(f"Charging dock position: {world.dock_pos}")
    print(
        f"Gamma={GAMMA}, theta={THETA}, evaluation episodes per p={EVALUATION_EPISODES}"
    )

    results = []
    policies = {}
    for p in PROBABILITIES:
        values, policy, iterations = value_iteration(world, p)
        policies[p] = policy
        metrics = evaluate_policy(
            world, policy, p, EVALUATION_EPISODES, seed=10_000 + int(p * 1000)
        )
        record = {
            "p": p,
            "gamma": GAMMA,
            "theta": THETA,
            "iterations_to_converge": iterations,
            **metrics,
        }
        results.append(record)
        plot_path = output_dir / f"value_iteration_policy_p_{p:.2f}.png"
        plot_policy(world, policy, p, plot_path)
        print(
            f"p={p:.2f}: iterations={iterations}, "
            f"avg_reward={metrics['average_cumulative_reward']:.2f}, "
            f"success_rate={metrics['success_rate']:.1%}, "
            f"avg_steps={metrics['average_steps']:.2f}"
        )
        print(f"  Policy map: {plot_path.name}")

    csv_path = output_dir / "value_iteration_results.csv"
    fields = [
        "p",
        "gamma",
        "theta",
        "iterations_to_converge",
        "episodes",
        "average_cumulative_reward",
        "success_rate",
        "average_steps",
    ]
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(results)

    # Find a state whose preferred action changes as p changes.
    p_high, p_mid, p_low = 1.00, 0.90, 0.80
    changed = []
    for state in policies[p_high]:
        actions = tuple(policies[p][state] for p in (p_high, p_mid, p_low))
        if len(set(actions)) > 1:
            changed.append((state, actions))
    change_path = output_dir / "policy_action_changes.txt"
    with change_path.open("w", encoding="utf-8") as f:
        f.write("States where the preferred action changes as p decreases\n")
        f.write("Actions are listed in order p=1.00, p=0.90, p=0.80.\n\n")
        if changed:
            for state, actions in changed[:20]:
                f.write(
                    f"state={state}: p=1.00 -> {actions[0]}, p=0.90 -> {actions[1]}, p=0.80 -> {actions[2]}\n"
                )
        else:
            f.write(
                "No action changes were found on this layout. Try another documented layout seed.\n"
            )

    summary_path = output_dir / "run_summary.txt"
    with summary_path.open("w", encoding="utf-8") as f:
        f.write("COSC-4117EL Assignment 2 - Value Iteration\n")
        f.write(f"Layout seed: {LAYOUT_SEED}\n")
        f.write(f"Pickup position: {world.pickup_pos}\n")
        f.write(f"Packing position: {world.packing_pos}\n")
        f.write(f"Charging dock position: {world.dock_pos}\n")
        f.write(f"Discount factor gamma: {GAMMA}\n")
        f.write(f"Convergence threshold theta: {THETA}\n")
        f.write(f"Evaluation episodes per p: {EVALUATION_EPISODES}\n")
        f.write(
            "The max-step limit is used during policy evaluation; it is not included as a state variable in this stationary Value Iteration model.\n"
        )
        f.write(
            "The supplied environment's step() is deterministic, so the stochastic transition/reward model is implemented in this file for Value Iteration.\n"
        )
        f.write(
            "See value_iteration_results.csv and policy_action_changes.txt for results.\n"
        )

    print(f"\nResults saved to: {output_dir}")
    print(f"Metrics CSV: {csv_path.name}")
    print(f"Action-change analysis: {change_path.name}")


if __name__ == "__main__":
    main()
