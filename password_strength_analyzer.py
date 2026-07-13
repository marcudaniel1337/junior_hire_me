#!/usr/bin/env python3
"""
Password Strength Analyzer
A lightweight, single-file tool to score password strength.

Usage:
    python password_analyzer.py            # interactive prompt (hidden input)
    python password_analyzer.py "myPass1!" # analyze a password passed as arg
"""

import sys
import re
import math
import getpass

COMMON_PASSWORDS = {
    "123456", "password", "12345678", "qwerty", "abc123", "111111",
    "123123", "letmein", "iloveyou", "admin", "welcome", "monkey",
    "password1", "1234567890", "dragon", "master", "login", "starwars",
}

COMMON_PATTERNS = [
    r"^\d+$",                     # all digits
    r"^[a-zA-Z]+$",                # all letters
    r"(.)\1{2,}",                  # 3+ repeated chars in a row
    r"(0123|1234|2345|3456|4567|5678|6789|9876|8765|7654|6543|5432|4321)",
    r"(abcd|bcde|cdef|qwer|asdf|zxcv)",
]


def char_pool_size(pwd: str) -> int:
    pool = 0
    if re.search(r"[a-z]", pwd):
        pool += 26
    if re.search(r"[A-Z]", pwd):
        pool += 26
    if re.search(r"\d", pwd):
        pool += 10
    if re.search(r"[^\w\s]", pwd):
        pool += 32
    if re.search(r"\s", pwd):
        pool += 1
    return pool


def calc_entropy(pwd: str) -> float:
    pool = char_pool_size(pwd)
    if pool == 0 or not pwd:
        return 0.0
    return len(pwd) * math.log2(pool)


def analyze(pwd: str) -> dict:
    issues = []
    score = 0

    # Length scoring
    length = len(pwd)
    if length >= 16:
        score += 30
    elif length >= 12:
        score += 22
    elif length >= 8:
        score += 12
    else:
        issues.append("Too short (use at least 12 characters)")

    # Character variety
    variety = sum([
        bool(re.search(r"[a-z]", pwd)),
        bool(re.search(r"[A-Z]", pwd)),
        bool(re.search(r"\d", pwd)),
        bool(re.search(r"[^\w\s]", pwd)),
    ])
    score += variety * 12
    if variety < 3:
        issues.append("Mix uppercase, lowercase, numbers, and symbols")

    # Entropy
    entropy = calc_entropy(pwd)
    if entropy >= 60:
        score += 25
    elif entropy >= 40:
        score += 15
    elif entropy >= 25:
        score += 8
    else:
        issues.append("Low entropy — password is too predictable")

    # Common password check
    if pwd.lower() in COMMON_PASSWORDS:
        score = min(score, 5)
        issues.append("This is a extremely common password")

    # Pattern check
    for pattern in COMMON_PATTERNS:
        if re.search(pattern, pwd, re.IGNORECASE):
            score -= 10
            issues.append("Contains a predictable pattern or sequence")
            break

    score = max(0, min(100, score))

    if score >= 80:
        rating = "Very Strong"
    elif score >= 60:
        rating = "Strong"
    elif score >= 40:
        rating = "Moderate"
    elif score >= 20:
        rating = "Weak"
    else:
        rating = "Very Weak"

    return {
        "score": score,
        "rating": rating,
        "entropy_bits": round(entropy, 1),
        "length": length,
        "issues": issues,
    }


def print_report(pwd: str) -> None:
    result = analyze(pwd)
    bar_len = 30
    filled = round(bar_len * result["score"] / 100)
    bar = "#" * filled + "-" * (bar_len - filled)

    print("\nPassword Strength Report")
    print("-" * 40)
    print(f"Length      : {result['length']}")
    print(f"Entropy     : {result['entropy_bits']} bits")
    print(f"Score       : {result['score']}/100  [{bar}]")
    print(f"Rating      : {result['rating']}")
    if result["issues"]:
        print("Suggestions :")
        for issue in result["issues"]:
            print(f"  - {issue}")
    else:
        print("Suggestions : None — looks great!")
    print("-" * 40)


def main():
    if len(sys.argv) > 1:
        pwd = sys.argv[1]
    else:
        pwd = getpass.getpass("Enter password to analyze (hidden): ")

    if not pwd:
        print("No password entered.")
        return

    print_report(pwd)


if __name__ == "__main__":
    main()
