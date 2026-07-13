#!/usr/bin/env python3
"""
Duplicate File Finder
A lightweight, single-file tool to find duplicate files in a directory tree.

Usage:
    python duplicate_finder.py /path/to/folder
    python duplicate_finder.py /path/to/folder --delete   # keep 1 copy, delete rest
    python duplicate_finder.py /path/to/folder --min-size 1024
"""

import sys
import os
import hashlib
import argparse
from collections import defaultdict


def human_size(num: float) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if num < 1024:
            return f"{num:.1f}{unit}"
        num /= 1024
    return f"{num:.1f}PB"


def file_hash(path: str, chunk_size: int = 65536) -> str:
    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(chunk_size):
            hasher.update(chunk)
    return hasher.hexdigest()


def find_duplicates(root: str, min_size: int = 0) -> dict:
    # Step 1: group files by size (cheap first pass)
    size_map = defaultdict(list)
    for dirpath, _, filenames in os.walk(root):
        for name in filenames:
            path = os.path.join(dirpath, name)
            try:
                size = os.path.getsize(path)
            except OSError:
                continue
            if size >= min_size:
                size_map[size].append(path)

    # Step 2: hash only files that share a size with another file
    hash_map = defaultdict(list)
    for size, paths in size_map.items():
        if len(paths) < 2:
            continue
        for path in paths:
            try:
                h = file_hash(path)
            except OSError:
                continue
            hash_map[h].append(path)

    # Step 3: keep only actual duplicate groups
    return {h: paths for h, paths in hash_map.items() if len(paths) > 1}


def print_report(duplicates: dict) -> int:
    if not duplicates:
        print("No duplicate files found.")
        return 0

    total_wasted = 0
    group_num = 1
    for h, paths in duplicates.items():
        size = os.path.getsize(paths[0])
        wasted = size * (len(paths) - 1)
        total_wasted += wasted

        print(f"\nDuplicate group {group_num} ({len(paths)} files, {human_size(size)} each):")
        for p in paths:
            print(f"  {p}")
        group_num += 1

    print("\n" + "-" * 40)
    print(f"Groups found   : {len(duplicates)}")
    print(f"Wasted space   : {human_size(total_wasted)}")
    print("-" * 40)
    return len(duplicates)


def delete_duplicates(duplicates: dict) -> None:
    freed = 0
    for h, paths in duplicates.items():
        keep, *rest = paths
        for p in rest:
            try:
                size = os.path.getsize(p)
                os.remove(p)
                freed += size
                print(f"Deleted: {p}")
            except OSError as e:
                print(f"Failed to delete {p}: {e}")
        print(f"Kept:    {keep}")
    print(f"\nFreed {human_size(freed)}.")


def main():
    parser = argparse.ArgumentParser(description="Find (and optionally delete) duplicate files.")
    parser.add_argument("directory", help="Root directory to scan")
    parser.add_argument("--min-size", type=int, default=0, help="Ignore files smaller than this many bytes")
    parser.add_argument("--delete", action="store_true", help="Delete duplicates, keeping one copy per group")
    args = parser.parse_args()

    if not os.path.isdir(args.directory):
        print(f"Error: '{args.directory}' is not a valid directory.")
        sys.exit(1)

    print(f"Scanning '{args.directory}'...")
    duplicates = find_duplicates(args.directory, args.min_size)
    print_report(duplicates)

    if args.delete and duplicates:
        confirm = input("\nDelete duplicates now? This cannot be undone. [y/N]: ").strip().lower()
        if confirm == "y":
            delete_duplicates(duplicates)
        else:
            print("Aborted. No files deleted.")


if __name__ == "__main__":
    main()
