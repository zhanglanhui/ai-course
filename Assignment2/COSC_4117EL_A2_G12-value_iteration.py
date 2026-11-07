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

# Generative AI disclosure: OpenAI ChatGPT assisted with revising and checking
# this five-dimensional finite-horizon Value Iteration implementation.
# Conversation reference: https://chatgpt.com/share/6aef6e1b-27c8-83ea-ad80-a71f47888e9a

# Match the five-component state used by the Q-Learning implementation.
# (row, col, has_package, delivered, steps_remaining)
State = Tuple[int, int, int, int, int]

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


# Use the same phase/time slices as plot_policies.py for easier visual comparison.
# (has_package, delivered, phase label, steps remaining)


def phase_slices(max_steps: int):
    return (
        (0, 0, "Before pickup", max_steps),
        (1, 0, "Carrying package", max(1, max_steps - 15)),
        (1, 1, "After delivery", max(1, max_steps - 30)),
    )


def is_goal_state(state: State, dock_pos: Tuple[int, int]) -> bool:
    row, col, _has_package, delivered, _remaining = state
    return (row, col) == dock_pos and delivered == 1


def is_terminal_state(state: State, dock_pos: Tuple[int, int]) -> bool:
    """A state is terminal after a successful return or when no steps remain."""
    return state[4] <= 0 or is_goal_state(state, dock_pos)


def build_states(grid, max_steps: int) -> List[State]:
    """Build time-aware states in ascending remaining-time order.

    This ordering is important for the finite-horizon Gauss-Seidel update:
    every successor of a state with t steps remaining has t-1 steps remaining,
    so all successor values have already been updated in the current sweep.
    """
    states: List[State] = []
    for remaining in range(max_steps + 1):
        for row in range(grid.shape[0]):
            for col in range(grid.shape[1]):
                if int(grid[row, col]) == domain.SHELF:
                    continue
                for has_package, delivered in ((0, 0), (1, 0), (1, 1)):
                    states.append((row, col, has_package, delivered, remaining))
    return states


def transition_for_actual_action(
        state: State,
        actual_action: str,
        world,
) -> Tuple[State, float, bool]:
    """Apply one executed direction and return (next_state, reward, done)."""
    row, col, has_package, delivered, remaining = state
    if remaining <= 0 or is_goal_state(state, world.dock_pos):
        raise ValueError("Cannot take an action from a terminal state")
    if actual_action not in ACTION_DELTA:
        raise ValueError(f"Unknown action: {actual_action}")

    dr, dc = ACTION_DELTA[actual_action]
    next_row, next_col = row + dr, col + dc
    reward = float(domain.STEP_PENALTY)

    # A blocked move leaves the robot in place and adds the invalid-move penalty.
    if not world.in_bounds(next_row, next_col) or not world.passable(
            next_row, next_col
    ):
        next_row, next_col = row, col
        reward += domain.INVALID_MOVE_PENALTY

    # Match the supplied environment: congestion penalty is checked on the
    # resulting cell after blocked movement has been resolved.
    cell = int(world.grid[next_row, next_col])
    if cell == domain.CONGESTION:
        reward += domain.CONGESTION_PENALTY

    # Update task progress in the state transition.
    if (next_row, next_col) == world.pickup_pos and not has_package:
        has_package = 1
        reward += domain.PICKUP_REWARD

    if (next_row, next_col) == world.packing_pos and has_package and not delivered:
        delivered = 1
        reward += domain.DELIVERY_REWARD

    # The successful-return reward is paid on the transition into the dock.
    successful_return = (next_row, next_col) == world.dock_pos and delivered == 1
    if successful_return:
        reward += domain.DOCK_REWARD

    next_remaining = remaining - 1
    next_state: State = (
        next_row,
        next_col,
        int(has_package),
        int(delivered),
        next_remaining,
    )
    # done includes both successful completion and the max-step timeout.
    done = successful_return or next_remaining == 0
    return next_state, reward, done


def stochastic_outcomes(state: State, intended_action: str, p: float, world):
    """Yield probability, next state, reward, and terminal flag for each outcome."""
    if not (0.0 <= p <= 1.0):
        raise ValueError("p must be between 0 and 1")
    if is_terminal_state(state, world.dock_pos):
        raise ValueError("Cannot expand a terminal state")
    if intended_action not in PERPENDICULAR:
        raise ValueError(f"Unknown action: {intended_action}")

    outcomes = [(intended_action, p)]
    side_probability = (1.0 - p) / 2.0
    side_one, side_two = PERPENDICULAR[intended_action]
    outcomes.extend(((side_one, side_probability), (side_two, side_probability)))

    for actual_action, probability in outcomes:
        if probability <= 0.0:
            continue
        next_state, reward, done = transition_for_actual_action(
            state, actual_action, world
        )
        yield probability, next_state, reward, done


