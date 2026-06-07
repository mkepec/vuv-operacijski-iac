# VUV Operacijski Sustavi — IAC

Infrastructure for Red Hat Academy Operating Systems (RH124/RH134) practical exams at Virovitica University of Applied Sciences (VUV). Provisions up to 20 AlmaLinux 10 student VMs on a dedicated Proxmox server.

## Context

- Instructor: Marin Kepec, marin.kepec@gmail.com
- Course: RHCSA-track (RH124 + RH134), performance-based practical exams
- Each student gets their own isolated VM during the exam
- Infrastructure is brought up for exams and torn down after

## Infrastructure

**Proxmox host**
- Hetzner EX44: Intel i5-13500, 64 GB RAM, 476 GB NVMe
- Public IP: 135.181.128.170
- SSH: `root@135.181.128.170` via `~/.ssh/id_ed25519`
- Node name: `proxmox-lab`
- NAT bridge: `vmbr0` — 172.16.16.1/24 (gateway)
- API token: `terraform@pve!terraform-token` (secret in `.env`)
- Terraform provider: `bpg/proxmox ~> 0.83.1`
- Terraform Cloud org: `marin-prox-lab`, workspace: `vuv-operacijski-iac` (local execution mode)

**VM template**
- VM ID 9002 — AlmaLinux 10 cloud-init template

**Student VMs**
| Property | Value |
|---|---|
| VM IDs | 200–219 (student-01 through student-20) |
| IPs | 172.16.16.101–120/24 |
| CPU | 2 vCores |
| RAM | 3072 MB |
| Disk | 10 GB on local-lvm (`scsi0` → `/dev/sda`) |
| OS users | `student` (password auth, exam use); `ansible` (SSH key only, Ansible use) |
| SSH key | `~/.ssh/id_ed25519.pub` injected into `ansible` user via cloud-init |
| Start on boot | false (manually started for exams) |
| Tags | exam, rhcsa, vuv |

**Network**
- All VMs on 172.16.16.0/24
- Homelab VMs occupy .2–.80; student VMs use .101–.120
- DNS: 1.1.1.1, 8.8.8.8
- Instructor Ansible reaches VMs via ProxyJump: `ssh -J root@135.181.128.170 ansible@172.16.16.10x`
- Additional Ansible keys managed via `ansible/manage-ansible-keys.yml` (no reprovision needed)

**Student SSH access — DNAT port forwarding**
- Students connect directly to the Proxmox public IP on a per-student port
- Port mapping: `2200 + N` on `135.181.128.170` → `172.16.16.100 + N :22`
- student-01: `ssh -p 2201 student@135.181.128.170`
- student-02: `ssh -p 2202 student@135.181.128.170`
- student-N:  `ssh -p 220N student@135.181.128.170`
- DNAT rules live on the Proxmox host, managed from the **homelab repo** (not this repo)
- Role: `proxmox-homelab/foundation/ansible/roles/exam_dnat/`
- Open ports before exam (run from `proxmox-homelab/foundation/ansible/`):
  ```
  ansible-playbook playbooks/site.yml --tags exam_dnat --extra-vars "dnat_action=add student_count=20"
  ```
- Close ports after exam:
  ```
  ansible-playbook playbooks/site.yml --tags exam_dnat --extra-vars "dnat_action=remove student_count=20"
  ```

## Task tracking

`TODO.md` in the repo root tracks all work items with statuses. Update it at the end of every session. Read it at the start of every session to know what's done and what's next.

---

## Additional infrastructure (planned, not yet provisioned)

**Repo VM**
- VM ID 221, IP 172.16.16.121
- Serves a local DNF package repository over HTTP (`http://172.16.16.121/repo`)
- Also hosts the exam task portal at `http://172.16.16.121/exam` (static HTML, no backend)
- Required before any exam — students must not depend on internet access

**Second disk per student VM (RH124)**
- 1 GB, interface `virtio0` → appears inside the VM as `/dev/vda` (the OS disk is `scsi0` → `/dev/sda`)
- One partition `/dev/vda1`, XFS formatted, pre-formatted by Ansible but **not mounted** —
  students mount it during the exam (Task 6)
