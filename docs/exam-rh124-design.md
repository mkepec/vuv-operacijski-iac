# RH124 Mid-Semester Performance Exam — Design Requirements

**Course:** Red Hat System Administration I (RH124 10.0)  
**Institution:** Virovitica University of Applied Sciences (VUV)  
**Instructor:** Marin Kepec  
**Exam type:** Performance-based practical exam  
**Duration:** 90 minutes  
**Total points:** 100  

---

## 1. Infrastructure Requirements

### 1.1 Student VMs (existing)

20 AlmaLinux 10 VMs provisioned via Terraform on Proxmox, VM IDs 200–219, IPs 172.16.16.101–120. See `CLAUDE.md` for full spec.

### 1.2 Repo VM (new)

A 21st VM to serve as a local DNF package repository for all student VMs during the exam. Students must not depend on internet access.

| Property | Value |
|---|---|
| VM ID | 221 |
| IP | 172.16.16.121 |
| OS | AlmaLinux 10 |
| Role | HTTP package repository server |
| URL students use | `http://172.16.16.121/repo` |
| Packages to serve | `tree`, `wget`, `zip`, `unzip`, `bc`, `screen`, `dos2unix`, `words`, `lsof`, `pinfo`, `vim-enhanced` |
| Setup | Apache/nginx serving a local DNF repo created with `createrepo` |

This VM must be running before any student VM exam begins. Ansible provisioning of the repo VM is a separate playbook.

### 1.3 Extra disk per student VM (new Terraform requirement)

Each student VM needs a second block device for Task 6 (mount task).

| Property | Value |
|---|---|
| Size | 2 GB |
| Device path | `/dev/sdb` |
| Partition | One partition: `/dev/sdb1` |
| Filesystem | XFS (pre-formatted) |
| Mount state | **Not mounted** at exam start |

This is a Terraform resource requirement. Add a second `disk` block to the student VM resource in `terraform/main.tf`.

---

## 2. Per-Student Variation

To prevent copy-paste between neighboring students, each VM has a unique variant. Variation is implemented via Ansible inventory host variables — values are baked into the rendered task sheet and grading script at provisioning time.

### 2.1 Variant assignment (NATO phonetic alphabet)

| Student | Variant | GID | Expiry | Extra package |
|---|---|---|---|---|
| student-01 | alpha | 40001 | 2026-11-30 | tree |
| student-02 | bravo | 40002 | 2026-12-31 | wget |
| student-03 | charlie | 40003 | 2027-01-31 | zip |
| student-04 | delta | 40004 | 2027-02-28 | unzip |
| student-05 | echo | 40005 | 2027-03-31 | bc |
| student-06 | foxtrot | 40006 | 2027-04-30 | screen |
| student-07 | golf | 40007 | 2027-05-31 | dos2unix |
| student-08 | hotel | 40008 | 2027-06-30 | words |
| student-09 | india | 40009 | 2027-07-31 | lsof |
| student-10 | juliet | 40010 | 2027-08-31 | pinfo |
| student-11 | kilo | 40011 | 2026-11-30 | tree |
| student-12 | lima | 40012 | 2026-12-31 | wget |
| student-13 | mike | 40013 | 2027-01-31 | zip |
| student-14 | november | 40014 | 2027-02-28 | unzip |
| student-15 | oscar | 40015 | 2027-03-31 | bc |
| student-16 | papa | 40016 | 2027-04-30 | screen |
| student-17 | quebec | 40017 | 2027-05-31 | dos2unix |
| student-18 | romeo | 40018 | 2027-06-30 | words |
| student-19 | sierra | 40019 | 2027-07-31 | lsof |
| student-20 | tango | 40020 | 2027-08-31 | pinfo |

Students 11–20 reuse packages from 01–10. They are not seated next to their pair.

### 2.2 Variables per host (Ansible inventory)

Each host entry in `ansible/inventory.yml` carries:

```yaml
student-01:
  ansible_host: 172.16.16.101
  exam_variant: alpha
  exam_dir: exam-alpha
  exam_username: dbadmin1
  exam_gid: 40001
  exam_expiry: "2026-11-30"
  exam_workspace: dbteam-workspace-alpha
  exam_mount: /mnt/exam-disk-alpha
  exam_mount_text: "alpha disk mounted"
  exam_extra_package: tree
```

