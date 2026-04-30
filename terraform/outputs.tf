output "student_vm_ids" {
  description = "VM IDs of all provisioned student VMs"
  value       = { for k, v in proxmox_virtual_environment_vm.student : k => v.vm_id }
}

output "student_ips" {
  description = "IP addresses of all provisioned student VMs"
  value = {
    for k, v in proxmox_virtual_environment_vm.student : k =>
    trimprefix(split("/", v.initialization[0].ip_config[0].ipv4[0].address)[0], "")
  }
}

output "ansible_inventory_hint" {
  description = "SSH connection pattern for student VMs (via ProxyJump)"
  value       = "ssh -J root@${var.proxmox_host_ip} student@<student-ip>"
}
