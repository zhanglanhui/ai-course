import tkinter as tk
from tkinter import filedialog, messagebox


def parse_puzzle(filename):
    size = None
    given_matrix = []
    inequalities = []
    current_section = None

    sections_seen = set()
    size_value_seen = False

    with open(filename, "r", encoding="utf-8") as file:
        for i, x in enumerate(file, start=1):
            line = x.strip()

            # Ignore blank lines and comments
            if not line or line.startswith("#"):
                continue

            # Section heading
            if line in ("SIZE", "GIVENS", "INEQUALITIES"):
                if line in sections_seen:
                    raise ValueError(f"Line {i}: Duplicate section '{line}'.")

                sections_seen.add(line)
                current_section = line
                continue

            # Parse SIZE
            if current_section == "SIZE":
                if size_value_seen:
                    raise ValueError(f"Line {i}: SIZE must contain only one integer.")

                try:
                    size = int(line)
                except ValueError:
                    raise ValueError(f"Line {i}: SIZE must be an integer.")

                if size <= 0:
                    raise ValueError(f"Line {i}: SIZE must be greater than 0.")

                size_value_seen = True
                continue

            # Parse GIVENS
            if current_section == "GIVENS":
                parts = [x.strip() for x in line.split(",")]

                if len(parts) != 3:
                    raise ValueError(f"Line {i}: GIVENS must be row,column,value.")

                try:
                    row = int(parts[0])
                    col = int(parts[1])
                    value = int(parts[2])
                except ValueError:
                    raise ValueError(f"Line {i}: GIVENS contains an invalid integer.")

                given_matrix.append((row, col, value))
                continue

            # Parse INEQUALITIES
            if current_section == "INEQUALITIES":
                parts = [x.strip() for x in line.split(",")]

                if len(parts) != 5:
                    raise ValueError(
                        f"Line {i}: INEQUALITIES must be "
                        f"row1,column1,operator,row2,column2."
                    )

                try:
                    row1 = int(parts[0])
                    col1 = int(parts[1])
                    operator = parts[2]
                    row2 = int(parts[3])
                    col2 = int(parts[4])
                except ValueError:
                    raise ValueError(
                        f"Line {i}: INEQUALITIES contains an invalid integer."
                    )

                if operator not in ("<", ">"):
                    raise ValueError(
                        f"Line {i}: Invalid operator '{operator}'. "
                        f"Only '<' or '>' are allowed."
                    )

                inequalities.append((row1, col1, operator, row2, col2))
                continue

            # Data before any valid section heading
            raise ValueError(f"Line {i}: Unexpected data outside a valid section.")

    # All three section headings must appear.
    required_sections = {"SIZE", "GIVENS", "INEQUALITIES"}
    missing_sections = required_sections - sections_seen

    if missing_sections:
        raise ValueError(f"Missing section(s): {', '.join(sorted(missing_sections))}.")

    if size is None:
        raise ValueError("SIZE section must contain one integer.")

    return {"size": size, "givens": given_matrix, "inequalities": inequalities}


def validate_puzzle(puzzle_data):
    size = puzzle_data["size"]
    given_matrix = puzzle_data["givens"]
    inequalities = puzzle_data["inequalities"]

    # Check out-of-range GIVENS values.
    for index, data in enumerate(given_matrix, start=1):
        row, col, value = data

        if not (1 <= row <= size):
            raise ValueError(f"Given #{index}: Row {row} is outside 1..{size}.")

        if not (1 <= col <= size):
            raise ValueError(f"Given #{index}: Column {col} is outside 1..{size}.")

        if not (1 <= value <= size):
            raise ValueError(f"Given #{index}: Value {value} is outside 1..{size}.")

    # Check inequality cells and adjacency.
    for index, data in enumerate(inequalities, start=1):
        row1, col1, operator, row2, col2 = data

        if not (1 <= row1 <= size and 1 <= col1 <= size):
            raise ValueError(f"Inequality #{index}: First cell is outside the puzzle.")

        if not (1 <= row2 <= size and 1 <= col2 <= size):
            raise ValueError(f"Inequality #{index}: Second cell is outside the puzzle.")

        distance = abs(row1 - row2) + abs(col1 - col2)

        if distance != 1:
            raise ValueError(
                f"Inequality #{index}: Endpoints "
                f"({row1},{col1}) and ({row2},{col2}) "
                f"must be horizontally or vertically adjacent."
            )

    # Check repeated GIVENS cells.
    seen_cells = set()

    for row, col, _ in given_matrix:
        if (row, col) in seen_cells:
            raise ValueError(f"Repeated cell found: ({row},{col}).")

        seen_cells.add((row, col))

    # Check duplicate fixed values in a row or column.
    tmp_row = [set() for _ in range(size)]
    tmp_col = [set() for _ in range(size)]

    for row, col, val in given_matrix:
        if val in tmp_row[row - 1]:
            raise ValueError(f"Duplicate fixed value {val} found in row {row}.")

        if val in tmp_col[col - 1]:
            raise ValueError(f"Duplicate fixed value {val} found in column {col}.")

        tmp_row[row - 1].add(val)
        tmp_col[col - 1].add(val)


