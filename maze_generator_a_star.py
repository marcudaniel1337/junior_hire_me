#!/usr/bin/env python3
"""
Maze Generator & A* Solver
A lightweight, single-file tool that generates a random maze (recursive
backtracker) and solves it with A*, printing both as ASCII art.

Usage:
    python maze_astar.py                     # 21x21 maze, random seed
    python maze_astar.py --width 41 --height 21
    python maze_astar.py --seed 42            # reproducible maze
"""

import argparse
import heapq
import random

WALL, PATH, START, END, ROUTE = "#", " ", "S", "E", "."


def generate_maze(width, height, seed=None):
    """Recursive-backtracker maze on an odd x odd grid of cells."""
    if width % 2 == 0:
        width += 1
    if height % 2 == 0:
        height += 1

    rng = random.Random(seed)
    grid = [[WALL] * width for _ in range(height)]

    def neighbors(r, c):
        dirs = [(-2, 0), (2, 0), (0, -2), (0, 2)]
        rng.shuffle(dirs)
        for dr, dc in dirs:
            nr, nc = r + dr, c + dc
            if 0 < nr < height - 1 and 0 < nc < width - 1:
                yield nr, nc, dr, dc

    start_r, start_c = 1, 1
    grid[start_r][start_c] = PATH
    stack = [(start_r, start_c)]

    while stack:
        r, c = stack[-1]
        carved = False
        for nr, nc, dr, dc in neighbors(r, c):
            if grid[nr][nc] == WALL:
                grid[r + dr // 2][c + dc // 2] = PATH
                grid[nr][nc] = PATH
                stack.append((nr, nc))
                carved = True
                break
        if not carved:
            stack.pop()

    return grid, width, height


def find_open_extreme(grid, width, height, corner):
    """Pick the open cell closest to a given corner ('tl' or 'br')."""
    cells = [(r, c) for r in range(height) for c in range(width) if grid[r][c] == PATH]
    if corner == "tl":
        return min(cells, key=lambda rc: rc[0] + rc[1])
    return max(cells, key=lambda rc: rc[0] + rc[1])


def heuristic(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def astar(grid, width, height, start, goal):
    open_set = [(0, start)]
    came_from = {}
    g_score = {start: 0}
    visited = set()

    while open_set:
        _, current = heapq.heappop(open_set)
        if current == goal:
            path = [current]
            while current in came_from:
                current = came_from[current]
                path.append(current)
            path.reverse()
            return path

        if current in visited:
            continue
        visited.add(current)

        r, c = current
        for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            nr, nc = r + dr, c + dc
            if 0 <= nr < height and 0 <= nc < width and grid[nr][nc] != WALL:
                tentative = g_score[current] + 1
                neighbor = (nr, nc)
                if tentative < g_score.get(neighbor, float("inf")):
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative
                    f_score = tentative + heuristic(neighbor, goal)
                    heapq.heappush(open_set, (f_score, neighbor))

    return None


def render(grid, width, height, start=None, end=None, path=None):
    display = [row[:] for row in grid]
    if path:
        for r, c in path:
            display[r][c] = ROUTE
    if start:
        display[start[0]][start[1]] = START
    if end:
        display[end[0]][end[1]] = END
    return "\n".join("".join(row) for row in display)


def main():
    parser = argparse.ArgumentParser(description="Generate and solve a maze with A*.")
    parser.add_argument("--width", type=int, default=21, help="Maze width in cells (default: 21)")
    parser.add_argument("--height", type=int, default=21, help="Maze height in cells (default: 21)")
    parser.add_argument("--seed", type=int, default=None, help="Random seed for reproducible mazes")
    args = parser.parse_args()

    grid, width, height = generate_maze(args.width, args.height, args.seed)
    start = find_open_extreme(grid, width, height, "tl")
    end = find_open_extreme(grid, width, height, "br")

    print(f"Maze ({width}x{height}):\n")
    print(render(grid, width, height, start, end))

    path = astar(grid, width, height, start, end)

    print("\n" + "-" * 40)
    if path:
        print(f"Solved! Path length: {len(path)} steps\n")
        print(render(grid, width, height, start, end, path))
    else:
        print("No path found between start and end.")


if __name__ == "__main__":
    main()
