#!/usr/bin/env python3
"""
Generate the final combined grade report for the RHCSA course.
Pulls RH124 combined, RH134 combined, and final exam results,
then assigns a course grade for each student.

Grade ladder (Croatian):
  >= 91%  → 5 (odličan)
  >= 81%  → 4 (vrlo dobar)
  >= 61%  → 3 (dobar)
  >= 51%  → 2 (dovoljan)
  < 51%   → 1 (nedovoljan)

Students who passed BOTH mid-terms (>=50% each) are graded on the
average of the two mid-term percentages.
Students who failed one or both mid-terms and sat the final are
graded on their final exam score (out of 165).
"""

import csv, sys, os
from pathlib import Path

BASE = Path(__file__).parent.parent / "ansible" / "exam-results"


def parse_score(s):
    """'79/165' → (79, 165). Returns None for '-' or empty."""
    if not s or s == "-":
        return None
    parts = s.split("/")
    return int(parts[0]), int(parts[1])


def grade(pct):
    if pct >= 0.91:
        return "5"
    if pct >= 0.81:
        return "4"
    if pct >= 0.61:
        return "3"
    if pct >= 0.51:
        return "2"
    return "1"


def grade_label(pct):
    labels = {"5": "odličan", "4": "vrlo dobar", "3": "dobar", "2": "dovoljan", "1": "nedovoljan"}
    g = grade(pct)
    return f"{g} ({labels[g]})"


# ── Load RH124 combined ────────────────────────────────────────────────────
rh124 = {}
with open(BASE / "rh124/archive/rh124-combined-2026-05.csv") as f:
    for row in csv.DictReader(f):
        if row["JMBAG"]:
            rh124[row["JMBAG"]] = {"name": row["Ime i prezime"], "score": row["total"]}

# ── Load RH134 combined ────────────────────────────────────────────────────
rh134 = {}
with open(BASE / "rh134/archive/rh134-combined-2026-06.csv") as f:
    for row in csv.DictReader(f):
        if row["JMBAG"]:
            rh134[row["JMBAG"]] = {"name": row["Ime i prezime"], "score": row["total"]}

# ── Final exam results (teacher-observed scores, authoritative) ────────────
# VM assignment for 2026-07-01 final exam
final_exam = {
    "0308007418": {"name": "Ivan Grubač",    "vm": "student-19", "score": "79/165"},
    "0307020439": {"name": "Luka Kapusta",   "vm": "student-09", "score": "86/165"},
    "0122245222": {"name": "Gabrijel Sić",   "vm": "student-07", "score": "85/165"},
    "0307020647": {"name": "Luka Lukačević", "vm": "student-10", "score": "103/165"},
    "0307020540": {"name": "Noel Špićak",    "vm": "student-02", "score": "98/165"},
    "0307020491": {"name": "Tomislav Tomić", "vm": "student-08", "score": "100/165"},
}

# ── Build combined table ───────────────────────────────────────────────────
all_jmbags = sorted(set(rh124) | set(rh134))

rows = []
for jmbag in all_jmbags:
    r4 = rh124.get(jmbag, {})
    r34 = rh134.get(jmbag, {})
    fin = final_exam.get(jmbag, {})

    name = (r4 or r34).get("name", "?")
    s124 = r4.get("score", "-")
    s134 = r34.get("score", "-")
    s_fin = fin.get("score", "-")

    p124 = parse_score(s124)
    p134 = parse_score(s134)
    p_fin = parse_score(s_fin)

    mid_pass = (
        p124 and p134
        and (p124[0] / p124[1] >= 0.50)
        and (p134[0] / p134[1] >= 0.50)
    )

    if p_fin:
        # Sat the final — grade on final result
        pct = p_fin[0] / p_fin[1]
        basis = "final exam"
        final_score_str = s_fin
    elif mid_pass:
        # Passed both mid-terms — grade on average of both
        pct = (p124[0] / p124[1] + p134[0] / p134[1]) / 2
        basis = "mid-terms"
        final_score_str = "-"
    else:
        # Failed one/both mid-terms and didn't sit (or not found) — fail
        pct = 0.0
        basis = "absent/fail"
        final_score_str = "-"

    rows.append({
        "JMBAG": jmbag,
        "Ime i prezime": name,
        "RH124": s124,
        "RH134": s134,
        "Final (2026-07-01)": final_score_str,
        "Postotak": f"{pct:.1%}",
        "Ocjena": grade_label(pct),
        "Osnova": basis,
    })

