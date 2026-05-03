# Infrastructure Timing Report — RH124 Mid-Semester Exam

Measured on a dedicated Hetzner EX44 server (Intel i5-13500, 64 GB RAM, 476 GB NVMe)
running Proxmox VE. All VMs cloned from a single AlmaLinux 10 cloud-init template (VM 9002).
Terraform executed locally (MacBook Air) against the Proxmox API over the public internet.
Ansible executed locally via ProxyJump through the Proxmox host.

**Scope:** 20 student VMs (VM IDs 200–219, IPs 172.16.16.101–120) + 1 repo VM (VM ID 221).

---

## Timing Summary

| Phase | Command | Wall time | Frequency |
|---|---|---|---|
| VM provisioning | `terraform apply` | ~4 min 20 sec | Once per exam season (or on demand) |
| VM teardown | `terraform destroy` | — | Once per exam season |
| Cloud-init wait | — | ~60–90 sec | Automatic after Terraform |
| Repo VM configuration | `ansible-playbook repo-provision.yml` | 1 min 12 sec | Once per exam season |
| Student VM exam setup | `ansible-playbook exam-provision.yml` | 37 sec | Once per exam |
| Exam reset | `ansible-playbook exam-reset.yml` | 10 sec | After exam (before retake) |
| Post-exam grading | `ansible-playbook exam-grade.yml` | 10 sec | Once per exam |
| Report generation | `python3 exam-report.py` | < 1 sec | On demand |

**Total instructor time from zero to exam-ready: approximately 6–7 minutes.**  
**Total grading-to-report time: approximately 10 seconds.**

---

## Phase Details

### 1. VM Provisioning — `terraform apply` (~4 min 20 sec)

Terraform provisions all 21 VMs in parallel by calling the Proxmox API. Each VM is a full
clone of the AlmaLinux 10 template: disk image copied on local-lvm, cloud-init snippet
uploaded, network and hardware configuration applied, and VM started. The second disk
(1 GB, VirtIO) is attached to each student VM at this stage.

Two runs were measured: 4 min 19 sec and 4 min 21 sec (both after a fresh destroy/re-apply
cycle). Times are consistent. The conservative figure of ~5 minutes should be used when
planning exam day logistics to account for Proxmox load variability.

Terraform state is stored in Terraform Cloud (remote state, local execution mode), so no
local state file management is required.

### 2. Cloud-init Wait (~60–90 sec, not timed separately)

Terraform completes as soon as VMs are started — it does not wait for the OS to finish
first-boot initialization. Cloud-init runs inside each VM after boot and performs:

- Hostname assignment
- Creation of `student` (password auth) and `ansible` (SSH key only) users
- SSH public key injection into the `ansible` user
- Installation of `qemu-guest-agent` (required for Proxmox VM lifecycle management)

All 20 student VMs were reachable via Ansible (SSH through ProxyJump) within 60–90 seconds
of Terraform completing. This wait is a characteristic of VM boot time, not of the
provisioning tooling, and cannot be parallelized further.

Readiness can be verified with:
```
ansible students -m ping
```

### 3. Repo VM Configuration — `ansible-playbook repo-provision.yml` (1 min 12 sec)

This playbook configures the repo VM (172.16.16.121) as a local DNF package mirror and
deploys the exam task portal. It performs three main operations:

- Downloads exam packages from upstream AlmaLinux mirrors using `dnf download --resolve`
  and runs `createrepo_c` to generate repository metadata (~50–60 sec, network-bound)
- Installs and starts Apache (`httpd`) to serve the repo and exam portal over HTTP
- Renders and deploys 20 per-student HTML task sheet pages + index via Jinja2 templates

The majority of the time is package downloading. This step is run once per exam season
(not before every exam), so the ~72 seconds is a one-time cost. On a re-run the download
and createrepo steps are skipped entirely (guarded by a check for `repodata/repomd.xml`),
making subsequent runs take only a few seconds.

### 4. Student VM Exam Setup — `ansible-playbook exam-provision.yml` (37 sec)

