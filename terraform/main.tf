locals {
  # Generate all 20 student entries. student_count slices how many are actually created.
  all_students = {
    for i in range(20) : format("student-%02d", i + 1) => {
      name  = format("student-%02d", i + 1)
      ip    = "172.16.16.${101 + i}/24"
      vm_id = 200 + i
      index = i
    }
  }

  # Slice to only the first student_count entries (sorted by index for determinism)
  active_students = {
    for k, v in local.all_students : k => v
    if v.index < var.student_count
  }

  ssh_keys = compact([
    file(pathexpand(var.vm_ssh_public_key_path)),
    var.student_ssh_public_key,
  ])
}

resource "proxmox_virtual_environment_vm" "student" {
  for_each = local.active_students

  name      = each.value.name
  node_name = var.proxmox_node_name
  vm_id     = each.value.vm_id

  clone {
    vm_id        = 9002
    full         = true
    datastore_id = "local-lvm"
  }

  cpu {
    cores = 2
    type  = "host"
  }

  memory {
    dedicated = 3072
  }

  network_device {
    bridge = "vmbr0"
    model  = "virtio"
  }

  disk {
    datastore_id = "local-lvm"
    interface    = "scsi0"
    size         = 20
    iothread     = true
    discard      = "on"
  }

  initialization {
    ip_config {
      ipv4 {
        address = each.value.ip
        gateway = "172.16.16.1"
      }
    }

    dns {
      servers = ["1.1.1.1", "8.8.8.8"]
    }

    user_account {
      username = "student"
      password = var.student_password
      keys     = local.ssh_keys
    }
  }

  on_boot       = false
  started       = true
  tablet_device = false

  agent {
    enabled = true
    timeout = "15m"
  }

  tags = ["exam", "rhcsa", "vuv"]
}
