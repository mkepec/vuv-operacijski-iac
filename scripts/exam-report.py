#!/usr/bin/env python3
"""
exam-report.py — reads per-student JSON grading results and produces:
  - console summary table
  - CSV file
  - HTML report

Usage:
  python3 scripts/exam-report.py                          # reads ansible/exam-results/*.json
  python3 scripts/exam-report.py --results-dir path/      # custom results directory
  python3 scripts/exam-report.py --csv out.csv            # explicit CSV path
  python3 scripts/exam-report.py --html out.html          # explicit HTML path
  python3 scripts/exam-report.py --no-html                # skip HTML output
  python3 scripts/exam-report.py --students students.csv  # merge JMBAG + name from student list

Student CSV format (--students):
  JMBAG,Ime i prezime,e-mail,server
  0123456789,Ana Anić,ana@example.com,1
  The "server" column is the student VM number (1–20).
  When provided, JMBAG and Ime i prezime are added to each report row.
"""

import argparse
import csv
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
DEFAULT_RESULTS_DIR = REPO_ROOT / "ansible" / "exam-results"

TASK_LABELS = {
    "t1": "T1 File/Dir",
    "t2": "T2 Users",
    "t3": "T3 Perms",
    "t4": "T4 Services",
    "t5": "T5 Packages",
    "t6": "T6 Mount",
}
TASK_ORDER = ["t1", "t2", "t3", "t4", "t5", "t6"]
TASK_MAXES = {"t1": 15, "t2": 20, "t3": 20, "t4": 15, "t5": 15, "t6": 15}


def load_students(path: Path) -> dict[str, dict]:
    """Load student CSV and return a dict keyed by host name (e.g. 'student-01')."""
    students = {}
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                server_num = int(row["server"])
            except (KeyError, ValueError):
                print(f"Warning: skipping student row with invalid server: {row}", file=sys.stderr)
                continue
            host = f"student-{server_num:02d}"
            students[host] = {"jmbag": row.get("JMBAG", ""), "name": row.get("Ime i prezime", "")}
    return students


def load_results(results_dir: Path) -> list[dict]:
    files = sorted(results_dir.glob("student-*.json"))
    if not files:
        print(f"No result files found in {results_dir}", file=sys.stderr)
        sys.exit(1)
    results = []
    for f in files:
        with open(f) as fh:
            results.append(json.load(fh))
    return results


def print_console(results: list[dict]) -> None:
    col_w = 12
    header = f"{'Student':<14} {'Variant':<10}" + "".join(
        f"{TASK_LABELS[t]:>{col_w}}" for t in TASK_ORDER
    ) + f"{'TOTAL':>{col_w}}"
    divider = "-" * len(header)

    print(divider)
    print(header)
    print(divider)

    for r in results:
        tasks = r.get("tasks", {})
        row = f"{r['host']:<14} {r['variant']:<10}"
        for t in TASK_ORDER:
            td = tasks.get(t, {})
            score = td.get("score", 0)
            mx = td.get("max", TASK_MAXES[t])
            cell = f"{score}/{mx}"
            row += f"{cell:>{col_w}}"
        total_cell = f"{r['total']}/100"
        row += f"{total_cell:>{col_w}}"
        print(row)

    print(divider)
    _print_pass_rates(results)


def _print_pass_rates(results: list[dict]) -> None:
    n = len(results)
    print(f"\nPer-task average score (n={n}):")
    for t in TASK_ORDER:
        scores = [r["tasks"].get(t, {}).get("score", 0) for r in results]
        avg = sum(scores) / n if n else 0
        mx = TASK_MAXES[t]
        pct = avg / mx * 100
        bar_len = int(pct / 5)
        bar = "#" * bar_len + "." * (20 - bar_len)
        print(f"  {TASK_LABELS[t]:<14} {avg:5.1f}/{mx}  [{bar}] {pct:5.1f}%")
    totals = [r["total"] for r in results]
    avg_total = sum(totals) / n if n else 0
    print(f"\n  {'Class average':<14} {avg_total:.1f}/100")


