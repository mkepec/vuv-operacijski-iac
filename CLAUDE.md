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
- Ansible reaches VMs via ProxyJump through root@135.181.128.170

## Repo layout

```
vuv-operacijski-iac/
├── .env                        # secrets — gitignored, copy from .env.example
├── .env.example                # template for all secrets and config
├── setup.sh                    # sources .env, exports TF_VAR_* for Terraform
├── terraform/
│   ├── versions.tf             # provider + TF Cloud backend
│   ├── variables.tf            # all input variables
│   ├── main.tf                 # proxmox_virtual_environment_vm resource (for_each)
│   ├── outputs.tf              # VM IDs, IPs, SSH hint
│   └── terraform.tfvars.example
└── ansible/
    ├── ansible.cfg             # remote_user=student, ProxyJump configured
    ├── inventory.yml           # static, all 20 hosts listed (101–120)
    └── site.yml                # placeholder: ping + print hostname
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

## What's working (as of session 1)

- Terraform init/plan/apply tested against Proxmox — student-01 created in ~24s
- SSH via ProxyJump confirmed working
- Ansible ping + fact gather confirmed working on student-01
- STUDENT_COUNT=1 is the current default; next step is exam task design in Ansible

## Next tasks (not yet started)

- Design exam tasks as Ansible roles (apply broken config, student must fix)
- Per-student task variation (different broken configs per VM)
- Exam reset playbook (destroy + recreate VMs, re-apply broken config)
- Student access: web portal or printed credential sheet
- Time-limited exam enforcement (optional)
