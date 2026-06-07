# Instructor Cheatsheet — RH134 Mid-Semester Exam (Alpha Variant)

Exact commands to complete all 6 tasks on `student-01` (variant: alpha).
Use this for end-to-end testing after provisioning and to verify the grading script produces full marks.

**Connect:**
```
ssh -p 2201 student@135.181.128.170
```

(Pattern: `ssh -p 220N student@135.181.128.170` for student N)

---

## Task 1 — Shell Scripting: Service Status Report (15 pts)

```bash
mkdir -p /home/student/bin /home/student/reports

cat > /home/student/bin/collect-alpha.sh <<'EOF'
#!/bin/bash
SERVICES="sshd crond chronyd rsyslog"
for svc in $SERVICES; do
  active=$(systemctl is-active "$svc")
  enabled=$(systemctl is-enabled "$svc")
  echo "SERVICE: $svc ACTIVE: $active ENABLED: $enabled"
done
EOF

chmod +x /home/student/bin/collect-alpha.sh

# The script prints to stdout — redirect to (over)write the report file
/home/student/bin/collect-alpha.sh > /home/student/reports/alpha-status.txt
```

**Verify:**
```bash
/home/student/bin/collect-alpha.sh   # stdout shows the 4 formatted lines directly
cat /home/student/reports/alpha-status.txt
/home/student/bin/collect-alpha.sh > /home/student/reports/alpha-status.txt
wc -l /home/student/reports/alpha-status.txt   # still 4 lines after rerun (overwrite, not append)
```

