# Prompt: Restructure the Repo for Multi-Exam Support and Begin RH134 Implementation

Use this prompt to start a fresh session whose job is to (1) restructure `docs/`,
`ansible/`, and (if needed) `terraform/` so RH124 and RH134 exams cleanly coexist,
and (2) begin implementing the RH134 exam per its design document. This is an
**implementation** session — unlike the design session, this one writes code,
playbooks, and Terraform.

---

## Prompt to paste into a new session

> I need you to do two things in this session, in order:
>
> 1. **Restructure the repo** so RH124 and RH134 exam artifacts are cleanly
>    separated, with shared pieces (inventory, report script, common roles)
>    staying shared — laying groundwork for a likely future **third exam that
>    combines RH124+RH134 topics** (a comprehensive end-of-semester exam).
> 2. **Begin RH134 implementation**, following the design at
>    `docs/rh134/exam-rh134-design.md` and the session breakdown in its §8
>    ("Open Items by Session" → "Session 2 — Infrastructure + Provisioning").
>
> Read these first, in this order:
> - `CLAUDE.md` — infrastructure context, standard workflow, current status
> - `docs/rh134/exam-rh134-design.md` — the full RH134 design (tasks, variation
>   scheme, provisioning requirements, the proposed restructure in §7, and the
>   open items in §8)
> - `docs/exam-rh124-design.md` — the RH124 reference design (for comparing what
>   already exists vs. what's RH134-specific)
> - `TODO.md` — current status; RH124 is "fully implemented", RH134 design is
>   marked done, RH134 implementation has not started
>
> ### Part 1 — Repo restructure
>
> The RH134 design doc (§7) already proposes a target layout. Use it as your
> starting point, but treat it as a proposal to validate and adjust, not a
> blueprint to follow blindly — check it against what actually exists before
> moving anything.
>
> **Current state (as of this writing):**
> - `docs/` is flat: `exam-rh124-design.md` sits next to the new `rh134/` subfolder
>   (which currently holds only `exam-rh134-design.md`). `instructor-cheatsheet.md`,
>   `instructor-runbook.md`, and `timing-report.md` are RH124-specific but live at
>   the top level.
> - `ansible/` is flat: `exam-provision.yml`, `exam-grade.yml`, `exam-reset.yml`,
>   `repo-provision.yml` are all RH124-specific but have generic names with no
>   `rh124` prefix or subfolder. `inventory.yml`, `group_vars/all.yml`,
>   `ansible.cfg`, `site.yml`, and `manage-ansible-keys.yml` are shared/general.
>   `exam-results/` holds RH124's JSON results and archived CSV/HTML reports.
>   There's no `roles/` directory yet — check whether one exists or whether
>   provisioning logic lives directly in the playbooks (read `exam-provision.yml`
>   to find out).
> - `terraform/` is a single flat module: `main.tf` defines exactly two
>   `proxmox_virtual_environment_vm` resources — `repo` (the shared services VM,
>   172.16.16.121) and `student` (the for_each-based 20-VM resource, IDs 200–219).
>   The student VM resource currently has **two** `disk` blocks (the primary OS
>   disk and RH124's pre-formatted second disk on `scsi1`).
>
> **What needs to change — work through these questions and implement your
> conclusions:**
>
> 1. **`docs/`**: Move `exam-rh124-design.md` into a new `docs/rh124/` to mirror
>    the existing `docs/rh134/`. Decide whether `instructor-cheatsheet.md`,
>    `instructor-runbook.md`, and `timing-report.md` are RH124-specific (move them
>    into `docs/rh124/`) or general-purpose (leave them at top level, or rename to
>    make their scope obvious) — read them to find out, don't guess.
>
> 2. **`ansible/`**: Decide between the layout the design doc proposes
>    (`ansible/rh124/{exam-provision,exam-grade,exam-reset}.yml` +
>    `ansible/rh134/...` + shared `ansible/roles/`) versus a flatter alternative
>    (keep playbooks at top level but prefix filenames, e.g. `rh124-exam-provision.yml`).
>    Whichever you choose, the goals are: (a) it should be obvious at a glance
>    which playbook belongs to which exam, (b) shared roles/templates that both
>    exams can use should not be duplicated, (c) `exam-results/` should separate
>    RH124 and RH134 output (e.g. `exam-results/rh124/` and `exam-results/rh134/`)
>    without breaking the existing archive naming convention documented in
>    `CLAUDE.md` ("Archiving past exam results" section). State your reasoning for
>    the choice in a short note (in the session, not as a new doc file) before
>    doing the `git mv`.
>
> 3. **`terraform/`**: This is the part that most needs your judgment — the prompt
>    author isn't sure whether a restructure is needed here at all. Investigate and
>    decide:
>    - RH134's design (§1.3 and §6 of `docs/rh134/exam-rh134-design.md`) requires a
>      **third disk** on each student VM: 1 GB, raw/unpartitioned, on `scsi2`,
>      appearing as `/dev/sdb` — used only for the RH134 LVM task. RH124's existing
>      second disk (`scsi1`, pre-formatted XFS, `/dev/sdb`) must keep working for
>      RH124 retakes and any future RH124 reruns.
>    - Should both disks be **unconditionally** attached to every student VM
>      (simplest — no Terraform restructure needed, just add a third `disk` block;
>      costs a small amount of extra storage per VM whether or not that exam is
>      running), or should disk attachment be **conditional** on which exam is
>      being provisioned (more complex — needs a Terraform variable like
>      `active_exam = "rh124" | "rh134" | "both"` gating which disk resources/blocks
>      apply, via `count` or `for_each` conditionals)?
>    - Factor in the constraint that **a future combined RH124+RH134 exam** will
>      likely need *both* disks present simultaneously — does that tip the balance
>      toward "just always attach both, it's cheap" rather than building
>      conditional infrastructure you'll just disable for the combined exam anyway?
>    - Check actual remaining disk headroom: the Proxmox host has 476 GB NVMe on
>      `local-lvm`; 20 VMs × 20 GB primary + up to 20 × (2 GB + 1 GB) extra = how
>      much is that, and is it comfortable? Do the arithmetic before recommending.
>    - Recommend an approach and implement it. If you recommend "just always attach
>      both disks," that's a valid, even preferable, outcome — don't manufacture
>      complexity. Update `terraform/main.tf` (and `variables.tf`/`outputs.tf` if
>      needed) accordingly. **Do not run `terraform apply`** — planning and code
>      changes only; applying provisions real infrastructure and costs money/time,
>      and should be a deliberate separate step the user runs themselves.
>
> 4. After moving files, grep the whole repo for references to old paths
>    (`docs/exam-rh124-design.md`, `ansible/exam-provision.yml`, etc. — check
>    `CLAUDE.md`, `TODO.md`, other docs, playbook `import_playbook`/`include_tasks`
>    statements, and any READMEs) and update them. A restructure that leaves stale
>    path references is worse than no restructure.
>
> ### Part 2 — Begin RH134 implementation (Session 2 scope from the design doc)
>
> Once the restructure is done and committed, start working through the RH134
> design's §8 "Session 2 — Infrastructure + Provisioning" checklist:
>
> - Add the RH134 disk resource to Terraform (per your Part 1 decision)
> - Update `ansible/inventory.yml` with all `rh134_*` per-host variables — the
>   design doc §2.2 shows the exact variable block structure and §2.1 has the
>   full 20-student variant table (LV/VG names, rsyslog facility.priority,
>   NFS export dirs, Podman ports, backup dir names)
> - Implement the RH134 provisioning role (tasks listed in design doc §5.1 —
>   12 numbered actions, e.g. ensuring `/dev/sdb` stays raw, planting the T4
>   file-transfer anchor tree with distinguishable permissions, pre-pulling the
>   Podman base image, enabling user lingering for persistent containers)
> - Extend the repo VM provisioning to add the new NFS-server role (design doc
>   §5.2 — installing `nfs-utils`, creating 20 per-student exports, planting
>   `welcome.txt` anchors, configuring `/etc/exports`, creating the `student` OS
>   account needed by Tasks 4 and 5)
> - Write the three Jinja2 templates (`exam-tasks.txt.j2`, `grade.sh.j2`,
>   `hint.sh.j2`) — you can use the existing RH124 templates as a structural
>   reference for format and conventions, but the content (task instructions,
>   grading checks, hints) must be written fresh from the RH134 design doc §3
>
> **Important — pacing:** This is a lot of work. Don't try to finish all of
> Session 2 in one sitting if it doesn't fit. Get the restructure solid and
> committed first (that's the foundation everything else sits on), then make
> visible progress on the provisioning pieces, and tell me clearly what's done
> vs. what's left for a follow-up session. Use a plan (not just a task list) for
> the restructure specifically, since file moves are hard to cleanly undo — show
> me the plan before executing it.
>
> ### Constraints
>
> - **Do not run `terraform apply`, `terraform destroy`, or any Ansible playbook
>   that touches live infrastructure** (provisioning, grading, reset). This
>   session is about writing and organizing code/config, not running it against
>   the real Proxmox host or student VMs. Validate Terraform changes with
>   `terraform plan` only if you want to sanity-check syntax — even that touches
>   the TF Cloud workspace, so ask first.
> - **Git operations**: file moves (`git mv`) and commits for the restructure are
>   expected and fine — but keep the restructure as its own commit(s), separate
>   from the RH134 implementation work, so either can be reviewed/reverted
>   independently. Ask before pushing.
> - If you find that the design doc and the actual current repo state disagree
>   on some assumption (e.g. a file that the design doc assumed exists doesn't,
>   or `exam-provision.yml` already has a `roles/` structure the design doc didn't
>   account for), trust the repo and flag the discrepancy — don't force the repo
>   to match the doc, and don't force the doc's assumptions onto code that doesn't
>   fit them.

---

## Notes for whoever runs this prompt

- This prompt assumes the restructure proposed in `docs/rh134/exam-rh134-design.md`
  §7 is still the right shape. If significant repo changes have happened since
  this prompt was written (new exams added, RH124 re-run with structural changes,
  etc.), re-validate that proposal against current reality before following it.
- The Terraform question (conditional vs. always-attach disks) is explicitly left
  open for the implementing session to resolve with real arithmetic — don't
  pre-decide it here. The "always attach both, it's cheap, and the combined exam
  needs both anyway" argument is fairly strong, but let the session do the actual
  disk-space math against the 476 GB NVMe budget before committing to it.
- Expect this to span more than one session. The prompt asks the agent to pace
  itself and report back what's done vs. outstanding — that's intentional; don't
  be surprised if "Session 2" work needs a "Session 2b".
- Before running this, confirm `tmp/rh134-labs/` either still exists or isn't
  needed anymore — Part 2 (provisioning) shouldn't need the raw lab content again
  (the design doc already distilled what's needed), but if templates need example
  scenarios reworded, having the labs handy doesn't hurt.
