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

  # Merge first-attempt and retake CSVs (best score per student wins):
  python3 scripts/exam-report.py --merge-csv first.csv --merge-retake retake.csv \\
      --csv combined.csv --html combined.html

Student CSV format (--students):
  JMBAG,Ime i prezime,e-mail,server
  0123456789,Ana Anić,ana@example.com,1
  The "server" column is the student VM number (1–20).
  When provided, JMBAG and Ime i prezime are added to each report row.

Merge CSV format (--merge-csv / --merge-retake):
  The CSVs produced by this script (with JMBAG,Ime i prezime,host,variant,T1..T6,total columns).
  For students who appear in both CSVs the attempt with the higher total is kept.
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


def _parse_score(cell: str) -> int:
    """Parse a 'score/max' cell like '15/15' and return the score integer."""
    try:
        return int(cell.split("/")[0])
    except (ValueError, IndexError):
        return 0


def _parse_total(cell: str) -> int:
    """Parse a 'total/100' cell and return the total integer."""
    return _parse_score(cell)


def load_results_from_csv(path: Path) -> list[dict]:
    """Load a report CSV (produced by write_csv) back into the internal results format."""
    results = []
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            tasks = {}
            for key, label in TASK_LABELS.items():
                cell = row.get(label, f"0/{TASK_MAXES[key]}")
                score = _parse_score(cell)
                tasks[key] = {"score": score, "max": TASK_MAXES[key], "checks": []}
            total_cell = row.get("total", "0/100")
            total = _parse_total(total_cell)
            results.append({
                "host": row.get("host", ""),
                "variant": row.get("variant", ""),
                "jmbag": row.get("JMBAG", ""),
                "name": row.get("Ime i prezime", ""),
                "tasks": tasks,
                "total": total,
            })
    return results


def merge_results(first: list[dict], retake: list[dict]) -> list[dict]:
    """Merge two result sets. For students in both (matched by JMBAG), keep the higher total."""
    retake_by_jmbag = {r["jmbag"]: r for r in retake if r.get("jmbag")}

    merged = []
    retake_used = set()
    for r in first:
        jmbag = r.get("jmbag", "")
        if jmbag and jmbag in retake_by_jmbag:
            retake_r = retake_by_jmbag[jmbag]
            retake_used.add(jmbag)
            if retake_r["total"] > r["total"]:
                entry = dict(retake_r)
                entry["retake"] = True
                entry["first_total"] = r["total"]
            else:
                entry = dict(r)
                entry["retake"] = True
                entry["first_total"] = r["total"]
                entry["retake_total"] = retake_r["total"]
        else:
            entry = dict(r)
            entry["retake"] = False
        merged.append(entry)

    # Add any retake students not in first attempt (shouldn't happen, but be safe)
    for r in retake:
        if r.get("jmbag") not in retake_used:
            entry = dict(r)
            entry["retake"] = True
            entry["first_total"] = None
            merged.append(entry)

    return merged


def print_console_merged(results: list[dict]) -> None:
    col_w = 12
    header = (
        f"{'Student':<26} {'Variant':<10}"
        + "".join(f"{TASK_LABELS[t]:>{col_w}}" for t in TASK_ORDER)
        + f"{'TOTAL':>{col_w}}  Note"
    )
    divider = "-" * (len(header) + 4)
    print(divider)
    print(header)
    print(divider)

    for r in results:
        tasks = r.get("tasks", {})
        name = r.get("name", r["host"])
        row = f"{name:<26} {r['variant']:<10}"
        for t in TASK_ORDER:
            td = tasks.get(t, {})
            score = td.get("score", 0)
            mx = td.get("max", TASK_MAXES[t])
            cell = f"{score}/{mx}"
            row += f"{cell:>{col_w}}"
        total_cell = f"{r['total']}/100"
        note = ""
        if r.get("retake"):
            first = r.get("first_total")
            retake_score = r.get("retake_total")
            if retake_score is not None:
                note = f"retake ({retake_score}) < first ({first}) → kept first"
            elif first is not None:
                note = f"retake ↑ from {first}"
            else:
                note = "retake only"
        row += f"{total_cell:>{col_w}}  {note}"
        print(row)

    print(divider)
    n = len(results)
    totals = [r["total"] for r in results]
    avg = sum(totals) / n if n else 0
    print(f"\n  Class average: {avg:.1f}/100  (n={n})")


