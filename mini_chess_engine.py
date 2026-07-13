#!/usr/bin/env python3
"""
Mini Chess Engine
A lightweight, single-file chess engine: full legal move generation
(no castling / en passant, pawns auto-promote to queen) plus a
minimax + alpha-beta AI opponent. Play against it from the terminal.

Usage:
    python mini_chess.py              # play white vs the engine, depth 3
    python mini_chess.py --color b    # play black instead
    python mini_chess.py --depth 4    # stronger (slower) engine

Move input format: "e2e4" (from-square + to-square).
"""

import argparse
import copy

PIECE_VALUES = {"P": 1, "N": 3, "B": 3, "R": 5, "Q": 9, "K": 0}


def init_board():
    return [
        list("RNBQKBNR"),
        list("PPPPPPPP"),
        list("........"),
        list("........"),
        list("........"),
        list("........"),
        list("pppppppp"),
        list("rnbqkbnr"),
    ]


def piece_color(p):
    if p == ".":
        return None
    return "white" if p.isupper() else "black"


def opponent(color):
    return "black" if color == "white" else "white"


def sq_to_coord(sq):
    col = ord(sq[0]) - ord("a")
    row = int(sq[1]) - 1
    return row, col


def coord_to_sq(r, c):
    return f"{chr(c + ord('a'))}{r + 1}"


def print_board(board):
    for r in range(7, -1, -1):
        row_str = f"{r + 1} "
        for c in range(8):
            row_str += board[r][c] + " "
        print(row_str)
    print("  a b c d e f g h")


def add_pawn_move(moves, nr, nc, last_row):
    if nr == last_row:
        moves.append((nr, nc, "Q"))
    else:
        moves.append((nr, nc, None))


def piece_moves(board, r, c):
    """Pseudo-legal destination squares for the piece at (r, c)."""
    p = board[r][c]
    kind = p.upper()
    color = piece_color(p)
    moves = []

    if kind == "P":
        direction = 1 if color == "white" else -1
        start_row = 1 if color == "white" else 6
        last_row = 7 if color == "white" else 0
        nr = r + direction
        if 0 <= nr < 8 and board[nr][c] == ".":
            add_pawn_move(moves, nr, c, last_row)
            if r == start_row and board[r + 2 * direction][c] == ".":
                moves.append((r + 2 * direction, c, None))
        for dc in (-1, 1):
            nc = c + dc
            if 0 <= nr < 8 and 0 <= nc < 8:
                target = board[nr][nc]
                if target != "." and piece_color(target) != color:
                    add_pawn_move(moves, nr, nc, last_row)

    elif kind == "N":
        for dr, dc in [(1, 2), (2, 1), (-1, 2), (-2, 1), (1, -2), (2, -1), (-1, -2), (-2, -1)]:
            nr, nc = r + dr, c + dc
            if 0 <= nr < 8 and 0 <= nc < 8:
                target = board[nr][nc]
                if target == "." or piece_color(target) != color:
                    moves.append((nr, nc, None))

    elif kind == "K":
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if dr == 0 and dc == 0:
                    continue
                nr, nc = r + dr, c + dc
                if 0 <= nr < 8 and 0 <= nc < 8:
                    target = board[nr][nc]
                    if target == "." or piece_color(target) != color:
                        moves.append((nr, nc, None))

    else:  # sliding pieces: B, R, Q
        directions = []
        if kind in ("B", "Q"):
            directions += [(1, 1), (1, -1), (-1, 1), (-1, -1)]
        if kind in ("R", "Q"):
            directions += [(1, 0), (-1, 0), (0, 1), (0, -1)]
        for dr, dc in directions:
            nr, nc = r + dr, c + dc
            while 0 <= nr < 8 and 0 <= nc < 8:
                target = board[nr][nc]
                if target == ".":
                    moves.append((nr, nc, None))
                else:
                    if piece_color(target) != color:
                        moves.append((nr, nc, None))
                    break
                nr += dr
                nc += dc

    return moves


def square_attacked(board, tr, tc, by_color):
    """True if by_color has a piece that attacks square (tr, tc)."""
    for r in range(8):
        for c in range(8):
            p = board[r][c]
            if p == "." or piece_color(p) != by_color:
                continue
            kind = p.upper()
            dr, dc = tr - r, tc - c
            if kind == "P":
                direction = 1 if by_color == "white" else -1
                if dr == direction and abs(dc) == 1:
                    return True
            elif kind == "N":
                if (abs(dr), abs(dc)) in ((1, 2), (2, 1)):
                    return True
            elif kind == "K":
                if max(abs(dr), abs(dc)) == 1:
                    return True
            elif kind in ("B", "R", "Q"):
                if kind == "B" and abs(dr) != abs(dc):
                    continue
                if kind == "R" and dr != 0 and dc != 0:
                    continue
                if kind == "Q" and not (abs(dr) == abs(dc) or dr == 0 or dc == 0):
                    continue
                if dr == 0 and dc == 0:
                    continue
                step_r = (dr > 0) - (dr < 0)
                step_c = (dc > 0) - (dc < 0)
                rr, cc = r + step_r, c + step_c
                blocked = False
                while (rr, cc) != (tr, tc):
                    if board[rr][cc] != ".":
                        blocked = True
                        break
                    rr += step_r
                    cc += step_c
                if not blocked:
                    return True
    return False


