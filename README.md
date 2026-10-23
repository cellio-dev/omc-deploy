# Quick Start

**You need:** a Debian or Ubuntu server with a static IP, a DNS name for the portal (for example `vpn.example.com`), and router forwards for TCP 443 and UDP 1194 to the server. TCP 443 is the enrollment portal. An optional VPN fallback, off until Settings → VPN enables it, listens on container port 1443 and is published as host port 10443. Recommended: forward public TCP 443 on your firewall to this server's port 10443. Two public IPs need no .env changes (portal on IP1:443, VPN TCP on IP2:443 forwarded to :10443). One public IP: move the portal to host port 9443 (`PORTAL_PUBLISH=0.0.0.0:9443:8444`, portal public port 9443) and forward IP:443 to :10443. Forward TCP 80 as well if you use Let's Encrypt: port 80 is required for certificate issuance and renewal.

## Changing the TCP fallback port

The host port defaults to 10443. Profiles use the public port from Settings → VPN, which defaults to 443, and never the host port. Recommended: forward public TCP 443 on your firewall to this server's port 10443.

Change the host port only when the firewall cannot translate ports. Set `VPN_TCP_PUBLISH` to another free port that still ends in `:1443` (for example `0.0.0.0:9443:1443`) and recreate the OpenVPN container. The one-public-IP and two-public-IP layouts are in [DEPLOYMENT.md](DEPLOYMENT.md#changing-the-fallback-port).

## 1. Install Docker

Official Docker apt repository (Debian shown):

```bash
sudo apt update
sudo apt install -y ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/debian $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo usermod -aG docker "$USER"
```

On Ubuntu, replace `debian` with `ubuntu` in both repo URLs. Log out and back in so the `docker` group applies.

## 2. Download the files

```bash
sudo mkdir -p /opt/omc/scripts
sudo chown -R "$USER": /opt/omc
cd /opt/omc
curl -fsSL -o docker-compose.yml https://raw.githubusercontent.com/cellio-dev/omc-deploy/main/docker-compose.yml
curl -fsSL -o scripts/ensure_userland_proxy.py https://raw.githubusercontent.com/cellio-dev/omc-deploy/main/scripts/ensure_userland_proxy.py
curl -fsSL -o scripts/host-setup.sh https://raw.githubusercontent.com/cellio-dev/omc-deploy/main/scripts/host-setup.sh
chmod +x scripts/host-setup.sh
```

## 3. Create `.env`

```bash
echo "DB_PASSWORD=$(openssl rand -hex 24)" > .env
```

This generates a random database password. Keep a copy of `.env` somewhere safe: the database cannot be opened without it.

## 4. Enable real client IPs

```bash
sudo python3 scripts/ensure_userland_proxy.py --restart
```

This sets `"userland-proxy": false` in `/etc/docker/daemon.json` so OMC sees real client addresses, and restarts Docker if the file changed. Run it before the next step so the containers are created with the new setting. Without `--restart` the script exits with code 10 and tells you to restart Docker yourself.

## 5. Start OMC

```bash
docker compose up -d
```

## 6. Host forwarding

Run this after step 5. Use your LAN adapter name from `ip -br a` (for example `eth0`):

```bash
sudo ./scripts/host-setup.sh eth0
```

It enables IP forwarding and allows traffic between the Docker networks and that adapter. Persist the iptables rules with `iptables-persistent` or `netfilter-persistent`, or a reboot drops them.

## 7. Get the setup token

```bash
docker compose logs app | grep -i token
```

The line reads `Setup token: ...`.

## 8. Complete setup

1. Browse to `https://<server-ip>:8443/setup` (accept the self-signed certificate warning), enter the token, and create the first administrator and its authenticator.
2. **Settings → Portal:** set the Public hostname (for example `vpn.example.com`) and your Company name.
3. **Settings → Certificate:** choose Let's Encrypt (port 80 must be forwarded).
4. **Settings → Authentication:** configure Active Directory, or skip it to use local users.
5. **Users → Onboard user:** create the first user and send the invitation.