def value_iteration(world, p: float, gamma: float = GAMMA, theta: float = THETA):
    """Solve the finite-horizon known-model MDP using Bellman value iteration."""
    if not (0.0 <= p <= 1.0):
        raise ValueError("p must be between 0 and 1")
    if not (0.0 <= gamma <= 1.0):
        raise ValueError("gamma must be between 0 and 1")
    if theta <= 0.0:
        raise ValueError("theta must be positive")

    states = build_states(world.grid, world.max_steps)
    state_set = set(states)
    values: Dict[State, float] = {state: 0.0 for state in states}
    terminal_states = {
        state for state in states if is_terminal_state(state, world.dock_pos)
    }
    iterations = 0

    # In-place Gauss-Seidel Bellman updates. This is a finite-horizon,
    # acyclic MDP: every transition decreases remaining steps by exactly one.
    # Since build_states orders states by ascending remaining steps, successor
    # values are already updated in the current sweep (backward induction).
    # A second sweep verifies that the maximum change is below theta.
    for iteration in range(1, MAX_ITERATIONS + 1):
        delta = 0.0
        for state in states:
            if state in terminal_states:
                values[state] = 0.0
                continue

            old_value = values[state]
            best_value = -math.inf
            for action in ACTIONS:
                action_value = 0.0
                for probability, next_state, reward, done in stochastic_outcomes(
                        state, action, p, world
                ):
                    if next_state not in state_set:
                        raise RuntimeError(
                            f"Transition produced invalid state: {next_state}"
                        )
                    next_value = 0.0 if done else values[next_state]
                    action_value += probability * (reward + gamma * next_value)
                best_value = max(best_value, action_value)

            values[state] = best_value
            delta = max(delta, abs(best_value - old_value))

        iterations = iteration
        if delta < theta:
            break
    else:
        raise RuntimeError(
            f"Value Iteration did not converge within {MAX_ITERATIONS} iterations for p={p}."
        )

    # Extract a greedy action for every nonterminal state, including each
    # remaining-step value. Terminal states are explicitly marked as 'done'.
    policy: Dict[State, str] = {}
    for state in states:
        if state in terminal_states:
            policy[state] = "done"
            continue

        best_action = ACTIONS[0]
        best_value = -math.inf
        for action in ACTIONS:
            action_value = 0.0
            for probability, next_state, reward, done in stochastic_outcomes(
                    state, action, p, world
            ):
                next_value = 0.0 if done else values[next_state]
                action_value += probability * (reward + gamma * next_value)
            if action_value > best_value:
                best_value = action_value
                best_action = action
        policy[state] = best_action

    return values, policy, iterations


def evaluate_policy(
        world, policy: Dict[State, str], p: float, episodes: int, seed: int
):
    """Monte Carlo evaluation of the five-dimensional finite-horizon policy."""
    if episodes <= 0:
        raise ValueError("episodes must be positive")

    reward_totals: List[float] = []
    lengths: List[int] = []
    successes = 0

    for episode in range(episodes):
        rng = random.Random(seed + episode)
        state: State = (
            world.dock_pos[0],
            world.dock_pos[1],
            0,
            0,
            world.max_steps,
        )
        total_reward = 0.0
        steps = 0
        success = False

        while not is_terminal_state(state, world.dock_pos):
            intended_action = policy.get(state)
            if intended_action is None or intended_action == "done":
                break

            if rng.random() < p:
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
            if is_goal_state(state, world.dock_pos):
                success = True
            if done:
                break

        reward_totals.append(total_reward)
        lengths.append(steps)
        successes += int(success)

    return {
        "episodes": episodes,
        "average_cumulative_reward": sum(reward_totals) / episodes,
        "success_rate": successes / episodes,
        # This is mean episode length across all episodes, including failures.
        "average_steps": sum(lengths) / episodes,
    }


