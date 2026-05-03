# Instructor Runbook — RH124 Mid-Semester Practical Exam

Step-by-step operational guide for running the exam. For task design and grading logic, see `docs/exam-rh124-design.md`.

---

## Overview

| Item | Value |
|---|---|
| Duration | 90 minutes |
| Students | up to 20 |
| Student VMs | student-01 through student-20, IPs 172.16.16.101–120 |
| Repo VM | 172.16.16.121 (DNF repo + exam portal) |
| Exam portal | https://vuv.bikanalabs.xyz/operacijski-sustavi/exam/ |
| Student SSH port | 2200+N → port 2201 for student-01, 2202 for student-02, etc. |

---

## 1. Before exam day

### 1.1 Verify secrets

```bash
cat .env          # PROXMOX_API_TOKEN_SECRET, STUDENT_PASSWORD, STUDENT_PASSWORD_HASH, STUDENT_COUNT
```

- `STUDENT_PASSWORD` — the plaintext password students use to SSH in (written on the board and shown in the exam portal intro)
- `STUDENT_PASSWORD_HASH` — the hashed version injected into VMs via cloud-init
- `STUDENT_COUNT` must match the number of students attending

### 1.2 Provision VMs

```bash
source setup.sh

# Provision student VMs via Terraform
cd terraform
terraform apply

# Wait ~60 seconds for cloud-init to finish, then provision for exam
cd ../ansible
ssh-add ~/.ssh/id_ed25519
ansible-playbook exam-provision.yml
```

Provisioning takes ~5–10 minutes for a full class. Verify with a spot-check:

```bash
ansible-playbook site.yml -l student-01
```

### 1.3 Provision the repo VM

If the repo VM has not been provisioned yet (first exam or after teardown):

```bash
cd ansible
ansible-playbook repo-provision.yml --extra-vars "student_password=$(grep ^STUDENT_PASSWORD= ../.env | cut -d= -f2)"
```

This sets up Apache, builds the local DNF repo, and deploys the 20 per-student exam portal pages with the plaintext password rendered in each student's intro section.

The repo VM must be running and serving both:
- `http://172.16.16.121/repo` — DNF package repository
- `http://172.16.16.121/exam/` (and per-student pages `student-01.html` through `student-20.html`)

Quick check from the Proxmox host:

```bash
ssh root@135.181.128.170
curl -s http://172.16.16.121/repo/repodata/repomd.xml | head -3
curl -I http://172.16.16.121/exam/
```

### 1.4 Open student SSH ports (DNAT)

Run from `proxmox-homelab/foundation/ansible/`:

```bash
ansible-playbook playbooks/site.yml --tags exam_dnat \
  --extra-vars "dnat_action=add student_count=20"
```

Verify a student port is reachable:

```bash
ssh -p 2201 student@135.181.128.170   # should prompt for password
```

### 1.5 End-to-end test (optional but recommended)

Use `docs/instructor-cheatsheet.md` to solve all 6 tasks on student-01, then run `grade` — expected output is 100/100. Reset student-01 afterwards:

```bash
ansible-playbook exam-reset.yml -l student-01
ansible-playbook exam-provision.yml -l student-01
```

---

## 2. Exam day — setup

### 2.1 Checklist before students arrive

- [ ] All student VMs are up: `ansible students -m ping`
- [ ] Repo VM is up and serving DNF repo and exam portal
- [ ] DNAT ports are open (verified above)
- [ ] `exam-provision.yml` has been run on all VMs
- [ ] Write on the board (see section 2.2)

### 2.2 What to write on the board

```
Exam portal:   https://vuv.bikanalabs.xyz/operacijski-sustavi/exam/
               → enter the number from your seat

SSH:           ssh student@vuv.bikanalabs.xyz -p 220X
               (X = your seat number, e.g. seat 3 → port 2203)

Password:      [student password from .env]

Duration:      90 minutes
```

Replace `[student password from .env]` with the value of `STUDENT_PASSWORD`.

### 2.3 Seat assignment

Each seat has a fixed student number (1–20). Students enter that number in the exam portal to get their personalised task sheet, and use it to construct their SSH port (`220X`).

Prepare a printed or projected seating plan mapping seat numbers to student numbers if your room layout is non-sequential.

---

## 3. During the exam

- Students work independently; each has a unique variant (see `docs/exam-rh124-design.md` section 2 for variant table)
- Students 11–20 reuse the same packages as 01–10 respectively — do not seat these pairs next to each other
- The `grade` and `hint` scripts are available on every VM; students can run them freely
- If a student's VM becomes unreachable, SSH directly as ansible user to investigate:

```bash
ssh -J root@135.181.128.170 ansible@172.16.16.10X
```

---

## 4. End of exam — grading

### 4.1 Reboot all VMs

After time is called, reboot all student VMs. This is required because:
- Task 4 (service state) is verified after reboot
- Task 6 (fstab mount) is verified after reboot
- The grading script checks whether a reboot has occurred since provisioning

```bash
cd ansible
ansible students -m shell -a "systemctl reboot" --become
```

Wait 60–90 seconds for all VMs to come back up:

```bash
ansible students -m ping    # repeat until all respond
```

### 4.2 Run the grading playbook

```bash
ansible-playbook exam-grade.yml
```

This SSHes into every VM, runs the same checks as the student `grade` script, and writes a JSON result file per student to `ansible/exam-results/`.

To re-grade a single student (e.g. after investigating a borderline case):

```bash
ansible-playbook exam-grade.yml -l student-05
```

### 4.3 Generate the report

```bash
cd ..
python3 scripts/exam-report.py
```

Outputs:
- `ansible/exam-results/report.csv` — import into a spreadsheet
- `ansible/exam-results/report.html` — open in a browser for a formatted view with per-check detail

---

## 5. After the exam

### 5.1 Close student SSH ports

```bash
# From proxmox-homelab/foundation/ansible/
ansible-playbook playbooks/site.yml --tags exam_dnat \
  --extra-vars "dnat_action=remove student_count=20"
```

### 5.2 Back up results

`ansible/exam-results/` is gitignored. Copy or archive before tearing down:

```bash
cp -r ansible/exam-results/ ~/Desktop/exam-results-$(date +%Y%m%d)/
```

### 5.3 Tear down

```bash
source setup.sh
cd terraform
terraform destroy
```

Set `STUDENT_COUNT=1` in `.env` after teardown so the next `terraform apply` starts with a single test VM.

---

## 6. Re-take / repeat exam

To reuse the same VMs for a retake:

```bash
cd ansible
ansible-playbook exam-reset.yml       # undo all exam provisioning
ansible-playbook exam-provision.yml   # re-provision clean state
```

The reset playbook undoes everything: removes planted files, reverses service state, removes the grade/hint scripts, uninstalls tmux re-preinstall, etc.
