# Warehouse Robot Decision Making

**Course:** CPSC-4117EL-01 – Artificial Intelligence  
**Assignment:** Assignment 2  
**Group:** 12

This project applies Value Iteration and tabular Q-Learning to the warehouse Gridworld framework included in this
submission. The robot must collect a package, deliver it to the packing station, and return to the charging dock. Both
algorithms use the same five-component state representation and the same 120-step episode limit.

## 1. Submitted files

The ZIP contains the following project files:

```text
COSC_4117EL_A2_G12/
├── Assignment2_Report.pdf
├── README.md
├── COSC_4117EL_A2_G12-value_iteration.py
├── COSC_4117EL_A2_G12-q_learning.py
├── warehouse_gridworld_domain_random.py
├── warehouse_bridge.py
├── plot_policies.py
└── compare_policies.py
```

The experiment output folders are created when the scripts run; they are not required to be present in the submitted
ZIP.

## 2. Environment and MDP

The project uses `warehouse_gridworld_domain_random.py`, the Gridworld environment included with the assignment project.
The fixed layout used for the reported experiments has seed `42` and the following station positions:

| Item            | Grid position `(row, column)` |
|-----------------|------------------------------:|
| Pickup station  |                      `(2, 2)` |
| Packing station |                      `(0, 4)` |
| Charging dock   |                      `(6, 0)` |

The grid is 10 × 10. Shelves block movement. Congestion cells can be entered but incur a penalty.

### State representation

Both algorithms use:

```text
(row, col, has_package, delivered, steps_remaining)
```

The task-progress flags use three valid combinations: `(0, 0)` before pickup, `(1, 0)` after pickup but before delivery,
and `(1, 1)` after delivery. The combination `(0, 1)` is invalid. The remaining-step value ranges from `0` to `120`.

For the fixed layout, there are 77 passable cells, three valid task-progress phases, and 121 remaining-step values:

```text
77 × 3 × 121 = 27,951 states
```

An episode ends when the robot has delivered the package and returned to the charging dock, or when the 120-step limit
is reached. The immediate reward on the transition into a terminal state is retained; terminal states have no future
value.

### Actions and stochastic movement

The action space is `up`, `down`, `left`, and `right`. For a selected action, the intended direction occurs with
probability `p`; the two perpendicular directions each occur with probability `(1 - p) / 2`.

The experiments use:

| Intended-action probability `p` | Each perpendicular outcome |
|--------------------------------:|---------------------------:|
|                            1.00 |                       0.00 |
|                            0.90 |                       0.05 |
|                            0.80 |                       0.10 |

If an executed movement would enter a shelf or leave the grid, the robot remains in its current cell.

### Reward model

| Event                                            |                Reward |
|--------------------------------------------------|----------------------:|
| Pick up the package                              |                   +25 |
| Deliver the package while carrying it            |                   +40 |
| Return to the charging dock after delivery       |                  +100 |
| Resulting cell is a congestion cell              |                   -10 |
| Each time step                                   |                    -1 |
| Attempt to move into a shelf or outside the grid | -3 additional penalty |

The reward is additive. The normal step penalty applies on every transition. The invalid-move penalty is additional to
the step penalty. The supplied environment checks congestion on the resulting cell after blocked movement has been
resolved.

## 3. Environment adapter and documented changes

The supplied environment's `step()` method executes one deterministic direction. The assignment requires stochastic
movement, so the project adds the following adaptation without replacing the Gridworld environment:

- `warehouse_bridge.py` samples the intended direction or one of its two perpendicular directions according to `p`, then
  delegates the executed direction to the original `world.step(...)` method.
- The bridge appends `steps_remaining` to the four-component state returned by the environment. This gives Q-Learning
  the same five-component state used by Value Iteration.
- The Value Iteration implementation explicitly enumerates the intended and perpendicular movement outcomes, applies the
  supplied environment's movement and reward rules, and combines probabilities when outcomes lead to the same next
  state.

The environment module imports `pygame` at module load time. Therefore, `pygame` must be installed even when running the
algorithms without opening the interactive window. The GUI itself is optional.

## 4. Requirements and installation

Use Python **3.10 or newer**. From the project directory, install the required packages:

```bash
python -m pip install numpy matplotlib pygame
```

`numpy` is used by the Gridworld environment and policy visualization; `matplotlib` is used for plots; `pygame` is
imported by the supplied environment module and is also used by its optional interactive GUI. No Gymnasium installation
is required.

All commands below should be run from the folder containing the submitted `.py` files.

## 5. Run the experiments

### 5.1 Value Iteration

Run:

```bash
python COSC_4117EL_A2_G12-value_iteration.py
```