This playbook runs across all 20 student VMs in parallel (`forks = 20` in `ansible.cfg`,
`gather_facts = false`). Each VM receives:

- Pre-created `dbteam` group with per-student GID
- Service state: `crond` stopped/disabled, `rsyslog` started/enabled
- `tmux` installed (students must remove it as part of Task 5)
- Second disk (VirtIO, /dev/vda) partitioned and formatted as XFS
- Planted files: `/var/exam-data/record-0[123].dat` (root:root, 640), `/etc/exam-data/bigfile.dat` (>50 KB)
- Provisioning timestamp at `/var/exam-provision-time` (mtime used by grading script to verify reboot)
- Student-facing scripts: `/usr/local/bin/grade`, `/usr/local/bin/hint`

Each student VM receives a personalised configuration derived from per-host inventory
variables (variant name, username, GID, mount point, extra package, password expiry date).
All 20 VMs are provisioned in a single parallel wave, completing in 37 seconds.

### 5. Exam Reset — `ansible-playbook exam-reset.yml` (10 sec)

Undoes all changes made by the provisioning playbook: removes scripts, planted files,
the provisioning timestamp, any student-created mounts and fstab entries, wipes the second
disk partition, removes the exam user and group, and restores service state. Runs in
10 seconds across all 20 VMs (same `forks = 20`, `gather_facts = false`). Safe to run
after an exam before a retake or before destroying the VMs.

### 6. Post-Exam Grading — `ansible-playbook exam-grade.yml` (10 sec)

Run by the instructor after all students have submitted. The playbook SSHes into each of
the 20 VMs in parallel, executes `/usr/local/bin/grade all` (the on-VM grading script),
and retrieves the output. A Python helper parses each output into a structured JSON file
(`ansible/exam-results/<hostname>.json`).

The grading script checks all 6 tasks across approximately 20 individual sub-checks per VM.
The 10 sec figure was measured on freshly provisioned VMs (no student work done); on VMs
where students completed all tasks the time would be marginally longer but not meaningfully
different.

The playbook is fully idempotent and safe to rerun — the grade script only reads VM state
and the JSON result file is overwritten on each run. Re-grading a single student is
supported via `ansible-playbook exam-grade.yml -l student-01`.

### 7. Report Generation — `python3 exam-report.py` (< 1 sec)

Reads the 20 JSON result files produced by the grading playbook and generates:
- `ansible/exam-results/report.csv` — spreadsheet-ready, one row per student
- `ansible/exam-results/report.html` — browser report with per-task breakdown and class averages

At 0.08 seconds wall time, report generation is effectively instantaneous.

---

## Exam Day Sequence

The complete pre-exam workflow on exam day (assuming repo VM already configured):

```
source setup.sh && cd terraform
time terraform apply -auto-approve          # ~4 min 20 sec

# wait ~90 sec for cloud-init to complete
cd ../ansible && ssh-add ~/.ssh/id_ed25519
ansible students -m ping                    # verify all 20 VMs reachable
ansible-playbook exam-provision.yml         # ~37 sec
```

Total preparation time from zero to all 20 VMs exam-ready: **approximately 6–7 minutes**
(excluding the one-time repo VM setup of ~72 seconds).

Post-exam:

```
ansible-playbook exam-grade.yml             # ~10 sec
python3 ../scripts/exam-report.py           # < 1 sec
```

Grades for all 20 students available within **10 seconds of the exam ending**.

---

## Infrastructure Specification

| Component | Specification |
|---|---|
| Proxmox host | Hetzner EX44 — Intel i5-13500, 64 GB RAM, 476 GB NVMe |
| Student VMs (×20) | 2 vCPU, 3 GB RAM, 10 GB OS disk + 1 GB exam disk |
| Repo VM (×1) | 2 vCPU, 2 GB RAM, 20 GB disk |
| OS template | AlmaLinux 10 (cloud-init, VM ID 9002) |
| Provisioning | Terraform (bpg/proxmox provider) + Ansible |
| Student connectivity | DNAT port forwarding: port 220N → student-N:22 |
| Ansible connectivity | ProxyJump via Proxmox host → student VM private IPs |
