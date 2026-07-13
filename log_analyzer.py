#!/usr/bin/env python3
"""
Log Analyzer
A lightweight, single-file tool to analyze huge log files without loading
them fully into memory (streams line by line).

Outputs:
    - Top errors (grouped by normalized message)
    - Log level frequency
    - Response time stats (min/max/avg/median/p95)
    - A graph-ready CSV time series (bucketed count / error count / avg response time)

Usage:
    python log_analyzer.py app.log
    python log_analyzer.py app.log --top 15 --bucket-seconds 300 --csv-out trend.csv

Recognizes common formats out of the box:
    - "2024-01-15 10:23:45 ERROR Failed to connect to database"
    - Apache/nginx style "[15/Jan/2024:10:23:45 +0000]" timestamps
    - Syslog style "Jan 15 10:23:45 host process[123]: message"
    - Response times like "duration=123ms", "took 45ms", "response_time: 1.2s"
"""

import argparse
import csv
import re
import random
import sys
import time
from collections import Counter
from datetime import datetime

LEVEL_RE = re.compile(r"\b(CRITICAL|FATAL|ERROR|WARN(?:ING)?|INFO|DEBUG|TRACE)\b", re.I)

TIMESTAMP_PATTERNS = [
    (re.compile(r"(\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2})"), lambda s: s.replace("T", " "), "%Y-%m-%d %H:%M:%S"),
    (re.compile(r"\[(\d{2}/\w{3}/\d{4}:\d{2}:\d{2}:\d{2})"), lambda s: s, "%d/%b/%Y:%H:%M:%S"),
    (re.compile(r"^(\w{3}\s+\d{1,2} \d{2}:\d{2}:\d{2})"), lambda s: s, "%b %d %H:%M:%S"),
]

RESPONSE_TIME_PATTERNS = [
    re.compile(r"response_time[=:]\s*(\d+\.?\d*)\s*(ms|s)?", re.I),
    re.compile(r"duration[=:]\s*(\d+\.?\d*)\s*(ms|s)?", re.I),
    re.compile(r"\btook\s+(\d+\.?\d*)\s*(ms|s)?", re.I),
    re.compile(r"\btime[=:]\s*(\d+\.?\d*)\s*(ms|s)?", re.I),
    re.compile(r"(\d+\.?\d*)\s*ms\b", re.I),
]

ID_RE = re.compile(r"\d+")
RESERVOIR_SIZE = 50000


def parse_timestamp(line):
    for pattern, normalize, fmt in TIMESTAMP_PATTERNS:
        m = pattern.search(line)
        if m:
            raw = normalize(m.group(1))
            try:
                dt = datetime.strptime(raw, fmt)
                if fmt == "%b %d %H:%M:%S":
                    dt = dt.replace(year=datetime.now().year)
                return dt
            except ValueError:
                continue
    return None


def parse_response_time_ms(line):
    for pattern in RESPONSE_TIME_PATTERNS:
        m = pattern.search(line)
        if m:
            value = float(m.group(1))
            unit = (m.group(2) or "ms").lower() if pattern.groups >= 2 else "ms"
            return value * 1000 if unit == "s" else value
    return None


def normalize_message(line, level_match):
    msg = line[level_match.end():].strip() if level_match else line.strip()
    msg = ID_RE.sub("#", msg)
    msg = re.sub(r"\s+", " ", msg)
    return msg[:160]


class RunningStats:
    """Streaming min/max/avg with a reservoir sample for percentile estimates."""

    def __init__(self, size=RESERVOIR_SIZE):
        self.count = 0
        self.total = 0.0
        self.min = None
        self.max = None
        self.reservoir = []
        self.size = size

    def add(self, value):
        self.count += 1
        self.total += value
        self.min = value if self.min is None else min(self.min, value)
        self.max = value if self.max is None else max(self.max, value)
        if len(self.reservoir) < self.size:
            self.reservoir.append(value)
        else:
            j = random.randint(0, self.count - 1)
            if j < self.size:
                self.reservoir[j] = value

    def percentile(self, pct):
        if not self.reservoir:
            return None
        data = sorted(self.reservoir)
        idx = min(len(data) - 1, int(len(data) * pct / 100))
        return data[idx]

    @property
    def avg(self):
        return self.total / self.count if self.count else None


