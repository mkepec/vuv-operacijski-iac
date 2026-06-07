# RH134 Mid-Semester Performance Exam — Design Requirements

**Course:** Red Hat System Administration II (RH134 10.0)
**Institution:** Virovitica University of Applied Sciences (VUV)
**Instructor:** Marin Kepec
**Exam type:** Performance-based practical exam
**Duration:** 90 minutes
**Total points:** 100
**Reference template:** `docs/exam-rh124-design.md` (RH124 mid-semester exam — fully implemented, tested, graded, archived; this document follows the same structure and pipeline. Note: §7 proposes moving this to `docs/rh124/exam-rh124-design.md` as part of a `docs/`/`ansible/` restructure — that move has not happened yet, so the path above is the current, correct one.)

---

## 1. Infrastructure Requirements

### 1.1 Student VMs (existing — reused as-is)

The same 20 AlmaLinux 10 VMs used for RH124 (VM IDs 200–219, IPs 172.16.16.101–120, 2 vCores / 3072 MB / 20 GB disk). See `CLAUDE.md` for full spec. No Terraform changes to the base VM definition are required.

### 1.2 Repo VM — gains a second role (no new VM)

RH134 does **not** introduce a 21st/22nd VM. Instead, the existing repo VM (172.16.16.121, VM ID 221) is extended to also serve as the "shared lab server" for the NFS task (Task 5).

**Why fold in rather than stand up a new VM:**
- The host has 64 GB RAM and already runs 20 × 3072 MB (61 GB) for student VMs plus the repo VM. There is effectively no headroom for a 22nd VM at any meaningful size.
- The NFS workload this exam needs (20 students mounting small per-student exports, each doing a handful of read/write operations during a 90-minute window) is light — comparable in load to the existing DNF repo traffic during an exam.
- One fewer VM means one fewer thing to provision, monitor, and tear down.

**Trade-off accepted:** the repo VM becomes a shared dependency for *both* RH124 (DNF repo + portal) and RH134 (DNF repo + portal + NFS exports). If RH124 and RH134 exams (or retakes) ever overlap in time, an issue on this VM affects both. This is judged acceptable — the VM is lightweight (static HTTP + NFS export of small directories) and the existing RH124 pre-flight check pattern ("repo VM must be running before any student VM exam begins") extends naturally to cover the new NFS role too.

**Updated repo VM role summary:**

| Property | Value |
|---|---|
| VM ID | 221 (unchanged) |
| IP | 172.16.16.121 (unchanged) |
| OS | AlmaLinux 10 |
| Roles | (a) HTTP DNF package repository, (b) exam task portal (static HTML), (c) **NEW:** NFS server exporting per-student directories |
| New URL/service | `nfs-server` exporting `/exports/student-NN` for N = 01..20 |
| New packages to install | `nfs-utils` |
| New provisioning | Per-student export directories, `/etc/exports` entries, planted per-student files for grading anchors |

This VM must be running — DNF repo, portal, **and NFS service** all healthy — before any student VM exam begins. The pre-flight check (already part of the RH124 runbook) is extended with an NFS health check (see §5).

### 1.3 No second disk needed for student VMs from RH124 reuse — but RH134 needs its own

RH124 added a second 1 GB XFS-preformatted disk (Terraform interface `virtio0`, appearing in-guest as `/dev/vda` — see `CLAUDE.md`) to each student VM for its mount/find task. That disk and partition layout is **specific to the RH124 task design** (pre-partitioned, pre-formatted, not mounted).

RH134's storage task (Task 2 — LVM) requires the **opposite starting state**: a raw, unpartitioned block device that the student turns into a PV → VG → LV → filesystem → mount from scratch, then extends. Reusing the RH124 disk as-is (already partitioned and XFS-formatted) would short-circuit half the task.

**Recommendation:** add a **second**, separate raw disk to the student VM resource — used only when the VM is provisioned for an RH134 exam (RH124 and RH134 exams are not expected to run concurrently on the same VMs, but the Terraform/Ansible split must allow either disk to be present independently; see §6 and §7 for how this is modeled without conflict).