def plot_policy(world, policy: Dict[State, str], p: float, output_path: Path):
    """Plot policy slices for three task phases at explicit remaining-step values."""
    phases = phase_slices(world.max_steps)
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

    for ax, (has_package, delivered, phase_name, remaining) in zip(axes, phases):
        ax.set_title(f"{phase_name} (steps remaining: {remaining})", fontsize=11)
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
                        (col, row),
                        1,
                        1,
                        facecolor=cell_colors[cell],
                        edgecolor="none",
                    )
                )
                state: State = (row, col, has_package, delivered, remaining)
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
                if action in ARROWS:
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
        f"Five-dimensional Value Iteration Policy (intended-action probability p={p:.2f})",
        fontsize=14,
    )
    fig.savefig(output_path, dpi=180, bbox_inches="tight")
    plt.close(fig)


def main():
    output_dir = Path(__file__).resolve().parent / "value_iteration_results"
    output_dir.mkdir(parents=True, exist_ok=True)

    world = domain.WarehouseGridWorld(seed=LAYOUT_SEED)
    print("Warehouse layout fixed for fair comparison")
    print(f"Layout seed: {LAYOUT_SEED}")
    print(f"Pickup position: {world.pickup_pos}")
    print(f"Packing position: {world.packing_pos}")
    print(f"Charging dock position: {world.dock_pos}")
    state_count = len(build_states(world.grid, world.max_steps))
    print(
        f"State representation: (row, col, has_package, delivered, steps_remaining); "
        f"states={state_count}"
    )
    print(
        f"Gamma={GAMMA}, theta={THETA}, max_steps={world.max_steps}, "
        f"evaluation episodes per p={EVALUATION_EPISODES}"
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
            "max_steps": world.max_steps,
            "state_count": state_count,
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
        "max_steps",
        "state_count",
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

    # Compare the exact same five-dimensional states across p values. Sort by
    # more remaining time first so the exported examples are useful for report
    # discussion rather than being dominated by one-step-to-timeout states.
    p_high, p_mid, p_low = 1.00, 0.90, 0.80
    changed = []
    for state in policies[p_high]:
        actions = tuple(policies[p][state] for p in (p_high, p_mid, p_low))
        if len(set(actions)) > 1 and actions[0] != "done":
            changed.append((state, actions))
    changed.sort(
        key=lambda item: (-item[0][4], item[0][0], item[0][1], item[0][2], item[0][3])
    )

    change_path = output_dir / "policy_action_changes.txt"
    with change_path.open("w", encoding="utf-8") as f:
        f.write(
            "Five-dimensional states where preferred actions change as p decreases\n"
        )
        f.write("Actions are listed in order p=1.00, p=0.90, p=0.80.\n")
        f.write(
            "State format: (row, col, has_package, delivered, steps_remaining).\n\n"
        )
        f.write(f"Number of states with an action change: {len(changed)}\n\n")
        if changed:
            for state, actions in changed:
                f.write(
                    f"state={state}: p=1.00 -> {actions[0]}, "
                    f"p=0.90 -> {actions[1]}, p=0.80 -> {actions[2]}\n"
                )
        else:
            f.write("No action changes were found on this layout.\n")

    summary_path = output_dir / "run_summary.txt"
    with summary_path.open("w", encoding="utf-8") as f:
        f.write("COSC-4117EL Assignment 2 - Value Iteration\n")
        f.write(f"Layout seed: {LAYOUT_SEED}\n")
        f.write(f"Pickup position: {world.pickup_pos}\n")
        f.write(f"Packing position: {world.packing_pos}\n")
        f.write(f"Charging dock position: {world.dock_pos}\n")
        f.write(
            "State representation: (row, col, has_package, delivered, steps_remaining)\n"
        )
        f.write(f"Number of states: {state_count}\n")
        f.write(f"Maximum episode length: {world.max_steps}\n")
        f.write(f"Discount factor gamma: {GAMMA}\n")
        f.write(f"Convergence threshold theta: {THETA}\n")
        f.write(f"Evaluation episodes per p: {EVALUATION_EPISODES}\n")
        f.write(
            "Terminal states: successful return to the charging dock after delivery, "
            "or steps_remaining == 0.\n"
        )
        f.write(
            "Terminal states have zero future value; the reward on the transition "
            "into a terminal state is retained.\n"
        )
        f.write(
            "The supplied environment's step() is deterministic; stochastic outcomes "
            "are explicitly enumerated by this Value Iteration implementation.\n"
        )
        f.write(
            "The transition reward follows the supplied environment's reward checks, "
            "including invalid-move and resulting-cell congestion penalties.\n"
        )
        f.write(
            "See value_iteration_results.csv and policy_action_changes.txt for results.\n"
        )

    print(f"\nResults saved to: {output_dir}")
    print(f"Metrics CSV: {csv_path.name}")
    print(f"Action-change analysis: {change_path.name}")


if __name__ == "__main__":
    main()
