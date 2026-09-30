import sys
import time
from load_puzzle_file import *
from pathlib import Path
from collections import defaultdict, deque

BASIC_BT = "Basic Backtracking"
ENHANCED_BT = "AC-3 Enhanced Backtracking"

OPERATOR_LESS = "<"
OPERATOR_MORE = ">"
OPERATOR_UNEQUAL = "!="
TIMEOUT = 60


class FutoshikiSolver:
    def __init__(self, puzzle_data):
        # self.solver_name = solver_name
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

        # init unknown_nodes
        self.unknown_nodes = []
        self.unknown_nodes_set = set()
        self.unknown_nodes_size = 0
        self.unknown_nodes_info()

        # init inequalities_dict
        self.inequalities_direction_dict = self.get_inequalities_direction()

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

    def satisfy_constraints(self, x_value, y_value, operators):
        for operator in operators:
            if operator == OPERATOR_UNEQUAL:
                if x_value == y_value:
                    return False
            elif operator == OPERATOR_LESS:
                if x_value >= y_value:
                    return False
            elif operator == OPERATOR_MORE:
                if x_value <= y_value:
                    return False
        return True

    def get_inequalities_direction(self):
        pass

    def backtracking(self, st):
        pass

    def run(self, start_time):
        solution = None
        # if self.solver_name == BASIC_BT:
        try:
            is_solved = self.backtracking(start_time)
            status = "Solved" if is_solved else "No solution"
            solution = self.puzzle_matrix if is_solved else None
        except TimeoutError:
            status = "Time out"
        # elif self.solver_name == ENHANCED_BT:
        #     try:
        #         is_solved = self.backtracking(start)
        #         status = "Solved" if is_solved else "No solution"
        #         solution = self.puzzle_matrix if is_solved else None
        #     except TimeoutError:
        #         status = "Time out"
        # else:
        #     raise ValueError(f"Solver_name {self.solver_name} is error.")
        runtime = time.perf_counter() - start_time
        return {
            "size": self.size,
            "givens": self.givens,
            "inequalities": self.inequalities,
            "solution": solution,
            "status": status,  # Solved / No solution / Time out
            "runtime": runtime,
            "nodes": self.nodes_visited,
        }


class BackTrackingSolver(FutoshikiSolver):
    def __init__(self, puzzle_data):
        super().__init__(puzzle_data)

    def get_inequalities_direction(self):
        inequalities_direction_dict = defaultdict(list)
        # inequalities update
        for i, data in enumerate(self.inequalities):
            row1, col1, operator, row2, col2 = data
            x = (row1 - 1, col1 - 1)
            y = (row2 - 1, col2 - 1)
            if x in self.unknown_nodes_set and y in self.unknown_nodes_set:
                if row1 + col1 < row2 + col2:
                    inequalities_direction_dict[y].append((x, self.switch_op(operator)))
                else:
                    inequalities_direction_dict[x].append((y, operator))
            elif x in self.unknown_nodes_set:
                inequalities_direction_dict[x].append((y, operator))
            else:
                inequalities_direction_dict[y].append((x, self.switch_op(operator)))
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
                    inequalities_direction_dict[vals[j]].append(
                        (vals[i], OPERATOR_UNEQUAL)
                    )
        for vals in same_col.values():
            if len(vals) <= 1:
                continue
            for j in range(1, len(vals)):
                for i in range(j):
                    inequalities_direction_dict[vals[j]].append(
                        (vals[i], OPERATOR_UNEQUAL)
                    )
        # print("inequalities_dict2", self.inequalities_dict)
        return inequalities_direction_dict

    def backtracking(self, start_time):
        def check_valid(i, j, v):
            if (i, j) not in self.inequalities_direction_dict:
                return True
            val_curr = v
            for pos, operation in self.inequalities_direction_dict[(i, j)]:
                compare_val = self.puzzle_matrix[pos[0]][pos[1]]
                if not self.satisfy_constraints(val_curr, compare_val, [operation]):
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


