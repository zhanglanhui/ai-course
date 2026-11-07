
"""Compare learned Q-Learning policies under different motion probabilities."""

import argparse
import csv
import json
from pathlib import Path

RESULTS_DIR = Path(__file__).resolve().parent / "results_q_learning"


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "policy_high_p",
        nargs="?",
        type=Path,
        default=RESULTS_DIR / "policy_A_fast_decay_p1.00_seed11.json"
    )

    parser.add_argument(
        "policy_low_p",
        nargs="?",
        type=Path,
        default=RESULTS_DIR / "policy_A_fast_decay_p0.80_seed11.json"
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=RESULTS_DIR / "changed_actions.csv"
    )

    parser.add_argument(
        "--min-visits",
        type=int,
        default=20
    )

    args = parser.parse_args()
    if args.min_visits < 1:
        parser.error("--min-visits must be positive")

    # Load learned policies.
    policy_high = json.loads(
        args.policy_high_p.read_text(encoding="utf-8")
    )

    policy_low = json.loads(
        args.policy_low_p.read_text(encoding="utf-8")
    )

    # Load visitation counts corresponding to each policy.
    high_visits_path = args.policy_high_p.with_name(
        args.policy_high_p.name.replace("policy_", "visits_", 1)
    )

    low_visits_path = args.policy_low_p.with_name(
        args.policy_low_p.name.replace("policy_", "visits_", 1)
    )

    visits_high = json.loads(
        high_visits_path.read_text(encoding="utf-8")
    )

    visits_low = json.loads(
        low_visits_path.read_text(encoding="utf-8")
    )

    # Identify states appearing in both policies.
    shared_states = sorted(
        policy_high.keys() & policy_low.keys()
    )

    # Compare preferred actions.
    changed = [
        (state, policy_high[state], policy_low[state])
        for state in shared_states
        if policy_high[state] != policy_low[state]
    ]

    # Keep states visited frequently in both runs.
    meaningful_changes = [
        {
            "state": state,
            "action_high_p": action_high,
            "action_low_p": action_low,
            "visits_high_p": visits_high.get(state, 0),
            "visits_low_p": visits_low.get(state, 0)
        }
        for state, action_high, action_low in changed
        if visits_high.get(state, 0) >= args.min_visits
        and visits_low.get(state, 0) >= args.min_visits
    ]

    # Export comparison.
    args.output.parent.mkdir(parents=True, exist_ok=True)

    with args.output.open(
        "w", newline="", encoding="utf-8"
    ) as output:

        writer = csv.DictWriter(
            output,
            fieldnames=[
                "state",
                "action_high_p",
                "action_low_p",
                "visits_high_p",
                "visits_low_p"
            ]
        )

        writer.writeheader()
        writer.writerows(meaningful_changes)

    print(f"Shared states: {len(shared_states)}")
    print(f"All changed actions: {len(changed)}")
    print(f"Changes meeting visit threshold: {len(meaningful_changes)}")

    for item in meaningful_changes[:10]:
        print(item)

    print(f"Results saved to: {args.output}")


if __name__ == "__main__":
    main()

