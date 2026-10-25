COSC-4117EL Assignment 2

Files

- warehouse_gridworld_domain_random.py: supplied environment file
- value_iteration.py: Value Iteration implementation and experiments for p = 1.00, 0.90, 0.80
- value_iteration_results/value_iteration_results.csv: convergence and Monte Carlo evaluation metrics
- value_iteration_results/value_iteration_policy_p_*.png: policy maps. Each figure contains three task phases:
  before pickup, carrying package, and after delivery
- value_iteration_results/policy_action_changes.txt: examples where the preferred action changes as p decreases
- value_iteration_results/run_summary.txt: configuration and layout information

How to run

1. Keep value_iteration.py and warehouse_gridworld_domain_random.py in the same folder.
2. Install dependencies if needed: numpy and matplotlib. pygame is only needed for the environment GUI; this Value
   Iteration script can run without it.
3. Run: python value_iteration.py
4. Results will be regenerated in value_iteration_results/.

Current experimental settings

- Layout seed: 42 (kept fixed across p values for a fair comparison)
- Discount factor gamma: 0.95
- Convergence threshold theta: 1e-6
- Evaluation: 500 episodes per p
- Maximum steps per evaluation episode: taken from the environment (120)

Prompt/conversation link:

https://chatgpt.com/share/6add64f7-64f0-83ea-95e0-cb169aee07e5