# ── Write CSV ──────────────────────────────────────────────────────────────
out_csv = BASE / "final/archive/final-combined-2026-07-01.csv"
fieldnames = ["JMBAG", "Ime i prezime", "RH124", "RH134", "Final (2026-07-01)", "Postotak", "Ocjena", "Osnova"]
with open(out_csv, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=fieldnames)
    w.writeheader()
    w.writerows(rows)
print(f"CSV: {out_csv}")

# ── Write HTML ─────────────────────────────────────────────────────────────
out_html = BASE / "final/archive/final-combined-2026-07-01.html"

grade_colors = {
    "5": "#2d6a4f",
    "4": "#52b788",
    "3": "#74c69d",
    "2": "#b7e4c7",
    "1": "#e63946",
}

def row_html(r):
    g = grade(float(r["Postotak"].rstrip("%")) / 100)
    color = grade_colors[g]
    bg = "#fff3f3" if g == "1" else "#f0fff4" if g in ("4", "5") else "#fffff0" if g == "3" else ""
    style = f'style="background:{bg}"' if bg else ""
    badge = f'<span style="background:{color};color:#fff;padding:2px 8px;border-radius:4px;font-weight:bold">{r["Ocjena"]}</span>'
    cells = "".join(f"<td>{v}</td>" for v in [
        r["JMBAG"], r["Ime i prezime"], r["RH124"], r["RH134"],
        r["Final (2026-07-01)"], r["Postotak"], badge, r["Osnova"]
    ])
    return f"<tr {style}>{cells}</tr>"

pass_count = sum(1 for r in rows if not r["Ocjena"].startswith("1"))
fail_count = len(rows) - pass_count

html = f"""<!DOCTYPE html>
<html lang="hr">
<head>
<meta charset="UTF-8">
<title>RHCSA Final Combined Results — 2026-07-01</title>
<style>
  body {{ font-family: system-ui, sans-serif; margin: 2em; color: #222; }}
  h1 {{ margin-bottom: 0.2em; }}
  .meta {{ color: #666; margin-bottom: 1.5em; }}
  table {{ border-collapse: collapse; width: 100%; }}
  th, td {{ border: 1px solid #ddd; padding: 8px 12px; text-align: left; }}
  th {{ background: #2b2d42; color: #fff; }}
  tr:hover {{ background: #f5f5f5 !important; }}
  .summary {{ margin-top: 1.5em; font-size: 0.95em; }}
  .stat {{ display: inline-block; margin-right: 2em; }}
</style>
</head>
<body>
<h1>RHCSA — Završni kombinirani rezultati</h1>
<div class="meta">
  Virovitica University of Applied Sciences &nbsp;|&nbsp;
  Kolegij: Operacijski sustavi (RH124 + RH134) &nbsp;|&nbsp;
  Datum: 2026-07-01
</div>
<table>
<thead>
<tr>
  <th>JMBAG</th><th>Ime i prezime</th>
  <th>RH124 (/100)</th><th>RH134 (/100)</th>
  <th>Završni (/165)</th>
  <th>Postotak</th><th>Ocjena</th><th>Osnova ocjene</th>
</tr>
</thead>
<tbody>
{"".join(row_html(r) for r in rows)}
</tbody>
</table>
<div class="summary">
  <span class="stat"><strong>Ukupno studenata:</strong> {len(rows)}</span>
  <span class="stat"><strong>Položilo:</strong> {pass_count}</span>
  <span class="stat"><strong>Palo:</strong> {fail_count}</span>
  <span class="stat"><strong>Prolaznost:</strong> {pass_count/len(rows):.0%}</span>
</div>
</body>
</html>
"""

with open(out_html, "w") as f:
    f.write(html)
print(f"HTML: {out_html}")

# ── Print summary to terminal ──────────────────────────────────────────────
print()
print(f"{'JMBAG':<14} {'Ime i prezime':<25} {'RH124':>10} {'RH134':>10} {'Final':>10} {'%':>7}  Ocjena")
print("-" * 90)
for r in rows:
    print(f"{r['JMBAG']:<14} {r['Ime i prezime']:<25} {r['RH124']:>10} {r['RH134']:>10} {r['Final (2026-07-01)']:>10} {r['Postotak']:>7}  {r['Ocjena']}")
print()
print(f"Položilo: {pass_count}/{len(rows)} ({pass_count/len(rows):.0%})")
