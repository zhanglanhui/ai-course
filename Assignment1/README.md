# Futoshiki Puzzle Solver

## Course Information

- **Course:** CPSC-4117EL-01 Artificial Intelligence
- **Assignment:** Assignment 1 – Futoshiki Puzzle Solver using Constraint Satisfaction
- **Language:** Python
- **GUI:** Tkinter

## Files

- `main.py` – starts the application
- `gui.py` – graphical user interface
- `load_puzzle_file.py` – puzzle parsing and validation
- `solver.py` – Basic Backtracking and AC-3 Enhanced Backtracking solvers
- `*.txt` – puzzle files used for testing
- `report.pdf` – assignment report

## Requirements

- Python 3
- Tkinter
- No additional third-party packages are required.

## How to Run

Place all Python files in the same folder and run:

```bash
python main.py
```

If needed, use:

```bash
python3 main.py
```

## How to Use

1. Click **Load** and select a puzzle `.txt` file.
2. Select **Basic Backtracking** or **AC-3 Enhanced Backtracking**.
3. Click **Solve**.
4. The GUI displays the puzzle status, solution, runtime, and nodes visited.

## Puzzle Input Format

```text
SIZE
N

GIVENS
row,column,value

INEQUALITIES
row1,column1,operator,row2,column2
```

Blank lines and lines beginning with `#` are ignored.

## Generative AI Disclosure

OpenAI ChatGPT was used to assist with interpreting the assignment requirements, designing the GUI, checking the solver implementation, preparing test cases, and drafting the report. Generated material was checked against the assignment specification and source code.

Prompt/conversation link:

https://chatgpt.com/share/6ac403f4-5aa4-83e9-a8dc-ec7ee0ef1db0