The script runs all three intended-action probabilities (`1.00`, `0.90`, and `0.80`) using the fixed layout seed `42`.
Its settings are defined near the top of the script:

- Discount factor: `gamma = 0.95`
- Convergence threshold: `theta = 1e-6`
- Maximum episode length: `120`
- Evaluation episodes: `500` per probability

The script creates `value_iteration_results/` and writes:

- `value_iteration_results.csv` – convergence and evaluation metrics for each probability.
- `value_iteration_policy_p_1.00.png`, `value_iteration_policy_p_0.90.png`, and `value_iteration_policy_p_0.80.png` –
  five-dimensional policy visualizations using selected remaining-step slices.
- `policy_action_changes.txt` – five-dimensional states whose preferred action changes across the three probabilities.
- `run_summary.txt` – the layout, state representation, settings, and terminal-condition summary.

The convergence count is reported as the number of full Gauss-Seidel sweeps. States are processed in ascending order of
remaining steps, so the finite-horizon updates use backward induction.

### 5.2 Q-Learning

Run the documented experiment configuration:

```bash
python COSC_4117EL_A2_G12-q_learning.py --adapter warehouse_bridge:create_env --episodes 5000 --eval-episodes 100 --max-steps 120 --seeds 11 42 99 --probabilities 1.0 0.9 0.8 --output results_q_learning
```

This runs two Q-Learning configurations for each probability and each of the three seeds. Each trained policy is
evaluated for 100 episodes with exploration disabled. With the settings above, the experiment contains 18 training runs,
90,000 training episodes in total, and 1,800 evaluation episodes in total.

The two built-in configurations are:

| Parameter               | Configuration A – `A_fast_decay` | Configuration B – `B_slow_decay` |
|-------------------------|---------------------------------:|---------------------------------:|
| Learning rate `alpha`   |                             0.20 |                             0.10 |
| Discount factor `gamma` |                             0.95 |                             0.99 |
| Initial epsilon         |                             1.00 |                             1.00 |
| Epsilon decay           |                            0.995 |                            0.999 |
| Minimum epsilon         |                             0.05 |                             0.05 |

The Q-Learning agent receives sampled states and rewards through the adapter. It is not given the transition probability
`p`; the adapter uses `p` to generate the stochastic transitions.

The script creates `results_q_learning/` and writes training/evaluation episode CSV files, per-seed summary CSV files,
policy and visitation JSON files, example greedy rollout CSV files, training plots, and a `settings.json` file.

### 5.3 Plot learned Q-Learning policies and example routes

Run this after the Q-Learning experiment has generated its output files:

```bash
python plot_policies.py
```

The plotting script uses Configuration A (`A_fast_decay`) and training seed `11` by default. It reads the generated
policy JSON and example rollout CSV files from `results_q_learning/`, then writes `policy_grid.png` and
`sample_routes.png` to that folder.

### 5.4 Compare Q-Learning policies across two motion settings

Run this after the Q-Learning experiment:

```bash
python compare_policies.py
```

By default, this compares the Configuration A, seed 11 Q-Learning policies at `p = 1.00` and `p = 0.80`, and writes
`results_q_learning/changed_actions.csv`. It keeps states visited at least 20 times in both runs. This script compares
two Q-Learning policies across motion settings; it does **not** calculate a direct Value Iteration-versus-Q-Learning
policy agreement score.

## 6. Reproducibility notes

- The warehouse layout seed is fixed at `42` for the reported experiments.
- Q-Learning motion/training seeds are `11`, `42`, and `99`.
- The Q-Learning evaluation is greedy (`epsilon = 0`) and does not update the learned Q-values.
- Evaluation seeds and sample sizes for Value Iteration and Q-Learning are not paired; cross-algorithm performance
  comparisons should therefore be interpreted descriptively, not as paired statistical tests.
- The generated CSV and JSON files provide the run-level records and summaries used to inspect the experiments.

## 7. Generative AI acknowledgment

OpenAI ChatGPT was used to assist with interpreting the assignment requirements, discussing algorithm design, reviewing
parts of the implementations, and improving documentation and report wording. The group reviewed the submitted code and
results. The relevant conversation links are:

- **Value Iteration discussion:** https://chatgpt.com/share/6aef6e1b-27c8-83ea-ad80-a71f47888e9a
- **Q-Learning discussion:** https://chatgpt.com/share/6aef6095-5a6c-83ea-a53f-07abde8c9a5f

The Value Iteration source file includes a code-level acknowledgment and its conversation link. The assignment also
requires AI-assisted code or text to be acknowledged in the relevant source-code comments. If other submitted source
files were generated or modified with AI assistance, add the corresponding shareable conversation link in those files as
well; README and report links do not replace that code-comment requirement.
