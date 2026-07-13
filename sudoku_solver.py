#!/usr/bin/env python3
"""
Sudoku Solver
A lightweight, single-file backtracking Sudoku solver.

Usage:
    python sudoku_solver.py                 # solves a built-in example puzzle
    python sudoku_solver.py puzzle.txt       # solves a puzzle from a file

File format: 9 lines of 9 characters each.
Use digits 1-9 for known cells and 0 or . for blanks. Example:

53..7....
6..195...
.98....6.
8...6...3
4..8.3..1
7...2...6
.6....28.
...419..5
....8..79
"""

import sys

EXAMPLE = [
    "53..7....",
    "6..195...",
    ".98....6.",
    "8...6...3",
    "4..8.3..1",
    "7...2...6",
    ".6....28.",
    "...419..5",
    "....8..79",
]


def parse_board(lines) -> list:
    board = []
    for line in lines:
        row = [0 if c in "0." else int(c) for c in line.strip()]
        if len(row) != 9:
            raise ValueError(f"Invalid row (needs 9 cells): {line!r}")
        board.append(row)
    if len(board) != 9:
        raise ValueError("Puzzle must have exactly 9 rows")
    return board


def load_board(path: str) -> list:
    with open(path) as f:
        lines = [l for l in f.read().splitlines() if l.strip()]
    return parse_board(lines)


def find_empty(board):
    for r in range(9):
        for c in range(9):
            if board[r][c] == 0:
                return r, c
    return None


def is_valid(board, row, col, num) -> bool:
    if num in board[row]:
        return False
    if num in (board[r][col] for r in range(9)):
        return False
    box_r, box_c = 3 * (row // 3), 3 * (col // 3)
    for r in range(box_r, box_r + 3):
        for c in range(box_c, box_c + 3):
            if board[r][c] == num:
                return False
    return True


def solve(board) -> bool:
    empty = find_empty(board)
    if not empty:
        return True
    row, col = empty

    for num in range(1, 10):
        if is_valid(board, row, col, num):
            board[row][col] = num
            if solve(board):
                return True
            board[row][col] = 0

    return False


def print_board(board) -> None:
    for r in range(9):
        if r % 3 == 0 and r != 0:
            print("-" * 21)
        row_str = ""
        for c in range(9):
            if c % 3 == 0 and c != 0:
                row_str += "| "
            val = board[r][c]
            row_str += (str(val) if val != 0 else ".") + " "
        print(row_str.strip())


def main():
    if len(sys.argv) > 1:
        board = load_board(sys.argv[1])
    else:
        print("No puzzle file given, solving built-in example puzzle.\n")
        board = parse_board(EXAMPLE)

    print("Puzzle:")
    print_board(board)

    if solve(board):
        print("\nSolved:")
        print_board(board)
    else:
        print("\nNo solution exists for this puzzle.")


if __name__ == "__main__":
    main()
