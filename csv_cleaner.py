#!/usr/bin/env python3
"""
CSV Cleaner
Cleans a CSV file: trims whitespace, normalizes headers, drops empty rows,
removes duplicate rows, and optionally fills missing values.

Usage:
    python csv_cleaner.py input.csv
    python csv_cleaner.py input.csv -o cleaned.csv
    python csv_cleaner.py input.csv --fillna "N/A"
    python csv_cleaner.py input.csv --dedupe-cols name,email
"""

import argparse
import csv
import sys
from pathlib import Path


def normalize_header(name: str) -> str:
    return name.strip().lower().replace(" ", "_")


def clean_csv(input_path, output_path, fillna=None, dedupe_cols=None, keep_empty_rows=False):
    with open(input_path, newline="", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        rows = list(reader)

    if not rows:
        print("Input file is empty.")
        return 0, 0

    raw_header = rows[0]
    header = [normalize_header(h) for h in raw_header]
    data_rows = rows[1:]

    seen = set()
    cleaned_rows = []
    dupe_count = 0
    empty_count = 0

    dedupe_idx = None
    if dedupe_cols:
        try:
            dedupe_idx = [header.index(normalize_header(c)) for c in dedupe_cols]
        except ValueError as e:
            print(f"Warning: dedupe column not found ({e}); deduping on full row instead.")
            dedupe_idx = None

    for row in data_rows:
        # pad/truncate row to header length
        if len(row) < len(header):
            row = row + [""] * (len(header) - len(row))
        elif len(row) > len(header):
            row = row[:len(header)]

        row = [cell.strip() for cell in row]

        if fillna is not None:
            row = [cell if cell != "" else fillna for cell in row]

        if not keep_empty_rows and all(cell == "" for cell in row):
            empty_count += 1
            continue

        key = tuple(row[i] for i in dedupe_idx) if dedupe_idx else tuple(row)
        if key in seen:
            dupe_count += 1
            continue
        seen.add(key)
        cleaned_rows.append(row)

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(cleaned_rows)

    print(f"Rows in:  {len(data_rows)}")
    print(f"Rows out: {len(cleaned_rows)}")
    print(f"Removed:  {dupe_count} duplicate(s), {empty_count} empty row(s)")
    print(f"Saved to: {output_path}")
    return len(data_rows), len(cleaned_rows)


def main():
    parser = argparse.ArgumentParser(description="Clean a CSV file.")
    parser.add_argument("input", help="Path to input CSV file")
    parser.add_argument("-o", "--output", help="Path to output CSV file (default: <input>_cleaned.csv)")
    parser.add_argument("--fillna", help="Value to fill empty cells with", default=None)
    parser.add_argument("--dedupe-cols", help="Comma-separated column names to dedupe on (default: whole row)")
    parser.add_argument("--keep-empty-rows", action="store_true", help="Keep fully empty rows instead of dropping them")
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: file not found: {input_path}")
        sys.exit(1)

    output_path = Path(args.output) if args.output else input_path.with_name(input_path.stem + "_cleaned.csv")
    dedupe_cols = [c.strip() for c in args.dedupe_cols.split(",")] if args.dedupe_cols else None

    clean_csv(input_path, output_path, fillna=args.fillna, dedupe_cols=dedupe_cols, keep_empty_rows=args.keep_empty_rows)


if __name__ == "__main__":
    main()
