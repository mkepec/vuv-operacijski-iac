# Practice Session — RH124 + RH134 Final Exam Prep

Self-service practice environment for students preparing for the final
combined exam. Students get one VM each with 10 pre-configured tasks
covering the full RHCSA-track syllabus. Each task can be graded and reset
independently.

---

## What students get

- **10 tasks** covering RH124 (T1–T5) and RH134 (T6–T10) topics
- **`grade`** script on every VM: `grade [all|t1..t10]` to check work at any time
- **Per-task reset**: `grade reset t<N>` wipes just that task back to start state — students can retry without losing other tasks
- **Task sheet**: readable at `http://172.16.16.121/exam/practice/` from their workstation browser, or `cat ~/practice-tasks.txt` in terminal

### Task catalog

| Task | Topic | Max pts | Covers |
|---|---|---|---|
| T1 | File and directory management | 15 | mkdir, cp, tail, ln hard+soft |
| T2 | Users, groups, password policy | 20 | useradd, chage, sudoers |
| T3 | Permissions, SGID, sticky bit, umask | 20 | chmod, collaborative directory |
| T4 | Service management | 15 | systemctl, reboot persistence |
| T5 | DNF repo + package management | 15 | yum.repos.d, install, remove |
| T6 | Shell scripting | 15 | for loop, command substitution, redirection |
| T7 | LVM: build, mount, extend | 20 | parted, PV/VG/LV, XFS, fstab, lvextend |
| T8 | Persistent logging | 15 | journald, rsyslog routing |
| T9 | SELinux: context and boolean | 15 | semanage fcontext, restorecon, setsebool |
| T10 | Podman: build, run, persist | 15 | Containerfile, podman run, systemd unit |

Tasks T4, T7, T8, T10 require a reboot to verify persistence. Students should plan one reboot near the end of their session.

---

## Instructor runbook

### 1. Tear down the RH134 exam VMs

The practice environment reuses the same 20 VM slots (IDs 200–219).

```bash
source setup.sh
cd terraform
terraform destroy
```

> Set `STUDENT_COUNT` back to 1 in `.env` for the next full deploy, then scale to 20 again below.

### 2. Provision 20 fresh VMs

```bash
# .env
STUDENT_COUNT=20

source setup.sh
cd terraform
terraform apply
```

Wait for cloud-init to finish (~1 min after VMs show as running).

### 3. Clear stale SSH host keys

```bash
for i in $(seq 101 120); do ssh-keygen -R "172.16.16.$i" 2>/dev/null; done
```

### 4. Reprovsion the repo VM (adds practice portal page)

The repo VM already serves the RH124 and RH134 exam portals. Re-running
`repo-provision.yml` adds `http://172.16.16.121/exam/practice/` without
touching any existing portal pages or NFS exports.

```bash
cd ../ansible
ssh-add ~/.ssh/id_ed25519
ansible-playbook repo-provision.yml
```

This renders `practice-portal.html.j2` and uploads it alongside the existing
RH124/RH134 pages. The chooser at `http://172.16.16.121/exam/` gains a
third link: **Practice Session (Final exam prep)**.

### 5. Deploy the practice environment on all 20 VMs

```bash
ansible-playbook practice/practice-provision.yml
```

This runs the `practice-provision` role on every student VM. What it does:

- Plants `/var/practice-data/` with data files for T1 find/perms tasks
- Pre-creates the `ops` group (GID 50100) so T2 and T3 are independent
- Sets `crond` and `rsyslog` to stopped+disabled (T4 start state)
- Pre-installs `zip` (T5 — students must remove it)
- Ensures `/home/student/bin/` and `/home/student/reports/` exist
- Sets services to a mixed active/disabled state for T6 scripting task
- Attaches a raw 1 GB disk (`/dev/sdb`) via Terraform — T7 LVM disk
- Removes `/var/log/journal` so T8 is not trivially pre-solved
- Installs httpd and plants `/var/www/html/practice.html` with the wrong
  SELinux context (`var_t` instead of `httpd_sys_content_t`) for T9
- Installs Podman, enables linger for the `student` user, pre-pulls the
  base container image for T10
- Deploys `/home/student/practice-tasks.txt` and `/usr/local/bin/grade`

To target a single VM:

```bash
ansible-playbook practice/practice-provision.yml -l student-01
```

### 6. Verify

```bash
# Smoke-check: SSH into student-01 and confirm the grade script exists
ssh -J root@135.181.128.170 student@172.16.16.101 "grade t1 2>&1 | head -5"

# Confirm practice portal is reachable from Proxmox host
ssh root@135.181.128.170 \
  "curl -s -o /dev/null -w '%{http_code}' http://172.16.16.121/exam/practice/index.html"
# expect: 200
```

---

## During the practice session

Students connect the same way as for exams:

```
ssh -p 220N student@135.181.128.170   (N = their student number)
```

Password: same `STUDENT_PASSWORD` from `.env` as previous exams.

They can visit the task sheet from their workstation browser:
```
http://172.16.16.121/exam/practice/
```

The grade script is self-contained — no instructor action needed while students work.

---

## Resetting a single student VM

If a student wants a completely fresh start (or to hand a VM to a different student):

```bash
ansible-playbook practice/practice-reset.yml -l student-05
ansible-playbook practice/practice-provision.yml -l student-05
```

The reset playbook undoes all student work and returns every task to its
provisioned start state. It is safe to run at any time.

Students can also reset individual tasks themselves without instructor help:

```bash
grade reset t7     # wipe just the LVM task, retry from scratch
grade reset all    # wipe everything locally (does not reinstall grade script)
```

---

## Tear down after practice

```bash
source setup.sh && cd terraform && terraform destroy
```

No exam results to archive — this is practice only.

---

## Files added by this feature

```
ansible/
├── practice/
│   ├── practice-provision.yml       # top-level provisioning playbook
│   └── practice-reset.yml           # full VM wipe playbook
└── roles/
    └── practice-provision/
        ├── tasks/
        │   └── main.yml             # role: all 10 task pre-conditions
        └── templates/
            ├── grade.sh.j2          # grade + reset script (deployed to /usr/local/bin/grade)
            ├── practice-tasks.txt.j2 # plain-text task sheet (/home/student/practice-tasks.txt)
            └── practice-portal.html.j2 # web portal page (served at /exam/practice/)
```

`ansible/repo-provision.yml` and `ansible/templates/exam-portal-chooser.html.j2`
were updated to render and serve the practice portal page alongside the
existing exam pages. No other existing files were changed.

---

## Design notes

**No per-student variation.** All 20 VMs get identical task names, paths, and
values. This is practice — the anti-cheat variation used in exams is not
needed. It also means the task sheet is a single static page (not 20
per-student variants like the exam portals).

**Per-task reset on the VM.** The `grade reset t<N>` command lets students retry
a specific task without losing work on others. This mirrors the `lab start
<topic>` reset pattern from the Red Hat Online Learning environment, but
implemented as a simple bash function in the grade script rather than a
separate tool. The instructor-side `practice-reset.yml` does a full wipe and
is intended for between-student reuse, not mid-session use.

**SELinux included (T9).** SELinux was excluded from both mid-semester exams
(too risky for shared exam VMs — a misconfigured SELinux policy could break
other students' SSH sessions). Practice VMs are isolated single-student
sandboxes, so SELinux tasks are safe and valuable to include.

**Reboot requirement.** Tasks T4, T7, T8, and T10 each have at least one check
that requires a reboot to verify persistence. The task sheet tells students
to plan one reboot near the end of their session. This is the same pattern as
both mid-semester exams.