class EnhancedBackTrackingSolver(FutoshikiSolver):
    def __init__(self, puzzle_data):
        super().__init__(puzzle_data)
        self.domains = self.init_domains()

    def get_inequalities_direction(self):
        inequalities_direction_dict = defaultdict(list)
        # inequalities rules
        for data in self.inequalities:
            row1, col1, operator, row2, col2 = data
            x = (row1 - 1, col1 - 1)
            y = (row2 - 1, col2 - 1)
            inequalities_direction_dict[x].append((y, operator))
            inequalities_direction_dict[y].append((x, self.switch_op(operator)))

        # row rules
        for r in range(self.size):
            for i in range(self.size):
                for j in range(i + 1, self.size):
                    x = (r, i)
                    y = (r, j)
                    inequalities_direction_dict[x].append((y, OPERATOR_UNEQUAL))
                    inequalities_direction_dict[y].append((x, OPERATOR_UNEQUAL))

        # column rules
        for c in range(self.size):
            for i in range(self.size):
                for j in range(i + 1, self.size):
                    x = (i, c)
                    y = (j, c)
                    inequalities_direction_dict[x].append((y, OPERATOR_UNEQUAL))
                    inequalities_direction_dict[y].append((x, OPERATOR_UNEQUAL))
        return inequalities_direction_dict

    def init_domains(self):
        domains = {}
        for i in range(self.size):
            for j in range(self.size):
                if self.puzzle_matrix[i][j] != 0:
                    domains[(i, j)] = {self.puzzle_matrix[i][j]}
                else:
                    domains[(i, j)] = set(range(1, self.size + 1))
        return domains

    def order_values(self, var, domains):
        values = []
        neighbors = {neighbor for neighbor, _ in self.inequalities_direction_dict[var]}
        for value in sorted(domains[var]):
            eliminated = 0
            for neighbor in neighbors:
                operators = [
                    operator
                    for n, operator in self.inequalities_direction_dict[var]
                    if n == neighbor
                ]
                for neighbor_value in domains[neighbor]:
                    if not self.satisfy_constraints(value, neighbor_value, operators):
                        eliminated += 1
            values.append((eliminated, value))

        # Least constraining value first
        values.sort()

        return [value for eliminated, value in values]

    def select_variable(self, domains):
        candidates = [x for x in domains if len(domains[x]) > 1]
        if not candidates:
            return None

        def degree(x):
            neighbors = {
                neighbor for neighbor, _ in self.inequalities_direction_dict[x]
            }
            return sum(1 for neighbor in neighbors if len(domains[neighbor]) > 1)

        # MRV first: smallest domain
        # Degree second: most unassigned neighbors
        return min(candidates, key=lambda x: (len(domains[x]), -degree(x)))

    def revise(self, domains, x, y):
        # Get all constraints between x and y
        operators = [
            operator
            for neighbor, operator in self.inequalities_direction_dict[x]
            if neighbor == y
        ]

        # No constraints
        if not operators:
            return False

        revised = False
        values_to_remove = set()
        for x_value in domains[x]:
            supported = False
            for y_value in domains[y]:
                if self.satisfy_constraints(x_value, y_value, operators):
                    supported = True
                    break
            # No value in Y can support x_value
            if not supported:
                values_to_remove.add(x_value)

        if values_to_remove:
            domains[x] -= values_to_remove
            revised = True

        return revised

    def ac3(self, domains, start_time, initial_queue=None):
        if not initial_queue:
            inequalities_pairs = {
                (x, y)
                for x in self.inequalities_direction_dict
                for y, _ in self.inequalities_direction_dict[x]
            }
            queue = deque(inequalities_pairs)
        else:
            queue = deque(initial_queue)

        while queue:
            # timeout check
            if time.perf_counter() - start_time >= TIMEOUT:
                raise TimeoutError
            x, y = queue.popleft()
            if self.revise(domains, x, y):
                # Empty domain -> failure
                if not domains[x]:
                    return False
                # x changed, so check relation of neighbors of x with x again.
                for z, _ in self.inequalities_direction_dict[x]:
                    if z != y:
                        queue.append((z, x))

        return True

    def backtracking(self, start_time):
        # Recursive search
        def dfs(domains):
            # timeout
            if time.perf_counter() - start_time >= TIMEOUT:
                raise TimeoutError
            # Complete assignment
            if all(
                len(domains[(i, j)]) == 1
                for i in range(self.size)
                for j in range(self.size)
            ):
                self.puzzle_matrix = [
                    [next(iter(domains[(i, j)])) for j in range(self.size)]
                    for i in range(self.size)
                ]
                self.domains = domains
                return True

            # MRV + Degree
            var = self.select_variable(domains)

            # LCV
            for value in self.order_values(var, domains):
                # One node = one attempted value assignment
                self.nodes_visited += 1
                # Copy domains
                new_domains = {x: set(values) for x, values in domains.items()}
                # Tentative assignment
                new_domains[var] = {value}
                # AC-3 on affected arcs
                # Since var changed, check: neighbor -> var
                affected_arcs = {
                    (neighbor, var)
                    for neighbor, _ in self.inequalities_direction_dict[var]
                }
                if not self.ac3(new_domains, start_time, affected_arcs):
                    continue
                # Continue recursively
                if dfs(new_domains):
                    return True
            # If failed: new_domains is simply discarded.
            # This is our restore operation.
            return False

        # Initialize domains
        domains = self.init_domains()

        # Initial AC-3 propagation
        if not self.ac3(domains, start_time):
            return False

        return dfs(domains)


def main():
    INPUT_FILE = sys.argv[1]
    if not Path(INPUT_FILE).exists():
        print(f"the file {INPUT_FILE} is not exit.")
        return
    print(f"the file {INPUT_FILE} is exit. Now move on.")
    puzzle_input = parse_puzzle(INPUT_FILE)
    start = time.perf_counter()
    # solver = BackTrackingSolver(puzzle_input)
    solver = EnhancedBackTrackingSolver(puzzle_input)
    print(solver.run(start))


if __name__ == "__main__":
    main()
