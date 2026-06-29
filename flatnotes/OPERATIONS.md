# fatnotes — Operations & Maintenance Reference

## What Is This?

**fatnotes** is a fork of [flatnotes](https://github.com/dullage/flatnotes) that adds support for nested directory structures. The web UI shows a collapsible file/folder tree in a left-hand sidebar, and notes can be organised into subdirectories inside the notes storage path.

---

## Where Everything Lives

| Thing | Location |
|-------|----------|
| fatnotes source code | https://github.com/denverdigiman/fatnotes |
| Original flatnotes source | https://github.com/dullage/flatnotes |
| Docker image (GHCR) | `ghcr.io/denverdigiman/fatnotes:latest` |
| fatnotes web UI (public) | https://fatnotes.denverdigiman.com |
| fatnotes web UI (Tailscale) | http://100.123.113.13:8087 |
| Notes storage on VPS | `/mnt/aibrain` |
| Docker env file on VPS | `/root/fatnotes.env` |
| Caddy config on VPS | `/etc/caddy/Caddyfile` |
| Docker daemon config | `/etc/docker/daemon.json` |

---

## Architecture Overview

```
Internet
    │
    ▼
Caddy (ports 80/443)
    │  reverse proxy
    ▼
fatnotes container (port 8087)
    │  volume mount
    ▼
/mnt/aibrain  (markdown files)
```

Tailscale users can also reach fatnotes directly at `http://100.123.113.13:8087`, bypassing Caddy.

---

## VPS Details

| Item | Value |
|------|-------|
| Provider | Hostinger |
| OS | Ubuntu 24.04.4 LTS |
| Public IP | 2.25.129.60 |
| Tailscale IP | 100.123.113.13 |
| SSH user | root |

---

## Firewall (ufw)

ufw is enabled with the following rules:

| Port | Purpose |
|------|---------|
| 22/tcp | SSH |
| 80/tcp | Caddy (Let's Encrypt renewal) |
| 443/tcp | Caddy (HTTPS) |
| tailscale0 | All Tailscale traffic |

All other ports (8086, 8087, 8787, etc.) are blocked from the public internet but accessible via Tailscale.

```bash
# View current rules
ufw status verbose
```

---

## Running Containers

### fatnotes (active)

```bash
docker run -d \
  --name fatnotes \
  --restart unless-stopped \
  --env-file /root/fatnotes.env \
  -v /mnt/aibrain:/data \
  -p 8087:8080 \
  ghcr.io/denverdigiman/fatnotes:latest
```

### flatnotes (original — keep as fallback until decommissioned)

```bash
docker run -d \
  --name flatnotes \
  --restart unless-stopped \
  -e FLATNOTES_AUTH_TYPE=password \
  -e FLATNOTES_USERNAME=<username> \
  -e FLATNOTES_PASSWORD=<password> \
  -e FLATNOTES_SECRET_KEY=<secret> \
  -v /mnt/aibrain:/data \
  -p 8086:8080 \
  dullage/flatnotes:latest
```

> flatnotes is accessible via Tailscale at `http://100.123.113.13:8086` only (blocked from public internet).

---

## /root/fatnotes.env

The env file on the VPS contains the runtime configuration for fatnotes:

```
FLATNOTES_AUTH_TYPE=password
FLATNOTES_USERNAME=<your-username>
FLATNOTES_PASSWORD=<your-password>
FLATNOTES_SECRET_KEY=<your-secret-key>
```

> Keep this file secure. It is only readable by root.

---

## Docker Maintenance Commands

```bash
# View running containers
docker ps

# View all containers (including stopped)
docker ps -a

# View fatnotes logs
docker logs fatnotes

# Follow fatnotes logs in real time
docker logs -f fatnotes

# Stop a container
docker stop fatnotes

# Start a stopped container
docker start fatnotes

# Stop and remove a container (required before re-running)
docker stop fatnotes && docker rm fatnotes

# Pull the latest image
docker pull ghcr.io/denverdigiman/fatnotes:latest

# Remove old unused images (cleanup)
docker image prune -f
```

---

## Deploying a Code Change

Every push to the `main` branch of `https://github.com/denverdigiman/fatnotes` triggers a GitHub Actions build that pushes a new image to GHCR automatically.

### Workflow

**1. Make changes locally on your Mac:**

```bash
cd ~/GitHub/fatnotes
# ... edit files in VS Code ...
git add .
git commit -m "Description of change"
git push origin main
```

**2. Wait for the build to complete:**

Check https://github.com/denverdigiman/fatnotes/actions — wait for the green checkmark.

**3. Deploy on the VPS:**

```bash
ssh root@2.25.129.60

docker pull ghcr.io/denverdigiman/fatnotes:latest
docker stop fatnotes && docker rm fatnotes
docker run -d \
  --name fatnotes \
  --restart unless-stopped \
  --env-file /root/fatnotes.env \
  -v /mnt/aibrain:/data \
  -p 8087:8080 \
  ghcr.io/denverdigiman/fatnotes:latest
```

---

## GitHub Repositories

| Repo | URL | Branch |
|------|-----|--------|
| fatnotes (main repo) | https://github.com/denverdigiman/fatnotes | `main` |
| manufacturers-news-tracker (contains flatnotes source) | https://github.com/denverdigiman/manufacturers-news-tracker | `claude/flatnotes-directory-structure-tn4fpg` |

> The `manufacturers-news-tracker` repo contains the full fatnotes source under `flatnotes/`. Changes should be made directly in the `fatnotes` repo going forward.

### Useful Git Commands

```bash
# Clone fatnotes
git clone https://github.com/denverdigiman/fatnotes.git

# Check status
git status

# Pull latest changes
git pull origin main

# Push changes
git push origin main

# View commit history
git log --oneline
```

---

## Caddy

Caddy runs as a systemd service and handles HTTPS for `fatnotes.denverdigiman.com`. It automatically obtains and renews Let's Encrypt SSL certificates — no manual intervention needed.

```bash
# View Caddy status
systemctl status caddy

# Restart Caddy
systemctl restart caddy

# View Caddy logs
journalctl -u caddy -f

# Edit Caddy config
nano /etc/caddy/Caddyfile
```

Current `/etc/caddy/Caddyfile`:

```
fatnotes.denverdigiman.com {
    reverse_proxy localhost:8087
}
```

> SSL certificates are stored in `/var/lib/caddy/.local/share/caddy/` and auto-renew ~30 days before expiry. Certificates last 90 days.

---

## DNS

| Record | Type | Value |
|--------|------|-------|
| `fatnotes.denverdigiman.com` | A | `2.25.129.60` |

---

## Decommissioning the Original flatnotes

When you are confident fatnotes is stable and you no longer need the original flatnotes as a fallback:

```bash
docker stop flatnotes && docker rm flatnotes
docker image rm dullage/flatnotes:latest
```

---

## What Changed from Upstream flatnotes

| File | Change |
|------|--------|
| `server/main.py` | Added `GET /api/tree` endpoint; note routes use `{title:path}` to allow slashes |
| `server/notes/base.py` | Added abstract `get_tree()` method |
| `server/notes/models.py` | Added `TreeNode` model |
| `server/notes/file_system/file_system.py` | Recursive note discovery; subdirectory support in create/update/delete; `get_tree()` implementation |
| `server/helpers.py` | `is_valid_filename` allows `/` but blocks `..` path traversal |
| `client/App.vue` | Two-column layout with sidebar; tree loaded from API on every route change |
| `client/partials/NavBar.vue` | New Note button hidden when sidebar is visible |
| `client/components/DirectoryTree.vue` | New — renders tree root |
| `client/components/TreeNodeItem.vue` | New — recursive folder/file tree node |
| `client/api.js` | Added `getTree()` |
| `client/router.js` | Note route uses `/:title(.*)+` to support path segments |
| `client/views/Note.vue` | Removed `/` from reserved filename characters |
