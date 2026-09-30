import sys
import time
from load_puzzle_file import *
from pathlib import Path
from collections import defaultdict

BASIC_BT = "Basic Backtracking"
ENHANCED_BT = "AC-3 Enhanced Backtracking"

OPERATOR_LESS = "<"
OPERATOR_MORE = ">"
OPERATOR_UNEQUAL = "!="
TIMEOUT = 60


class BackTrackingSolver:
    def __init__(self, solver_name, puzzle_data):
        self.solver_name = solver_name
        self.puzzle_data = puzzle_data
        self.size = puzzle_data["size"]
        self.givens = puzzle_data["givens"]
        self.inequalities = puzzle_data["inequalities"]
        self.nodes_visited = 0

        # init puzzle_matrix
        self.puzzle_matrix = [[0] * self.size for _ in range(self.size)]
        for i, data in enumerate(self.givens):
            row, col, value = data
            self.puzzle_matrix[row - 1][col - 1] = value
        # print(self.puzzle_matrix)

        if solver_name == BASIC_BT:
            # init unknown_nodes
            self.unknown_nodes = []
            self.unknown_nodes_set = set()
            self.unknown_nodes_size = 0

            self.unknown_nodes_info()

            # init inequalities_dict
            self.inequalities_single_direction = defaultdict(list)
            self.get_inequalities_single_direction()

        elif solver_name == ENHANCED_BT:
            self.inequalities_direction_dict = defaultdict(list)
            self.get_inequalities_direction()

    def get_inequalities_direction(self):
        for data in self.inequalities:
            row1, col1, operator, row2, col2 = data
            x = (row1 - 1, col1 - 1)
            y = (row2 - 1, col2 - 1)
            self.inequalities_direction_dict[x].append((y, operator))
            self.inequalities_direction_dict[y].append((x, self.switch_op(operator)))

        for r in range(self.size):
            cells = [(r, c) for c in range(self.size)]
            for i in range(len(cells)):
                for j in range(i + 1, len(cells)):
                    x = cells[i]
                    y = cells[j]
                    self.inequalities_direction_dict[x].append((y, OPERATOR_UNEQUAL))
                    self.inequalities_direction_dict[y].append((x, OPERATOR_UNEQUAL))

        for c in range(self.size):
            cells = [(r, c) for r in range(self.size)]
            for i in range(len(cells)):
                for j in range(i + 1, len(cells)):
                    x = cells[i]
                    y = cells[j]
                    self.inequalities_direction_dict[x].append((y, OPERATOR_UNEQUAL))
                    self.inequalities_direction_dict[y].append((x, OPERATOR_UNEQUAL))
        return

    def unknown_nodes_info(self):
        for i in range(self.size):
            for j in range(self.size):
                if self.puzzle_matrix[i][j] == 0:
                    self.unknown_nodes.append((i, j))
                    self.unknown_nodes_set.add((i, j))
                    self.unknown_nodes_size += 1
        return

    def switch_op(self, operator):
        return OPERATOR_MORE if operator == OPERATOR_LESS else OPERATOR_LESS

    def get_inequalities_single_direction(self):
        # inequalities update
        for i, data in enumerate(self.inequalities):
            row1, col1, operator, row2, col2 = data
            x = (row1 - 1, col1 - 1)
            y = (row2 - 1, col2 - 1)
            if x in self.unknown_nodes_set and y in self.unknown_nodes_set:
                if row1 + col1 < row2 + col2:
                    self.inequalities_single_direction[y].append(
                        (x, self.switch_op(operator))
                    )
                else:
                    self.inequalities_single_direction[x].append((y, operator))
            elif x in self.unknown_nodes_set:
                self.inequalities_single_direction[x].append((y, operator))
            else:
                self.inequalities_single_direction[y].append(
                    (x, self.switch_op(operator))
                )
        # print("inequalities_dict", self.inequalities_dict)

        # same row
        same_row = defaultdict(list)
        same_col = defaultdict(list)
        for r, c in self.unknown_nodes:
            same_row[r].append((r, c))
            same_col[c].append((r, c))
        # print("same_row", same_row)
        # print("same_col", same_col)
        for vals in same_row.values():
            if len(vals) <= 1:
                continue
            for j in range(1, len(vals)):
                for i in range(j):
                    self.inequalities_single_direction[vals[j]].append(
                        (vals[i], OPERATOR_UNEQUAL)
                    )
        for vals in same_col.values():
            if len(vals) <= 1:
                continue
            for j in range(1, len(vals)):
                for i in range(j):
                    self.inequalities_single_direction[vals[j]].append(
                        (vals[i], OPERATOR_UNEQUAL)
                    )
        # print("inequalities_dict2", self.inequalities_dict)
        return

    def back_tracking(self, start_time):
        def check_valid(i, j, v):
            if (i, j) not in self.inequalities_single_direction:
                return True
            val_curr = v
            for pos, operation in self.inequalities_single_direction[(i, j)]:
                compare_val = self.puzzle_matrix[pos[0]][pos[1]]
                if operation == OPERATOR_MORE:
                    if val_curr <= compare_val:
                        return False
                elif operation == OPERATOR_LESS:
                    if val_curr >= compare_val:
                        return False
                else:
                    if val_curr == compare_val:
                        return False
            return True

        def dfs(id, st):
            if time.perf_counter() - start_time >= TIMEOUT:
                raise TimeoutError
            if id == len(ans_matrix):
                return True
            i, j = ans_matrix[id]
            for v in range(1, self.size + 1):
                if v in row_col_dup_val[(i, j)]:
                    continue
                self.nodes_visited += 1
                if not check_valid(i, j, v):
                    continue

                self.puzzle_matrix[i][j] = v
                if dfs(id + 1, st):
                    return True
                self.puzzle_matrix[i][j] = 0
            return False

        ans_matrix = []
        # duplicate fixed values
        row_col_dup_val = defaultdict(set)
        for i in range(self.size):
            for j in range(self.size):
                if self.puzzle_matrix[i][j] == 0:
                    ans_matrix.append((i, j))
                    # print([x for x in self.puzzle_matrix[i] if x > 0])
                    row_col_dup_val[(i, j)].update(
                        [x for x in self.puzzle_matrix[i] if x > 0]
                    )
                    row_col_dup_val[(i, j)].update(
                        [
                            self.puzzle_matrix[r][j]
                            for r in range(self.size)
                            if self.puzzle_matrix[r][j] > 0
                        ]
                    )

        is_solved = dfs(0, start_time)
        return is_solved

    def enhanced_back_tracking(self, start_time):
        pass

    def run(self):
        start = time.perf_counter()
        solution = None
        if self.solver_name == BASIC_BT:
            try:
                is_solved = self.back_tracking(start)
                status = "Solved" if is_solved else "No solution"
                solution = self.puzzle_matrix if is_solved else None
            except TimeoutError:
                status = "Time out"
        elif self.solver_name == ENHANCED_BT:
            try:
                is_solved = self.enhanced_back_tracking(start)
                status = "Solved" if is_solved else "No solution"
                solution = self.puzzle_matrix if is_solved else None
            except TimeoutError:
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
    print(solver.run())


if __name__ == "__main__":
    main()