def display_puzzle(parent, puzzle_data):
    # Clear the previous puzzle.
    for widget in parent.winfo_children():
        widget.destroy()

    size = puzzle_data["size"]
    givens = puzzle_data["givens"]
    inequalities = puzzle_data["inequalities"]

    # Store cell widgets for later use.
    cell_widgets = {}

    # Convert givens to a dictionary for quick lookup.
    given_values = {(row, col): value for row, col, value in givens}

    # Create the puzzle grid.
    for row in range(size):
        for col in range(size):
            grid_row = row * 2
            grid_col = col * 2

            puzzle_row = row + 1
            puzzle_col = col + 1

            value = given_values.get((puzzle_row, puzzle_col), "")

            if value != "":
                font = ("Arial", 16, "bold")
            else:
                font = ("Arial", 16)

            cell = tk.Label(
                parent,
                text=str(value),
                width=4,
                height=2,
                font=font,
                relief="solid",
                borderwidth=1,
            )

            cell.grid(
                row=grid_row,
                column=grid_col,
                padx=2,
                pady=2,
            )

            cell_widgets[(puzzle_row, puzzle_col)] = cell

    # Display inequalities.
    for row1, col1, operator, row2, col2 in inequalities:

        # Horizontal inequality.
        if row1 == row2:
            grid_row = (row1 - 1) * 2
            grid_col = (min(col1, col2) - 1) * 2 + 1

        # Vertical inequality.
        else:
            grid_row = (min(row1, row2) - 1) * 2 + 1
            grid_col = (col1 - 1) * 2

        clue = tk.Label(
            parent,
            text=operator,
            font=("Arial", 14, "bold"),
        )

        clue.grid(
            row=grid_row,
            column=grid_col,
        )

    return cell_widgets


class FutoshikiGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Futoshiki Puzzle Solver")

        self.puzzle = None
        self.cell_widgets = {}

        self.solver_var = tk.StringVar(value="Basic Backtracking")

        self.create_widgets()

    def create_widgets(self):
        # Top control frame.
        control_frame = tk.Frame(self.root)
        control_frame.pack(padx=20, pady=10, fill="x")

        self.load_button = tk.Button(
            control_frame,
            text="Load",
            command=self.load_file,
            width=10,
        )
        self.load_button.pack(side="left", padx=5)

        tk.Label(control_frame, text="Solver:").pack(side="left", padx=(20, 5))

        tk.Radiobutton(
            control_frame,
            text="Basic Backtracking",
            variable=self.solver_var,
            value="Basic Backtracking",
        ).pack(side="left")

        tk.Radiobutton(
            control_frame,
            text="AC-3 Enhanced Backtracking",
            variable=self.solver_var,
            value="AC-3 Enhanced Backtracking",
        ).pack(side="left")

        self.solve_button = tk.Button(
            control_frame,
            text="Solve",
            command=self.solve,
            width=10,
        )
        self.solve_button.pack(side="left", padx=10)

        # File label.
        self.file_label = tk.Label(
            self.root,
            text="No puzzle loaded.",
            anchor="w",
        )
        self.file_label.pack(
            padx=20,
            pady=(0, 5),
            fill="x",
        )

        # Puzzle display area.
        self.puzzle_frame = tk.Frame(self.root)
        self.puzzle_frame.pack(
            padx=20,
            pady=20,
        )

        # Status and metrics.
        self.status_label = tk.Label(
            self.root,
            text="Status: Ready",
            anchor="w",
        )
        self.status_label.pack(
            padx=20,
            fill="x",
        )

        self.runtime_label = tk.Label(
            self.root,
            text="Runtime: --",
            anchor="w",
        )
        self.runtime_label.pack(
            padx=20,
            fill="x",
        )

        self.nodes_label = tk.Label(
            self.root,
            text="Nodes visited: --",
            anchor="w",
        )
        self.nodes_label.pack(
            padx=20,
            pady=(0, 10),
            fill="x",
        )

    def load_file(self):
        filename = filedialog.askopenfilename(
            title="Select Futoshiki Puzzle",
            filetypes=[
                ("Text files", "*.txt"),
                ("All files", "*.*"),
            ],
        )

        if not filename:
            return

        try:
            puzzle = parse_puzzle(filename)
            validate_puzzle(puzzle)
        except (ValueError, OSError) as error:
            self.puzzle = None
            self.cell_widgets = {}
            messagebox.showerror(
                "Invalid Puzzle",
                str(error),
            )
            self.display_status("Invalid puzzle")
            return

        self.puzzle = puzzle
        self.cell_widgets = display_puzzle(
            self.puzzle_frame,
            puzzle,
        )

        self.file_label.config(text=f"Loaded: {filename}")

        self.display_status("Ready")
        self.display_metrics(None, None)

    def solve(self):
        if self.puzzle is None:
            messagebox.showwarning(
                "No Puzzle",
                "Please load a valid puzzle first.",
            )
            return

        selected_solver = self.solver_var.get()

        # Task 2 and Task 3 will provide the actual solver implementations.
        # The GUI already provides the required solver selection and Solve button.
        self.display_status("Solving")
        self.root.update_idletasks()

        print(f"Selected solver: {selected_solver}")
        # TODO: connect Task 2 / Task 3 solver here.

    def display_solution(self, solution):
        if self.puzzle is None:
            return

        given_cells = {(row, col) for row, col, _ in self.puzzle["givens"]}

        for row in range(1, self.puzzle["size"] + 1):
            for col in range(1, self.puzzle["size"] + 1):
                value = solution[row - 1][col - 1]
                cell = self.cell_widgets[(row, col)]

                if (row, col) in given_cells:
                    cell.config(
                        text=str(value),
                        font=("Arial", 16, "bold"),
                    )
                else:
                    cell.config(
                        text=str(value),
                        font=("Arial", 16),
                    )

    def display_status(self, status):
        self.status_label.config(text=f"Status: {status}")

    def display_metrics(self, runtime, nodes):
        if runtime is None:
            self.runtime_label.config(text="Runtime: --")
        else:
            self.runtime_label.config(text=f"Runtime: {runtime:.4f} s")

        if nodes is None:
            self.nodes_label.config(text="Nodes visited: --")
        else:
            self.nodes_label.config(text=f"Nodes visited: {nodes}")


def main():
    root = tk.Tk()
    app = FutoshikiGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