- Defined in `terraform/main.tf` on the `student` VM resource

## Exam project

**Full designs:**
- RH124 — `docs/rh124/exam-rh124-design.md` (fully implemented, tested, graded, archived)
- RH134 — `docs/rh134/exam-rh134-design.md` (design complete, implementation in progress)

Read the relevant design doc before any exam-related session.

**Two exams planned, a third (combined) likely later:**
1. RH124 mid-semester — fully implemented and run
2. RH134 mid-semester — design complete, implementation underway
3. Future: a comprehensive end-of-semester exam combining RH124+RH134 topics
   (this is *why* the repo is split by course below — so a combined exam can
   reuse both courses' shared roles/inventory without duplicating anything)

**Key design decisions (summary, RH124 — see RH134's own design doc for its specifics):**
- 6 tasks, 100 pts, 90 min; difficulty Easy → Medium-Hard
- Tasks: file management, users/groups/policy, permissions (SGID+sticky), services, package management, mount+find
- Networking tasks excluded — risk of breaking student SSH session
- Per-student variation via NATO phonetic alphabet (alpha–tango, students 01–20); values in inventory host vars, baked into grading script and task sheet via Jinja2 at provisioning time
- `dbteam` group pre-provisioned by Ansible to remove T2→T3 dependency; students can attempt tasks in any order
- Student grading script: `/usr/local/bin/grade [all|t1..t6]`, chmod 711 (executable, not readable)
- Student hint script: `/usr/local/bin/hint [t1..t6]`, directional text only
- Instructor grading: Ansible playbook writes JSON per host → Python script generates CSV/HTML report

**Exam task portal (web):**
- Hosted on repo VM at `http://172.16.16.121/exam`
- Single static HTML page — student enters their number (1–20), page renders their full personalised task sheet
- All 20 variants embedded as a JS object; no server-side logic needed
- Students access from their Windows workstation browser alongside their SSH terminal

## Repo layout

The repo is split by course (`rh124/`, `rh134/`) wherever artifacts are
exam-specific, with genuinely shared pieces (inventory, common roles, the
report script) staying at the shared level — see `docs/rh134/exam-rh134-design.md`
§7 for the reasoning behind this split (it's designed to support a future
combined RH124+RH134 exam without duplicating shared infrastructure).

```
vuv-operacijski-iac/
├── .env                        # secrets — gitignored, copy from .env.example
├── .env.example                # template for all secrets and config
├── setup.sh                    # sources .env, exports TF_VAR_* for Terraform
├── docs/
│   ├── rh124/
│   │   ├── exam-rh124-design.md      # full RH124 exam design requirements document
│   │   ├── instructor-cheatsheet.md  # exact commands to complete all 6 RH124 tasks
│   │   ├── instructor-runbook.md     # RH124 exam-day operations guide
│   │   └── timing-report.md          # measured RH124 infra timing
│   └── rh134/
│       └── exam-rh134-design.md      # full RH134 exam design requirements document
├── terraform/
│   ├── versions.tf             # provider + TF Cloud backend
│   ├── variables.tf            # all input variables
│   ├── main.tf                 # proxmox_virtual_environment_vm resource (for_each)
│   ├── outputs.tf              # VM IDs, IPs, SSH hint
│   └── terraform.tfvars.example
├── ansible/
│   ├── ansible.cfg             # remote_user=ansible, ProxyJump, roles_path=roles
│   ├── inventory.yml           # static, all 20 hosts — shared, carries BOTH rh124_* and rh134_* host vars
│   ├── site.yml                # placeholder: ping + print hostname
│   ├── manage-ansible-keys.yml # shared — manage additional Ansible SSH keys
│   ├── roles/
│   │   ├── exam-provision-rh124/     # RH124 provisioning role (tasks + templates)
│   │   └── exam-provision-rh134/     # RH134 provisioning role (tasks + templates)
│   ├── rh124/
│   │   ├── exam-provision.yml        # provisions student VMs for RH124
│   │   ├── exam-grade.yml            # instructor grading playbook (post-exam)
│   │   ├── exam-reset.yml            # resets VMs to clean state
│   │   └── repo-provision.yml        # repo VM: DNF repo + exam portal
│   ├── rh134/
│   │   ├── exam-provision.yml        # provisions student VMs for RH134
│   │   ├── exam-grade.yml            # instructor grading playbook (planned)
│   │   └── exam-reset.yml            # resets VMs to clean state
│   └── exam-results/
│       ├── rh124/                    # JSON grading output + archive, per host
│       └── rh134/                    # JSON grading output + archive, per host (planned)
└── scripts/
    └── exam-report.py          # reads exam-results/<course>/*.json, produces CSV/HTML — shared, course-agnostic
```

## Secrets setup

`.env` holds all secrets (gitignored). Fill from `.env.example`:

```
PROXMOX_API_TOKEN_SECRET=<from proxmox-api-token.json>
STUDENT_PASSWORD=<exam password>
STUDENT_COUNT=1
```

The API token secret lives in the homelab repo at:
`/Users/marin/projects/proxmox-homelab/foundation/secrets/proxmox-api-token.json`

## Standard workflow

```bash
# 1. Export variables
source setup.sh

# 2. Terraform
cd terraform
terraform init        # first time or after provider changes
terraform plan
terraform apply

# 3. Clear stale SSH host keys (required after every reprovision — same IPs, new VMs)
for i in $(seq 101 120); do ssh-keygen -R "172.16.16.$i" 2>/dev/null; done

# 4. Ansible (after VMs are up and cloud-init has finished, ~1 min)
ssh-add ~/.ssh/id_ed25519
cd ../ansible
ansible-playbook site.yml
```

## Scaling VMs — step by step

`STUDENT_COUNT` in `.env` controls how many VMs Terraform creates. The map of all 20 students is always generated; the count just slices it. Scaling up adds VMs, scaling down destroys them. **Never skip counts** (e.g. go 1 → 10, not 1 → 3 → 10) unless you're intentionally testing intermediate sizes.

### Start with 1 VM (default — testing/validation)

```bash
# .env
STUDENT_COUNT=1

source setup.sh && cd terraform && terraform apply
# Creates: student-01 (VM 200, 172.16.16.101)
```

### Scale to 10 VMs (half-class rehearsal)

```bash
# .env
STUDENT_COUNT=10

source setup.sh && cd terraform && terraform apply
# Adds: student-02 through student-10 (VMs 201–209, IPs .102–.110)
# student-01 is unchanged (Terraform only adds the delta)
```

### Scale to 20 VMs (full exam)

```bash
# .env
STUDENT_COUNT=20

source setup.sh && cd terraform && terraform apply
# Adds: student-11 through student-20 (VMs 210–219, IPs .111–.120)
```

### Tear down after exam

```bash
source setup.sh && cd terraform && terraform destroy
# Destroys all provisioned VMs; set STUDENT_COUNT back to 1 for next test
```

### Target Ansible at a subset

The inventory always lists all 20 hosts. Use `-l` to limit:

```bash
ansible-playbook site.yml -l student-01          # single VM
ansible-playbook site.yml -l 'student-01:student-02:student-03'  # named list
ansible-playbook site.yml -l students            # all in group
```

## Post-exam grading workflow

Run these after the exam ends and all students have submitted.

```bash
cd ansible
ssh-add ~/.ssh/id_ed25519

# 1. Grade all students — SSHes into each VM, runs grade script, writes JSON
#    (results land in ansible/exam-results/<course>/, e.g. exam-results/rh124/)
ansible-playbook <course>/exam-grade.yml

# Single student (re-grade or spot-check)
ansible-playbook <course>/exam-grade.yml -l student-01

# Example for RH124:
ansible-playbook rh124/exam-grade.yml
ansible-playbook rh124/exam-grade.yml -l student-01

# 2. Generate report from JSON results (defaults to RH124's results dir)
cd ..
python3 scripts/exam-report.py
# Outputs to ansible/exam-results/rh124/:
#   report.csv   — spreadsheet-ready
#   report.html  — browser report with per-check detail

# For RH134 (once its grading playbook exists), point at its results dir:
python3 scripts/exam-report.py --results-dir ansible/exam-results/rh134

# Custom output paths
python3 scripts/exam-report.py --csv ~/Desktop/results.csv --html ~/Desktop/results.html
```

**Idempotency:** `exam-grade.yml` is safe to rerun any number of times. The grade script only reads VM state — no writes. The JSON result file is overwritten on each run. Re-grading a student after they make a fix is fine.

**Results location:** `ansible/exam-results/<course>/<hostname>.json` — gitignored, stays local.

## Archiving past exam results

After each exam, archive the generated report before committing:

```bash
# Copy generated reports to archive with a dated name
cp ansible/exam-results/<course>/report.csv  ansible/exam-results/<course>/archive/<course>-<year>-<month>.csv
cp ansible/exam-results/<course>/report.html ansible/exam-results/<course>/archive/<course>-<year>-<month>.html

# Example for RH124 May 2026:
cp ansible/exam-results/rh124/report.csv  ansible/exam-results/rh124/archive/rh124-2026-05.csv
cp ansible/exam-results/rh124/report.html ansible/exam-results/rh124/archive/rh124-2026-05.html
```

**Naming convention:** `<course>-<year>-<month>` — e.g. `rh124-2026-05`, `rh134-2026-11`.
This is unchanged by the `docs/`/`ansible/` restructure — only the directory
prefix gained a `<course>/` segment (`exam-results/rh124/archive/...` instead
of `exam-results/archive/...`); filenames keep the same convention.

**What's tracked vs. ignored:**
- `ansible/exam-results/<course>/archive/*.{csv,html}` — **committed** (historical record)
- `ansible/exam-results/<course>/report.{csv,html}` — **gitignored** (live generated output)
- `ansible/exam-results/<course>/*.json` — **gitignored** (raw grading data, stays local)
- `scripts/students-*.csv` — **gitignored** (personal data: names, JMBAGs, emails)

**With student identity data** (optional, for official grade export):

```bash
python3 scripts/exam-report.py --students scripts/students-rh124-2026-05.csv
cp ansible/exam-results/rh124/report.csv  ansible/exam-results/rh124/archive/rh124-2026-05.csv
cp ansible/exam-results/rh124/report.html ansible/exam-results/rh124/archive/rh124-2026-05.html
```

The student CSV (`--students`) must have columns: `JMBAG,Ime i prezime,e-mail,server` where `server` is the student VM number (1–20). This file is gitignored — keep it local.

## Merging first attempt + retake results

After a retake exam, produce a combined report where retake students get the better of their two scores:

```bash
python3 scripts/exam-report.py \
  --merge-csv ansible/exam-results/<course>/archive/<course>-<year>-<month>.csv \
  --merge-retake ansible/exam-results/<course>/archive/<course>-retake-<year>-<month>-<day>/retake-<year>-<month>-<day>.csv \
  --csv ansible/exam-results/<course>/archive/<course>-combined-<year>-<month>.csv \
  --html ansible/exam-results/<course>/archive/<course>-combined-<year>-<month>.html

# Example for RH124 May 2026:
python3 scripts/exam-report.py \
  --merge-csv ansible/exam-results/rh124/archive/rh124-2026-05.csv \
  --merge-retake ansible/exam-results/rh124/archive/rh124-retake-2026-05-07/retake-2026-05-07.csv \
  --csv ansible/exam-results/rh124/archive/rh124-combined-2026-05.csv \
  --html ansible/exam-results/rh124/archive/rh124-combined-2026-05.html
```

Matching is done by JMBAG. For each retake student the higher total wins; the output CSV includes `retake` (yes/no) and `first_attempt_total` columns. Commit the combined files to archive.

## Status

**Fully implemented:**
- Terraform: student VMs (VM IDs 200–219) + second disk per VM
- Ansible: exam provisioning role, grading playbook, reset playbook
- Repo VM: DNF repo + exam portal (static HTML, all 20 variants)
- Python: exam report script (CSV + HTML)
- Full pipeline tested on student-01 (100/100 with cheatsheet commands)