| Property | Value |
|---|---|
| Size | 1 GB |
| Device path inside VM | `/dev/sdb` (RH124's second disk is on a different bus — `virtio0` → `/dev/vda` — so this is the only SCSI-bus disk besides the OS disk and lands as the next available `sd*` letter; confirmed live: `scsi2` in Terraform → `/dev/sdb` in-guest, **not** `/dev/sdc` as originally assumed in this design) |
| Partition | **None** — completely raw/unpartitioned at exam start |
| Filesystem | **None** — student creates PV/VG/LV/filesystem from scratch |
| Mount state | Not mounted, not even partitioned |

1 GB is plenty of headroom for the LV sizes in Task 2 (initial `300M`, extended to `800M` total — see §2.1) while keeping the disk small. This is the only new Terraform requirement for RH134 (see §6).

---

## 2. Per-Student Variation

Same mechanism as RH124: NATO phonetic alphabet mapping students 01–20 to `alpha`...`tango`, with values baked into inventory host vars and rendered into the task sheet, grade script, and portal at provisioning time via Jinja2.

### 2.1 Variant assignment (reuses the RH124 alpha–tango mapping)

The `exam_variant` value per student is **identical to RH124** (student-01 = alpha, … student-20 = tango) — this mapping is now an established convention for this cohort and is reused for every exam so it doesn't need to be re-derived or re-explained each time. New RH134-specific variant *values* (not the alpha/tango names themselves) are introduced below.

| Student | Variant | LV/VG suffix | Rsyslog facility.priority | NFS export dir | Podman port | Backup dir name |
|---|---|---|---|---|---|---|
| student-01 | alpha | vg_alpha / lv_alpha | local0.warning | export-alpha | 8101 | backup-alpha |
| student-02 | bravo | vg_bravo / lv_bravo | local1.err | export-bravo | 8102 | backup-bravo |
| student-03 | charlie | vg_charlie / lv_charlie | local2.crit | export-charlie | 8103 | backup-charlie |
| student-04 | delta | vg_delta / lv_delta | local3.alert | export-delta | 8104 | backup-delta |
| student-05 | echo | vg_echo / lv_echo | local4.notice | export-echo | 8105 | backup-echo |
| student-06 | foxtrot | vg_foxtrot / lv_foxtrot | local5.warning | export-foxtrot | 8106 | backup-foxtrot |
| student-07 | golf | vg_golf / lv_golf | local6.err | export-golf | 8107 | backup-golf |
| student-08 | hotel | vg_hotel / lv_hotel | local7.crit | export-hotel | 8108 | backup-hotel |
| student-09 | india | vg_india / lv_india | local0.alert | export-india | 8109 | backup-india |
| student-10 | juliet | vg_juliet / lv_juliet | local1.notice | export-juliet | 8110 | backup-juliet |
| student-11 | kilo | vg_kilo / lv_kilo | local2.warning | export-kilo | 8111 | backup-kilo |
| student-12 | lima | vg_lima / lv_lima | local3.err | export-lima | 8112 | backup-lima |
| student-13 | mike | vg_mike / lv_mike | local4.crit | export-mike | 8113 | backup-mike |
| student-14 | november | vg_november / lv_november | local5.alert | export-november | 8114 | backup-november |
| student-15 | oscar | vg_oscar / lv_oscar | local6.notice | export-oscar | 8115 | backup-oscar |
| student-16 | papa | vg_papa / lv_papa | local7.warning | export-papa | 8116 | backup-papa |
| student-17 | quebec | vg_quebec / lv_quebec | local0.err | export-quebec | 8117 | backup-quebec |
| student-18 | romeo | vg_romeo / lv_romeo | local1.crit | export-romeo | 8118 | backup-romeo |
| student-19 | sierra | vg_sierra / lv_sierra | local2.alert | export-sierra | 8119 | backup-sierra |
| student-20 | tango | vg_tango / lv_tango | local3.notice | export-tango | 8120 | backup-tango |

**Why these specific variation axes:**
- **LV/VG names** — prevents copy-pasting `lvcreate`/`vgcreate` commands verbatim between neighbors (the LVM lab, 11.7, uses fixed names; the exam must not).
- **Rsyslog facility.priority** — cycles through `local0`–`local7` × five priority levels so no two adjacent students share a combination; this is the single most copy-paste-prone value in the logging task (5.11_lab.md uses one fixed pair).
- **NFS export directory name** — doubles as the per-student namespace on the shared repo VM (see Task 5 and §1.2) — this is how 20 students hit the same NFS server without colliding, mirroring how 15.5_lab.md uses per-group export subdirectories.
- **Podman host port** — `8100 + N`, mirrors the existing DNAT port convention (`2200 + N`) already used for student SSH access; guarantees no two students bind the same host port even though they're on separate VMs (collision-avoidance here is more about habit/consistency than necessity, but it keeps the convention recognizable and makes grading scripts simpler to template).
- **Backup directory name** — used in the file-transfer task (rsync target naming) so directory-listing answers differ between students.

### 2.2 Variables per host (Ansible inventory)

Each host entry in `ansible/inventory.yml` gains an RH134-specific variable block (alongside the existing RH124 block — both can coexist since they use disjoint variable names and disjoint disks):

```yaml
student-01:
  ansible_host: 172.16.16.101
  exam_variant: alpha                     # shared with RH124 — same mapping
  rh134_vg_name: vg_alpha
  rh134_lv_name: lv_alpha
  rh134_lv_initial_size: 300M
  rh134_lv_extend_size: 500M
  rh134_mount_point: /storage/alpha
  rh134_rsyslog_facility: local0
  rh134_rsyslog_priority: warning
  rh134_log_file: /var/log/alpha-events
  rh134_nfs_export_dir: export-alpha
  rh134_nfs_local_mount: /remote/alpha
  rh134_podman_port: 8101
  rh134_podman_image_text: "alpha containerized webserver"
  rh134_backup_dir: backup-alpha
  rh134_script_name: collect-alpha.sh
  rh134_report_file: /home/student/reports/alpha-status.txt
```

All other RH134 exam values (service names to probe in T1, the planted long-running test pattern, container base image, NFS mount options, semaphore/anchor file names for grading) are identical across all students and defined as group variables — exactly as RH124 did with the repo URL, password policy numbers, and umask.

---

## 3. Exam Tasks

Six tasks, 100 points, ~90 minutes, difficulty Easy → Medium-Hard — same shape as RH124. Point split: **15 / 20 / 15 / 15 / 20 / 15** (T1 easiest/shortest, T2 and T5 are the two heaviest/most complex and get the most time and points).

### Task selection rationale

Of the candidate areas surveyed in `tmp/rh134-labs/`, these six were chosen because they (a) stay at or below the difficulty/step-count of their source labs, (b) carry zero risk of breaking the student's SSH session or the system's bootability, and (c) give good spread across storage, scripting, logging, networking-adjacent (NFS client only — no firewall/interface changes), and containers:

- **Included:** shell scripting (1.7), LVM (11.7), logging/journald+rsyslog (5.11, minus the timezone sub-step), NFS client/autofs (15.5), Podman (17.7/19.5), file transfer (8.5).
- **Deliberately excluded:**
  - **SELinux file contexts** (6.9) — while it appears in the labs, it requires audit-log forensics (`sealert`, `ausearch`, interpreting AVC denials) to *diagnose* the problem before fixing it. The labs scaffold this diagnosis step heavily; removing the scaffolding (as the exam must, per the "no example commands" rule) would push this well past the labs' assisted difficulty and risks turning it into a frustrating dead-end rather than a "low hanging fruit" scoring opportunity. Better to keep the easy task genuinely easy (shell scripting) and award those points reliably.
  - **SELinux booleans / firewall+SELinux for services** (14.5, 19.4) — directly conflicts with constraint #1 (no task that touches firewalld zones, port bindings, or could leave the box unreachable).
  - **Boot troubleshooting / default systemd target** (12.7, 19.2) — directly conflicts with constraint #1 (systemd target changes risk dropping network/SSH).
  - **Performance tuning / nice-renice** (9.5) — workable but its grading signal depends on a planted *running* process whose PID is unstable across reboots and re-grades; this adds provisioning fragility for a topic that doesn't add much variety beyond what T1 (scripting) and T4 (logging) already cover service-state/system-state checking. Cut for the sake of keeping six tasks tight and reliably gradeable.

### Task dependency note

Each task is fully independent — students can attempt them in any order, exactly like RH124 (where Ansible pre-provisioned the `dbteam` group to remove the T2→T3 dependency). Here, no task's grading or setup depends on another task's completion:
- T2 (LVM) needs only the raw `/dev/sdb` disk (provisioned by Terraform, untouched by any other task).
- T5 (NFS) needs only the repo VM's exports (provisioned independently of student VM state).
- T6 (Podman) needs only the registry/base image to be reachable (see §5 provisioning).

---

### Task 1 — Shell Scripting: Service Status Report (15 points, ~10 min)
**Difficulty:** Easy
**Topics:** bash scripting, for loops, variables, command substitution, redirection

**Student instructions:**

The team lead wants a quick script that reports the live status of a list of system services, so it can be run on demand without remembering each `systemctl` invocation by hand.

1. Create an executable script at `/home/student/bin/{{ rh134_script_name }}`. *(3 pts)*
2. The script must loop over the following service names: `{{ exam_service_list }}` (a fixed list of 4 services, identical for all students — e.g. `sshd crond chronyd rsyslog`). *(4 pts)*
3. For each service, the script must print one line in the exact format:
   `SERVICE: <name> ACTIVE: <active|inactive> ENABLED: <enabled|disabled>`
   using the live output of `systemctl is-active` and `systemctl is-enabled`. *(5 pts)*
4. Running the script must (over)write its output to `{{ rh134_report_file }}` — running it twice must not duplicate lines. *(3 pts)*

**Tip given to students:** use command substitution (`$(...)`) to capture the output of `systemctl is-active` / `is-enabled` into variables before formatting the line.

**Ansible provisioning needed:** None beyond ensuring `/home/student/bin` exists and the four named services are in their default (mixed) states so the script has real, varied data to report on — not all-active or all-inactive.

**Grading checks:**
| Check | Points | Method |
|---|---|---|
| Script exists and is executable | 3 | `test -x /home/student/bin/{{ rh134_script_name }}` |
| Script references all 4 service names | 4 | grep script source for each name (loose check — confirms the loop targets the right list) |
| Running the script produces 4 correctly-formatted lines | 5 | run script, parse stdout/output file with regex matching the required format, cross-check `ACTIVE`/`ENABLED` fields against live `systemctl is-active`/`is-enabled` for each service |
| Output file is overwritten (not appended) on rerun | 3 | run script twice, confirm line count stays at 4 |

---

### Task 2 — LVM: Build, Mount, and Extend Storage (20 points, ~20 min)
**Difficulty:** Medium
**Topics:** parted, pvcreate, vgcreate, lvcreate, mkfs.xfs, /etc/fstab, lvextend, xfs_growfs

**Student instructions:**

A new raw disk has been attached to your system (`/dev/sdb`, completely empty). The team needs it turned into a persistently-mounted LVM volume — and then the team realizes the initial size estimate was too small, so it must be grown without losing data.

1. Partition `/dev/sdb` for LVM use (one partition, LVM flag set), then create a physical volume on it and a volume group named `{{ rh134_vg_name }}`. *(4 pts)*
2. Create a logical volume named `{{ rh134_lv_name }}` of size `{{ rh134_lv_initial_size }}` in that volume group, format it XFS, and mount it persistently at `{{ rh134_mount_point }}` (must survive a reboot). *(7 pts)*
3. Create a file at `{{ rh134_mount_point }}/marker.txt` containing the text `{{ exam_variant }} volume ready`. *(2 pts)*
4. Extend the logical volume by `{{ rh134_lv_extend_size }}` and grow the XFS filesystem to use the new space — without unmounting or losing the marker file. *(7 pts)*

**Tip given to students:** `parted ... unit MiB print` shows sizes in a more LVM-friendly unit than the default. After `lvextend`, the filesystem itself needs a separate command to recognize the new space.

**Ansible provisioning needed:**
- Second raw disk `/dev/sdb` (1 GB, completely unpartitioned) attached to each student VM — Terraform resource (see §6).
- Write a provisioning timestamp marker so the grading script can detect a reboot occurred (reuses the same `/var/exam-provision-time` mechanism RH124's T4/T6 used).

**Grading checks:**
| Check | Points | Method |
|---|---|---|
| VG `{{ rh134_vg_name }}` exists on a PV from `/dev/sdb` | 4 | `vgs {{ rh134_vg_name }}` exits 0 and `pvs` shows a PV under `/dev/sdb*` belonging to it |
| LV `{{ rh134_lv_name }}` exists, XFS-formatted, mounted at `{{ rh134_mount_point }}` | 4 | `lvs`, `blkid` (TYPE=xfs), `findmnt {{ rh134_mount_point }}` |
| Mount entry present in `/etc/fstab` and survives reboot | 3 | `grep {{ rh134_mount_point }} /etc/fstab`; `findmnt` after reboot (paired with the same single end-of-exam reboot used by other tasks, see note below) |
| marker.txt contains exact expected text | 2 | `grep -Fx '{{ exam_variant }} volume ready' {{ rh134_mount_point }}/marker.txt` |
| LV size reflects the extension | 4 | `lvs -o lv_size --noheadings {{ rh134_vg_name }}/{{ rh134_lv_name }}` ≥ initial + extend size (with tolerance for rounding) |
| Filesystem size reflects the growth (not just the LV) | 3 | `df -h {{ rh134_mount_point }}` reports usable size consistent with extended LV, not the original |

**Note on reboot:** Like RH124's T4/T6, this task's persistence checks are validated against live state after a single end-of-exam reboot. The task sheet and portal both state once, prominently: *"Several tasks in this exam check that your changes survive a reboot. Reboot once, near the end of your session, after completing all tasks: `sudo systemctl reboot`."* This avoids the cost of multiple reboots eating into the 90-minute window.

---

### Task 3 — Persistent Logging: journald + rsyslog Routing (15 points, ~12 min)
**Difficulty:** Easy-Medium
**Topics:** systemd-journald persistent storage, rsyslog facility.priority routing, logger

**Student instructions:**

The operations team wants two logging improvements: journal entries must survive reboots (currently they're volatile), and messages of a specific severity from a specific subsystem must be routed to their own dedicated file for faster triage.

1. Configure `systemd-journald` so that journal entries are stored persistently on disk (must survive a reboot). *(5 pts)*
2. Create an rsyslog configuration file that routes all messages matching facility `{{ rh134_rsyslog_facility }}` at priority `{{ rh134_rsyslog_priority }}` (and higher) to the file `{{ rh134_log_file }}`. *(6 pts)*
3. Generate a test message using `logger` with the matching facility and priority, and confirm it appears in `{{ rh134_log_file }}`. *(4 pts)*

**Tip given to students:** persistent journald storage requires a specific directory to exist before the service is restarted — check the `journalctl` man page or `man systemd-journald` for where that directory lives. Rsyslog routing rules use the syntax `facility.priority    /path/to/file`. A routing rule only takes effect while the service that applies it is actually running — and "is it running, and will it still be after a reboot?" is exactly the kind of question Task 1 just had you check for this very service.

**Ansible provisioning needed:**
- Ensure `/var/log/journal` does **not** already exist (so the student must create it — otherwise the check is trivially already-true).
- No rsyslog-specific setup here — T1's baseline provisioning (see Task 1) deliberately
  leaves `rsyslog` **inactive and disabled**. This is *not* an oversight to "fix" before T3:
  it's an intentional extra wrinkle the student must reason through — their routing rule in
  `/etc/rsyslog.d/` does nothing until the service is actually running, and it won't survive
  the end-of-exam reboot unless it's also enabled. T1's own report should have already shown
  them `rsyslog: ACTIVE: inactive ENABLED: disabled`; connecting that observation to T3's
  requirement (`sudo systemctl enable --now rsyslog`) is part of the task.
  *(Earlier drafts of this note said "ensure rsyslog is in its default running/enabled state
  — no special setup needed," which directly contradicted T1's baseline and was never true on
  this image: AlmaLinux 10's cloud-init build ships rsyslog inactive+disabled regardless, and
  cloud-init explicitly skips its rsyslog module. Confirmed live via a full provision + dry run.)*
- Write the provisioning timestamp marker (shared with T2's reboot-detection mechanism).

**Grading checks:**
| Check | Points | Method |
|---|---|---|
| `/var/log/journal/<machine-id>/` exists with rotated journal files | 3 | `test -d /var/log/journal/$(cat /etc/machine-id)` and non-empty |
| Persistent storage survives reboot (journal dir populated post-reboot) | 2 | re-check the above after the single end-of-exam reboot |
| Rsyslog config file exists under `/etc/rsyslog.d/` | 2 | `test -f` (any filename — check content, not name) |
| Config routes the correct facility.priority to the correct file | 4 | grep config for a line matching `{{ rh134_rsyslog_facility }}.{{ rh134_rsyslog_priority }}` and `{{ rh134_log_file }}` (tolerant of whitespace/ordering) |
| Test message appears in the target log file | 4 | grading script runs its own `logger -p {{ rh134_rsyslog_facility }}.{{ rh134_rsyslog_priority }} "grading-probe-{{ exam_variant }}"` and checks `{{ rh134_log_file }}` for that exact string |

---

### Task 4 — File Transfer: rsync Backup and Secure Upload (15 points, ~10 min)
**Difficulty:** Easy
**Topics:** rsync (archive mode), scp/sftp

**Student instructions:**

Before any risky changes, the team always backs up configuration directories and securely ships specific files off-box.

1. Use `rsync` in archive mode to copy the entire `/etc/exam-source/` directory (provided on your system) to a new local directory `/home/student/{{ rh134_backup_dir }}/`, preserving permissions, ownership, and timestamps. *(6 pts)*
2. Securely copy the file `/home/student/{{ rh134_backup_dir }}/exam-source/manifest.txt` to the path `/home/student/uploaded-{{ exam_variant }}.txt` **on the repo VM** (`172.16.16.121`), authenticating as the `student` user over SSH/SCP/SFTP. *(9 pts)*

**Tip given to students:** `rsync -a <source>/ <destination>/` mirrors a directory tree including permissions and ownership. `scp` and `sftp` both move files over SSH — either is acceptable.

**Ansible provisioning needed:**
- Plant `/etc/exam-source/` on each student VM: a small directory tree (a few files and a subdirectory) with **non-default, distinguishable permissions/ownership** (e.g. one file `640 root:root`, one `750`, one owned by a planted non-root user) — so the grading check can verify that `-a` (archive mode) actually preserved them, not just that files were copied.
- Plant `manifest.txt` inside that tree with known, fixed content (identical across students — its content isn't a variation point, only its destination path is).
- Create a `student` OS account on the repo VM with password authentication enabled (mirrors how the repo VM already serves student-facing HTTP — this adds a student-facing SSH/SCP target). Pre-create `/home/student/` with correct ownership so uploads land predictably.
- The repo VM's SSH host key must be in a known/predictable state (or students pre-warned to accept it) — same `ssh-keygen -R` consideration noted in the workflow for student VM IPs, but in reverse: this is the *first* time students SSH to the repo VM, so no stale-key issue, but the task sheet should mention they'll see a host key prompt.

**Grading checks:**
| Check | Points | Method |
|---|---|---|
| `/home/student/{{ rh134_backup_dir }}/exam-source/` exists and contains all source files | 2 | recursive file-list comparison |
| File contents match exactly | 1 | checksum comparison against planted source |
| Permissions and ownership preserved on at least the two distinguishing files | 3 | `stat -c '%a %U:%G'` comparison against planted values |
| `manifest.txt` present at the correct path on the repo VM | 5 | instructor-side check (Ansible task targets the repo VM, not the student VM, for this one sub-check — see note below) | 
| Uploaded file content matches the original manifest exactly | 4 | checksum comparison, instructor-side, against the repo VM copy |

**Note on cross-host grading:** this is the first RH134 task whose grading requires checking state on a *different* host than the one being graded (the repo VM, not the student's VM). `exam-grade.yml` needs an extra play (or a delegated task with `delegate_to: repo_vm`) that, for this task only, inspects `/home/student/uploaded-{{ exam_variant }}.txt` on 172.16.16.121 once per student. This is a small but real addition to the grading playbook's structure — flagged here for the grading-session implementer (see §8, Session "Grading").

---

### Task 5 — NFS Client: Automount Your Shared Export (20 points, ~18 min)
**Difficulty:** Medium-Hard
**Topics:** autofs (master + indirect maps), NFS mount options, multi-host verification

**Student instructions:**

The repo server (`172.16.16.121`) now also serves each student a personal NFS export for exchanging files with the instructor. Configure your system to automatically mount your export on demand.

1. Install and enable the `autofs` service. *(2 pts)*
2. Configure an indirect automount map so that accessing `{{ rh134_nfs_local_mount }}` automatically mounts your export `172.16.16.121:/exports/{{ rh134_nfs_export_dir }}` with read-write, synchronous NFSv4 options. *(10 pts)*
3. Trigger the automount (e.g. by listing the directory) and confirm you can read the file `welcome.txt` that's already there. *(3 pts)*
4. Create a new file inside your mounted export named `{{ exam_variant }}-submitted.txt` containing the text `submission from {{ exam_variant }}`, proving the mount is writable. *(5 pts)*

**Tip given to students:** autofs uses two files working together — a master map that says *where* to mount things, and an indirect map that says *what* to mount and *how*. The wildcard `&` in an indirect map substitutes the requested key into the source path.

**Ansible provisioning needed (on the repo VM — see §1.2 and §5):**
- Install and configure `nfs-utils`; create `/exports/{{ rh134_nfs_export_dir }}` for all 20 students with an `/etc/exports` entry scoped to each student VM's IP only (e.g. `/exports/export-alpha 172.16.16.101(rw,sync,no_root_squash)`) — this both isolates students from each other's exports and avoids any shared-permission collision (mirrors 15.5_lab.md's per-group export isolation, adapted to per-student).
- Plant `welcome.txt` (fixed content, identical across all exports) in each export directory as a read-verification anchor.
- Ensure each export directory is owned/permissioned so the `student`-equivalent NFS client UID can write to it (the labs use `no_root_squash` + open group perms for this — adapt to single-student-per-export so no UID-mapping complexity is needed).

**Grading checks:**
| Check | Points | Method |
|---|---|---|
| `autofs` is active and enabled | 2 | `systemctl is-active autofs` / `is-enabled` |
| Master map references the correct mount point and indirect map file | 3 | grep `/etc/auto.master.d/*.autofs` (or `/etc/auto.master`) for `{{ rh134_nfs_local_mount }}` |
| Indirect map references the correct export path with rw,sync,nfs4 options | 7 | grep the referenced indirect map file for `172.16.16.121:/exports/{{ rh134_nfs_export_dir }}` and required mount options |
| Mount activates and `welcome.txt` is readable through it | 3 | `ls {{ rh134_nfs_local_mount }}` (triggers automount), `findmnt`, then read+compare `welcome.txt` content |
| Submitted file appears **on the repo VM's export directory** with correct content | 5 | instructor-side check (delegated to repo VM, same cross-host pattern as T4) — confirms the mount was genuinely writable, not just browsable |

---

### Task 6 — Containers: Build, Run, and Persist a Custom Web Server (15 points, ~15 min)
**Difficulty:** Medium-Hard
**Topics:** Containerfile authoring, podman build/run, port mapping, systemd unit generation for persistence

**Student instructions:**

The dev team needs a small custom web server container running and accessible — and it must keep running after you log out (containers do not survive your SSH session ending unless you make them persistent).

1. Create a Containerfile in `/home/student/webapp/` that starts from the provided base image `{{ rh134_base_image }}` and writes the exact text `{{ rh134_podman_image_text }}` as the content of `/var/www/html/index.html`. *(4 pts)*
2. Build and tag the image as `{{ exam_variant }}-web:1.0`. *(2 pts)*
3. Run the image as a detached container named `{{ exam_variant }}-srv`, mapping host port `{{ rh134_podman_port }}` to the container's port 8080. Confirm `curl localhost:{{ rh134_podman_port }}` returns the expected text. *(4 pts)*
4. Make the container **persist across logout and reboot** using a generated systemd unit (`podman generate systemd` or Quadlet — either is acceptable), enabled for your user. *(5 pts)*

**Tip given to students:** a container created with `podman run` disappears when your session ends unless something tells systemd to manage it. `podman generate systemd --new --files --name <container>` produces a unit file you can install and enable.

**Ansible provisioning needed:**
- Pre-pull `{{ rh134_base_image }}` (the same httpd-based image used in the labs) onto each student VM so the build step doesn't depend on internet/registry access during the exam — mirrors RH124's repo-VM approach to removing internet dependency, applied here to container images instead of RPMs.
- Ensure `podman` and `slirp4netns`/`fuse-overlayfs` (rootless container prerequisites) are present and the `student` user can run rootless containers (`loginctl enable-linger student` so user-level systemd units survive logout — this is the actual mechanism that makes step 4 gradeable without the student staying logged in).
- Write the provisioning timestamp marker (shared reboot-detection, confirms persistence survived the single end-of-exam reboot).

**Grading checks:**
| Check | Points | Method |
|---|---|---|
| Containerfile exists and references the correct base image + writes the correct text | 4 | inspect `/home/student/webapp/Containerfile` content (grep for FROM line and echo/RUN line) |
| Image built and tagged correctly | 2 | `podman images --format '{{.Repository}}:{{.Tag}}'` contains `localhost/{{ exam_variant }}-web:1.0` (or equivalent) |
| Container running, correctly named, correctly mapped, and serving expected content | 4 | `podman ps` shows the named container with the correct port mapping; `curl localhost:{{ rh134_podman_port }}` returns `{{ rh134_podman_image_text }}` |
| Container survives logout/reboot via a systemd unit | 5 | check for a generated/enabled systemd (user or system) unit referencing the container; **re-verify `curl` succeeds after the single end-of-exam reboot** — this is the strongest signal that persistence actually works, not just that a unit file exists |

---

## 4. Grading Tools

Reuses the RH124 pipeline end to end — **only the per-task check logic and rendered values differ**. No redesign of the tools themselves.

### 4.1 Student-side grading script

**Path:** `/usr/local/bin/grade`
**Permissions:** `755`
**Generated by:** Ansible from a Jinja2 template (`grade.sh.j2`), with RH134 per-student values baked in.

Identical interface to RH124 (`grade`, `grade all`, `grade t1`...`grade t6`), identical report format and TOTAL line. The only RH134-specific design point: **Tasks 4 and 5 each have one sub-check that depends on state on the repo VM, not the local VM.** The student-side script cannot reach into the repo VM's filesystem directly — so for those two sub-checks, the student script either:
- (a) checks only the *local* half (e.g., "file was uploaded without error" / "write to the mount succeeded locally"), and clearly notes in its output that the cross-host portion is verified by the instructor only, or
- (b) if the repo VM exposes a small read-only status endpoint or shared-readable directory, the student script can verify its own submission landed (e.g., `ssh student@172.16.16.121 'test -f ...'` using the same SSH credentials the task requires them to set up — this doubles as a "did you actually do it right" signal).

**Recommendation: option (b)** — it gives students genuine self-check feedback (matching the spirit of "students may run `grade` at any time and trust the result"), and costs nothing extra to provision since the credentials already exist for the task itself. This should be confirmed/refined during the grading-script implementation session.

### 4.2 Student-side hint script

**Path:** `/usr/local/bin/hint`, permissions `755`, identical mechanism to RH124 — static directional text per task, no commands.

**Example for T5 (NFS):**
```
Task 5 — Hint:
  Two configuration files work together to make a directory mount itself the
  first time something tries to access it: one says where the mountpoint lives
  and which map file to consult, the other says what to mount there and which
  options to use. A special character in the map file lets one line handle a
  whole family of similar mounts. Persistent, write-friendly NFSv4 mounts use
  a specific combination of options you've seen demonstrated before.
```

### 4.3 Instructor-side Ansible grading playbook

`exam-grade.yml` — same per-host JSON output format as RH124:

```json
{
  "host": "student-01",
  "variant": "alpha",
  "tasks": {
    "t1": {"score": 12, "max": 15, "checks": [...]},
    "t2": {"score": 20, "max": 20, "checks": [...]},
    ...
  },
  "total": 84
}
```

**RH134-specific addition:** two tasks (T4, T5) require a play (or delegated tasks) that inspects the **repo VM** rather than (or in addition to) the student VM. This is a structural first for the grading playbook — RH124's grading never needed to look anywhere but the student's own VM. Implementation approach: add a `hosts: repo_vm` play (or `delegate_to`) that, for each of the 20 students, checks for their expected uploaded/submitted file and folds that result into the same per-student JSON the rest of the playbook produces. This needs explicit design attention in the grading session (see §8).

### 4.4 Exam task portal (web)

Identical mechanism to RH124 — single static HTML page at `http://172.16.16.121/exam`, all 20 variants embedded as a JS object, rendered client-side from the student's number. **The portal itself is one of the things now hosted on the same VM that also serves the new NFS exports** — worth noting only because it reinforces why that VM's health-check needs to cover all three roles before the exam starts (see §5).

Each task's portal entry includes the same content shape as RH124: title, points, estimated time, fully-substituted instructions (no Jinja2 syntax visible), and a Tips section mirroring the hint script.

### 4.5 Instructor report Python script

`scripts/exam-report.py` — **no changes needed.** It already reads per-host JSON and produces CSV/HTML/merged-retake reports; RH134 JSON has the same shape (just different task keys/values), so the existing script works unmodified. This is a strong argument for keeping the JSON schema identical across exams (see §7).

---

## 5. Ansible Provisioning Role — Requirements

### 5.1 Student VM provisioning (`exam-provision` role, RH134 variant)

| # | Action | Notes |
|---|---|---|
| 1 | Read per-host vars from inventory | `rh134_vg_name`, `rh134_lv_name`, `rh134_nfs_export_dir`, etc. |
| 2 | Ensure `/home/student/bin/` exists | Target dir for T1's script |
| 3 | Set the 4 baseline services (T1) to mixed active/enabled states | So the script has real varied data — not a trivial all-same report |
| 4 | Confirm `/dev/sdb` is raw/unpartitioned | Terraform attaches it; Ansible must NOT partition or format it (that's the student's job in T2) |
| 5 | Ensure `/var/log/journal` does **not** pre-exist | T3 requires the student to create it — pre-creating it would make the check trivially true |
| 6 | Plant `/etc/exam-source/` tree with distinguishable permissions/ownership | T4 grading anchor — needs at least 2 files with different, non-default perms/owners |
| 7 | Pre-pull `{{ rh134_base_image }}` container image | T6 — removes registry dependency during the exam window |
| 8 | Ensure rootless Podman prerequisites + `loginctl enable-linger student` | T6 — makes "survives logout" actually achievable and gradeable |
| 9 | Write `/var/exam-provision-time` | Shared reboot-detection marker for T2/T3/T6 |
| 10 | Render task sheet from Jinja2 template | `/home/student/exam-tasks.txt`, fallback if portal is unreachable |
| 11 | Render `grade` script from Jinja2 template | `/usr/local/bin/grade`, chmod 755 |
| 12 | Render `hint` script from Jinja2 template | `/usr/local/bin/hint`, chmod 755 |
| 13 | Generate or verify SSH credentials for the repo VM | T4/T5 require the student to authenticate to 172.16.16.121 — confirm the `student` OS account + auth method exists there (see repo VM provisioning below); no special setup needed on the *student* VM side beyond ensuring outbound SSH works |

### 5.2 Repo VM provisioning (extends the existing RH124 repo VM playbook)

| # | Action | Notes |
|---|---|---|
| 1 | Install `nfs-utils`; enable and start `nfs-server` | New role for this VM |
| 2 | Create `/exports/{{ rh134_nfs_export_dir }}/` for all 20 students | One directory per student, scoped `/etc/exports` entry per directory restricted to that student's VM IP |
| 3 | Plant identical `welcome.txt` in each export | Read-verification anchor for T5 |
| 4 | Set ownership/permissions on each export so the client can write | Mirrors lab pattern (`no_root_squash` + appropriate perms), simplified since each export is single-tenant |
| 5 | Run `exportfs -ra`; verify with `showmount -e` | Standard NFS-server activation/verification step |
| 6 | Create/confirm the `student` OS account with password (or key) auth | New for RH134 — required by T4 (upload target) and optionally T5's self-check (§4.1) |
| 7 | Render the **combined** RH124+RH134 exam portal HTML | If both exams' portals are to coexist on this VM, the portal templating needs a course selector or separate URLs (e.g. `/exam/rh124`, `/exam/rh134`) — flagged as a design decision for the provisioning session (§8) |
| 8 | **Pre-flight health check** | Extends RH124's existing repo-VM check: confirm DNF repo reachable, portal reachable, **and** `showmount -e localhost` lists all 20 exports, **and** SSH/student-account login works — all four must pass before any student VM exam begins |

### 5.3 Reset playbook

A `exam-reset.yml` (RH134 variant) must be able to undo everything above — including, notably:
- Removing any LVs/VGs/PVs the student created on `/dev/sdb` and wiping it back to raw (so a retake starts from the same blank-slate state)
- Removing generated systemd units / lingering Podman containers
- Clearing `/var/log/journal` if it was created
- On the repo VM: clearing each student's export directory back to just `welcome.txt`, removing any uploaded/submitted files

This mirrors RH124's reset requirement and is essential for retake support and for any future combined-exam reuse.

---

## 6. Terraform Requirements (new, to be implemented)

**Single new resource type:** a second, independent disk attached to each student VM, used only for RH134 exams.

| Property | Value |
|---|---|
| Size | 1 GB |
| Storage pool | `local-lvm` (same as RH124's second disk and the primary) |
| Interface | `scsi2` (RH124's second disk uses `virtio0` — a different bus entirely — so `scsi2` simply needs to not collide with the OS disk's `scsi0`) |
| Filesystem | **None** — left completely raw; the student creates everything from `parted` onward |
| Partition | **None** — created by the student during the exam (T2 step 1) |

**Both disk definitions live in the same `main.tf`, unconditionally attached:** RH124 and RH134 exams are never run concurrently on the same VMs, so there's no runtime conflict — both `disk` blocks (RH124's `virtio0` → `/dev/vda`, RH134's `scsi2` → `/dev/sdb`) simply coexist as static resources on the shared `student` VM definition, attached to every student VM regardless of which exam is currently running. No per-exam toggling or scoping is needed.

**Note on the in-guest device path:** this disk appears as `/dev/sdb`, not `/dev/sdc` as originally assumed in earlier drafts of this section. With no `scsi1` disk defined, Linux assigns `sd*` letters in probe order across SCSI-bus disks only — `scsi0` (OS) → `/dev/sda`, `scsi2` (this disk) → `/dev/sdb` (the next available letter; the gap at `scsi1` doesn't reserve `sdb` for anything). `virtio0` (RH124's disk) is a separate bus with its own `vd*` namespace (`/dev/vda`) and doesn't factor into `sd*` enumeration at all. Confirmed live on `student-01` during first provisioning — all references to `/dev/sdc` elsewhere in this document have been corrected to `/dev/sdb`.

No changes to the base student VM resource (CPU/RAM/primary disk) or to the repo VM's Terraform definition (NFS is an Ansible-level service addition, not a Terraform-level VM change).

---

## 7. File/Directory Layout (planned — restructure recommended)

With a second exam now designed, the flat layout RH124 used (`docs/exam-rh124-design.md`, `ansible/exam-provision.yml`, etc. all at top level) doesn't scale cleanly to "many exams, possibly combined." Recommended restructure:

```
vuv-operacijski-iac/
├── docs/
│   ├── rh124/
│   │   └── exam-rh124-design.md
│   └── rh134/
│       └── exam-rh134-design.md        # this document
├── ansible/
│   ├── ansible.cfg
│   ├── inventory.yml                    # shared — carries BOTH rh124_* and rh134_* host vars per student
│   ├── roles/
│   │   ├── exam-provision-rh124/        # RH124-specific provisioning tasks/templates
│   │   ├── exam-provision-rh134/        # RH134-specific provisioning tasks/templates
│   │   ├── exam-provision-repo-vm/      # shared — DNF repo + portal + (new) NFS exports
│   │   └── exam-grade-common/           # shared grading helpers if any checks overlap (e.g. service-state checks)
│   ├── rh124/
│   │   ├── exam-provision.yml
│   │   ├── exam-grade.yml
│   │   └── exam-reset.yml
│   ├── rh134/
│   │   ├── exam-provision.yml
│   │   ├── exam-grade.yml
│   │   └── exam-reset.yml
│   └── exam-results/
│       ├── rh124/
│       └── rh134/
├── scripts/
│   └── exam-report.py                   # shared — already course-agnostic (reads JSON, writes CSV/HTML)
└── terraform/
    └── main.tf                          # see §6 — needs a way to scope per-exam disk resources
```

**Reasoning:**
- **`docs/<course>/` and `ansible/<course>/`** keep each exam's playbooks and design docs discoverable and independently versionable, while **`ansible/roles/`** stays a shared pool — this is exactly the split the prompt asked about, and it directly serves the stated future goal: a combined RH124+RH134 comprehensive exam can `import_playbook` or reuse roles from both course directories without duplicating role code.
- **One shared `inventory.yml`** (rather than per-course inventories) keeps the "20 students, alpha–tango" mapping as a single source of truth — each host simply carries both `rh124_*` and `rh134_*` variable blocks (as shown in §2.2), and a given playbook run only references the block it needs.
- **`scripts/exam-report.py` stays shared and untouched** — it's already course-agnostic by design (operates purely on JSON shape), which validates RH124's original choice to keep course-specific values out of the report tooling. RH134 should follow the same discipline: keep the *JSON schema* identical, vary only the *content*.
- **`exam-results/<course>/`** keeps gitignored grading output cleanly separated, mirroring how `archive/` already uses `<course>-<year>-<month>` naming.

This restructure is a small amount of `git mv` work relative to the value of not having two exams' files interleaved at the top level of `ansible/` and `docs/` — recommended to do **before** RH134 implementation begins, not after.

---

## 8. Open Items by Session

### Session 2 — Infrastructure + Provisioning
- [ ] **Decide and implement the Terraform disk-scoping mechanism** (§6) — how RH124's `scsi1` disk and RH134's `scsi2` disk coexist without both being unconditionally attached to every VM (variable-gated resource? per-exam workspace? conditional `count`?)
- [ ] Carry out the `docs/`/`ansible/` restructure proposed in §7 (do this first — it's foundational for everything else)
- [ ] Add the RH134 disk resource to Terraform (raw 1 GB, `scsi2`, `/dev/sdb`)
- [ ] Update `ansible/inventory.yml` with all `rh134_*` per-host variables (see §2.2 table)
- [ ] Implement `ansible/roles/exam-provision-rh134/` with all tasks from §5.1
- [ ] Extend the repo VM role to add NFS export provisioning (§5.2) — install `nfs-utils`, create per-student exports, plant anchors, configure `/etc/exports`
- [ ] Decide how the portal hosts both RH124 and RH134 variant sets (separate URLs vs. course selector — flagged in §5.2 item 7)
- [ ] Create/confirm the `student` OS account + auth method on the repo VM (needed by T4 and T5)
- [ ] Write Jinja2 templates: `exam-tasks.txt.j2`, `grade.sh.j2`, `hint.sh.j2` for RH134
- [ ] Write `ansible/rh134/exam-provision.yml` and `exam-reset.yml`
- [ ] Extend the repo-VM pre-flight check to cover NFS health (`showmount -e`) and SSH/account login, alongside the existing DNF/portal checks
- [ ] Test full provisioning cycle on student-01 — including the cross-host pieces (T4 upload, T5 mount) against the repo VM

### Session 3 — Grading (after exam dry-run or real exam)
- [ ] Refine `grade.sh.j2` based on observed student behaviour
- [ ] **Design and implement the cross-host grading mechanism** for T4 and T5 (§4.3) — a `delegate_to`/`hosts: repo_vm` play that folds repo-VM-side checks into each student's per-host JSON
- [ ] Decide whether the student-side `grade` script attempts a self-check of the cross-host pieces (§4.1, option (a) vs (b)) and implement accordingly
- [ ] Write `ansible/rh134/exam-grade.yml`

### Session 4 — Reporting
- [ ] Confirm `scripts/exam-report.py` runs unmodified against RH134 JSON output (expected — schema is identical; this is a verification step, not new development)
- [ ] Test full grading → report pipeline end to end, including the cross-host checks
- [ ] Add `rh134-<year>-<month>` archive naming convention entries to `CLAUDE.md` (mirrors the existing `rh124-*` convention)
