import random

from warehouse_gridworld_domain_random import WarehouseGridWorld, ACTIONS

PERPENDICULAR = {
    "up": ("left", "right"),
    "down": ("left", "right"),
    "left": ("up", "down"),
    "right": ("up", "down"),
}


class StochasticWarehouseAdapter:
    actions = tuple(ACTIONS)

    def __init__(self, p: float = 0.8, max_steps: int = 120, layout_seed: int = 42):
        if not 0.0 <= p <= 1.0:
            raise ValueError("p must be between 0 and 1")
        self.p = float(p)
        self.layout_seed = int(layout_seed)
        self.world = WarehouseGridWorld(seed=self.layout_seed, max_steps=max_steps)
        self.motion_rng = random.Random(0)
        self.successful = False

    def reset(self, seed: int):
        # Reseeding motion does not regenerate pickup/packing/dock positions.
        self.motion_rng.seed(seed)
        self.successful = False
        state = self.world.reset()
        return (*state, self.world.max_steps - self.world.steps)

    def step(self, action: str):
        if action not in self.actions:
            raise ValueError(f"Unknown action {action}")
        u = self.motion_rng.random()
        if u < self.p:
            executed = action
        elif u < self.p + (1.0 - self.p) / 2:
            executed = PERPENDICULAR[action][0]
        else:
            executed = PERPENDICULAR[action][1]
        result = self.world.step(executed)
        self.successful = (
            self.successful or result.info.get("event") == "return_to_dock"
        )
        terminated = self.successful
        truncated = result.done and not terminated
        state = (*result.state, self.world.max_steps - self.world.steps)
        return state, float(result.reward), terminated, truncated


def create_env(p: float, max_steps: int):
    return StochasticWarehouseAdapter(p=p, max_steps=max_steps)
