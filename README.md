# VUV Operacijski Sustavi — Exam Infrastructure

Infrastructure-as-Code for the Red Hat Academy Operating Systems (RH124/RH134) practical exam at Virovitica University of Applied Sciences.

Provisions up to 20 AlmaLinux 10 student VMs on a dedicated Proxmox server via Terraform, configured via Ansible.

## Prerequisites

- Terraform ≥ 1.5 with a [Terraform Cloud](https://app.terraform.io) account in the `marin-prox-lab` org
- `~/.terraformrc` with Terraform Cloud credentials
- Proxmox API token (`terraform@pve!terraform-token`) with VM provisioning permissions
- SSH key pair at `~/.ssh/id_ed25519` (used for both Proxmox host access and Ansible)

## Deploy

```bash
# 1. Configure secrets
cp .env.example .env
# Edit .env — set PROXMOX_API_TOKEN_SECRET and STUDENT_PASSWORD

# 2. Export Terraform variables
source setup.sh

# 3. Initialize and apply
cd terraform
terraform init
terraform apply
```

## Run Ansible

```bash
# Clear stale SSH host keys — required after every reprovision (same IPs, new host keys)
for i in $(seq 101 120); do ssh-keygen -R "172.16.16.$i" 2>/dev/null; done

# Ensure your SSH key is loaded
ssh-add ~/.ssh/id_ed25519

cd ansible
ansible-playbook site.yml
```

To target a single student VM: `ansible-playbook site.yml -l student-01`

## Scale from 1 VM to 20

```bash
# In .env:
STUDENT_COUNT=20

# Re-export and apply
source setup.sh
cd terraform && terraform apply
```

The Ansible inventory always lists all 20 hosts — only provisioned VMs will respond.

## Infrastructure

| Property | Value |
|---|---|
| Proxmox host | 135.181.128.170 (Hetzner EX44) |
| Template | VM 9002 — AlmaLinux 10 |
| Student VMs | VM IDs 200–219, IPs 172.16.16.101–120/24 |
| Resources | 2 vCPU, 3 GB RAM, 20 GB disk per VM |
| cloud-init user | `student` |
| Network | NAT bridge vmbr0, gateway 172.16.16.1 |