All other exam values (service names, find criteria, umask, password policy numbers, repo URL) are identical across all students and defined as group variables.

---

## 3. Exam Tasks

### Task dependency note

Tasks 2 and 3 both reference the `dbteam` group. To remove this dependency and allow students to attempt tasks in any order, Ansible **pre-provisions the `dbteam` group** on each VM with the correct GID before the exam. Task 2 is about creating the user and password policy; Task 3 is about the collaborative directory. Neither blocks the other.

---

### Task 1 — File and Directory Management (15 points, ~12 min)
**Difficulty:** Easy  
**Topics:** mkdir, touch, cp, tail, ln (hard and soft)

**Student instructions:**

You are organizing project files for the university IT department.

1. Create the directory `/home/student/projects/{{ exam_dir }}` with all intermediate directories. *(2 pts)*
2. Inside that directory, create three empty files: `report.txt`, `backup.txt`, `notes.txt`. *(2 pts)*
3. Copy `/etc/hostname` to `/home/student/projects/{{ exam_dir }}/hostname.txt`. *(2 pts)*
4. Append the last 5 lines of `/etc/passwd` to `/home/student/projects/{{ exam_dir }}/report.txt`. *(3 pts)*
5. Create a hard link to `report.txt` at the path `/home/student/projects/report-link-{{ exam_variant }}`. *(3 pts)*
6. Create a symbolic link to `/home/student/projects/{{ exam_dir }}` at the path `/home/student/exam-shortcut`. *(3 pts)*

**Ansible provisioning needed:** None. Clean VM is sufficient.

**Grading checks:**
| Check | Points | Method |
|---|---|---|
| Directory exists | 2 | `test -d /home/student/projects/{{ exam_dir }}` |
| All 3 files exist | 2 | `test -f` for each |
| hostname.txt matches /etc/hostname | 2 | `diff` |
| report.txt contains last 5 lines of /etc/passwd | 3 | `tail -5 /etc/passwd` and compare to file content |
| Hard link exists with link count ≥ 2 | 3 | `stat -c %h` on report.txt == 2 |
| Symbolic link exists and resolves correctly | 3 | `test -L` and `readlink -f` |

---

### Task 2 — User, Group, and Password Policy (20 points, ~15 min)
**Difficulty:** Easy-Medium  
**Topics:** groupadd, useradd, passwd, chage, sudoers

**Student instructions:**

You are provisioning accounts for a new team of database administrators.

1. Create a group named `dbteam` with GID `{{ exam_gid }}`. *(3 pts)*
2. Create a user named `{{ exam_username }}` with:
   - `dbteam` as a supplementary group *(2 pts)*
   - Initial password: `Welcome1` *(2 pts)*
   - Password must be changed on first login *(3 pts)*
3. Set the following password policy for `{{ exam_username }}`: *(6 pts — 2 each)*
   - Minimum days between password changes: `7`
   - Maximum days before password change is required: `60`
   - Account expiry date: `{{ exam_expiry }}`
4. Allow `{{ exam_username }}` to run any command with `sudo` without a password prompt. Use a dedicated file in `/etc/sudoers.d/`. *(4 pts)*

**Note:** The `dbteam` group already exists on your system — do not delete and recreate it, just confirm the GID matches and proceed.

**Ansible provisioning needed:**
- Pre-create `dbteam` group with correct `exam_gid` per host (breaks T2/T3 dependency).

**Grading checks:**
| Check | Points | Method |
|---|---|---|
| dbteam group exists with correct GID | 3 | `getent group dbteam \| grep ':{{ exam_gid }}:'` |
| User exists and is in dbteam | 2 | `id {{ exam_username }} \| grep dbteam` |
| Password is set (account not locked) | 2 | `passwd -S {{ exam_username }} \| grep -v LK` |
| Force change on first login | 3 | `chage -l {{ exam_username }} \| grep 'Last password change.*password must be changed'` |
| Min days == 7 | 2 | `chage -l {{ exam_username }} \| grep 'Minimum.*7'` |
| Max days == 60 | 2 | `chage -l {{ exam_username }} \| grep 'Maximum.*60'` |
| Account expiry == {{ exam_expiry }} | 2 | `chage -l {{ exam_username }} \| grep 'Account expires.*{{ exam_expiry }}'` |
| NOPASSWD sudo configured | 4 | `sudo -l -U {{ exam_username }} \| grep NOPASSWD` |

