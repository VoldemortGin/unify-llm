# Deploying the unify-llm Gateway on a Vultr VPS

This is a practical runbook for putting the **hidden-key, OpenAI-compatible proxy
gateway** into production on a single [Vultr](https://www.vultr.com/) cloud-compute
instance, fronted by HTTPS, with a Redis sidecar holding shared rate-limit / budget
state.

The shape of the deployment is fixed by the files at the repo root — read those if
you want the why behind any of this:

| File | Role |
|------|------|
| `Dockerfile` | uv multi-stage build, `python:3.13-slim`, non-root `app` user, `EXPOSE 8080`, `HEALTHCHECK curl /healthz`, runs `uvicorn unify_llm.gateway.app:app --host 0.0.0.0 --port 8080 --workers 2`. |
| `docker-compose.yml` | `gateway` + `redis`. Gateway is published only on `127.0.0.1:8080`, mounts `configs/gateway.yaml` read-only, reads secrets from `.env`, depends on a healthy Redis. |
| `.env.gateway.example` | Template for the host `.env`: `APP_ENV`, default provider, **upstream provider keys**, config path, rate-limit backend, Redis URL. |
| `configs/gateway.yaml` | App-key table (**sha256 only**) + public-model → provider/upstream-model routing + pricing. Demo key plaintext is `demo-app-key`. |

**Security model in one line:** upstream provider keys never leave the server — they
live only in `.env` (host-side, `chmod 600`, never committed) and are read by the
factory at request time; clients authenticate with an *app key* whose **sha256** (not
the plaintext) is the only thing stored, in `gateway.yaml`. The gateway container is
bound to `127.0.0.1` and is never exposed to the public internet directly — a reverse
proxy (Caddy) terminates TLS in front of it.

---

## 0. What you must provide before starting

A short checklist of things this runbook cannot generate for you:

- [ ] **Vultr access** — a Vultr account + API key (or just SSH access to a VPS you
      create in the web console) and an SSH public key registered with Vultr.
- [ ] **A domain + DNS** — e.g. `gateway.example.com`, with an **A record** pointing
      at the VPS public IP. Cloudflare is fine; if you use Cloudflare, set the record
      to **DNS only (grey cloud)** for the first issuance so Caddy can complete the
      ACME challenge, then proxy it afterwards if you want.
- [ ] **Real upstream provider key(s)** — at minimum the one your default provider
      uses, e.g. `DEEPSEEK_API_KEY` (also `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`,
      `GEMINI_API_KEY`, `DATABRICKS_API_KEY` / `DATABRICKS_BASE_URL` as needed).
- [ ] **The app keys to mint** — decide who gets to call the gateway, generate a
      secret per consumer, and store only its sha256 (see §2).

---

## 1. Provision the Vultr VPS (Docker pre-installed via cloud-init)

Create an Ubuntu 22.04 or 24.04 "Cloud Compute" instance. A 1 vCPU / 1 GB plan is
enough for the gateway + Redis to start; size up for real traffic.

Paste the following **cloud-init user-data** into the Vultr "Startup Script"
(type: *Boot*) or the API `user_data` field. It installs Docker Engine + the Compose
plugin from Docker's official apt repo, enables the service, and adds a non-root
`deploy` user to the `docker` group.

```yaml
#cloud-config
package_update: true
package_upgrade: true

users:
  - name: deploy
    groups: [sudo, docker]
    shell: /bin/bash
    sudo: ['ALL=(ALL) NOPASSWD:ALL']
    ssh_authorized_keys:
      - ssh-ed25519 AAAA...replace-with-your-public-key... you@example.com

write_files:
  - path: /etc/apt/keyrings/docker.asc
    permissions: '0644'
    content: ""   # placeholder; the key is fetched in runcmd below

runcmd:
  # --- Docker Engine + Compose plugin (official repo) ---
  - install -m 0755 -d /etc/apt/keyrings
  - curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
  - chmod a+r /etc/apt/keyrings/docker.asc
  - >
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc]
    https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable"
    > /etc/apt/sources.list.d/docker.list
  - apt-get update
  - DEBIAN_FRONTEND=noninteractive apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
  - systemctl enable --now docker
  # --- basic firewall: SSH + HTTP/HTTPS only (Caddy needs 80/443 for ACME) ---
  - ufw allow OpenSSH
  - ufw allow 80/tcp
  - ufw allow 443/tcp
  - ufw --force enable
```

Notes:
- Port **8080 is deliberately not opened** in the firewall — the gateway is only
  reachable on `127.0.0.1` and through the local Caddy reverse proxy.
- After boot, verify Docker is up:

```bash
ssh deploy@YOUR_VPS_IP
docker --version
docker compose version
```

If you provisioned the box without cloud-init, run the same steps by hand: the
[official Docker apt install](https://docs.docker.com/engine/install/ubuntu/) plus
`docker-compose-plugin`, then `sudo usermod -aG docker deploy && newgrp docker`.

---

## 2. Secrets handling (all server-side, via env)

There are two distinct secret classes, kept fully separate:

### a) Upstream provider keys → host `.env` only

These authenticate the gateway to the real LLM providers. They live **only** in the
host `.env`, are injected into the container by Compose's `env_file`, are read by the
factory at request time, and **never** appear in any gateway response or log, never go
into git, and never go into the image (`.env*` is in both `.gitignore` and
`.dockerignore`).

### b) App keys → `gateway.yaml`, sha256 only

Clients call the gateway with `Authorization: Bearer <app-key>`. The gateway stores
**only the sha256** of each app key; the plaintext is never written to disk.

**Mint a new app key** — generate a strong secret, hash it, and paste the hash into
`configs/gateway.yaml`:

```bash
# 1. Generate a random secret to hand to the consumer (store it in your password manager).
NEW_APP_KEY="$(openssl rand -hex 32)"
echo "Give this plaintext to the client (shown once): $NEW_APP_KEY"

# 2. Compute its sha256 using the project's own hashing function (run from repo root).
docker compose run --rm --no-deps gateway \
  python -c "from unify_llm.gateway.config import hash_app_key; import os; print(hash_app_key(os.environ['NEW_APP_KEY']))" \
  NEW_APP_KEY="$NEW_APP_KEY"
```

If you have a local virtualenv instead of running inside the container, the canonical
one-liner is:

```bash
python -c "from unify_llm.gateway.config import hash_app_key; print(hash_app_key('SOME-SECRET'))"
```

Paste the resulting hash into a new entry under `app_keys:` in `configs/gateway.yaml`:

```yaml
app_keys:
  - app_id: acme-prod
    key_sha256: <paste-the-sha256-here>
    allowed_models:
      - gpt-4o-mini          # or "*" to allow every routable model
    rate_limit_rpm: 60
    rate_limit_tpm: 100000
    budget_usd: 50.0
```

`gateway.yaml` contains **no secrets** (only hashes + routing + pricing), so it is safe
to commit. The plaintext app key exists only in the consumer's hands and your password
manager.

> The shipped demo entry (`app_id: demo`, plaintext `demo-app-key`) is for smoke-testing
> only — **delete it before going live**.

---

## 3. Copy the repo to the server and fill secrets

Either clone with git (simplest for `git pull` updates later) or rsync from your
laptop.

```bash
# Option A — git clone (on the VPS, as deploy)
ssh deploy@YOUR_VPS_IP
git clone https://github.com/unifyllm/unifyllm.git ~/unify-llm
cd ~/unify-llm

# Option B — rsync from your laptop (excludes local junk)
rsync -avz --exclude '.git' --exclude '.venv' --exclude '.env' \
  ./ deploy@YOUR_VPS_IP:~/unify-llm/
```

Create the host `.env` from the template, fill in the real upstream key(s), and lock
it down:

```bash
cd ~/unify-llm
cp .env.gateway.example .env
chmod 600 .env          # owner read/write only — never world-readable, never committed
nano .env               # fill DEEPSEEK_API_KEY=... (and any other providers you route to)
```

Minimum to set in `.env`:
- `APP_LLM_PROVIDER` — default/fallback provider (e.g. `deepseek`).
- The matching upstream key, e.g. `DEEPSEEK_API_KEY=sk-...`.

You do **not** need to set `APP_ENV`, `APP_GATEWAY_CONFIG`, `APP_RATELIMIT_BACKEND`, or
`APP_REDIS_URL` for production — `docker-compose.yml` pins those (`production`,
`/app/configs/gateway.yaml`, `redis`, `redis://redis:6379/0`) and they override the
`.env` values.

---

## 4. TLS + domain via Caddy in front

The gateway only listens on `127.0.0.1:8080`. Put **Caddy** in front for automatic
Let's Encrypt HTTPS on your domain, reverse-proxying to that local port. Caddy obtains
and renews certificates automatically — no certbot, no cron.

### Option A (recommended): Caddy on the host via apt

```bash
# Install Caddy from its official apt repo (Ubuntu).
sudo apt-get install -y debian-keyring debian-archive-keyring apt-transport-https curl
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' \
  | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' \
  | sudo tee /etc/apt/sources.list.d/caddy-stable.list
sudo apt-get update
sudo apt-get install -y caddy
```

Minimal `/etc/caddy/Caddyfile`:

```caddyfile
gateway.example.com {
    reverse_proxy 127.0.0.1:8080
}
```

Apply it:

```bash
sudo nano /etc/caddy/Caddyfile     # set your real domain
sudo systemctl reload caddy
sudo systemctl status caddy        # confirm it's running and got a cert
```

Caddy listens on 80/443 (opened in §1), terminates TLS, and forwards plaintext to the
gateway on loopback. Because the gateway is published only on `127.0.0.1:8080`, it is
never reachable from the internet except through Caddy.

### Option B: Caddy as a Compose service

If you would rather keep everything in Compose, drop the `127.0.0.1:` host-binding on
the gateway (so Caddy can reach it over the Compose network) and add a Caddy service
that publishes 80/443. Sketch:

```yaml
# (illustrative — add to docker-compose.yml; remove the gateway's 127.0.0.1:8080 port mapping)
  caddy:
    image: caddy:2-alpine
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile:ro
      - caddy_data:/data
      - caddy_config:/config
    depends_on:
      - gateway

volumes:
  caddy_data:
  caddy_config:
```

with a `Caddyfile` of `gateway.example.com { reverse_proxy gateway:8080 }`. Traefik is
an equivalent alternative if you prefer label-driven routing. Option A keeps the proxy
independent of the app's deploy cycle, so it is the default recommendation.

---

## 5. Launch

From the repo root on the VPS:

```bash
cd ~/unify-llm
docker compose up -d --build
```

This builds the gateway image, starts Redis (no persistence), waits for Redis to be
healthy, then starts the gateway with 2 uvicorn workers.

### Health check (unauthenticated)

```bash
# Through Caddy / HTTPS (public path):
curl -fsS https://gateway.example.com/healthz

# Or directly on the box (loopback), before DNS/TLS is ready:
curl -fsS http://127.0.0.1:8080/healthz
```

### Authenticated smoke test

```bash
# Lists the models the app key is allowed to route to.
curl https://gateway.example.com/v1/models \
  -H "Authorization: Bearer demo-app-key"
```

Use `demo-app-key` only if you kept the demo entry; otherwise use the plaintext of a
key you minted in §2. A real chat completion:

```bash
curl https://gateway.example.com/v1/chat/completions \
  -H "Authorization: Bearer demo-app-key" \
  -H "Content-Type: application/json" \
  -d '{"model":"gpt-4o-mini","messages":[{"role":"user","content":"ping"}]}'
```

---

## 6. Operations

```bash
# Tail gateway logs (follow). Secrets never appear here by design.
docker compose logs -f gateway

# Logs for everything (gateway + redis).
docker compose logs -f

# Show running services + health.
docker compose ps

# Restart just the gateway (e.g. after editing gateway.yaml — it's a read-only mount).
docker compose restart gateway

# Stop / start the whole stack.
docker compose down
docker compose up -d
```

### Update to a new version

```bash
cd ~/unify-llm
git pull                       # or rsync the new tree
docker compose up -d --build   # rebuild + recreate only what changed
docker image prune -f          # optional: reclaim old layers
```

### Rotate keys

- **Upstream provider key:** edit `.env` (it's still `chmod 600`), then
  `docker compose up -d` to recreate the gateway with the new env. No rebuild needed.
- **App key:** mint a new one (§2), add its sha256 to `gateway.yaml`, remove the old
  entry, then `docker compose restart gateway`. Hand the new plaintext to the consumer.

### Routing / pricing changes

`configs/gateway.yaml` is bind-mounted read-only, so changing models, limits, or
budgets needs no image rebuild — edit the file and `docker compose restart gateway`.

---

## 7. Horizontal scaling

Correctness under concurrency comes from **shared state in Redis**. Compose pins
`APP_RATELIMIT_BACKEND=redis` and `APP_REDIS_URL=redis://redis:6379/0`, so every worker
and every replica reads and writes the *same* rate-limit token buckets and budget
counters. Redis is the single coordination point — scale the gateway freely; the limits
stay globally correct.

Two levers, combinable:

**1. More uvicorn workers (vertical, within one container).** The image's `CMD` runs
`--workers 2`. Override it for a bigger box without editing the Dockerfile by adding a
`command:` to the gateway service in `docker-compose.yml`:

```yaml
    command: ["uvicorn", "unify_llm.gateway.app:app",
              "--host", "0.0.0.0", "--port", "8080", "--workers", "4"]
```

**2. More gateway replicas (horizontal).** Run several gateway containers behind the
proxy:

```bash
docker compose up -d --scale gateway=3
```

(For `--scale` to work, drop the fixed `127.0.0.1:8080:8080` host port on the gateway
and let the reverse proxy — Caddy as a Compose service, §4 Option B — load-balance
across replicas over the Compose network; a fixed host port can't be shared by 3
containers.) Because all replicas share the same Redis, a client's RPM/TPM/budget caps
are enforced across the whole fleet, not per-replica.

For traffic beyond one VPS, run the same image on additional Vultr instances pointed at
a **single shared Redis** (a managed Redis or one dedicated instance) and put a Vultr
load balancer in front. The shared-state invariant is unchanged: one Redis, global
limits.

---

## Appendix — recap of the "must provide" checklist

| Item | Where it goes |
|------|---------------|
| Vultr API key / SSH access + registered SSH public key | Vultr console / cloud-init `ssh_authorized_keys` |
| Domain + DNS A record (e.g. Cloudflare, grey-cloud for first issuance) | DNS provider → VPS public IP |
| Real upstream provider key(s) (`DEEPSEEK_API_KEY`, …) | host `.env` (`chmod 600`) |
| App keys to mint (sha256 only stored) | `configs/gateway.yaml` under `app_keys:` |
