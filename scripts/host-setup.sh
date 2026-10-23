#!/bin/bash
# Host forwarding for the appliance on Ubuntu or Debian.
# Run as root after `docker compose up -d`.
set -euo pipefail

LAN_IF="${1:-}"
if [[ -z "$LAN_IF" ]]; then
  echo "Usage: sudo ./scripts/host-setup.sh <lan-interface>" >&2
  echo "Example: sudo ./scripts/host-setup.sh eth0" >&2
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Preserve real client IPs on published ports (portal networks, IP lockouts, audit).
if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 is required to merge /etc/docker/daemon.json; install python3 or run scripts/ensure_userland_proxy.py by hand." >&2
  exit 1
fi
python3 "$SCRIPT_DIR/ensure_userland_proxy.py" --path /etc/docker/daemon.json --restart

sysctl -w net.ipv4.ip_forward=1
mkdir -p /etc/sysctl.d
echo "net.ipv4.ip_forward=1" > /etc/sysctl.d/99-openvpn-appliance.conf

if command -v ufw >/dev/null 2>&1 && ufw status | grep -q "Status: active"; then
  ufw route allow in on br-+ out on "$LAN_IF" || true
  ufw allow 1194/udp || true
  # Optional VPN TCP fallback is off by default. When it is on, the container
  # listens on 1443. Compose publishes host port 10443 by default.
  # Recommended: forward public TCP 443 on your firewall to this server's port 10443.
  # Allow it only for the address that should receive the fallback, for example:
  #   ufw allow 443/tcp
fi

iptables -N OVPN-HOST 2>/dev/null || true
iptables -F OVPN-HOST
iptables -C DOCKER-USER -j OVPN-HOST 2>/dev/null || iptables -I DOCKER-USER 1 -j OVPN-HOST
iptables -A OVPN-HOST -i br-+ -o "$LAN_IF" -j ACCEPT
iptables -A OVPN-HOST -i "$LAN_IF" -o br-+ -m conntrack --ctstate RELATED,ESTABLISHED -j ACCEPT
iptables -A OVPN-HOST -j RETURN

echo "Forwarding from Docker bridges to ${LAN_IF} is allowed."
echo "Persist the rules with iptables-persistent or netfilter-persistent if this host reboots."
