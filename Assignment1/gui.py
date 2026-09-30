import tkinter as tk
from tkinter import filedialog, messagebox

from load_puzzle_file import parse_puzzle, validate_puzzle
from solver import BackTrackingSolver, ENHANCED_BT, BASIC_BT


def display_puzzle(parent, puzzle_data):
    # Clear the previous puzzle
    for widget in parent.winfo_children():
        widget.destroy()

    size = puzzle_data["size"]
    givens = puzzle_data["givens"]
    inequalities = puzzle_data["inequalities"]
    # Store cell widgets for later use
    cell_widgets = {}
    given_values = {(row, col): value for row, col, value in givens}
    # Create the puzzle grid
    for row in range(size):
        for col in range(size):
            # GUI position of the actual cell
            grid_row = row * 2
            grid_col = col * 2
            puzzle_row = row + 1
            puzzle_col = col + 1

            # Get given value if this cell is fixed
            value = given_values.get((puzzle_row, puzzle_col), "")
            # Fixed value -> bold
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

            cell.grid(row=grid_row, column=grid_col, padx=2, pady=2)
            cell_widgets[(puzzle_row, puzzle_col)] = cell

    # Display inequalities
    for row1, col1, operator, row2, col2 in inequalities:
        if row1 == row2:
            grid_row = (row1 - 1) * 2
            grid_col = (min(col1, col2) - 1) * 2 + 1
        else:
            grid_row = (min(row1, row2) - 1) * 2 + 1
            grid_col = (col1 - 1) * 2

        clue = tk.Label(parent, text=operator, font=("Arial", 14, "bold"))
        clue.grid(row=grid_row, column=grid_col)

    return cell_widgets


class FutoshikiGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Futoshiki Puzzle Solver")
        self.puzzle_data = None
        self.cell_widgets = {}
        self.solver_var = tk.StringVar(value=BASIC_BT)
        self.create_widgets()

    def create_widgets(self):
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
            text=BASIC_BT,
            variable=self.solver_var,
            value=BASIC_BT,
        ).pack(side="left")

        tk.Radiobutton(
            control_frame,
            text=ENHANCED_BT,
            variable=self.solver_var,
            value=ENHANCED_BT,
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
            ],
        )

        if not filename:
            return
        try:
            puzzle = parse_puzzle(filename)
            validate_puzzle(puzzle)
        except (ValueError, OSError) as error:
            self.puzzle_data = None
            self.cell_widgets = {}
            messagebox.showerror(
                "Invalid Puzzle",
                str(error),
            )
            self.display_status("Invalid puzzle")
            return

        self.puzzle_data = puzzle
        self.cell_widgets = display_puzzle(
            self.puzzle_frame,
            puzzle,
        )
        self.file_label.config(text=f"Loaded: {filename}")
        self.display_status("Ready")
        self.display_metrics(None, None)

    def solve(self):
        if self.puzzle_data is None:
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
        # BackTrackingSolver(selected_solver, self.puzzle_data)
        try:
            solver = BackTrackingSolver(selected_solver, self.puzzle_data)
            ans = solver.run()
        except (ValueError, OSError) as error:
            self.puzzle_data = None
            self.cell_widgets = {}
            messagebox.showerror(
                "Invalid Puzzle",
                str(error),
            )
            self.display_status("Invalid puzzle")
            return

    def display_solution(self, solution):
        if self.puzzle_data is None:
            return

        given_cells = {(row, col) for row, col, _ in self.puzzle_data["givens"]}
        for row in range(1, self.puzzle_data["size"] + 1):
            for col in range(1, self.puzzle_data["size"] + 1):
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
