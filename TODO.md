# TODO

Exam infrastructure for VUV Operacijski Sustavi course.
Full design: `docs/exam-rh124-design.md`

---

## Phase 1 — Design
- [x] RH124 exam task design (6 tasks, point values, difficulty tiers)
- [x] Per-student variation scheme (NATO alphabet, inventory host vars)
- [x] Grading tool design (grade script, hint script, instructor playbook, report)
- [x] Exam task portal design (static HTML on repo VM)
- [x] Infrastructure requirements (repo VM, second disk per student VM)

## Phase 2 — Infrastructure + Provisioning
- [x] `terraform/main.tf` — add second disk (2 GB, scsi1) per student VM
- [x] `ansible/inventory.yml` — add per-host exam vars for all 20 students
- [x] `ansible/roles/exam-provision/tasks/main.yml` — provisioning role
- [x] `ansible/roles/exam-provision/templates/grade.sh.j2` — grading script template (chmod 755)
- [x] `ansible/roles/exam-provision/templates/hint.sh.j2` — hint script template
- [x] `ansible/roles/exam-provision/templates/exam-tasks.txt.j2` — fallback text task sheet
- [x] `ansible/exam-provision.yml` — exam provisioning playbook
- [x] `ansible/exam-reset.yml` — reset VMs to clean state
- [x] Repo VM provisioning playbook (DNF repo + Apache/nginx)
- [x] Exam portal HTML (Jinja2 template, all 20 variants embedded as JS)
- [x] `docs/instructor-cheatsheet.md` — exact commands to complete all 6 tasks (alpha variant), for end-to-end testing and grading verification
- [x] Test full provisioning cycle on student-01

## Phase 3 — Grading (after exam dry-run or real exam)
- [ ] Refine `grade.sh.j2` based on observed results
- [x] `ansible/exam-grade.yml` — instructor post-exam grading playbook

## Phase 4 — Reporting
- [x] `scripts/exam-report.py` — reads JSON results, produces CSV + HTML
- [x] Test full grading → report pipeline

## Future
- [ ] RH134 mid-semester exam design (after RH134 labs are complete)
- [ ] Final end-of-semester exam design (combined RH124+RH134, multi-step scenario)
- [x] Translate exam task sheet to Croatian (`exam-tasks.txt.j2` and exam portal)
- [x] Translate hint script to Croatian (`hint.sh.j2`)
