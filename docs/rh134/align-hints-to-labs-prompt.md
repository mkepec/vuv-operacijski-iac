# Prompt: Align RH134 Hint Script to Lab-Practice Gaps (T3, T4, T6)

**Context:** A lab-vs-exam verification pass (see `docs/rh134/exam-rh134-design.md`
§3, T3/T4/T5/T6 — "Hint script addition" / "Grading-regex note" / "Hint script —
expanded" notes added during this pass) found that 5 of 6 tasks are faithful,
same-difficulty recombinations of labs in `tmp/rh134-labs/`. Two small hint gaps
(T3, T4) and one larger gap (T6 step 4 — container persistence, which both
container labs explicitly call "out of scope") were identified, plus a grading
regex check for T5 that turned out to already be correct.

**Already verified as fine — do not change:**
- T5's NFS-options grep in `grade.sh.j2` (line ~317) already accepts
  `vers=4|nfsvers=4|nfs4`, so both the cheatsheet's `vers=4` syntax and the lab's
  `fstype=nfs4` syntax score correctly. No action needed.
- T6's grading logic (`grade_t6` in `grade.sh.j2`, lines ~342-385) already checks
  for a `systemctl --user` unit referencing the container plus a post-reboot curl —
  this is correct and matches the design doc. **Do not change grading logic for T6**
  — only the hint text needs enrichment.
- T2 provisioning/grading needs no change — confirmed fully covered by labs
  11.7 + 19.3 (comprehensive review).

**What needs to change — only `ansible/roles/exam-provision-rh134/templates/hint.sh.j2`:**

The hint script currently uses an abstract "riddle" style (deliberately vague,
bilingual EN/HR, no literal commands) for all 6 tasks. This style works for T1,
T2, T3, T4, T5 because each maps to a lab the students completed — the abstraction
is a *nudge* toward something they've already done. **T6 step 4 is different: no
lab covers container persistence at all**, so an abstract nudge isn't enough —
students have nothing to recall. The design doc now calls for T6's hint to be the
one exception to the "no literal commands" convention, including an actual command
skeleton (see exam-rh134-design.md §3, T6, "Hint script — expanded for T6 step 4").

### Task list

1. **T3 hint (`hint.sh.j2`, `t3` case, ~lines 48-71):** add a short line connecting
   T3 to T1's output — something like (keep it abstract/bilingual, consistent with
   the existing style; this is a *small* addition, not a rewrite):
   > "...Check what your Task 1 report says about this second system's running and
   > enabled state — a routing rule only works while that service is active, and
   > won't survive the reboot unless it's enabled too."
   (Croatian equivalent alongside, matching the existing bilingual pattern.)

2. **T4 hint (`hint.sh.j2`, `t4` case, ~lines 72-95):** add a line about the
   "your own backup copy may not be readable by you" friction — something like:
   > "...If the file you need to copy in step 2 isn't readable by your normal
   > user after step 1, that's expected — archive mode preserved its original
   > permissions. Don't change them; read or copy the file as root instead."
   (Croatian equivalent alongside.)

3. **T6 hint (`hint.sh.j2`, `t6` case, ~lines 115-139):** after the existing
   abstract paragraph (keep it — it still covers steps 1-3 well), append a
   concrete, literal command skeleton for step 4 only — in English with a
   Croatian intro line, e.g.:

   ```
   Task 6 — Hint / Savjet (step 4 / korak 4):

   No lab covered this step, so here is the actual command sequence
   (substitute your own container's name):

     podman generate systemd --new --files --name <your-container-name>
     mkdir -p ~/.config/systemd/user
     mv container-<your-container-name>.service ~/.config/systemd/user/
     systemctl --user daemon-reload
     systemctl --user enable --now container-<your-container-name>
     loginctl enable-linger student

   Ovaj korak nije obrađen u vježbama, pa slijedi stvarni niz naredbi
   (zamijenite nazivom svog kontejnera):

     [same commands]
   ```

   Match the existing heredoc/`cat <<'EOF'` structure and quoting style used
   by the other `case` branches in the file.

### Verification

After editing `hint.sh.j2`:

1. Re-render the template for `student-01` (variant `alpha`) via the existing
   provisioning playbook, or render it standalone with `ansible-playbook
   rh134/exam-provision.yml -l student-01 --tags <hint-related-tag-if-any>` —
   check what tags/scoping `exam-provision-rh134/tasks/main.yml` already uses
   for template rendering and reuse that, don't invent a new mechanism.
2. SSH to student-01 (`ssh -p 2201 student@135.181.128.170`) and run
   `hint t3`, `hint t4`, `hint t6` — confirm the new text renders correctly,
   variables substitute as expected (none of these additions introduce new
   Jinja2 variables — T6's skeleton uses literal placeholder text like
   `<your-container-name>`, not `{{ exam_variant }}-srv`, since the hint
   should teach the *pattern*, not hand over the exact answer).
3. Confirm `grade` still runs cleanly afterward (hint script changes shouldn't
   affect grading, but a quick `grade` run confirms nothing else broke from
   re-provisioning).

### Out of scope for this prompt

- No changes to `grade.sh.j2`, `exam-tasks.txt.j2`, `exam-task-sheet.html.j2`,
  or `exam-index.html.j2`.
- No changes to provisioning logic in `exam-provision-rh134/tasks/main.yml`.
- No changes to point weights or task requirements.

This is a small, low-risk, hint-text-only change — it should not require a full
reprovision/destroy-apply cycle, only a re-run of the template-rendering tasks
for the hint script.
