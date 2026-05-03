# Instructor Runbook — RH124 Mid-Semester Practical Exam

Step-by-step lifecycle guide for running the exam from first provision to final teardown.
For task design and grading logic, see `docs/exam-rh124-design.md`.

---

## Quick reference

| Item | Value |
|---|---|
| Duration | 90 minutes |
| Students | up to 20 |
| Student VMs | student-01 through student-20, IPs 172.16.16.101–120 |
| Repo VM | 172.16.16.121 (DNF repo + exam portal) |
| Exam portal | https://vuv.bikanalabs.xyz/operacijski-sustavi/exam/ |
| Student SSH | `ssh student@vuv.bikanalabs.xyz -p 220X` (X = seat number) |
| Instructor SSH to VM | `ssh -J root@135.181.128.170 ansible@172.16.16.10X` |
| Proxmox host | `root@135.181.128.170` |

---

## Lifecycle overview

```
Phase 1 — Provision        terraform apply → exam-provision.yml → repo-provision.yml
Phase 2 — Exam day         open DNAT → write board → invigilate
Phase 3 — Grading          reboot all VMs → exam-grade.yml → exam-report.py
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
| `STUDENT_PASSWORD` | Plaintext SSH password — written on the board and shown in the exam portal |
| `STUDENT_PASSWORD_HASH` | Hashed version injected into VMs via cloud-init (`openssl passwd -6 'yourpassword'`) |
| `STUDENT_COUNT` | Number of student VMs to create (1 for testing, up to 20 for a full class) |

### 1.2 Provision student VMs with Terraform

```bash
source setup.sh
cd terraform
terraform init    # only needed on first run or after provider changes
terraform apply
```

This creates the student VMs and the repo VM on Proxmox. Cloud-init runs automatically on first boot and sets up the `student` and `ansible` users. Wait about 60 seconds after `apply` completes before running Ansible.

Verify cloud-init has finished:

```bash
cd ../ansible
ssh-add ~/.ssh/id_ed25519
ansible students -m ping
```

All hosts should respond with `pong`. If some fail, wait another 30 seconds and retry.

### 1.3 Provision student VMs for the exam

```bash
ansible-playbook exam-provision.yml
```

This runs on all student VMs and sets the exam state: creates the `dbteam` group, stops/disables `crond`, ensures `rsyslog` is running, pre-installs `tmux`, plants the graded files, formats the second disk as XFS (without mounting), writes the provisioning timestamp, and deploys the `grade` and `hint` scripts.

Takes ~5–10 minutes for a full class of 20. Verify with a spot-check:

```bash
ansible students -m shell -a "ls /usr/local/bin/grade /usr/local/bin/hint" --become
```

### 1.4 Provision the repo VM

```bash
ansible-playbook repo-provision.yml \
  --extra-vars "student_password=$(grep ^STUDENT_PASSWORD= ../.env | cut -d= -f2)"
```

This installs Apache, builds the local DNF package repository with `createrepo`, and deploys all 20 per-student exam portal HTML pages with the student password rendered in the intro section.

Verify from the Proxmox host:

```bash
ssh root@135.181.128.170 \
  "curl -s http://172.16.16.121/repo/repodata/repomd.xml | head -3 && curl -so /dev/null -w '%{http_code}' http://172.16.16.121/exam/"
```

Expected: XML output followed by `200`.

### 1.5 End-to-end test (recommended before any real exam)

Use `docs/instructor-cheatsheet.md` to solve all 6 tasks on student-01, run `grade` and confirm 100/100, then reset and re-provision that VM:

```bash
ssh -J root@135.181.128.170 student@172.16.16.101
# ... complete all tasks per cheatsheet, run grade ...

# Back on your machine:
cd ansible
ansible-playbook exam-reset.yml -l student-01
ansible-playbook exam-provision.yml -l student-01
```

---

## Phase 2 — Exam day

### 2.1 Checklist before students arrive

- [ ] `ansible students -m ping` — all VMs respond
- [ ] Repo VM is serving DNF repo and exam portal (verified in 1.4)
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
Zadaci:    https://vuv.bikanalabs.xyz/operacijski-sustavi/exam/
           → unesite broj sa svog mjesta

SSH:       ssh student@vuv.bikanalabs.xyz -p 220X
           (X = vaš broj mjesta, npr. mjesto 3 → port 2203)

Lozinka:   [vrijednost STUDENT_PASSWORD iz .env]

Trajanje:  90 minuta
```

