
import ast
import csv
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Rectangle
from warehouse_bridge import create_env

OUT = Path(__file__).resolve().parent / 'results_q_learning'
ARROW = {'up':'↑','down':'↓','left':'←','right':'→'}


def background(ax, env):
    grid=env.world.grid
    colormap={0:'#fcfcfc',1:'#242424',2:'#ffd9d6',3:'#bdd5fc',4:'#fff0a8',5:'#b7e8c8'}
    for row in range(10):
        for col in range(10):
            val=int(grid[row,col]); ax.add_patch(Rectangle((col-.5,row-.5),1,1,color=colormap[val],ec='#cccccc',lw=.5))
            if val in (3,4,5): ax.text(col,row-.32,{3:'P',4:'D',5:'C'}[val],ha='center',va='center',size=8,weight='bold')
    ax.set(xlim=(-.5,9.5),ylim=(9.5,-.5),xticks=range(10),yticks=range(10))
    ax.set_aspect('equal')


def show_policy(config='A_fast_decay', seed=11):
    env = create_env(.8, 120)

    probabilities = (1.0, 0.9, 0.8)
    phases = ((0, 0, 120), (1, 0, 105), (1, 1, 90))

    fig, axs = plt.subplots(
        3, 3,
        figsize=(12, 12)
    )

    for i, p in enumerate(probabilities):

        policy = json.loads(
            (
                OUT /
                f'policy_{config}_p{p:.2f}_seed{seed}.json'
            ).read_text()
        )

        for phase, (carrying, delivered, remaining) in enumerate(phases):

            ax = axs[i, phase]
            background(ax, env)

            for r in range(10):
                for c in range(10):

                    if int(env.world.grid[r, c]) == 1:
                        continue

                    state = repr(
                        (r, c, carrying, delivered, remaining)
                    )

                    if state in policy:
                        ax.text(
                            c, r + .13,
                            ARROW[policy[state]],
                            ha='center',
                            va='center',
                            size=11
                        )

            ax.set_title(
                f'p={p:.2f} | ' +
                ('Before pickup', 'Carrying', 'Delivered')[phase] + f' | t={remaining}'
            )

    fig.suptitle(
        f'Q-Learning Greedy Policy '
        f'({config}, seed={seed})\nOnly visited states shown; fixed time slices'
    )

    fig.tight_layout()

    fig.savefig(
        OUT / 'policy_grid.png',
        dpi=160
    )

    plt.close(fig)

def show_route(config='A_fast_decay',seed=11):
    env=create_env(.8,120)
    fig,axs=plt.subplots(1,3,figsize=(13,4.5))
    for ax,p in zip(axs,(1.,.9,.8)):
        background(ax,env)
        filename=OUT/f'example_greedy_run_{config}_p{p:.2f}_seed{seed}.csv'
        with filename.open() as f: rows=list(csv.DictReader(f))
        points=[ast.literal_eval(row['state']) for row in rows]
        xs=[s[1] for s in points]; ys=[s[0] for s in points]
        ax.plot(xs,ys,color='#6845a0',lw=1.5,alpha=.8,marker='o',ms=2)
        ax.scatter(xs[0],ys[0],marker='s',s=80,color='#09814a',label='start')
        ax.set_title(f'p={p:.1f}, {len(rows)-1} steps')
    fig.suptitle('Example greedy rollout (one sampled trajectory per p)')
    fig.tight_layout();fig.savefig(OUT/'sample_routes.png',dpi=160);plt.close(fig)


if __name__=='__main__':
    show_policy();show_route()