def analyze(path, bucket_seconds):
    level_counts = Counter()
    error_counts = Counter()
    error_sample = {}
    bucket_total = Counter()
    bucket_errors = Counter()
    bucket_resp_sum = Counter()
    bucket_resp_count = Counter()
    resp_stats = RunningStats()

    total_lines = 0
    matched_timestamps = 0
    start_time, end_time = None, None
    t0 = time.time()

    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            total_lines += 1
            if total_lines % 200000 == 0:
                elapsed = time.time() - t0
                print(f"  ...{total_lines:,} lines processed ({elapsed:.1f}s)", file=sys.stderr)

            level_match = LEVEL_RE.search(line)
            level = level_match.group(1).upper() if level_match else "UNKNOWN"
            if level == "WARNING":
                level = "WARN"
            level_counts[level] += 1

            ts = parse_timestamp(line)
            bucket = None
            if ts:
                matched_timestamps += 1
                start_time = ts if start_time is None else min(start_time, ts)
                end_time = ts if end_time is None else max(end_time, ts)
                epoch = int(ts.timestamp())
                bucket = epoch - (epoch % bucket_seconds)
                bucket_total[bucket] += 1

            is_error = level in ("ERROR", "CRITICAL", "FATAL")
            if is_error:
                msg = normalize_message(line, level_match)
                error_counts[msg] += 1
                error_sample.setdefault(msg, line.strip())
                if bucket is not None:
                    bucket_errors[bucket] += 1

            rt = parse_response_time_ms(line)
            if rt is not None:
                resp_stats.add(rt)
                if bucket is not None:
                    bucket_resp_sum[bucket] += rt
                    bucket_resp_count[bucket] += 1

    return {
        "total_lines": total_lines,
        "matched_timestamps": matched_timestamps,
        "start_time": start_time,
        "end_time": end_time,
        "elapsed": time.time() - t0,
        "level_counts": level_counts,
        "error_counts": error_counts,
        "error_sample": error_sample,
        "bucket_total": bucket_total,
        "bucket_errors": bucket_errors,
        "bucket_resp_sum": bucket_resp_sum,
        "bucket_resp_count": bucket_resp_count,
        "resp_stats": resp_stats,
    }


def print_report(result, top_n):
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Lines processed   : {result['total_lines']:,}")
    print(f"Timestamps parsed : {result['matched_timestamps']:,}")
    if result["start_time"] and result["end_time"]:
        print(f"Time range        : {result['start_time']} -> {result['end_time']}")
    print(f"Processing time   : {result['elapsed']:.2f}s")

    print("\n" + "=" * 60)
    print(f"TOP {top_n} ERRORS")
    print("=" * 60)
    if not result["error_counts"]:
        print("No error-level lines found.")
    for i, (msg, count) in enumerate(result["error_counts"].most_common(top_n), 1):
        print(f"{i:>2}. [{count:>6,}x] {msg}")

    print("\n" + "=" * 60)
    print("LOG LEVEL FREQUENCY")
    print("=" * 60)
    total = sum(result["level_counts"].values()) or 1
    for level, count in result["level_counts"].most_common():
        pct = 100 * count / total
        print(f"{level:<10} {count:>10,}  ({pct:5.1f}%)")

    print("\n" + "=" * 60)
    print("RESPONSE TIMES (ms)")
    print("=" * 60)
    rs = result["resp_stats"]
    if rs.count == 0:
        print("No response-time values found in this log.")
    else:
        print(f"Samples : {rs.count:,}")
        print(f"Min     : {rs.min:.1f}")
        print(f"Avg     : {rs.avg:.1f}")
        print(f"P95     : {rs.percentile(95):.1f}")
        print(f"Max     : {rs.max:.1f}")


def write_csv(result, out_path, bucket_seconds):
    buckets = sorted(result["bucket_total"].keys())
    with open(out_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["bucket_start", "total_count", "error_count", "avg_response_ms"])
        for b in buckets:
            ts = datetime.fromtimestamp(b).strftime("%Y-%m-%d %H:%M:%S")
            total = result["bucket_total"][b]
            errors = result["bucket_errors"].get(b, 0)
            rcount = result["bucket_resp_count"].get(b, 0)
            avg_resp = result["bucket_resp_sum"][b] / rcount if rcount else ""
            writer.writerow([ts, total, errors, f"{avg_resp:.1f}" if avg_resp != "" else ""])
    print(f"\nGraph-ready CSV written to: {out_path} ({len(buckets)} buckets of {bucket_seconds}s)")


def main():
    parser = argparse.ArgumentParser(description="Analyze huge log files.")
    parser.add_argument("logfile", help="Path to the log file")
    parser.add_argument("--top", type=int, default=10, help="Number of top errors to show (default: 10)")
    parser.add_argument("--bucket-seconds", type=int, default=60, help="Time bucket size for CSV (default: 60)")
    parser.add_argument("--csv-out", default="log_analysis.csv", help="Output CSV path (default: log_analysis.csv)")
    args = parser.parse_args()

    print(f"Analyzing '{args.logfile}'...")
    result = analyze(args.logfile, args.bucket_seconds)
    print_report(result, args.top)
    write_csv(result, args.csv_out, args.bucket_seconds)


if __name__ == "__main__":
    main()
