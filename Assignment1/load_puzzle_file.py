def parse_puzzle(filename):
    size = None
    given_matrix = []
    inequalities = []
    current_section = None
    with open(filename, "r", encoding="utf-8") as file:
        for i, x in enumerate(file):
            line = x.strip()
            # if "SIZE" in line:
            #     print(line)
            #     break
            if not line or str(line).startswith("#"):
                # current_section = None
                continue
            if line in ("SIZE", "GIVENS", "INEQUALITIES"):
                current_section = line
                continue
            # print(line, current_section)
            # Parse SIZE
            if current_section == "SIZE":
                try:
                    size = int(line)
                except ValueError:
                    raise ValueError(f"Line {i}: SIZE must be an integer.")
                if size <= 0:
                    raise ValueError(f"Line {i}: SIZE must be greater than 0.")
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
                        f"Line {i}: INEQUALITIES must be row1,column1,operator,row2,column2."
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

            # outside any section
            raise ValueError(f"Line {i}: Unexpected data outside a valid section.")

    # Basic final validation
    if size is None:
        raise ValueError("Missing SIZE section.")
    if len(given_matrix) == 0:
        raise ValueError("Missing givens section.")
    if len(inequalities) == 0:
        raise ValueError("Missing inequalities section.")
    return {"size": size, "givens": given_matrix, "inequalities": inequalities}


def validate_puzzle(puzzle_data):
    size = puzzle_data["size"]
    given_matrix = puzzle_data["givens"]
    inequalities = puzzle_data["inequalities"]
    # check out-of-range values
    for i, data in enumerate(given_matrix):
        row, col, value = data
        if not (1 <= row <= size):
            raise ValueError(f"Line {i}: Row {row} is outside 1 and {size}.")
        if not (1 <= col <= size):
            raise ValueError(f"Line {i}: Column {col} is outside 1 and {size}.")
        if not (1 <= value <= size):
            raise ValueError(f"Line {i}: Value {value} is outside 1 and {size}.")
    for i, data in enumerate(inequalities):
        row1, col1, operator, row2, col2 = data
        # check out-of-range values
        if not (1 <= row1 <= size and 1 <= col1 <= size):
            raise ValueError(f"Line {i}: First cell is outside the puzzle.")
        if not (1 <= row2 <= size and 1 <= col2 <= size):
            raise ValueError(f"Line {i}: Second cell is outside the puzzle.")
        # Check adjacency
        distance = abs(row1 - row2) + abs(col1 - col2)
        if distance != 1:
            raise ValueError(
                f"Line {i}: Inequality endpoints ({row1},{col1}) and ({row2},{col2}) must be horizontally or vertically adjacent."
            )

    # repeated cells
    tmp = set()
    for row, col, _ in given_matrix:
        if (row, col) in tmp:
            raise ValueError(f"repeated cells found ({row},{col}).")
        tmp.add((row, col))

    # check duplicate fixed values in a row or column
    tmp_row = [set() for _ in range(size)]
    tmp_col = [set() for _ in range(size)]
    for row, col, val in given_matrix:
        if val in tmp_row[row - 1]:
            raise ValueError(f"duplicate fixed values {val} found in Row: {row}.")
        if val in tmp_col[col - 1]:
            raise ValueError(f"duplicate fixed values {val} found in Col: {col}.")
        tmp_row[row - 1].add(val)
        tmp_col[col - 1].add(val)
    return