> **Note:** the script must **print** the formatted lines to stdout (per the task wording — "print one
> line in the exact format ... using the live output of `systemctl is-active`/`is-enabled`"); the
> grading check captures and validates stdout directly. Redirecting (`>`) on each run is what
> satisfies "(over)write its output ... running it twice must not duplicate lines" — `>>` inside the
> script would defeat that requirement just as surely as appending from the outside would.

---

## Task 2 — LVM: Build, Mount, and Extend Storage (20 pts)

```bash
# Partition /dev/sdb for LVM
sudo parted /dev/sdb --script mklabel gpt mkpart primary 1MiB 100% set 1 lvm on

# PV + VG
sudo pvcreate /dev/sdb1
sudo vgcreate vg_alpha /dev/sdb1

# LV (initial size), format, mount
sudo lvcreate -n lv_alpha -L 300M vg_alpha
sudo mkfs.xfs /dev/vg_alpha/lv_alpha
sudo mkdir -p /storage/alpha

UUID=$(sudo blkid -s UUID -o value /dev/vg_alpha/lv_alpha)
echo "UUID=${UUID}  /storage/alpha  xfs  defaults  0 0" | sudo tee -a /etc/fstab
sudo mount -a

# Marker file
echo 'alpha volume ready' | sudo tee /storage/alpha/marker.txt

# Extend LV and grow filesystem (without unmounting)
sudo lvextend -L +500M /dev/vg_alpha/lv_alpha
sudo xfs_growfs /storage/alpha
```

**Verify:**
```bash
sudo vgs vg_alpha
sudo lvs vg_alpha
findmnt /storage/alpha
grep storage/alpha /etc/fstab
cat /storage/alpha/marker.txt
sudo lvs -o lv_size --noheadings vg_alpha/lv_alpha   # should show ~800M
df -h /storage/alpha                                  # should reflect grown size
```

---

## Task 3 — Persistent Logging: journald + rsyslog Routing (15 pts)

```bash
# Persistent journald storage
sudo mkdir -p /var/log/journal
sudo systemctl restart systemd-journald
sudo journalctl --flush   # forces immediate migration to /var/log/journal/<machine-id>/
                          # — a bare restart alone leaves the directory empty until the
                          # next log write triggers rotation; --flush makes the check
                          # pass immediately rather than "eventually"

# Rsyslog routing rule: local0.warning -> /var/log/alpha-events
sudo tee /etc/rsyslog.d/alpha-routing.conf <<'EOF'
local0.warning    /var/log/alpha-events
EOF

# T1's baseline deliberately leaves rsyslog inactive AND disabled — your routing
# rule is inert until the service actually runs, and won't survive the end-of-exam
# reboot unless it's enabled too. `enable --now` does both in one step:
sudo systemctl enable --now rsyslog

# Test message
logger -p local0.warning "grading-probe-alpha"
```

> **Order matters:** configure persistent journald storage *before* setting up rsyslog routing
> (as above). Restarting `systemd-journald` resets the `imjournal` → `rsyslog` pipeline — if you
> start/restart rsyslog *before* journald's persistent-storage dance, do it again afterward,
> or your routed messages will silently stop landing in the target file.

> **Why `enable --now` and not `restart`:** T1's own report shows `rsyslog: ACTIVE: inactive
> ENABLED: disabled` — that's intentional baseline provisioning, not an oversight (see Task 1's
> "mixed active/enabled states" note). A bare `restart` would start it for this session only;
> it would be dead again after the reboot, and the persistence portion of this task's grading
> would fail right alongside the routing check (no service running → no routing → no probe
> message landing in the file). `enable --now` starts it immediately AND persists it.

**Verify:**
```bash
sudo test -d /var/log/journal/$(cat /etc/machine-id) && echo "journal dir present"
ls /var/log/journal/$(cat /etc/machine-id)
cat /etc/rsyslog.d/alpha-routing.conf
sudo grep grading-probe-alpha /var/log/alpha-events
```

---

## Task 4 — File Transfer: rsync Backup and Secure Upload (15 pts)

```bash
# Archive-mode backup of /etc/exam-source/
# sudo is needed to READ the source (manifest.txt is root:root 640 — student
# can't read it directly); rsync -a running as root preserves the ORIGINAL
# owner/group/perms on the copies, so do NOT chown the destination afterward —
# that would destroy exactly what the grading check verifies was preserved.
mkdir -p /home/student/backup-alpha
sudo rsync -a /etc/exam-source/ /home/student/backup-alpha/exam-source/

# Secure upload of manifest.txt to the repo VM as the student user there.
# NOTE: the rsync -a in step 1 correctly preserved manifest.txt's ORIGINAL
# permissions (640 root:root) — which means the student account can no longer
# read its own backup copy. `sudo` lets the local read happen as root while
# still authenticating OUTBOUND to the repo VM as `student`:
sudo scp /home/student/backup-alpha/exam-source/manifest.txt \
    student@172.16.16.121:/home/student/uploaded-alpha.txt
```
(SCP will prompt for the repo VM's `student` account password — same exam password as the student VM. Accept the host key prompt on first connection.)

> **This is intentional friction, not a bug:** `manifest.txt`'s permissions are *not* one of the
> two files the grading check inspects (`report.dat` and `notes/log.txt` are — see the design
> doc's T4 grading table), so reading it via `sudo` (or making a readable copy first, or piping
> through `sudo cat | ssh ... "cat > ..."`) costs nothing. Any of these approaches is acceptable;
> `sudo scp` is simply the most direct.

**Verify:**
```bash
ls -laR /home/student/backup-alpha/exam-source/
stat -c '%a %U:%G' /home/student/backup-alpha/exam-source/report.dat       # should match /etc/exam-source/report.dat (0750 root:student)
stat -c '%a %U:%G' /home/student/backup-alpha/exam-source/notes/log.txt    # should match /etc/exam-source/notes/log.txt (0644 student:student)
diff /home/student/backup-alpha/exam-source/manifest.txt /etc/exam-source/manifest.txt

# Cross-host (instructor-only check, but useful to confirm here):
ssh -J root@135.181.128.170 ansible@172.16.16.121 \
  "sudo diff /home/student/uploaded-alpha.txt /etc/exam-source/manifest.txt && echo MATCH"
```

---

## Task 5 — NFS Client: Automount Your Shared Export (20 pts)

```bash
# Install and enable autofs
sudo dnf install -y autofs
sudo systemctl enable --now autofs

# Master map: /remote -> /etc/auto.alpha
echo '/remote  /etc/auto.alpha' | sudo tee /etc/auto.master.d/alpha.autofs

# Indirect map: alpha -> repo VM export, rw/sync/NFSv4
echo 'alpha  -rw,sync,vers=4  172.16.16.121:/exports/export-alpha' | sudo tee /etc/auto.alpha

sudo systemctl restart autofs

# Trigger automount and verify read
ls /remote/alpha
cat /remote/alpha/welcome.txt

# Prove it's writable
echo 'submission from alpha' > /remote/alpha/alpha-submitted.txt
cat /remote/alpha/alpha-submitted.txt
```

> **Repo VM prerequisite — export directory must allow writes from a non-root client UID:**
> the `student` account (UID 1001) is neither the export's owner nor group (`nobody:nobody`),
> and `no_root_squash` only affects how *root* maps — `student` passes through as its own UID
> via `sec=sys`. The export directory therefore needs the **"other" write+execute bits**
> (mode `0777`) or the write will fail with `Permission denied`. This is set by
> `repo-provision.yml`'s "Create per-student NFS export directories" task — confirm it landed
> as `0777`, not `0775`, before the exam.

**Verify:**
```bash
systemctl is-active autofs; systemctl is-enabled autofs
cat /etc/auto.master.d/alpha.autofs
cat /etc/auto.alpha
findmnt /remote/alpha

# Cross-host (instructor-only check, but useful to confirm here):
ssh -J root@135.181.128.170 ansible@172.16.16.121 \
  "sudo cat /exports/export-alpha/alpha-submitted.txt"
```

---

## Task 6 — Containers: Build, Run, and Persist a Custom Web Server (15 pts)

```bash
mkdir -p /home/student/webapp
cat > /home/student/webapp/Containerfile <<'EOF'
FROM registry.access.redhat.com/ubi9/httpd-24:latest
RUN echo "alpha containerized webserver" > /var/www/html/index.html
EOF

cd /home/student/webapp
podman build -t alpha-web:1.0 .

# Run detached, mapping host 8101 -> container 8080
podman run -d --name alpha-srv -p 8101:8080 alpha-web:1.0

curl localhost:8101   # should print: alpha containerized webserver

# Persist across logout/reboot via generated systemd unit (rootless/user)
mkdir -p ~/.config/systemd/user
cd ~/.config/systemd/user
podman generate systemd --new --files --name alpha-srv

systemctl --user daemon-reload
systemctl --user enable --now container-alpha-srv.service
loginctl enable-linger student
```

**Verify:**
```bash
podman images --format '{{.Repository}}:{{.Tag}}'    # localhost/alpha-web:1.0
podman ps --format '{{.Names}} {{.Ports}}'           # alpha-srv  0.0.0.0:8101->8080/tcp
curl localhost:8101
systemctl --user is-enabled container-alpha-srv.service
loginctl show-user student -p Linger
```

> **Note:** `{{ rh134_base_image }}` = `registry.access.redhat.com/ubi9/httpd-24` (pre-pulled by
> Ansible as the `student` user — `podman images` shows it tagged `:latest`, ~310 MB). The
> `FROM` line above uses the exact pre-pulled reference so the build doesn't need registry access.

---

## Run grading script

```bash
grade
```

Expected: **100/100**

---

## Notes

- T2/T3/T6 persistence checks (fstab mount, journald storage, container survival) are all validated
  against a **single end-of-exam reboot** — reboot once near the end with `sudo systemctl reboot`,
  then reconnect (`ssh -p 2201 student@135.181.128.170`) and re-run `grade`.
- T4 and T5 each have one sub-check verified on the **repo VM** (172.16.16.121), not the student's
  own VM — the instructor-side grading playbook checks these; the commands above show how to
  spot-check them manually during the dry run.
- `/etc/exam-source/` is planted by Ansible with distinguishable, non-default permissions —
  `rsync -a` must preserve them for full T4 marks.
- `/dev/sdb` arrives completely raw (no partition table, no filesystem) — confirm with
  `sudo blkid -p /dev/sdb` (should report no signature, rc=2) before starting T2.
