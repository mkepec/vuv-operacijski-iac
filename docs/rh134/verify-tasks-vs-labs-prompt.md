# Prompt: Verify RH134 Exam Tasks Are Solvable From Practiced Labs

**Purpose:** Before running the live dry-run test on `student-01`, confirm that each
of the 6 RH134 exam tasks (as deployed — see `docs/rh134/instructor-cheatsheet.md`
and `docs/rh134/exam-rh134-design.md`) can realistically be solved by a student who
has only the knowledge/skills demonstrated in `tmp/rh134-labs/` (the labs and
comprehensive-review exercises actually completed during the course). The goal is
either:

- **Confirmation**: each task is a reasonable extension of a practiced lab — proceed
  with the live test as planned, or
- **A concrete gap list**: specific places where the exam requires a command, concept,
  tool, or workflow step that the labs never demonstrated — these need to be fixed
  in the exam design (`docs/rh134/exam-rh134-design.md`), the task sheet/hint script,
  or provisioning, *before* the exam is given to real students.

---

## How to run this check

For **each of the 6 tasks**, do the following:

1. Read the task's student instructions and grading checks in
   `docs/rh134/exam-rh134-design.md` §3.
2. Read the exact solution commands in `docs/rh134/instructor-cheatsheet.md`.
3. Identify the lab(s) in `tmp/rh134-labs/` that cover the same topic area
   (see the mapping table below as a starting point — verify it, don't just
   trust it).
4. For each command/concept the exam requires, check: **was this command,
   flag, file, or workflow step demonstrated in the lab(s)?**
   - If yes — note it as covered.
   - If it's a *minor variation* (different facility name, different service
     name, different mount point — same mechanic) — note it as a safe
     extension.
   - If it's **not demonstrated at all**, or the lab explicitly says it's
     "out of scope" — flag it as a **gap**.
5. For gaps, suggest a fix: e.g., add a line to the hint script, add a
   worked example to the task sheet's "Tip" section, adjust the grading
   weight, or (last resort) swap the task requirement for something the
   labs do cover.

## Task-to-lab mapping (starting point — verify and correct as needed)