### 2.4 Seat assignment

Each seat number maps directly to a student VM and SSH port. Students enter their seat number in the exam portal to get their personalised task sheet.

Students 11–20 have the same package variant as students 01–10 respectively — do not seat these pairs next to each other. See the variant table in `docs/exam-rh124-design.md` section 2.

### 2.5 During the exam

- Students work independently on their own VM
- The `grade` and `hint` scripts are freely available — running them costs no points
- If a VM becomes unreachable, SSH in directly as the ansible user to investigate:

```bash
ssh -J root@135.181.128.170 ansible@172.16.16.10X
```

---

## Phase 3 — Grading

### 3.1 Reboot all VMs

After time is called, reboot all student VMs. The grading script verifies post-reboot state for Task 4 (service persistence) and Task 6 (fstab mount persistence). A reboot is required for full marks on those tasks.

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
ansible-playbook exam-grade.yml
```

SSHes into every VM, runs the same checks as the student `grade` script, and writes a JSON result file per student to `ansible/exam-results/`. To re-grade a single student:

```bash
ansible-playbook exam-grade.yml -l student-05
```

### 3.3 Generate the report

```bash
cd ..
python3 scripts/exam-report.py
```

Outputs:
- `ansible/exam-results/report.csv` — import into a spreadsheet
- `ansible/exam-results/report.html` — open in a browser for a formatted view with per-check detail

### 3.4 Close student SSH ports

Once grading is done, close the DNAT rules so the exam ports are no longer publicly reachable. Run from `proxmox-homelab/foundation/ansible/`:

```bash
ansible-playbook playbooks/site.yml --tags exam_dnat \
  --extra-vars "dnat_action=remove student_count=20"
```

---

## Phase 4 — Post-exam review (optional)

After the exam you may want to keep the VMs available for the next lab class so students can review their results and go through the solutions with you.

### Keep VMs running

No action needed — VMs stay up after grading. A student can SSH in the same way they did during the exam and run `grade` to see their results. Note that DNAT ports are closed after phase 3, so for a review session you will need to re-open them:

```bash
# Re-open ports for the review session
ansible-playbook playbooks/site.yml --tags exam_dnat \
  --extra-vars "dnat_action=add student_count=20"

# Close again after the session
ansible-playbook playbooks/site.yml --tags exam_dnat \
  --extra-vars "dnat_action=remove student_count=20"
```

### Shut down VMs between exam day and review session

If the review session is days away and you want to free up Proxmox resources in the meantime, shut the VMs down rather than destroying them — their state is preserved and they can be started again before the review:

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

---

## Phase 5 — Teardown

Once results are saved and review sessions are done, destroy the exam environment to free the Proxmox host for other use.

### 5.1 Back up results

`ansible/exam-results/` is gitignored and will be lost on `terraform destroy`. Archive before proceeding:

```bash
cp -r ansible/exam-results/ ~/Desktop/exam-results-$(date +%Y%m%d)/
```

### 5.2 Destroy all VMs

```bash
source setup.sh
cd terraform
terraform destroy
```

This removes all student VMs and the repo VM from Proxmox. The Proxmox host itself is unaffected.

### 5.3 Reset for next time

After destroy, set `STUDENT_COUNT=1` in `.env` so the next `terraform apply` starts with a single test VM rather than the full class:

```bash
# In .env:
STUDENT_COUNT=1
```

The Proxmox host is now free for other projects. When the next exam cycle comes around, start again from Phase 1.

---

## Retake / same exam, new VMs

If VMs have been destroyed but you need to run the same exam again (retake group, etc.), just go through Phase 1 again from scratch — `terraform apply` will create fresh VMs from the cloud-init template.

If VMs are still running and you just need to reset their state to a clean exam start:

```bash
cd ansible
ansible-playbook exam-reset.yml       # undo all exam state
ansible-playbook exam-provision.yml   # re-apply clean exam state
```
