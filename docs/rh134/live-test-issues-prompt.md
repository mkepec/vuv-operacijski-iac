# Prompt: Triage Live-Test Issues from RH134 Exam Dry-Run (student-01)

**Context:** A live dry-run of the RH134 mid-semester exam is being performed on
`student-01` (variant `alpha`, `ssh -p 2201 student@135.181.128.170`), following
the exact steps in `docs/rh134/instructor-cheatsheet.md`. The goal of that cheatsheet
is to score 100/100 via `grade`. This session picks up with **issues encountered
during that run** — paste/describe them below and work through each one.

This follows on from a lab-vs-exam alignment pass (see
`docs/rh134/exam-rh134-design.md` §3 — T3/T4/T6 "Hint script" notes and T5
"Grading-regex note" — and `docs/rh134/align-hints-to-labs-prompt.md`, already
implemented) which confirmed the task design itself is sound and aligned with
`tmp/rh134-labs/`. So issues found now are more likely to be:
- provisioning bugs (something Ansible was supposed to set up but didn't, or set
  up in a state that doesn't match the cheatsheet's assumptions)
- grading script bugs (`grade.sh.j2` check logic doesn't match what a correct
  solution actually produces)
- cheatsheet/design doc drift (the cheatsheet command sequence doesn't actually
  work on the current image, or doesn't produce what the grading check expects)
- infra issues (DNAT, repo VM, NFS exports, SSH host keys, etc.)

---

## Issues encountered (fill in before/during session)

For each issue, capture:

1. **Which task** (T1-T6) and which step
2. **Command run** (exact, copy-pasted)
3. **Expected result** (per cheatsheet / design doc)
4. **Actual result** (full error output, not paraphrased)
5. **`grade <taskN>` output** for that task, if relevant

```
Issue 1:
Task: 
Command:
Expected:
Actual:


Issue 2:
...
```

---

## How to triage each issue

1. **Reproduce first** — re-run the failing command on student-01
   (`ssh -p 2201 student@135.181.128.170` or via ProxyJump
   `ssh -J root@135.181.128.170 ansible@172.16.16.101` for root-level
   inspection) to confirm it's not a one-off (stale SSH session, transient
   network blip, etc.)

2. **Classify the root cause:**
   - **Provisioning gap**: check `ansible/roles/exam-provision-rh134/tasks/main.yml`
     for the task that was supposed to set up this precondition. Did it run? Did
     it produce the expected state? (`ansible-playbook rh134/exam-provision.yml
     -l student-01 --check` can show drift without changing anything.)
   - **Grading script bug**: check the relevant `grade_tN()` function in
     `ansible/roles/exam-provision-rh134/templates/grade.sh.j2`. Does the check's
     command/regex actually match what the cheatsheet's solution produces? Test
     the check's exact command manually on student-01 and compare to what
     `grade` reports.
   - **Cheatsheet drift**: if the cheatsheet command itself fails or produces
     different output than documented (e.g. AlmaLinux 10 package/path differences,
     podman version differences, NFS option syntax), the cheatsheet needs
     correcting — but first confirm whether the *task design* or just the
     *documented command* is wrong.
   - **Infra issue**: DNAT, repo VM health (`http://172.16.16.121/repo`,
     `http://172.16.16.121/exam`, NFS exports via `showmount -e 172.16.16.121`),
     SSH host keys, repo VM `student` account — these are usually fixed at the
     infra layer, not by changing exam content.

3. **Fix at the right layer** — don't patch around a provisioning bug by manually
   fixing student-01's state and moving on; fix the Ansible role/template so a
   fresh `exam-provision.yml` run produces correct state for *any* student. The
   whole point of this dry-run is to catch issues before they hit 20 real students.

4. **Re-test after each fix**:
   - If you changed provisioning: re-run
     `ansible-playbook rh134/exam-provision.yml -l student-01` (idempotent —
     safe to rerun) and re-verify the affected step.
   - If you changed `grade.sh.j2`: re-render just that template (see
     `docs/rh134/align-hints-to-labs-prompt.md` for the
     `--start-at-task`-scoped re-render pattern) and re-run `grade <taskN>`.
   - If you changed the cheatsheet: re-run the corrected command sequence on
     student-01 to confirm it now produces 100% for that task.

5. **At the end of the session**, for each issue fixed:
   - Update `docs/rh134/instructor-cheatsheet.md` if the command sequence changed
   - Update `docs/rh134/exam-rh134-design.md` if the task design, grading
     weights, or provisioning requirements changed
   - Note any remaining open issues that need a fresh VM/reprovision cycle to
     re-test cleanly (e.g. T2's "raw disk" precondition or T3's "`/var/log/journal`
     must not pre-exist" precondition can't be re-tested on an already-modified
     student-01 without a reset)

---

## Useful reference commands

```bash
# Connect as student (exam-realistic)
ssh -p 2201 student@135.181.128.170

# Connect as ansible/root for inspection (no exam-state pollution from root actions,
# but be careful not to "fix" things this way that should be fixed by Ansible)
ssh -J root@135.181.128.170 ansible@172.16.16.101

# Run grading for one task
grade t1   # ... t6

# Full grade
grade

# Re-render a single template after editing it (replace task name as needed)
cd /Users/marin/projects/vuv-operacijski-iac/ansible
ansible-playbook rh134/exam-provision.yml -l student-01 --start-at-task "<Task name from main.yml>"

# Full reprovision of student-01 (clean slate — use if state is too tangled to
# fix incrementally; check exam-reset.yml first if it exists/works)
ansible-playbook rh134/exam-provision.yml -l student-01

# Repo VM health checks
curl -sf http://172.16.16.121/repo/ >/dev/null && echo "repo OK"
curl -sf http://172.16.16.121/exam/ >/dev/null && echo "portal OK"
showmount -e 172.16.16.121
```
