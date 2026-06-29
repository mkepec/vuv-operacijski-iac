#!/usr/bin/env python3
"""Parse grade script stdout into a structured JSON result file."""

import argparse
import json
import re
import sys


TASK_MAXES_BY_COURSE = {
    "rh124":  {"t1": 15, "t2": 20, "t3": 20, "t4": 15, "t5": 15, "t6": 15},
    "rh134":  {"t1": 15, "t2": 20, "t3": 15, "t4": 15, "t5": 20, "t6": 15},
    "final":  {"t1": 15, "t2": 20, "t3": 20, "t4": 15, "t5": 15,
               "t6": 15, "t7": 20, "t8": 15, "t9": 15, "t10": 15},
}


def parse(text: str, hostname: str, variant: str, task_maxes: dict, cross_host: dict | None = None) -> dict:
    tasks = {}
    current_task = None
    current_checks = []
    current_score = 0

    for line in text.splitlines():
        # Task header: "Task N — ..." (N may be 1-10)
        m = re.match(r"Task (\d{1,2}) ", line)
        if m:
            if current_task:
                tasks[current_task] = {
                    "score": current_score,
                    "max": task_maxes[current_task],
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

        # Local sub-score line (tasks with an instructor-only cross-host
        # portion): "  Local sub-score: N/M  (full task max: P)"
        m = re.match(r"\s+Local sub-score:\s+(\d+)/\d+", line)
        if m and current_task:
            current_score = int(m.group(1))
            continue

        # Check lines: "  [PASS] ..." or "  [FAIL] ..." (also matches the
        # multi-line "[INFO] ..." continuation, which carries no result)
        m = re.match(r"\s+\[(PASS|FAIL)\] (.+)", line)
        if m and current_task:
            current_checks.append({"result": m.group(1), "message": m.group(2).strip()})

    # Flush last task
    if current_task:
        tasks[current_task] = {
            "score": current_score,
            "max": task_maxes[current_task],
            "checks": current_checks,
        }

    # Fold in instructor-side cross-host checks (e.g. RH134 T4/T5 repo-VM
    # verification), adding their points/checks on top of the local sub-score.
    if cross_host:
        for task_key, extra in cross_host.items():
            if task_key not in tasks:
                tasks[task_key] = {"score": 0, "max": task_maxes[task_key], "checks": []}
            tasks[task_key]["score"] += extra["score"]
            tasks[task_key]["checks"].extend(extra["checks"])

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
    parser.add_argument("--course", default="rh124", choices=sorted(TASK_MAXES_BY_COURSE),
                        help="Exam course — selects task maxes (default: rh124)")
    parser.add_argument("--input", required=True, help="Path to raw grade output text")
    parser.add_argument("--output", required=True, help="Path to write JSON result")
    parser.add_argument("--cross-host", help="Path to JSON with instructor-side cross-host check results")
    args = parser.parse_args()

    with open(args.input) as f:
        text = f.read()

    if not text.strip():
        print(f"WARNING: empty grade output for {args.host}", file=sys.stderr)

    cross_host = None
    if args.cross_host:
        with open(args.cross_host) as f:
            cross_host = json.load(f)

    result = parse(text, args.host, args.variant, TASK_MAXES_BY_COURSE[args.course], cross_host)

    with open(args.output, "w") as f:
        json.dump(result, f, indent=2)
        f.write("\n")

    print(f"{args.host} ({args.variant}): {result['total']}/100")


if __name__ == "__main__":
    main()
