# RH134 — Provision, Deploy, and Test-Grade Session Prompt

Use this prompt to start the next session: provisioning the RH134 infrastructure
end-to-end on a small scale (1 student VM), deploying the exam content, writing
an instructor runbook + cheatsheet, and using the cheatsheet to drive the
grading script through a full test pass.

---

## Context

RH134 implementation (Session 2 — provisioning) is done: the
`exam-provision-rh134` Ansible role, `rh134/exam-provision.yml` /
`rh134/exam-reset.yml` playbooks, the three Jinja2 templates
(`exam-tasks.txt.j2`, `grade.sh.j2`, `hint.sh.j2`), the RH134 portal templates,
the `rh134_*` inventory vars, the Terraform disk (`scsi2`, 1 GB raw → `/dev/sdb`),
and the extended shared `repo-provision.yml` (NFS exports + student account +
combined portal) all exist but have **never been run against live
infrastructure**. None of it has been validated end-to-end.

This session is the first time any of this touches real VMs. Treat it as a
careful, incremental dry run — not a full-class rehearsal.

Read these first, in this order:
- `CLAUDE.md` — infrastructure context, standard workflow, scaling guidance,
  current status
- `docs/rh134/exam-rh134-design.md` — full design (tasks, variation scheme,
  grading logic in §4, provisioning requirements in §5, open items in §8)
- `docs/rh124/instructor-runbook.md` and `docs/rh124/instructor-cheatsheet.md`
  — structural references for the RH134 equivalents you'll write (§3 below)
- `TODO.md` — current status; look at the "RH134 implementation — Session 2"
  block for exactly what's built vs. outstanding

---

## Part 1 — Provision the infrastructure (small scale)

Follow `CLAUDE.md`'s "Standard workflow" and "Scaling VMs" sections. Start at
`STUDENT_COUNT=1` — this gives you `student-01` (VM 200, 172.16.16.101,
variant `alpha`) plus the repo VM, which is enough to validate the whole
pipeline without burning a full provisioning cycle on 20 VMs.

1. **Terraform** — `source setup.sh && cd terraform && terraform apply`. This
   is the *first time* `terraform apply` runs since the RH134 disk
   (`scsi2`, 1 GB raw) was added to `main.tf` — confirm in the plan output that
   the new disk attaches to `student-01` (and the repo VM is untouched) before
   approving. **Ask before running `apply`** — it touches live infra and the
   TF Cloud workspace.

