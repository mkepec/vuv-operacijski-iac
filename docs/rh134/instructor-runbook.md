# Instructor Runbook — RH134 Mid-Semester Practical Exam

Step-by-step lifecycle guide for running the exam from first provision to final teardown.
For task design and grading logic, see `docs/rh134/exam-rh134-design.md`.

RH134 reuses the same student VMs, repo VM, and pipeline tooling as RH124 — the
key differences are: a second raw disk per student VM (`/dev/sdb`, for the LVM
task), an expanded repo VM role (it now also serves NFS exports and a `student`
SSH/SCP account), and two tasks (T4, T5) whose grading checks state on the repo
VM rather than the student's own VM.

---

## Quick reference

| Item | Value |
|---|---|
| Duration | 90 minutes |
| Students | up to 20 |
| Student VMs | student-01 through student-20, IPs 172.16.16.101–120 |
| Repo VM | 172.16.16.121 (DNF repo + exam portal + **NFS exports + `student` SSH account**) |
| Exam portal | http://172.16.16.121/exam/ → choose RH134 |
| Student SSH | `ssh student@vuv.bikanalabs.xyz -p 220X` (X = seat number) |
| Instructor SSH to VM | `ssh -J root@135.181.128.170 ansible@172.16.16.10X` |
| Instructor SSH to repo VM | `ssh -J root@135.181.128.170 ansible@172.16.16.121` |
| Proxmox host | `root@135.181.128.170` |

---

## Lifecycle overview

```
Phase 1 — Provision        terraform apply → exam-provision.yml (rh124+rh134) → repo-provision.yml
Phase 2 — Exam day         open DNAT → write board → invigilate
Phase 3 — Grading          reboot all VMs → exam-grade.yml (incl. cross-host checks) → exam-report.py
Phase 4 — Post-exam review keep VMs running (or shut down) for student consultations
Phase 5 — Teardown         backup results → terraform destroy
```

---

## Phase 1 — Provision from scratch

This is the starting point whether it is your first time or you are reprovisioning after a previous teardown.

### 1.1 Check secrets

```bash
cat .env
```

Make sure these are set:

| Variable | Purpose |
|---|---|
| `PROXMOX_API_TOKEN_SECRET` | Terraform access to Proxmox API |
| `STUDENT_PASSWORD` | Plaintext SSH password — written on the board, shown in the exam portal, and used for the `student` account on the repo VM (T4 upload target) |
| `STUDENT_PASSWORD_HASH` | Hashed version injected into VMs via cloud-init (`openssl passwd -6 'yourpassword'`) |
| `STUDENT_COUNT` | Number of student VMs to create (1 for testing, up to 20 for a full class) |

### 1.2 Provision student VMs with Terraform

```bash
source setup.sh
cd terraform
terraform init    # only needed on first run or after provider changes
terraform apply
```

> **`terraform destroy`/`apply` always includes the repo VM.** The repo VM
> resource (`proxmox_virtual_environment_vm.repo`) is unconditional — it is
> *not* behind `for_each`/`count`, so it's destroyed and recreated on every
> `terraform destroy` + `apply` regardless of `STUDENT_COUNT`, even if you only
> meant to reset a single student VM. If you destroy/redeploy for a retest,
> plan on re-running `repo-provision.yml` afterward too (§1.4) — the repo VM
> comes back with none of its DNF repo / NFS exports / portal / student
> account set up.

This creates the student VMs and the repo VM on Proxmox — including **both**
RH124's second disk (`virtio0` → `/dev/vda`, pre-formatted XFS, unmounted) and
RH134's second disk (`scsi2` → `/dev/sdb`, completely raw — no partition table,
no filesystem). Both disks are unconditionally attached to every student VM
since the two exams never run concurrently (see design doc §6).

Cloud-init runs automatically on first boot and sets up the `student` and
`ansible` users. Wait about 60 seconds after `apply` completes, then clear
stale SSH host keys (same IPs, new VMs):

```bash
for i in $(seq 101 120); do ssh-keygen -R "172.16.16.$i" 2>/dev/null; done
```

Verify cloud-init has finished:

```bash
cd ../ansible
ssh-add ~/.ssh/id_ed25519
ansible students -m ping
```

All hosts should respond with `pong`. If some fail, wait another 30 seconds and retry.

### 1.3 Provision student VMs for both exams

If running RH124 and RH134 back-to-back (or want a single VM ready for either),
run both provisioning playbooks. For an RH134-only cycle, just run the RH134 one:

```bash
ansible-playbook rh134/exam-provision.yml
```