def find_king(board, color):
    target = "K" if color == "white" else "k"
    for r in range(8):
        for c in range(8):
            if board[r][c] == target:
                return r, c
    return None


def is_in_check(board, color):
    king_pos = find_king(board, color)
    if king_pos is None:
        return False
    return square_attacked(board, king_pos[0], king_pos[1], opponent(color))


def apply_move(board, move):
    fr, fc, tr, tc, promo = move
    nb = copy.deepcopy(board)
    piece = nb[fr][fc]
    if promo:
        piece = promo if piece.isupper() else promo.lower()
    nb[tr][tc] = piece
    nb[fr][fc] = "."
    return nb


def generate_legal_moves(board, color):
    legal = []
    for r in range(8):
        for c in range(8):
            p = board[r][c]
            if p == "." or piece_color(p) != color:
                continue
            for tr, tc, promo in piece_moves(board, r, c):
                move = (r, c, tr, tc, promo)
                new_board = apply_move(board, move)
                if not is_in_check(new_board, color):
                    legal.append(move)
    return legal


def evaluate(board):
    """Positive = good for white, negative = good for black."""
    score = 0
    for row in board:
        for p in row:
            if p == ".":
                continue
            value = PIECE_VALUES[p.upper()]
            score += value if p.isupper() else -value
    return score


def negamax(board, depth, alpha, beta, sign, color):
    legal = generate_legal_moves(board, color)
    if depth == 0 or not legal:
        if not legal and is_in_check(board, color):
            return -100000 - depth  # checkmate: worse the closer to root
        if not legal:
            return 0  # stalemate
        return sign * evaluate(board)

    best = float("-inf")
    for move in legal:
        new_board = apply_move(board, move)
        val = -negamax(new_board, depth - 1, -beta, -alpha, -sign, opponent(color))
        best = max(best, val)
        alpha = max(alpha, val)
        if alpha >= beta:
            break
    return best


def best_move(board, color, depth):
    sign = 1 if color == "white" else -1
    legal = generate_legal_moves(board, color)
    best_val, chosen = float("-inf"), None
    for move in legal:
        new_board = apply_move(board, move)
        val = -negamax(new_board, depth - 1, float("-inf"), float("inf"), -sign, opponent(color))
        if val > best_val:
            best_val, chosen = val, move
    return chosen


def parse_move(text, legal_moves):
    text = text.strip().lower()
    if len(text) not in (4, 5):
        return None
    try:
        fr, fc = sq_to_coord(text[0:2])
        tr, tc = sq_to_coord(text[2:4])
    except (ValueError, IndexError):
        return None
    for move in legal_moves:
        if move[0] == fr and move[1] == fc and move[2] == tr and move[3] == tc:
            return move
    return None


def main():
    parser = argparse.ArgumentParser(description="Play chess against a minimax engine.")
    parser.add_argument("--color", choices=["w", "b"], default="w", help="Your color (default: w)")
    parser.add_argument("--depth", type=int, default=3, help="Engine search depth (default: 3)")
    args = parser.parse_args()

    human_color = "white" if args.color == "w" else "black"
    board = init_board()
    turn = "white"

    while True:
        print()
        print_board(board)
        legal = generate_legal_moves(board, turn)

        if not legal:
            if is_in_check(board, turn):
                print(f"\nCheckmate! {opponent(turn).capitalize()} wins.")
            else:
                print("\nStalemate. It's a draw.")
            break

        if is_in_check(board, turn):
            print(f"\n{turn.capitalize()} is in check.")

        if turn == human_color:
            text = input(f"\nYour move ({turn}), e.g. e2e4: ")
            move = parse_move(text, legal)
            if move is None:
                print("Illegal or invalid move, try again.")
                continue
        else:
            print(f"\nEngine ({turn}) is thinking...")
            move = best_move(board, turn, args.depth)

        fr, fc, tr, tc, promo = move
        print(f"{turn.capitalize()} plays: {coord_to_sq(fr, fc)}{coord_to_sq(tr, tc)}")
        board = apply_move(board, move)
        turn = opponent(turn)


if __name__ == "__main__":
    main()