2. **Clear stale SSH host keys** — `for i in $(seq 101 101); do ssh-keygen -R "172.16.16.$i"; done`
   (only `student-01`'s IP needs clearing at `STUDENT_COUNT=1`).

3. **RH124 provisioning** (still required — both exams' content lives on the
   same VMs and the same repo VM):
   ```
   cd ansible
   ansible-playbook rh124/exam-provision.yml -l student-01
   ```

4. **RH134 provisioning** — the actual first live run of the new role:
   ```
   ansible-playbook rh134/exam-provision.yml -l student-01
   ```
   Watch closely for the first failure on real infrastructure — likely
   candidates: the `containers.podman.podman_image` pre-pull (network/registry
   reachability), `loginctl enable-linger`, the `/dev/sdb` raw-disk check
   (`blkid -p` exit codes), or template variable mismatches that
   `--syntax-check` couldn't catch. Fix forward; don't paper over failures with
   `failed_when: false` unless the design doc already calls for it.

5. **Repo VM provisioning** — also a first live run, and the riskiest piece
   (NFS server setup, `student` OS account creation, combined portal
   rendering, the new pre-flight health check with `ansible.builtin.expect`
   for SSH/password login):
   ```
   ansible-playbook repo-provision.yml
   ```
   This always targets the full `reposervers` group (there's only one), so it
   provisions NFS exports for **all 20 students** even though only
   `student-01` exists yet — that's fine, the exports are independent of
   student VM state (per design doc: "T5 (NFS) needs only the repo VM's
   exports, provisioned independently of student VM state"). Confirm
   `showmount -e 172.16.16.121` lists all 20 exports and the pre-flight health
   check passes.

**If anything in the roles/playbooks/templates needs fixing to get a clean
run** — fix it in place, note what was wrong and why in your final summary
(this is exactly the kind of thing that won't surface until first contact with
real infrastructure), and re-run the affected playbook to confirm the fix
before moving on.

---

## Part 2 — Deploy and verify the exam content

With `student-01` provisioned:

1. Confirm the task sheet, `grade`, and `hint` scripts landed correctly:
   ```
   ssh -J root@135.181.128.170 ansible@172.16.16.101
   cat /home/student/exam-tasks.txt | head -30
   ls -la /usr/local/bin/grade /usr/local/bin/hint   # both should be 0755
   ```
2. Open the exam portal in a browser and check:
   - `http://172.16.16.121/exam/` shows the new course chooser
   - `http://172.16.16.121/exam/rh124/` and `.../rh134/` both render correctly
   - The RH134 student-01 (alpha) page shows fully-substituted values (no raw
     Jinja2 syntax, no `{{ }}` visible)
3. Spot-check the repo VM additions directly:
   ```
   ssh root@135.181.128.170
   showmount -e 172.16.16.121
   ssh student@172.16.16.121   # password auth — confirm it prompts and accepts STUDENT_PASSWORD
   ```

---

## Part 3 — Write the instructor runbook and cheatsheet

Use `docs/rh124/instructor-runbook.md` and `docs/rh124/instructor-cheatsheet.md`
as structural references (their format, sectioning, and level of detail have
already been validated against a real exam run) — but write RH134's content
fresh against the design doc's six tasks and the actual commands you used.

1. **`docs/rh134/instructor-cheatsheet.md`** — exact commands to complete all
   6 RH134 tasks on `student-01` (variant: alpha). This needs real, tested
   commands for:
   - T1: writing `/home/student/bin/collect-alpha.sh`
   - T2: the full LVM chain on `/dev/sdb` — partition → PV → VG (`vg_alpha`) →
     LV (`lv_alpha`, 300M) → XFS → persistent mount at `/storage/alpha` →
     `marker.txt` → extend by 500M → `xfs_growfs`
   - T3: persistent journald + the `local0.warning` → `/var/log/alpha-events`
     rsyslog rule + `logger` test message
   - T4: `rsync -a /etc/exam-source/ /home/student/backup-alpha/` +
     `scp`/`sftp` of `manifest.txt` to `student@172.16.16.121`
   - T5: autofs master + indirect map for `/remote/alpha` →
     `172.16.16.121:/exports/export-alpha`, NFSv4 rw/sync, plus the
     `alpha-submitted.txt` write-test
   - T6: Containerfile from `{{ rh134_base_image }}`, build/tag
     `alpha-web:1.0`, run on port 8101, `podman generate systemd` for
     persistence
   - Verification snippets after each task (mirror RH124's cheatsheet style —
     a `**Verify:**` block with read-only checks)

2. **`docs/rh134/instructor-runbook.md`** — step-by-step lifecycle guide
   mirroring RH124's structure: quick-reference table, lifecycle phase diagram,
   provisioning steps (referencing this session's commands), exam-day
   procedure, grading procedure, teardown. Update its "Phase 1" commands to
   reflect that `repo-provision.yml` now lives at the shared top level (not
   `rh124/repo-provision.yml`).

---

## Part 4 — Test the grading script end-to-end

This is the actual point of the exercise: confirm `grade.sh.j2`'s rendered
output (`/usr/local/bin/grade` on `student-01`) correctly scores a fully-solved
exam.

1. **Run the cheatsheet commands** from Part 3 on `student-01`, end to end —
   this *is* the dry run; if a command in the cheatsheet doesn't work as
   written against the real VM, that's a bug to fix (in the cheatsheet, or
   possibly in the task design itself if the design doc's expectations don't
   hold up against real AlmaLinux 10 behavior).

2. **Run `grade` after each task** (not just at the end) — this validates
   incrementally and makes it much easier to isolate whether a failure is in
   your solution, the grading script's check logic, or a template-rendering
   mismatch (e.g. a hostvar that doesn't match what the grading script expects).
   ```
   grade t1
   grade t2
   ...
   grade t6
   grade        # full run
   ```

3. **Reboot and re-grade** — T2 (LVM persistence), T3 (journald persistence),
   and T6 (container persistence via systemd unit + linger) all require
   surviving a reboot. After completing all 6 tasks:
   ```
   sudo systemctl reboot
   # reconnect, then:
   grade
   ```
   Confirm the score doesn't drop after reboot — if it does, that's either a
   real gap in the cheatsheet's solution (the persistence step was
   insufficient) or a grading-script bug (e.g. `rebooted_since_provision()`
   not detecting the reboot correctly).

4. **Confirm the cross-host sub-scores** — T4 and T5 each have points that
   `grade` can only locally sub-score (per design doc §4.3, the full T4/T5
   marks require instructor-side verification against the repo VM). Confirm:
   - The local sub-score lines appear with the correct "X/Y (full task max: Z)"
     format and an INFO note about instructor-side verification
   - The cross-host pieces actually landed correctly on the repo VM:
     `/home/student/uploaded-alpha.txt` exists there (T4), and
     `/exports/export-alpha/alpha-submitted.txt` exists with the right content
     (T5) — these are the things the (not-yet-built) `exam-grade.yml` will
     check in Session 3.

5. **Target: 100/100** (or the correct max given the cross-host caveat — note
   in your summary exactly what `grade` reports as the max it can verify
   locally vs. the true 100-point total). If it doesn't reach that, decide
   whether the bug is in the student-side solution (cheatsheet), the
   `exam-provision-rh134` role (e.g. wrong baseline state), or `grade.sh.j2`
   itself — and fix the right one. Don't adjust the cheatsheet to work around a
   grading bug, or loosen a grading check to match a flawed solution — get to
   the root cause.

---

## Constraints

- **This session runs live infrastructure commands** — that's the explicit
  point of it (unlike the previous implementation session, which avoided all
  live touches). Still: **ask before `terraform apply`/`destroy`** and before
  any playbook run that's notably broad in scope or destructive
  (`exam-reset.yml`, anything touching all 20 students). Routine `-l
  student-01` runs and read-only checks (`ansible ... -m ping`, `grade`,
  `showmount`, `ssh ... cat ...`) don't need pre-approval — just narrate what
  you're running and why.
- If you hit a bug in the role/playbook/template, **fix it in place** and
  re-run — that's the whole purpose of this dry run. Note each fix in your
  summary so the rationale isn't lost.
- **Do not scale to `STUDENT_COUNT=10` or `20`** in this session — one student
  VM is sufficient to validate the whole pipeline (provisioning, content,
  grading) and keeps the iteration loop fast. Scaling up is a separate,
  later decision once this dry run is clean.
- Keep the runbook/cheatsheet writing and the live-infra debugging as
  separable concerns in your commits if it makes sense to split them — but use
  your judgment; a single "RH134 dry-run: provisioning fixes + docs" commit is
  also reasonable if the changes are entangled.
- **Ask before pushing.**
- Update `TODO.md` at the end of the session reflecting what's now verified
  live vs. still outstanding (Session 3 — grading playbook — remains the next
  major piece).

---

## Constraints carried over from the design (don't relitigate these)

- `rh134_base_image` is currently `registry.access.redhat.com/ubi9/httpd-24`
  — my placeholder choice from the provisioning session, since the design doc
  only specified "the same httpd-based image used in the labs." If the
  pre-pull fails or the image doesn't behave as `grade.sh.j2` expects
  (specifically the `Containerfile`/`index.html` checks in T6), this is the
  first place to look — confirm or swap it for whatever the labs actually use.
- The design doc explicitly defers `exam-grade.yml` (the instructor-side
  grading playbook with cross-host checks) to "Session 3 — Grading." Don't
  build it in this session — Part 4 above tests the *student-side* `grade`
  script only, which is what's actually deployed and runnable right now.
