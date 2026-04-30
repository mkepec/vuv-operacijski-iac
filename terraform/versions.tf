terraform {
  required_version = ">= 1.5.0"

  cloud {
    organization = "marin-prox-lab"

    workspaces {
      name = "vuv-operacijski-iac"
    }
  }

  required_providers {
    proxmox = {
      source  = "bpg/proxmox"
      version = "~> 0.83.1"
    }
  }
}

provider "proxmox" {
  endpoint  = var.proxmox_api_url
  api_token = var.proxmox_api_token
  insecure  = true

  ssh {
    agent       = false
    username    = "root"
    private_key = file(pathexpand(var.proxmox_ssh_private_key_path))
  }
}
