#!/usr/bin/env python3
"""Parse grade script stdout into a structured JSON result file."""

import argparse
import json
import re
import sys


TASK_MAXES = {"t1": 15, "t2": 20, "t3": 20, "t4": 15, "t5": 15, "t6": 15}


def parse(text: str, hostname: str, variant: str) -> dict:
    tasks = {}
    current_task = None
    current_checks = []
    current_score = 0

    for line in text.splitlines():
        # Task header: "Task N — ..."
        m = re.match(r"Task (\d) ", line)
        if m:
            if current_task:
                tasks[current_task] = {
                    "score": current_score,
                    "max": TASK_MAXES[current_task],
                    "checks": current_checks,
                }
            current_task = "t" + m.group(1)
            current_checks = []
            current_score = 0
            continue

        # Score line: "  Score: N/M"
        m = re.match(r"\s+Score:\s+(\d+)/\d+", line)
        if m and current_task:
            current_score = int(m.group(1))
            continue

        # Check lines: "  [PASS] ..." or "  [FAIL] ..."
        m = re.match(r"\s+\[(PASS|FAIL)\] (.+)", line)
        if m and current_task:
            current_checks.append({"result": m.group(1), "message": m.group(2).strip()})

    # Flush last task
    if current_task:
        tasks[current_task] = {
            "score": current_score,
            "max": TASK_MAXES[current_task],
            "checks": current_checks,
        }

    total = sum(t["score"] for t in tasks.values())

    return {
        "host": hostname,
        "variant": variant,
        "tasks": tasks,
        "total": total,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", required=True)
    parser.add_argument("--variant", required=True)
    parser.add_argument("--input", required=True, help="Path to raw grade output text")
    parser.add_argument("--output", required=True, help="Path to write JSON result")
    args = parser.parse_args()

    with open(args.input) as f:
        text = f.read()

    if not text.strip():
        print(f"WARNING: empty grade output for {args.host}", file=sys.stderr)

    result = parse(text, args.host, args.variant)

    with open(args.output, "w") as f:
        json.dump(result, f, indent=2)
        f.write("\n")

    print(f"{args.host} ({args.variant}): {result['total']}/100")


if __name__ == "__main__":
    main()