| Exam Task | Primary lab(s) | Known concern to check |
|---|---|---|
| T1 — Shell scripting (service status report) | `1.7_lab.md` | Lab loops over **remote hosts via SSH** and uses `>`/`>>` redirection; exam loops over **local services** via `systemctl is-active`/`is-enabled`. Is "loop + command substitution + formatted print + redirect-to-overwrite" enough transfer, or does the exam need an explicit example of `systemctl is-active` output capture? |
| T2 — LVM build/mount/extend | `11.7_lab.md` | **Lab starts from an existing VG/LV and only extends it** (`vgextend`, `lvextend`, `xfs_growfs` on an already-mounted volume). The exam requires the *entire first half* from scratch: `parted` partitioning + `set ... lvm on`, `pvcreate`, `vgcreate`, `lvcreate` (new), `mkfs.xfs`, first-time `/etc/fstab` entry + `mount -a`. **Is the from-scratch PV→VG→LV→mkfs→fstab pipeline demonstrated anywhere in the labs the students did?** If not, is the "Tip" sufficient, or does T2 need a worked from-scratch example in the hint/task sheet? |
| T3 — journald persistence + rsyslog routing | `5.11_lab.md` | Lab covers `mkdir /var/log/journal` + `journalctl --flush` + `systemctl restart systemd-journald` + reboot-survival, and rsyslog `facility.priority -> file` routing with `authpriv.alert`. Exam uses `local0-7.<priority>` facilities (per-student variant) — same mechanic, different facility names. **Check:** does the lab ever show a `localN.priority` example, or only `authpriv`/`mail`/etc. named facilities? Is the jump from "authpriv.alert" to "local3.notice" obvious to a student? Also: the lab's rsyslog service is presumably already running — the exam's deliberate "`rsyslog` starts inactive+disabled" wrinkle (cheatsheet lines 108-127) is **not** in the lab. Is this twist adequately hinted? |
| T4 — rsync backup + scp/sftp upload | `8.5_lab.md` | Lab does `rsync -av root@servera:/etc /configsync` (pull from remote, as root) and `sftp` push of a single file. Exam requires **local-to-local** `rsync -a` (preserving perms of a planted tree with non-default owners — readable only via `sudo`) and then **scp/sftp to a different host (repo VM) authenticating as `student`**, where the source file just copied is `640 root:root` and unreadable by the student who copied it. **Check:** does the lab ever demonstrate `rsync -a` preserving non-default permissions/ownership in a way a student would notice/verify? Does the lab ever hit the "I just copied this file but can't read my own copy" friction the cheatsheet calls out (lines 151-164)? Is that friction adequately hinted, or will students get stuck? |
| T5 — NFS autofs automount | `15.5_lab.md` | Close match — lab covers master map (`/etc/auto.master.d/*.autofs`) + indirect map with `-rw,sync,fstype=nfs4` and wildcard `&`, triggering automount via `ls`, and write-testing. Exam swaps `fstype=nfs4` for `vers=4` in the indirect map line (cheatsheet line 191: `alpha -rw,sync,vers=4 172.16.16.121:/exports/export-alpha`) — **is `vers=4` vs `fstype=nfs4` a meaningful difference a student needs to reconcile, or are both accepted by the grading regex?** Check `exam-rh134-design.md` T5 grading check wording (§3, T5 grading table) for how strict the options match is. |
| T6 — Podman build/run/persist | `17.7_lab.md`, `comprehensive-review/19.5_comprehensive-review.md` | Both labs cover Containerfile authoring, `podman build -t`, `podman run -d -p`, and `curl` verification — good match for steps 1-3. **Step 4 (persistence via `podman generate systemd --new --files` + `systemctl --user enable --now` + `loginctl enable-linger`) is explicitly called "out of scope" in both labs** (17.7_lab.md line 103, 19.5 line 40: "Configuring persistent containers is out of the scope of this lesson"). This is worth **5 of T6's 15 points** and is the single largest topic in this exam with **zero lab coverage**. Does the task sheet's "Tip" (exam-rh134-design.md §3 T6) give students enough to derive the `podman generate systemd` workflow cold, or does this need a fuller worked hint / a short reference card? |

## What "good" looks like at the end of this check

A short report (not a new design doc — update `exam-rh134-design.md` directly if
changes are needed) covering, per task:

- **OK** — task is solvable as a natural extension of the practiced lab(s); no
  change needed.
- **Minor gap** — small variation from the lab the student should be able to
  bridge themselves, but worth a one-line addition to the hint script or task
  sheet "Tip" to reduce avoidable point loss.
- **Major gap** — concept/command genuinely absent from all practiced labs
  (T2's from-scratch LVM pipeline and T6's persistence step are the two
  candidates flagged above — confirm or refute both). For each major gap,
  propose one of:
  - expand the relevant hint script entry with a closer worked example,
  - expand the task sheet's "Tip" with a one-line command skeleton (not the
    full answer — matching RH124's "no example commands" rule),
  - re-weight points if the gap is severe enough that most students will
    likely lose them regardless,
  - (only if truly unfixable via hints) swap the requirement for something
    the labs do cover.

Focus on **T2's from-scratch LVM setup** and **T6's persistence step** first —
these are the two places the cheatsheet itself adds extensive "why" commentary
(see instructor-cheatsheet.md T2 and T3 notes, and the T6 "Note" about the base
image), which is often a signal that the original exam author already sensed
these spots needed extra explanation beyond what a lab would have taught.

Don't re-litigate tasks that are already a close match (T4's rsync mechanic, T5's
autofs mechanic, T1's loop mechanic) unless the check above turns up something
genuinely missing — the goal is a prioritized punch list, not a full rewrite.
