# Instructor Cheatsheet — RH124 Mid-Semester Exam (Alpha Variant)

Exact commands to complete all 6 tasks on `student-01` (variant: alpha).  
Use this for end-to-end testing after provisioning and to verify the grading script produces full marks.

**Connect:**
```
ssh -J root@135.181.128.170 student@172.16.16.101
```

---

## Task 1 — File and Directory Management (15 pts)

```bash
mkdir -p /home/student/projects/exam-alpha
touch /home/student/projects/exam-alpha/report.txt \
      /home/student/projects/exam-alpha/backup.txt \
      /home/student/projects/exam-alpha/notes.txt
cp /etc/hostname /home/student/projects/exam-alpha/hostname.txt
tail -5 /etc/passwd >> /home/student/projects/exam-alpha/report.txt
ln /home/student/projects/exam-alpha/report.txt \
   /home/student/projects/report-link-alpha
ln -s /home/student/projects/exam-alpha /home/student/exam-shortcut
```

**Verify:**
```bash
ls -la /home/student/projects/exam-alpha/
stat -c %h /home/student/projects/exam-alpha/report.txt   # should be 2
readlink -f /home/student/exam-shortcut                   # should be /home/student/projects/exam-alpha
```

---

## Task 2 — User, Group, and Password Policy (20 pts)

```bash
# dbteam group already exists (GID 40001) — just verify
getent group dbteam

# Create user with dbteam as supplementary group
sudo useradd -G dbteam dbadmin1

# Set password
echo 'dbadmin1:Welcome1' | sudo chpasswd

# Force password change on first login
sudo chage -d 0 dbadmin1

# Set password policy
sudo chage -m 7 -M 60 -E 2026-11-30 dbadmin1

# NOPASSWD sudo
echo 'dbadmin1 ALL=(ALL) NOPASSWD: ALL' | sudo tee /etc/sudoers.d/dbadmin1
sudo chmod 440 /etc/sudoers.d/dbadmin1
```

**Verify:**
```bash
id dbadmin1
sudo chage -l dbadmin1
sudo -l -U dbadmin1
```

---

## Task 3 — File Permissions and Collaborative Directory (20 pts)

```bash
sudo mkdir /home/dbteam-workspace-alpha
sudo chown root:dbteam /home/dbteam-workspace-alpha
sudo chmod 3770 /home/dbteam-workspace-alpha   # rwxrws--T = owner rwx, group rwx+SGID, others none+sticky
```

**umask for dbadmin1** (run after Task 2 creates the user):
```bash
echo 'umask 007' | sudo tee -a /home/dbadmin1/.bashrc
```

**Verify:**
```bash
stat -c %A /home/dbteam-workspace-alpha   # should be drwxrws--T
grep 'umask 007' /home/dbadmin1/.bashrc
```

---

## Task 4 — Service Management (15 pts)

```bash
sudo systemctl start crond
sudo systemctl enable crond
sudo systemctl stop rsyslog
sudo systemctl disable rsyslog

# Reboot (required for full marks — T4 reboot check + T6 fstab persistence check)
sudo systemctl reboot
```

After reboot, reconnect and verify:
```bash
systemctl is-active crond    # active
systemctl is-enabled crond   # enabled
systemctl is-active rsyslog  # inactive
systemctl is-enabled rsyslog # disabled
```

---

## Task 5 — Package Management and Custom Repository (15 pts)

```bash
sudo tee /etc/yum.repos.d/exam.repo <<'EOF'
[exam]
name=Exam Repository
baseurl=http://172.16.16.121/repo
enabled=1
gpgcheck=0
EOF

sudo dnf install -y vim-enhanced tree
sudo dnf remove -y tmux
```

**Verify:**
```bash
rpm -q vim-enhanced tree
rpm -q tmux   # should print "not installed"
```

---

## Task 6 — Mount a File System and Search for Files (15 pts)

```bash
# Find the UUID of /dev/sdb1
lsblk -fp /dev/sdb

# Create mount point
sudo mkdir -p /mnt/exam-disk-alpha

# Add to fstab (replace UUID with actual value from lsblk above)
UUID=$(lsblk -no UUID /dev/sdb1)
echo "UUID=${UUID}  /mnt/exam-disk-alpha  xfs  defaults  0 0" | sudo tee -a /etc/fstab

# Mount
sudo mount -a

# Write required file
echo 'alpha disk mounted' | sudo tee /mnt/exam-disk-alpha/mounted.txt

# Find large files in /etc (sudo needed to read /etc/exam-data/)
sudo find /etc -type f -size +50k 2>/dev/null | sudo tee /mnt/exam-disk-alpha/large-files.txt > /dev/null

# Find root:root files with exact perms 640 in /var (sudo needed to read /var/exam-data/)
sudo find /var -type f -user root -group root -perm 640 2>/dev/null | sudo tee /mnt/exam-disk-alpha/perms-files.txt > /dev/null
```

**Verify:**
```bash
findmnt /mnt/exam-disk-alpha
grep exam-disk-alpha /etc/fstab
cat /mnt/exam-disk-alpha/mounted.txt
grep bigfile.dat /mnt/exam-disk-alpha/large-files.txt
grep record-01.dat /mnt/exam-disk-alpha/perms-files.txt
```

---

## Run grading script

```bash
grade
```

Expected: **100/100**

---

## Notes

- Task 4 reboot is shared with Task 6 fstab persistence — one reboot covers both.
- After reboot, reconnect via: `ssh -J root@135.181.128.170 student@172.16.16.101`
- The `dbteam` group is pre-created by Ansible (GID 40001) — do not delete and recreate it.
- `/etc/exam-data/bigfile.dat` and `/var/exam-data/record-0[123].dat` are planted by Ansible — they must appear in the find output.