def write_csv(results: list[dict], path: Path, students: dict[str, dict] | None = None) -> None:
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        extra_headers = ["JMBAG", "Ime i prezime"] if students is not None else []
        header = extra_headers + ["host", "variant"] + [TASK_LABELS[t] for t in TASK_ORDER] + ["total"]
        writer.writerow(header)
        for r in results:
            tasks = r.get("tasks", {})
            extra = []
            if students is not None:
                s = students.get(r["host"], {})
                extra = [s.get("jmbag", ""), s.get("name", "")]
            row = extra + [r["host"], r["variant"]]
            for t in TASK_ORDER:
                td = tasks.get(t, {})
                row.append(f"{td.get('score', 0)}/{td.get('max', TASK_MAXES[t])}")
            row.append(f"{r['total']}/100")
            writer.writerow(row)
    print(f"CSV written: {path}")


def write_html(results: list[dict], path: Path, students: dict[str, dict] | None = None) -> None:
    n = len(results)
    totals = [r["total"] for r in results]
    avg_total = sum(totals) / n if n else 0

    # Per-task averages for the summary section
    task_avgs = {}
    for t in TASK_ORDER:
        scores = [r["tasks"].get(t, {}).get("score", 0) for r in results]
        task_avgs[t] = sum(scores) / n if n else 0

    # Build per-student rows
    student_rows = []
    for r in results:
        tasks = r.get("tasks", {})
        cells = ""
        for t in TASK_ORDER:
            td = tasks.get(t, {})
            score = td.get("score", 0)
            mx = td.get("max", TASK_MAXES[t])
            pct = score / mx * 100
            cls = "full" if pct == 100 else ("pass" if pct >= 60 else "fail")
            cells += f'<td class="{cls}">{score}/{mx}</td>'
        total = r["total"]
        total_cls = "full" if total == 100 else ("pass" if total >= 60 else "fail")
        extra_cells = ""
        if students is not None:
            s = students.get(r["host"], {})
            extra_cells = (
                f'<td class="jmbag">{s.get("jmbag", "")}</td>'
                f'<td class="stuname">{s.get("name", "")}</td>'
            )
        student_rows.append(
            f'<tr>{extra_cells}<td class="name">{r["host"]}</td>'
            f'<td class="variant">{r["variant"]}</td>'
            f"{cells}"
            f'<td class="total {total_cls}">{total}/100</td></tr>'
        )

    # Build per-task detail sections (collapsible)
    detail_sections = []
    for r in results:
        tasks = r.get("tasks", {})
        checks_html = ""
        for t in TASK_ORDER:
            td = tasks.get(t, {})
            score = td.get("score", 0)
            mx = td.get("max", TASK_MAXES[t])
            checks_html += f'<h4>{TASK_LABELS[t]} — {score}/{mx}</h4><ul>'
            for chk in td.get("checks", []):
                icon = "✓" if chk["result"] == "PASS" else "✗"
                css = "chk-pass" if chk["result"] == "PASS" else "chk-fail"
                checks_html += f'<li class="{css}"><span class="icon">{icon}</span> {chk["message"]}</li>'
            checks_html += "</ul>"
        summary_label = r["host"]
        if students is not None:
            s = students.get(r["host"], {})
            if s.get("name"):
                summary_label = f'{s["name"]} ({r["host"]})'
        detail_sections.append(
            f'<details><summary>{summary_label} ({r["variant"]}) — {r["total"]}/100</summary>'
            f'<div class="detail">{checks_html}</div></details>'
        )

    task_avg_rows = ""
    for t in TASK_ORDER:
        avg = task_avgs[t]
        mx = TASK_MAXES[t]
        pct = avg / mx * 100
        bar_w = int(pct)
        task_avg_rows += (
            f'<tr><td>{TASK_LABELS[t]}</td>'
            f'<td>{avg:.1f}/{mx}</td>'
            f'<td><div class="bar-bg"><div class="bar-fill" style="width:{bar_w}%"></div></div></td>'
            f'<td>{pct:.1f}%</td></tr>'
        )

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>RH124 Exam Results</title>
<style>
  body {{ font-family: sans-serif; max-width: 1100px; margin: 2rem auto; color: #222; }}
  h1 {{ font-size: 1.4rem; margin-bottom: 0.2rem; }}
  .subtitle {{ color: #666; margin-bottom: 2rem; font-size: 0.9rem; }}
  table {{ border-collapse: collapse; width: 100%; margin-bottom: 2rem; font-size: 0.9rem; }}
  th {{ background: #334; color: #fff; padding: 8px 10px; text-align: left; }}
  td {{ padding: 6px 10px; border-bottom: 1px solid #eee; }}
  tr:hover td {{ background: #f8f8f8; }}
  .name {{ font-weight: bold; }}
  .variant {{ color: #666; font-size: 0.85rem; }}
  td.full {{ color: #1a7a1a; font-weight: bold; }}
  td.pass {{ color: #444; }}
  td.fail {{ color: #b00; }}
  td.total {{ font-weight: bold; font-size: 1rem; }}
  .avg-row td {{ background: #f0f0f0; font-weight: bold; }}
  h2 {{ font-size: 1.1rem; margin-top: 2rem; border-bottom: 2px solid #334; padding-bottom: 4px; }}
  .bar-bg {{ background: #ddd; border-radius: 4px; height: 14px; min-width: 120px; }}
  .bar-fill {{ background: #3a7; height: 14px; border-radius: 4px; }}
  details {{ margin-bottom: 0.5rem; border: 1px solid #ddd; border-radius: 4px; }}
  summary {{ padding: 8px 12px; cursor: pointer; font-weight: bold; background: #f5f5f5; }}
  summary:hover {{ background: #eee; }}
  .detail {{ padding: 12px 16px; }}
  .detail h4 {{ margin: 0.8rem 0 0.3rem; font-size: 0.9rem; color: #334; }}
  .detail ul {{ margin: 0; padding-left: 1.2rem; list-style: none; }}
  .detail li {{ font-size: 0.85rem; padding: 2px 0; }}
  .chk-pass .icon {{ color: #2a8; }}
  .chk-fail .icon {{ color: #c33; }}
  .jmbag {{ font-family: monospace; font-size: 0.85rem; color: #555; }}
  .stuname {{ font-weight: bold; }}
</style>
</head>
<body>
<h1>RH124 Mid-Semester Exam — Results</h1>
<p class="subtitle">{n} students &nbsp;|&nbsp; Class average: {avg_total:.1f}/100</p>

<h2>Score Summary</h2>
<table>
  <tr>
    {('<th>JMBAG</th><th>Ime i prezime</th>' if students is not None else '')}<th>Student</th><th>Variant</th>
    {"".join(f"<th>{TASK_LABELS[t]}</th>" for t in TASK_ORDER)}
    <th>Total</th>
  </tr>
  {"".join(student_rows)}
  <tr class="avg-row">
    <td colspan="{2 + (2 if students is not None else 0)}">Class average</td>
    {"".join(f'<td>{task_avgs[t]:.1f}/{TASK_MAXES[t]}</td>' for t in TASK_ORDER)}
    <td>{avg_total:.1f}/100</td>
  </tr>
</table>

<h2>Per-Task Pass Rates</h2>
<table>
  <tr><th>Task</th><th>Avg score</th><th style="min-width:180px">Progress</th><th>%</th></tr>
  {task_avg_rows}
</table>

<h2>Per-Student Detail</h2>
{"".join(detail_sections)}

</body>
</html>
"""
    with open(path, "w") as f:
        f.write(html)
    print(f"HTML written: {path}")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--results-dir", type=Path, default=DEFAULT_RESULTS_DIR,
                        help="Directory containing student-*.json result files")
    parser.add_argument("--csv", type=Path, help="CSV output path (default: <results-dir>/report.csv)")
    parser.add_argument("--html", type=Path, help="HTML output path (default: <results-dir>/report.html)")
    parser.add_argument("--no-html", action="store_true", help="Skip HTML output")
    parser.add_argument("--students", type=Path, metavar="FILE",
                        help="CSV with columns JMBAG,Ime i prezime,e-mail,server — merges student identity into report")
    args = parser.parse_args()

    students = None
    if args.students:
        if not args.students.exists():
            print(f"Error: students file not found: {args.students}", file=sys.stderr)
            sys.exit(1)
        students = load_students(args.students)
        print(f"Loaded {len(students)} students from {args.students}")

    results = load_results(args.results_dir)
    print_console(results)

    csv_path = args.csv or args.results_dir / "report.csv"
    write_csv(results, csv_path, students)

    if not args.no_html:
        html_path = args.html or args.results_dir / "report.html"
        write_html(results, html_path, students)


if __name__ == "__main__":
    main()