This runs on all student VMs and sets the RH134 exam state: ensures
`/home/student/bin/` exists, sets the four baseline services (`sshd`, `crond`,
`chronyd`, `rsyslog`) to mixed active/enabled states, confirms `/dev/sdb` is
still raw and untouched, ensures `/var/log/journal` does **not** pre-exist,
plants the `/etc/exam-source/` tree with distinguishable permissions, installs
rootless Podman prerequisites and enables linger for the `student` user,
pre-pulls the base container image, writes the provisioning timestamp, and
deploys the `grade` and `hint` scripts.

Takes a few minutes per VM (longer on first run — installing Podman and
pulling the ~310 MB base image). Verify with a spot-check:

```bash
ansible students -m shell -a "ls /usr/local/bin/grade /usr/local/bin/hint" --become
ansible students -m shell -a "blkid -p /dev/sdb" --become   # should report no signature (raw)
```

### 1.4 Provision the repo VM

The repo VM gains a third role for RH134: NFS server (per-student exports) plus
a `student` OS account with password authentication (T4's upload target, and
the SSH credential T5 students also need to reach the export's host). One
playbook does it all — portal (both courses), DNF repo, NFS exports, account:

```bash
ansible-playbook repo-provision.yml \
  --extra-vars "student_password=$(grep ^STUDENT_PASSWORD= ../.env | cut -d= -f2)"
```

> **Always `source setup.sh` (or `--extra-vars`) before this playbook.**
> `group_vars/all.yml` defaults `student_password` to
> `lookup('env', 'STUDENT_PASSWORD')`. If that env var is empty (e.g. you ran
> `ansible-playbook` in a fresh shell without sourcing `setup.sh` first and
> without `--extra-vars`), the `student` account on the repo VM gets a hash of
> the **empty string** — `sshd` will accept the connection but the password
> won't be `STUDENT_PASSWORD`, so T4/T5 uploads (and the pre-flight check)
> fail with no obvious cause. Fix: `source ../setup.sh` (or pass
> `--extra-vars` as above) and re-run — the `user` module detects the hash
> mismatch and updates the account in place.

This installs Apache + `createrepo`, builds the local DNF repo, renders and
deploys both RH124 and RH134 portal pages (plus the course-chooser landing
page) for all 20 students, installs `nfs-utils`, creates and exports
`/exports/export-<variant>/` per student (each scoped to that student's VM IP
only), plants `welcome.txt` anchors, creates the `student` group/account with
password auth, and ensures `sshd` actually allows password authentication
(see note below).

**Note — sshd password auth drop-in:** AlmaLinux 10's cloud-init ships
`/etc/ssh/sshd_config.d/50-cloud-init.conf` with `PasswordAuthentication no`,
which — due to `Include` ordering and first-directive-wins semantics — silently
overrides anything written later in `sshd_config` itself. The playbook works
around this with an early drop-in, `/etc/ssh/sshd_config.d/00-exam-password-auth.conf`
(sorts alphabetically before `50-cloud-init.conf`), containing
`PasswordAuthentication yes`, with a handler that restarts `sshd`. **If you
ever see the pre-flight SSH/password check fail with
`Permission denied (publickey,...)` despite `sshd -T` reporting
`passwordauthentication yes`,** the running daemon is probably stale — compare
`systemctl show sshd --property=ActiveEnterTimestamp` against the drop-in
file's mtime; if the daemon predates the file, `systemctl restart sshd`
manually and re-run the playbook.

The playbook ends with **pre-flight health checks** (run via SSH through the
Proxmox host, since the controller has no direct route to the 172.16.16.0/24
NAT bridge): DNF repo reachable, exam portal reachable, all 20 NFS exports
advertised by `showmount`, and the `student` account's password login works.
A failure here means students cannot complete T4/T5 — do not proceed to Phase 2
until this playbook runs clean.

Verify manually if you want extra confidence:

```bash
ssh root@135.181.128.170 \
  "curl -s http://172.16.16.121/repo/repodata/repomd.xml | head -3 && curl -so /dev/null -w '%{http_code}' http://172.16.16.121/exam/"

ssh -J root@135.181.128.170 ansible@172.16.16.121 "showmount -e localhost"
```

### 1.5 End-to-end test (recommended before any real exam)

Use `docs/rh134/instructor-cheatsheet.md` to solve all 6 tasks on student-01,
run `grade` and confirm 100/100 (after the required end-of-exam reboot — see
§3.1 below), then reset and re-provision that VM:

```bash
ssh -p 2201 student@135.181.128.170
# ... complete all tasks per cheatsheet, reboot once near the end, run grade ...

# Back on your machine:
cd ansible
ansible-playbook rh134/exam-reset.yml -l 'student-01:repo'
ansible-playbook rh134/exam-provision.yml -l student-01
```

`exam-reset.yml` also wipes `/dev/sdb` back to raw (removes any LVs/VGs/PVs the
student created), removes generated systemd units and lingering Podman
containers, clears `/var/log/journal` if it was created, and (via its
repo-VM play — hence `repo` in `-l`) removes this student's T4/T5 cross-host
artifacts from the repo VM — so a retake starts from the same blank-slate
state.

---

## Phase 2 — Exam day

### 2.1 Checklist before students arrive

- [ ] `ansible students -m ping` — all VMs respond
- [ ] Repo VM is serving DNF repo, exam portal, and NFS exports (verified in 1.4 — pre-flight checks passed)
- [ ] `student` account on the repo VM accepts password SSH/SCP login
- [ ] DNAT ports are open (see below)
- [ ] Board is written (see below)

### 2.2 Open student SSH ports

Run from `proxmox-homelab/foundation/ansible/`:

```bash
ansible-playbook playbooks/site.yml --tags exam_dnat \
  --extra-vars "dnat_action=add student_count=20"
```

Quick check that a student port is reachable:

```bash
ssh -p 2201 student@135.181.128.170    # should prompt for password
```

### 2.3 What to write on the board

```
Zadaci:    http://172.16.16.121/exam/   (or your portal URL)
           → unesite broj sa svog mjesta, odaberite RH134

SSH:       ssh student@vuv.bikanalabs.xyz -p 220X
           (X = vaš broj mjesta, npr. mjesto 3 → port 2203)

Lozinka:   [vrijednost STUDENT_PASSWORD iz .env — ista lozinka vrijedi
            i za prijavu na repo poslužitelj u zadacima 4 i 5]

Trajanje:  90 minuta

Napomena:  Nekoliko zadataka provjerava postojanost nakon ponovnog
           pokretanja. Pokrenite "sudo systemctl reboot" JEDNOM, pri
           kraju ispita, nakon što završite sve zadatke.
```

### 2.4 Seat assignment

Each seat number maps directly to a student VM and SSH port. Students enter
their seat number in the exam portal to get their personalised RH134 task
sheet. The variant mapping (alpha–tango) is identical to RH124 — see the
variant table in `docs/rh134/exam-rh134-design.md` §2.1. The same
adjacent-seat caution from RH124 applies if students 01–10 and 11–20 reuse
neighboring values.

### 2.5 During the exam

- Students work independently on their own VM
- The `grade` and `hint` scripts are freely available — running them costs no points
- T4 (upload) and T5 (NFS mount) require students to authenticate to the repo
  VM (`172.16.16.121`) as `student`, using the same exam password — they will
  see an unfamiliar host-key prompt the first time; this is expected (the task
  sheet mentions it)
- If a VM becomes unreachable, SSH in directly as the ansible user to investigate:

```bash
ssh -J root@135.181.128.170 ansible@172.16.16.10X
```

- If the repo VM becomes unreachable, **both T4 and T5 are blocked for every
  student** — treat this as a priority incident:

```bash
ssh -J root@135.181.128.170 ansible@172.16.16.121
```

---

## Phase 3 — Grading

### 3.1 Reboot all VMs

After time is called, reboot all student VMs. The grading script verifies
post-reboot state for **Task 2** (LVM mount persists via `/etc/fstab`),
**Task 3** (persistent journald storage survived), and **Task 6** (the
container's systemd unit brought it back up). A single reboot is required for
full marks on all three — this is the same "one reboot near the end" model
RH124 used for T4/T6.

```bash
cd ansible
ansible students -m shell -a "systemctl reboot" --become
```

Wait 60–90 seconds, then confirm all VMs are back up:

```bash
ansible students -m ping
```

### 3.2 Run the grading playbook

```bash
ansible-playbook rh134/exam-grade.yml
```

SSHes into every student VM, runs the same checks as the student `grade`
script, **and additionally checks state on the repo VM** for the T4 (uploaded
file) and T5 (NFS-submitted file) cross-host sub-checks — folding both results
into the same per-student JSON written to `ansible/exam-results/rh134/`.

To re-grade a single student:

```bash
ansible-playbook rh134/exam-grade.yml -l student-05
```

`exam-grade.yml` is read-only and idempotent — safe to rerun any number of
times, including after a student fixes something during a consultation.

### 3.3 Generate the report

```bash
cd ..
python3 scripts/exam-report.py --results-dir ansible/exam-results/rh134
```

Outputs:
- `ansible/exam-results/rh134/report.csv` — import into a spreadsheet
- `ansible/exam-results/rh134/report.html` — open in a browser for a formatted view with per-check detail

`exam-report.py` needs no RH134-specific changes — its JSON schema is
identical across exams (see design doc §4.5/§7).

### 3.4 Close student SSH ports

Once grading is done, close the DNAT rules so the exam ports are no longer
publicly reachable. Run from `proxmox-homelab/foundation/ansible/`:

```bash
ansible-playbook playbooks/site.yml --tags exam_dnat \
  --extra-vars "dnat_action=remove student_count=20"
```

---

## Phase 4 — Post-exam review (optional)

After the exam you may want to keep the VMs available so students can review
their results and go through the solutions with you.

### Keep VMs running

No action needed — VMs stay up after grading. A student can SSH in the same
way they did during the exam and run `grade` to see their results. Note that
DNAT ports are closed after Phase 3, so for a review session you will need to
re-open them:

```bash
# Re-open ports for the review session
ansible-playbook playbooks/site.yml --tags exam_dnat \
  --extra-vars "dnat_action=add student_count=20"

# Close again after the session
ansible-playbook playbooks/site.yml --tags exam_dnat \
  --extra-vars "dnat_action=remove student_count=20"
```

The repo VM's NFS exports and `student` account remain available during a
review session too — no extra steps needed for T4/T5 review.

### Shut down VMs between exam day and review session

If the review session is days away and you want to free up Proxmox resources
in the meantime, shut the VMs down rather than destroying them — their state
(including LVs, container images, mounted exports) is preserved and they can
be started again before the review:

```bash
# Shut down all student VMs
ansible students -m shell -a "systemctl poweroff" --become

# Or shut down a single VM (e.g. to review with one student)
ansible students -m shell -a "systemctl poweroff" --become -l student-05
```

To start them again from the Proxmox host before a review session:

```bash
ssh root@135.181.128.170
for vmid in $(seq 200 219); do qm start $vmid; done
```

Or start a single VM:

```bash
ssh root@135.181.128.170 "qm start 204"   # student-05 = VM ID 204
```

Wait for cloud-init / boot to complete (~30 seconds), then verify:

```bash
ansible students -m ping
```

The repo VM (221) should be left running throughout — both for portal access
during review and because it's a shared dependency for any other in-progress
exam activity.

---

## Phase 5 — Teardown

Once results are saved and review sessions are done, destroy the exam
environment to free the Proxmox host for other use.

### 5.1 Back up results

`ansible/exam-results/rh134/` is gitignored and will be lost on
`terraform destroy`. Archive before proceeding:

```bash
cp -r ansible/exam-results/rh134/ ~/Desktop/exam-results-rh134-$(date +%Y%m%d)/
```

### 5.2 Destroy all VMs

```bash
source setup.sh
cd terraform
terraform destroy
```

This removes all student VMs and the repo VM from Proxmox — including both
second disks (RH124's `virtio0`/`/dev/vda` and RH134's `scsi2`/`/dev/sdb`).
The Proxmox host itself is unaffected.

### 5.3 Reset for next time

After destroy, set `STUDENT_COUNT=1` in `.env` so the next `terraform apply`
starts with a single test VM rather than the full class:

```bash
# In .env:
STUDENT_COUNT=1
```

The Proxmox host is now free for other projects. When the next exam cycle
comes around, start again from Phase 1.

---

## Retake / same exam, new VMs

If VMs have been destroyed but you need to run the same exam again (retake
group, etc.), just go through Phase 1 again from scratch — `terraform apply`
will create fresh VMs from the cloud-init template, with both second disks
attached.

If VMs are still running and you just need to reset their state to a clean
exam start:

```bash
cd ansible
ansible-playbook rh134/exam-reset.yml -l 'student-01:repo'      # single student
ansible-playbook rh134/exam-reset.yml                           # all students
# (include "repo" in -l for single-student resets — otherwise the repo-VM
# cleanup play is skipped, see below)

ansible-playbook rh134/exam-provision.yml -l student-01         # re-apply clean exam state
```

**The repo VM does need a cleanup step between attempts** — `exam-reset.yml`'s
second play (`hosts: reposervers`) removes that student's T4 upload
(`/home/student/uploaded-<variant>.txt`) and resets their T5 export back to
just `welcome.txt` (removes `<variant>-submitted.txt`). Without this, a fresh
attempt would inherit the previous attempt's "already submitted" artifacts and
`exam-grade.yml` would award T4/T5's cross-host points before the student does
anything. The `student` OS account and NFS export *structure* itself remain
stateless and don't need `repo-provision.yml` rerun between attempts.
