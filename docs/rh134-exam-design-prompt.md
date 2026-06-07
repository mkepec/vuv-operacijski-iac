# Prompt: Design the RH134 Mid-Semester Performance Exam

Use this prompt to start a fresh session whose only job is to **produce a design document**
(`docs/rh134/exam-rh134-design.md`), mirroring what we did for RH124. Do not implement
anything in this session — design only.

---

## Prompt to paste into a new session

> I need you to design a performance-based practical exam for RH134 (Red Hat System
> Administration II), the same way we designed the RH124 mid-semester exam. Read
> `CLAUDE.md` and `docs/exam-rh124-design.md` first — that document is the reference
> template for structure, depth, and tone. Your output should be a new design document
> at `docs/rh134/exam-rh134-design.md`, structured the same way (infrastructure
> requirements, per-student variation, task list with grading checks, grading tools,
> Ansible provisioning requirements, Terraform requirements, file layout, open items
> by session).
>
> ### Background
>
> - This is for Virovitica University of Applied Sciences (VUV), RHCSA-track course
>   RH134, instructor Marin Kepec.
> - We already ran the RH124 exam successfully (see `docs/exam-rh124-design.md` and
>   `docs/exam-rh124-design.md`'s "Status" section in `CLAUDE.md` — fully implemented,
>   tested, graded, archived). This RH134 exam reuses the same pipeline pattern:
>   Terraform provisions VMs → Ansible provisions the exam content → students take the
>   exam → Ansible grades → Python generates the report.
> - **Same constraints apply:** 90 minutes, 100 points, up to 20 students taking the
>   exam simultaneously, on the same Hetzner Proxmox host (64 GB RAM total, currently
>   running the 20 student VMs at 3072 MB each — budget carefully if you're proposing
>   additional always-on infrastructure).
> - **Read the student labs before designing tasks:** `tmp/rh134-labs/` contains every
>   lab the students completed this semester (filenames like `10.5_lab.md`,
>   `11.7_lab.md`, plus a `comprehensive-review/` subfolder with end-of-section review
>   labs). These are the actual exercises students practiced — **the exam must not be
>   harder than what's in these labs.** Stay at or below that difficulty level. Pull
>   task ideas, terminology, and realistic scenarios directly from this material so the
>   exam feels familiar rather than novel.
>
> ### Hard constraints (carried over from RH124, do not relax)
>
> 1. **No networking tasks that can break the student's SSH session.** RH124 excluded
>    networking entirely for this reason — it stands for RH134 too, even though
>    students are more advanced. If you include firewall/SELinux-for-services tasks
>    (e.g. from the `14.5_lab.md` netsecurity material), make sure no task requires
>    touching the interface or port the student's SSH session depends on, and no task
>    can leave the box unreachable if done wrong (e.g. don't have students reload
>    firewalld with a bad default zone, don't have them set a SELinux boolean that
>    blocks sshd, don't have them change the default systemd target to something that
>    drops network).
> 2. **NATO phonetic per-student variation, same pattern as RH124.** Reuse the
>    alpha/bravo/charlie/... → student-01..20 mapping idea (see
>    `docs/exam-rh124-design.md` section 2) so neighbors can't copy-paste answers.
>    Decide what should vary per student for RH134 topics — e.g. LV/VG names, mount
>    point paths, container image tags, log file names, tuned profile names, archive
>    filenames, NFS share subdirectory names, cron job names/schedules, SELinux
>    booleans/contexts, swap sizes, partition labels. Bake these into inventory host
>    vars exactly like RH124 did with `exam_variant`, `exam_gid`, etc.
> 3. **6 tasks, 100 points, ~90 minutes, difficulty curve Easy → Medium-Hard** — same
>    shape as RH124 (15/20/20/15/15/15 or similar split; tune as needed for RH134
>    topic weight).
> 4. **Same grading/reporting pipeline** — student-side `grade`/`hint` scripts rendered
>    from Jinja2, instructor Ansible playbook (`exam-grade.yml`) writing JSON per host,
>    `scripts/exam-report.py` producing CSV/HTML. Reuse these tools — only the task
>    *content* and *checks* differ. Don't redesign the pipeline.
> 5. **Idempotent, rerunnable provisioning and reset**, same as RH124
>    (`exam-provision.yml` / `exam-reset.yml` pattern), so this can be reused for
>    retakes and for a possible future combined RH124+RH134 comprehensive exam.
>
> ### New consideration: shared lab server VM
>
> Several RH134 topics are inherently client/server (NFS automounter, Podman registry,
> rsync/scp targets, remote log aggregation). Rather than give each student a second
> VM (we don't have RAM headroom for 40 VMs at 3 GB each — we're capped at 64 GB and
> already running 20), **design one additional shared "lab server" VM** that all 20
> students connect to for the relevant task(s) — similar in spirit to the existing
> repo VM (172.16.16.121) but serving exam content instead of packages.
>
> Things to work out in the design:
> - What should this VM serve? Pick from what the labs actually exercise — e.g. an
>   NFS server exporting per-student or shared directories (mirroring `15.5_lab.md`'s
>   servera/serverb pattern), a container registry for Podman push/pull tasks
>   (mirroring `17.7_lab.md`), an rsync/SSH target for file-transfer tasks (mirroring
>   `8.5_lab.md`), or a syslog/journal remote-logging target (mirroring `5.11_lab.md`).
>   You don't have to support all of these — pick what gives the best task coverage
>   for the least added complexity, and justify the choice.
> - How do 20 students hit the same server concurrently without colliding? (e.g.
>   per-student exported directories/users/registry namespaces/ports — look at how
>   RH124's repo VM and per-student DNAT ports avoided collisions, and how the labs'
>   per-user NFS export permissions work.)
> - Does it need its own VM ID/IP, or can it be folded into the existing repo VM
>   (172.16.16.121, VM ID 221) to save resources? Weigh added load vs. one fewer VM.
>   State a recommendation either way.
> - What does Ansible need to provision on it before the exam, and how does the
>   instructor verify it's healthy before students start (a pre-flight check, like
>   RH124's "repo VM must be running before any student VM exam begins")?
>
> ### Topics available to draw from (from `tmp/rh134-labs/`)
>
> Skim these labs and pick ~6 task areas that (a) stay within lab difficulty,
> (b) avoid the networking/SSH-breaking risk above, and (c) give good topic spread.
> Roughly, the labs cover:
> - Shell scripting basics (`1.7`)
> - Storage: partitions, XFS, swap (`10.5`); LVM — create/resize/extend LVs (`11.7`)
> - Boot process: troubleshooting, default systemd target (`12.7`)
> - Logging: timezone, persistent journald, rsyslog routing by priority (`5.11`)
> - SELinux: modes, file contexts (`restorecon`/`semanage fcontext`), booleans (`6.9`)
> - Firewall + SELinux for services together (`14.5` — networking-adjacent, handle
>   per constraint #1 above)
> - NFS client + automounter (autofs indirect maps) (`15.5`)
> - Performance tuning: `tuned` profiles, process scheduling priority/`nice`/`renice`
>   (`9.5`)
> - File transfer: `rsync`, `scp` (`8.5`)
> - Containers: Podman — build from Containerfile, registry push/pull, run detached
>   with port mapping (`17.7`)
> - Comprehensive review labs in `comprehensive-review/` — these combine multiple
>   topics; they're a good signal for what "exam-level" combined difficulty looks like
>
> Good candidate task areas that avoid the SSH-breaking risk and fit a 90-minute
> performance exam: LVM (create/extend/mount a logical volume), SELinux file contexts
> and booleans (without touching sshd-related ones), persistent journald + rsyslog
> routing, tuned profiles + process priority, rsync/scp file transfer, Podman
> build/run/registry workflow, NFS automounter client config against the shared lab
> server, swap space management, cron/systemd timers. Use your judgment — these are
> starting points, not a mandate.
>
> ### What "not harder than the labs" means in practice
>
> The labs are scaffolded practice exercises — they tell students what to do in
> sequence with example commands shown. The exam should ask students to *produce the
> same category of result* from instructions alone (no example commands, the way
> RH124's task sheet describes outcomes and constraints, not command sequences), but
> should not require:
> - combining more moving parts than the hardest single lab does
> - any topic, flag, or tool that doesn't appear in `tmp/rh134-labs/`
> - multi-step troubleshooting chains longer than what `12.7_lab.md` (boot
>   troubleshooting) already exercises
>
> If you're unsure whether something is in scope, check whether it appears in the labs
> folder — if it doesn't, leave it out.
>
> ### Deliverable
>
> Write `docs/rh134/exam-rh134-design.md` following the structure of
> `docs/exam-rh124-design.md`:
> 1. Infrastructure requirements (student VMs — reuse existing 200–219 — and the new
>    shared lab server VM; any new disks/storage needed for LVM tasks)
> 2. Per-student variation (NATO phonetic mapping + table of variant values + inventory
>    var design)
> 3. Exam tasks (6 tasks with point breakdown, student instructions, ansible
>    provisioning needed, grading checks table — same format as RH124's task sections) But 6 is not actual exact number, during the desing you will provide the recommended tasks we should cover
> 4. Grading tools (student `grade`/`hint` scripts, instructor Ansible playbook, JSON
>    output format, exam task portal — reuse RH124's design, note what's identical vs.
>    what needs RH134-specific values)
> 5. Ansible provisioning role requirements (numbered checklist like RH124 section 5)
> 6. Terraform requirements (what's new — e.g. extra disk/LV setup for storage tasks,
>    the shared lab server VM resource)
> 7. File/directory layout — propose splitting `docs/` and `ansible/` into per-exam
>    subfolders now that there's more than one exam (e.g. `docs/rh124/`, `docs/rh134/`,
>    `ansible/rh124/`, `ansible/rh134/`, or a shared `ansible/roles/` with per-exam
>    playbooks — your call, but state the reasoning, and keep in mind a likely future
>    combined RH124+RH134 comprehensive exam that may want to reuse pieces of both)
> 8. Open items by session (mirror RH124's session breakdown: provisioning, grading,
>    reporting)
>
> Ask me clarifying questions if anything about infrastructure limits, scheduling, or
> task selection is unclear before you finalize the design. Don't write any
> implementation code in this session — design document only.

---

## Notes for whoever runs this prompt

- This prompt assumes `tmp/rh134-labs/` still exists at
  `vuv-operacijski-iac/tmp/rh134-labs/` with the lab markdown files. If it's been
  moved or cleaned up, point the new session at wherever the labs now live (or copy
  them back in) before running this — the design quality depends on grounding task
  difficulty in real lab content, not generic RH134 curriculum knowledge.
- The shared lab server VM is the biggest open architectural question — expect the
  design session to spend real effort there. Push back if it proposes something that
  won't fit in the remaining RAM budget (20 student VMs × 3072 MB = ~61 GB already;
  there's very little headroom on a 64 GB host — folding the new server into the
  existing repo VM, or keeping it small, is probably the right call).
- Once this design doc exists and is reviewed, the implementation will follow the same
  session breakdown RH124 used (provisioning → grading → reporting), each as its own
  prompt/session.