---

### Task 3 — File Permissions and Collaborative Directory (20 points, ~15 min)
**Difficulty:** Medium  
**Topics:** mkdir, chown, chmod, SGID, sticky bit, umask

**Student instructions:**

The `dbteam` group needs a shared workspace where all members can create and modify files, but cannot delete each other's work.

1. Create the directory `/home/{{ exam_workspace }}`. *(2 pts)*
2. Set the group owner of the directory to `dbteam`. *(3 pts)*
3. Set permissions so that:
   - The owner has full read, write, and execute access *(1 pt)*
   - Group members have read, write, and execute access *(2 pts)*
   - All other users have no access *(2 pts)*
4. Set the **SGID bit** on the directory so that new files created inside it automatically inherit the `dbteam` group. *(4 pts)*
5. Set the **sticky bit** on the directory so that users can only delete their own files. *(4 pts)*
6. Configure `{{ exam_username }}`'s shell so that the `umask` is persistently set to `007` (new files have no permissions for others). *(2 pts)*

**Expected final permissions on the directory:** `drwxrws--T`

**Ansible provisioning needed:**
- `dbteam` group must exist (same pre-provisioning as T2).
- `{{ exam_username }}` user should exist for umask verification, but partial credit is given if user is missing (T2 incomplete).

**Grading checks:**
| Check | Points | Method |
|---|---|---|
| Directory exists | 2 | `test -d /home/{{ exam_workspace }}` |
| Group owner is dbteam | 3 | `stat -c %G /home/{{ exam_workspace }}` == `dbteam` |
| Owner has rwx | 1 | `stat -c %A` starts with `drwx` |
| Group has rwx | 2 | `stat -c %A` has `rwx` in group position |
| Others have no access | 2 | `stat -c %A` ends with `---` (before special bits) |
| SGID bit set | 4 | `stat -c %A /home/{{ exam_workspace }} \| grep 's\|S'` in group position |
| Sticky bit set | 4 | `stat -c %A /home/{{ exam_workspace }} \| grep 'T\|t'` in other position |
| umask 007 in user's shell config | 2 | `grep 'umask 007' /home/{{ exam_username }}/.bashrc` or `.bash_profile` |

---

### Task 4 — Service Management (15 points, ~10 min)
**Difficulty:** Easy  
**Topics:** systemctl start/stop/enable/disable, reboot

**Student instructions:**

Configure system services for the database environment. **Changes must survive a reboot** — the grading script checks live service state, so reboot your VM before running final grading (`sudo systemctl reboot`).

1. Ensure the `crond` service is **running** and **enabled** to start automatically on boot. *(5 pts)*
2. **Stop** the `rsyslog` service and **disable** it so it does not start on boot. *(5 pts)*
3. Reboot the system and verify both services are in the correct state after boot. *(5 pts)*

**Ansible provisioning needed:**
- Stop and disable `crond` on each VM before exam (students must enable it).
- Ensure `rsyslog` is running and enabled (default on AlmaLinux 10 — verify and force if needed).
- Write provisioning timestamp to `/var/exam-provision-time` so the grading script can detect if a reboot has occurred.

**Grading checks (all checked against live state):**
| Check | Points | Method |
|---|---|---|
| crond is active | 2 | `systemctl is-active crond` == `active` |
| crond is enabled | 3 | `systemctl is-enabled crond` == `enabled` |
| rsyslog is inactive | 2 | `systemctl is-active rsyslog` == `inactive` |
| rsyslog is disabled | 3 | `systemctl is-enabled rsyslog` == `disabled` |
| System has been rebooted since provisioning | 5 | Compare `stat -c %Y /var/exam-provision-time` to system boot time via `who -b` or `/proc/uptime` |

**Note:** If the reboot check fails, the grading script prints a reminder: *"Reboot your VM before final grading: sudo systemctl reboot"* — and awards 0 for the reboot sub-check only, not the full task.

---

### Task 5 — Package Management and Custom Repository (15 points, ~12 min)
**Difficulty:** Medium  
**Topics:** DNF repo configuration, dnf install, dnf remove, rpm -q

