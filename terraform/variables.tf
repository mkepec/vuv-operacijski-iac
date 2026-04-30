### Proxmox connection — set automatically by setup.sh via TF_VAR_* exports

variable "proxmox_api_url" {
  description = "Proxmox API URL (https://<host>:8006/api2/json)"
  type        = string
}

variable "proxmox_api_token" {
  description = "Proxmox API token in <token_id>=<secret> format"
  type        = string
  sensitive   = true
}

variable "proxmox_host_ip" {
  description = "Proxmox host public IP address"
  type        = string
}

variable "proxmox_ssh_private_key_path" {
  description = "Path to SSH private key used to connect to the Proxmox host"
  type        = string
  default     = "~/.ssh/id_ed25519"
}

variable "proxmox_node_name" {
  description = "Proxmox node name"
  type        = string
  default     = "proxmox-lab"
}

variable "vm_ssh_public_key_path" {
  description = "Path to SSH public key injected into all student VMs (for Ansible access)"
  type        = string
  default     = "~/.ssh/id_ed25519.pub"
}

### Student VM variables

variable "student_password" {
  description = "Password for the 'student' cloud-init user on all student VMs"
  type        = string
  sensitive   = true
}

variable "student_count" {
  description = "Number of student VMs to create (1 for testing, 20 for full exam)"
  type        = number
  default     = 1

  validation {
    condition     = var.student_count >= 1 && var.student_count <= 20
    error_message = "student_count must be between 1 and 20."
  }
}

variable "student_ssh_public_key" {
  description = "Optional extra SSH public key to inject into student VMs (for student direct access)"
  type        = string
  default     = ""
}
