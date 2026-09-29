import collections
import sys
import time
from load_puzzle_file import *
from pathlib import Path

BASIC_BT = "Basic Backtracking"
ENHANCED_BT = "AC-3 Enhanced Backtracking"


class BackTrackingSolver:
    def __init__(self, solver_name, puzzle_data):
        self.solver_name = solver_name
        self.puzzle_data = puzzle_data
        self.size = puzzle_data["size"]
        self.givens = puzzle_data["givens"]
        self.inequalities = puzzle_data["inequalities"]
        self.puzzle_matrix = [[0] * self.size for _ in range(self.size)]
        self.nodes_visited = 0
        for i, data in enumerate(self.givens):
            row, col, value = data
            self.puzzle_matrix[row - 1][col - 1] = value
        print(self.puzzle_matrix)
        self.inequalities_dict = collections.defaultdict(list)
        for i, data in enumerate(self.inequalities):
            row1, col1, operator, row2, col2 = data
            if row1 + col1 < row2 + col2:
                self.inequalities_dict[(row2 - 1, col2 - 1)].append(
                    (row1 - 1, col1 - 1)
                )
                self.inequalities_dict[(row2 - 1, col2 - 1)].append(operator)
            else:
                self.inequalities_dict[(row1 - 1, col1 - 1)].append(
                    (row2 - 1, col2 - 1)
                )
                self.inequalities_dict[(row1 - 1, col1 - 1)].append(operator)

    def back_tracking(self, start_time):
        pass

    def enhanced_back_tracking(self, start_time):
        pass

    def run(self):
        start = time.perf_counter()
        solution = None
        if self.solver_name == BASIC_BT:
            try:
                solution = self.back_tracking(start)
                status = "Solved" if solution else "No solution"
            except TimeoutError:
                solution = None
                status = "Time out"
        elif self.solver_name == BASIC_BT:
            try:
                solution = self.enhanced_back_tracking(start)
                status = "Solved" if solution else "No solution"
            except TimeoutError:
                solution = None
                status = "Time out"
        else:
            raise ValueError(f"Solver_name {self.solver_name} is error.")
        runtime = time.perf_counter() - start
        return {
            "size": self.size,
            "givens": self.givens,
            "inequalities": self.inequalities,
            "solution": solution,
            "status": status,  # Solved / No solution / Time out
            "runtime": runtime,
            "nodes": self.nodes_visited,
        }


def main():
    INPUT_FILE = sys.argv[1]
    if not Path(INPUT_FILE).exists():
        print(f"the file {INPUT_FILE} is not exit.")
        return
    print(f"the file {INPUT_FILE} is exit. Now move on.")
    puzzle_input = parse_puzzle(INPUT_FILE)
    # print(tt)
    solver = BackTrackingSolver(BASIC_BT, puzzle_input)
    solver.run()


if __name__ == "__main__":
    main()