**Student instructions:**

Configure the system to use the internal exam repository and install required packages.

1. Create a DNF repository configuration file at `/etc/yum.repos.d/exam.repo` with the following settings: *(6 pts)*
   - Repository name: `Exam Repository`
   - Base URL: `http://172.16.16.121/repo`
   - Enabled: yes
   - GPG check: disabled
2. Install the package `vim-enhanced`. *(3 pts)*
3. Install the package `{{ exam_extra_package }}`. *(3 pts)*
4. Ensure the package `tmux` is **not installed** — remove it if present. *(3 pts)*

**Ansible provisioning needed:**
- Pre-install `tmux` on all student VMs (students must remove it).
- Repo VM (172.16.16.121) must be running and serving all packages listed in section 1.2 before exam start.

**Grading checks:**
| Check | Points | Method |
|---|---|---|
| exam.repo file exists | 1 | `test -f /etc/yum.repos.d/exam.repo` |
| baseurl points to 172.16.16.121/repo | 2 | `grep 'baseurl.*172.16.16.121/repo' /etc/yum.repos.d/exam.repo` |
| enabled=1 | 1 | `grep 'enabled=1' /etc/yum.repos.d/exam.repo` |
| gpgcheck=0 | 2 | `grep 'gpgcheck=0' /etc/yum.repos.d/exam.repo` |
| vim-enhanced installed | 3 | `rpm -q vim-enhanced` exits 0 |
| {{ exam_extra_package }} installed | 3 | `rpm -q {{ exam_extra_package }}` exits 0 |
| tmux not installed | 3 | `rpm -q tmux` exits non-zero |

---

### Task 6 — Mount a File System and Search for Files (15 points, ~15 min)
**Difficulty:** Medium-Hard  
**Topics:** lsblk, mkdir, mount, /etc/fstab, UUID, find

**Student instructions:**

A new disk has been attached to your system. Mount it persistently and use it to store search results.

1. Identify the unformatted block device. It is available as `/dev/sdb` with one partition `/dev/sdb1`. Create a mount point at `{{ exam_mount }}`. *(2 pts)*
2. Mount the partition persistently by adding an entry to `/etc/fstab`. Use either the **UUID** (recommended) or the device path `/dev/sdb1`. The mount must survive a reboot. *(5 pts)*
3. After mounting, create a file at `{{ exam_mount }}/mounted.txt` containing exactly the text: `{{ exam_mount_text }}`. *(2 pts)*
4. Find all files in `/etc` that are **larger than 50 KB** and save the full path list to `{{ exam_mount }}/large-files.txt`. *(3 pts)*
5. Find all files in `/var` owned by user `root` and group `root` with permissions **exactly `640`**, and save the full path list to `{{ exam_mount }}/perms-files.txt`. *(3 pts)*

**Tip:** Use `lsblk -fp` to find the UUID of a device. Suppress errors in `find` output with `2>/dev/null`.

**Ansible provisioning needed:**
- Second disk (2 GB, XFS, one partition `/dev/sdb1`) pre-formatted but **not mounted** on each student VM. Terraform resource required.
- Plant at least 3 files in `/var/exam-data/` owned by `root:root` with permissions `640` so the find in step 5 has guaranteed results. The grading script checks for these specific planted files.
- Plant at least one file larger than 50 KB in `/etc/exam-data/` as a known anchor for grading step 4 (in addition to naturally large files in `/etc`).

**Grading checks:**
| Check | Points | Method |
|---|---|---|
| Mount point directory exists | 1 | `test -d {{ exam_mount }}` |
| Partition is currently mounted | 1 | `findmnt {{ exam_mount }}` exits 0 |
| /etc/fstab entry exists for mount point | 3 | `grep '{{ exam_mount }}' /etc/fstab` with either UUID or /dev/sdb1 |
| Mount survives reboot | 2 | Checked via same `findmnt` after reboot (same reboot as T4) |
| mounted.txt contains correct text | 2 | `grep -Fx '{{ exam_mount_text }}' {{ exam_mount }}/mounted.txt` |
| large-files.txt is non-empty and contains known large file | 3 | `test -s` and `grep` for anchor file |
| perms-files.txt contains planted 640 files | 3 | `grep` for each planted file path |

