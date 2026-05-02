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
| Disk | 20 GB on local-lvm |
| OS user | `student` (password from `.env`) |
| SSH key | `~/.ssh/id_ed25519.pub` injected via cloud-init |
| Start on boot | false (manually started for exams) |
| Tags | exam, rhcsa, vuv |

**Network**
- All VMs on 172.16.16.0/24
- Homelab VMs occupy .2–.80; student VMs use .101–.120
- DNS: 1.1.1.1, 8.8.8.8
- Instructor Ansible reaches VMs via ProxyJump: `ssh -J root@135.181.128.170 student@172.16.16.10x`

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

**Second disk per student VM**
- 2 GB, attached as `/dev/sdb`, one partition `/dev/sdb1`, XFS formatted
- Pre-formatted by Ansible but **not mounted** — students mount it during the exam (Task 6)
- Terraform resource required in `main.tf`

## Exam project

**Full design:** `docs/exam-rh124-design.md` — read this before any exam-related session.

**Two exams planned:**
1. RH124 mid-semester — design complete, implementation not started
2. RH134 mid-semester — design not started (after RH134 labs are done)

**Key design decisions (summary):**
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

**Implementation sessions planned:**
- Session 2: Terraform disk + inventory vars + Ansible provisioning role + Jinja2 templates + exam portal HTML + repo VM playbook
- Session 3: Grading script refinement + `ansible/exam-grade.yml` (post-exam instructor playbook)
- Session 4: `scripts/exam-report.py` + full pipeline test

## Repo layout

```
vuv-operacijski-iac/
├── .env                        # secrets — gitignored, copy from .env.example
├── .env.example                # template for all secrets and config
├── setup.sh                    # sources .env, exports TF_VAR_* for Terraform
├── docs/
│   └── exam-rh124-design.md    # full exam design requirements document
├── terraform/
│   ├── versions.tf             # provider + TF Cloud backend
│   ├── variables.tf            # all input variables
│   ├── main.tf                 # proxmox_virtual_environment_vm resource (for_each)
│   ├── outputs.tf              # VM IDs, IPs, SSH hint
│   └── terraform.tfvars.example
├── ansible/
│   ├── ansible.cfg             # remote_user=student, ProxyJump configured
│   ├── inventory.yml           # static, all 20 hosts + per-host exam vars
│   ├── site.yml                # placeholder: ping + print hostname
│   ├── exam-provision.yml      # provisions all VMs before exam (planned)
│   ├── exam-grade.yml          # instructor grading playbook post-exam (planned)
│   ├── exam-reset.yml          # resets VMs to clean state (planned)
│   ├── exam-results/           # JSON grading output per host (planned)
│   └── roles/
│       └── exam-provision/
│           ├── tasks/main.yml
│           └── templates/
│               ├── exam-tasks.txt.j2
│               ├── grade.sh.j2
│               └── hint.sh.j2
└── scripts/
    └── exam-report.py          # reads exam-results JSON, produces CSV/HTML (planned)
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

# 3. Ansible (after VMs are up and cloud-init has finished, ~1 min)
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

## Status

**Working:**
- Terraform init/plan/apply tested against Proxmox — student-01 created in ~24s
- SSH via ProxyJump confirmed working
- Ansible ping + fact gather confirmed working on student-01

**Design complete, implementation not started:**
- RH124 mid-semester exam — see `docs/exam-rh124-design.md`

**Not started:**
- Terraform: second disk per student VM
- Ansible: exam provisioning role, grading playbook, reset playbook
- Repo VM: provisioning + DNF repo + exam portal
- Python: exam report script
