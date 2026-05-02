#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"

if [[ ! -f "${SCRIPT_DIR}/.env" ]]; then
  echo "ERROR: .env not found. Copy .env.example and fill in the values." >&2
  exit 1
fi

# shellcheck disable=SC1091
source "${SCRIPT_DIR}/.env"

export TF_VAR_proxmox_api_url="https://${PROXMOX_HOST_IP}:8006/api2/json"
export TF_VAR_proxmox_host_ip="${PROXMOX_HOST_IP}"
export TF_VAR_proxmox_ssh_private_key_path="${PROXMOX_HOST_SSH_KEY}"
export TF_VAR_proxmox_node_name="${PROXMOX_NODE_NAME}"
export TF_VAR_ansible_ssh_public_key_path="${ANSIBLE_SSH_PUBLIC_KEY_PATH}"
export TF_VAR_proxmox_api_token="${PROXMOX_API_TOKEN_ID}=${PROXMOX_API_TOKEN_SECRET}"
export TF_VAR_student_password_hash="${STUDENT_PASSWORD_HASH}"
export TF_VAR_student_count="${STUDENT_COUNT}"

echo "Terraform variables exported."
echo "  API URL : ${TF_VAR_proxmox_api_url}"
echo "  Node    : ${TF_VAR_proxmox_node_name}"
echo "  Count   : ${TF_VAR_student_count} student VM(s)"