---

## 4. Grading Tools

### 4.1 Student-side grading script

**Path:** `/usr/local/bin/grade`  
**Permissions:** `755` (executable and readable by all — shell scripts require read permission to execute on Linux; obscuring content via 711 is not functional for interpreted scripts)  
**Generated by:** Ansible, from a Jinja2 template, with student-specific values baked in at provisioning time.

**Usage:**
```
grade           # grade all tasks
grade all       # same
grade t1        # grade Task 1 only
grade t2        # grade Task 2 only
...
grade t6        # grade Task 6 only
```

**Output format:**
```
===== EXAM GRADING REPORT =====
Hostname: student-01  Variant: alpha

Task 1 — File and Directory Management      [12/15]
  [PASS] Directory /home/student/projects/exam-alpha exists
  [PASS] Files report.txt, backup.txt, notes.txt exist
  [PASS] hostname.txt matches /etc/hostname
  [FAIL] report.txt does not contain last 5 lines of /etc/passwd
  [PASS] Hard link report-link-alpha verified (link count = 2)
  [PASS] Symbolic link exam-shortcut verified

Task 2 — Users, Groups, Password Policy     [20/20]
  [PASS] Group dbteam exists with GID 40001
  ...

TOTAL: 72/100
================================
```

Students may run the script at any time during the exam. It is safe to run repeatedly — all checks are read-only and non-destructive.

### 4.2 Student-side hint script

**Path:** `/usr/local/bin/hint`  
**Permissions:** `755`  
**Content:** Static text per task — directional guidance only, no commands.

**Usage:**
```
hint t1
hint t3
```

**Example output for T6:**
```
Task 6 — Hint:
  Check what block devices are attached to the system and which are not yet mounted.
  The UUID of a block device can be queried with a tool that lists block devices and
  their filesystems. Persistent mounts are configured in a system file that is read
  at boot time. The find command can filter by size (in kilobytes or bytes) and by
  ownership and permission simultaneously.
```

### 4.3 Instructor-side Ansible grading playbook

After the exam, the instructor runs an Ansible playbook that SSHes into all 20 VMs, executes the same checks as the student grading script, and writes structured output per host.

**Output:** JSON file per host in `ansible/exam-results/`, e.g.:
```json
{
  "host": "student-01",
  "variant": "alpha",
  "tasks": {
    "t1": {"score": 12, "max": 15, "checks": [...]},
    "t2": {"score": 20, "max": 20, "checks": [...]},
    ...
  },
  "total": 72
}
```

### 4.4 Exam task portal (web)

Students access their personalised task sheet from their **Windows workstation browser**, not from the VM terminal. This avoids the need to read a text file in nano/vim and allows copy-pasting variant-specific values (usernames, directory names, GIDs) directly.

**URL:** `http://172.16.16.121/exam`  
**Hosted on:** Repo VM (172.16.16.121), same server as the DNF repo  
**Technology:** Single static HTML file — no server-side logic, no backend  
**Deployed by:** Ansible (repo VM provisioning playbook)

**User flow:**
1. Student opens `http://172.16.16.121/exam` in browser on their Windows workstation
2. Page shows a single input: "Enter your student number (1–20)"
3. Student types their number and clicks a button (or presses Enter)
4. Page renders their complete personalised task sheet — all variant values filled in, all 6 tasks visible on one scrollable page
5. Student keeps browser open alongside SSH terminal for the full 90 minutes

**Implementation:**
- All 20 variant objects embedded as a JavaScript array in the HTML file
- On submit, JS looks up the variant by student number and renders the task sheet via DOM templating
- No external dependencies, no network calls — works entirely offline once the page is loaded
- The HTML file is generated by Ansible from a Jinja2 template at repo VM provisioning time, with all variant data injected

**Content per task on the portal:**
- Task title, point value, estimated time
- All instructions with variant-specific values already substituted (not Jinja2 syntax — real values)
- A "Tips" section below each task (same content as the hint script, for convenience)

### 4.5 Instructor report Python script

A Python script (`scripts/exam-report.py`) reads all JSON result files and produces:
- A per-student summary table (console and CSV)
- A per-task pass rate across the cohort (useful for paper data)
- Optional HTML report

This script is a separate implementation task.

---