def write_csv_merged(results: list[dict], path: Path) -> None:
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            ["JMBAG", "Ime i prezime", "host", "variant"]
            + [TASK_LABELS[t] for t in TASK_ORDER]
            + ["total", "retake", "first_attempt_total"]
        )
        for r in results:
            tasks = r.get("tasks", {})
            row = [
                r.get("jmbag", ""),
                r.get("name", ""),
                r["host"],
                r["variant"],
            ]
            for t in TASK_ORDER:
                td = tasks.get(t, {})
                row.append(f"{td.get('score', 0)}/{td.get('max', TASK_MAXES[t])}")
            row.append(f"{r['total']}/100")
            row.append("yes" if r.get("retake") else "no")
            row.append(r.get("first_total", "") if r.get("retake") else "")
            writer.writerow(row)
    print(f"CSV written: {path}")


def write_html_merged(results: list[dict], path: Path) -> None:
    # Exclude unidentified students (no JMBAG)
    results = [r for r in results if r.get("jmbag")]

    n = len(results)
    totals = [r["total"] for r in results]
    avg_total = sum(totals) / n if n else 0

    task_avgs = {}
    for t in TASK_ORDER:
        scores = [r["tasks"].get(t, {}).get("score", 0) for r in results]
        task_avgs[t] = sum(scores) / n if n else 0

    student_rows = []
    for r in results:
        tasks = r.get("tasks", {})
        cells = ""
        for t in TASK_ORDER:
            td = tasks.get(t, {})
            score = td.get("score", 0)
            mx = td.get("max", TASK_MAXES[t])
            cells += f'<td>{score}/{mx}</td>'
        total = r["total"]
        total_cls = "total-pass" if total >= 50 else "total-fail"
        note = ""
        if r.get("retake"):
            first = r.get("first_total")
            retake_score = r.get("retake_total")
            if retake_score is not None:
                note = f'<span class="note retake-worse">retake {retake_score} &lt; {first} → kept first</span>'
            elif first is not None:
                note = f'<span class="note retake-better">retake ↑ from {first}</span>'
            else:
                note = '<span class="note retake-only">retake only</span>'
        student_rows.append(
            f'<tr>'
            f'<td class="jmbag">{r.get("jmbag","")}</td>'
            f'<td class="stuname">{r.get("name","")}</td>'
            f'{cells}'
            f'<td class="total {total_cls}">{total}/100</td>'
            f'<td class="notetd">{note}</td>'
            f'</tr>'
        )

    task_avg_rows = ""
    for t in TASK_ORDER:
        avg = task_avgs[t]
        mx = TASK_MAXES[t]
        pct = avg / mx * 100
        bar_w = int(pct)
        bar_cls = "bar-fill-pass" if pct >= 50 else "bar-fill-fail"
        pct_cls = "pct-pass" if pct >= 50 else "pct-fail"
        pct_label = f"{pct:.1f}% ▲" if pct >= 50 else f"{pct:.1f}% ▼"
        task_avg_rows += (
            f'<tr><td>{TASK_LABELS[t]}</td>'
            f'<td>{avg:.1f}/{mx}</td>'
            f'<td><div class="bar-bg"><div class="{bar_cls}" style="width:{bar_w}%"></div></div></td>'
            f'<td class="{pct_cls}">{pct_label}</td></tr>'
        )

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>RH124 Exam Results — Combined</title>
<style>
  body {{ font-family: sans-serif; max-width: 1100px; margin: 2rem auto; color: #222; }}
  h1 {{ font-size: 1.4rem; margin-bottom: 0.2rem; }}
  .subtitle {{ color: #666; margin-bottom: 2rem; font-size: 0.9rem; }}
  table {{ border-collapse: collapse; width: 100%; margin-bottom: 2rem; font-size: 0.9rem; }}
  th {{ background: #334; color: #fff; padding: 8px 10px; text-align: left; }}
  td {{ padding: 6px 10px; border-bottom: 1px solid #eee; color: #222; }}
  tr:hover td {{ background: #f8f8f8; }}
  .avg-row td {{ background: #f0f0f0; font-weight: bold; }}
  h2 {{ font-size: 1.1rem; margin-top: 2rem; border-bottom: 2px solid #334; padding-bottom: 4px; }}
  .bar-bg {{ background: #ddd; border-radius: 4px; height: 14px; min-width: 120px; }}
  .bar-fill-pass {{ background: #3a7; height: 14px; border-radius: 4px; }}
  .bar-fill-fail {{ background: #c33; height: 14px; border-radius: 4px; }}
  .pct-pass {{ color: #1a7a1a; font-weight: bold; }}
  .pct-fail {{ color: #b00; font-weight: bold; }}
  td.total {{ font-weight: bold; font-size: 1rem; }}
  td.total-pass {{ font-weight: bold; font-size: 1rem; color: #1a7a1a; }}
  td.total-fail {{ font-weight: bold; font-size: 1rem; color: #b00; }}
  .jmbag {{ font-family: monospace; font-size: 0.85rem; color: #555; }}
  .stuname {{ font-weight: bold; }}
  .notetd {{ font-size: 0.8rem; }}
  .note {{ padding: 2px 6px; border-radius: 3px; }}
  .retake-better {{ background: #d4edda; color: #155724; }}
  .retake-worse {{ background: #fff3cd; color: #856404; }}
  .retake-only {{ background: #cce5ff; color: #004085; }}
</style>
</head>
<body>
<h1>RH124 Mid-Semester Exam — Combined Results (First Attempt + Retake)</h1>
<p class="subtitle">{n} students &nbsp;|&nbsp; Class average: {avg_total:.1f}/100 &nbsp;|&nbsp;
  <span class="note retake-better">green = retake improved</span> &nbsp;
  <span class="note retake-worse">yellow = first attempt kept</span></p>

<h2>Score Summary</h2>
<table>
  <tr>
    <th>JMBAG</th><th>Ime i prezime</th>
    {"".join(f"<th>{TASK_LABELS[t]}</th>" for t in TASK_ORDER)}
    <th>Total</th><th>Note</th>
  </tr>
  {"".join(student_rows)}
  <tr class="avg-row">
    <td colspan="2">Class average</td>
    {"".join(f'<td>{task_avgs[t]:.1f}/{TASK_MAXES[t]}</td>' for t in TASK_ORDER)}
    <td>{avg_total:.1f}/100</td><td></td>
  </tr>
</table>

<h2>Per-Task Pass Rates</h2>
<table>
  <tr><th>Task</th><th>Avg score</th><th style="min-width:180px">Progress</th><th>%</th></tr>
  {task_avg_rows}
</table>

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
    parser.add_argument("--merge-csv", type=Path, metavar="FILE",
                        help="First-attempt report CSV (produced by this script). When given, --merge-retake is also required.")
    parser.add_argument("--merge-retake", type=Path, metavar="FILE",
                        help="Retake report CSV. Combined with --merge-csv: best score per student (by JMBAG) wins.")
    args = parser.parse_args()

    # --- Merge mode ---
    if args.merge_csv or args.merge_retake:
        if not args.merge_csv or not args.merge_retake:
            print("Error: --merge-csv and --merge-retake must be used together.", file=sys.stderr)
            sys.exit(1)
        for p in (args.merge_csv, args.merge_retake):
            if not p.exists():
                print(f"Error: file not found: {p}", file=sys.stderr)
                sys.exit(1)
        first = load_results_from_csv(args.merge_csv)
        retake = load_results_from_csv(args.merge_retake)
        print(f"Loaded {len(first)} first-attempt results, {len(retake)} retake results.")
        merged = merge_results(first, retake)
        retake_count = sum(1 for r in merged if r.get("retake"))
        print(f"Merged: {len(merged)} students total, {retake_count} took retake.")
        print_console_merged(merged)
        csv_path = args.csv or DEFAULT_RESULTS_DIR / "report-combined.csv"
        write_csv_merged(merged, csv_path)
        if not args.no_html:
            html_path = args.html or DEFAULT_RESULTS_DIR / "report-combined.html"
            write_html_merged(merged, html_path)
        return

    # --- Normal JSON mode ---
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