## 5. Ansible Provisioning Role — Requirements

The exam provisioning playbook (`ansible/exam-provision.yml`) must complete all of the following before the exam starts:

| # | Action | Notes |
|---|---|---|
| 1 | Read per-host vars from inventory | exam_variant, exam_dir, exam_username, etc. |
| 2 | Pre-create `dbteam` group with `exam_gid` | Breaks T2/T3 dependency |
| 3 | Stop and disable `crond` | Students must enable it in T4 |
| 4 | Ensure `rsyslog` is running and enabled | Default state; force if needed |
| 5 | Pre-install `tmux` | Students must remove it in T5 |
| 6 | Plant files in `/var/exam-data/` | 3+ files, owned root:root, perms 640 |
| 7 | Plant large file in `/etc/exam-data/` | >50 KB, known filename for grading anchor |
| 8 | Write `/var/exam-provision-time` | Timestamp file; used by T4 reboot check |
| 9 | Render task sheet from Jinja2 template | Write to `/home/student/exam-tasks.txt` |
| 10 | Render `grade` script from Jinja2 template | Write to `/usr/local/bin/grade`, chmod 711, owner root |
| 11 | Render `hint` script from Jinja2 template | Write to `/usr/local/bin/hint`, chmod 755 |

A corresponding **reset playbook** (`ansible/exam-reset.yml`) must be able to undo all of the above and restore the VM to a clean state, so the same infrastructure can be reused for retakes or future exams.

---

## 6. Terraform Requirements (new, to be implemented)

In `terraform/main.tf`, add a second disk resource to each student VM:

| Property | Value |
|---|---|
| Size | 2 GB |
| Storage pool | `local-lvm` (same as primary) |
| Interface | `scsi1` |
| Filesystem | XFS (provisioned by Ansible, not Terraform) |
| Partition | Created by Ansible (`parted` or `fdisk`) |

The disk appears as `/dev/sdb` inside the VM. Ansible then partitions it (`/dev/sdb1`) and formats it with XFS as part of provisioning — **but does not mount it**. The student mounts it during the exam.

---

## 7. File/Directory Layout (planned)

```
vuv-operacijski-iac/
├── ansible/
│   ├── ansible.cfg
│   ├── inventory.yml               # updated with per-host exam vars
│   ├── exam-provision.yml          # provisions all VMs for exam
│   ├── exam-grade.yml              # instructor grading playbook (post-exam)
│   ├── exam-reset.yml              # resets VMs to clean state
│   ├── exam-results/               # JSON output from grading playbook
│   └── roles/
│       └── exam-provision/
│           ├── tasks/main.yml
│           └── templates/
│               ├── exam-tasks.txt.j2
│               ├── grade.sh.j2
│               └── hint.sh.j2
├── scripts/
│   └── exam-report.py              # generates CSV/HTML report from JSON results
├── docs/
│   └── exam-rh124-design.md        # this document
└── terraform/
    └── main.tf                     # updated with second disk per student VM
```

---

## 8. Open Items by Session

### Session 2 — Infrastructure + Provisioning
- [ ] Update `terraform/main.tf` to add second disk per student VM
- [ ] Update `ansible/inventory.yml` with all per-host exam variables
- [ ] Implement `ansible/roles/exam-provision/` role with all tasks
- [ ] Write Jinja2 template for `exam-tasks.txt` (fallback text file on VM)
- [ ] Write Jinja2 template for `grade.sh` (student grading script, chmod 711)
- [ ] Write Jinja2 template for `hint.sh` (student hint script)
- [ ] Write `ansible/exam-provision.yml` playbook
- [ ] Write `ansible/exam-reset.yml` playbook
- [ ] Write repo VM provisioning playbook (DNF repo + exam portal)
- [ ] Write static exam portal HTML (Jinja2 template with all 20 variants embedded)
- [ ] Test full provisioning cycle on student-01

### Session 3 — Grading (after exam dry-run or real exam)
- [ ] Refine `grade.sh.j2` based on observed student behaviour
- [ ] Write `ansible/exam-grade.yml` (instructor post-exam grading playbook)

### Session 4 — Reporting
- [ ] Write `scripts/exam-report.py` (reads JSON results → CSV + HTML)
- [ ] Test full grading → report pipeline
