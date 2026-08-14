# Deployment (AWS free tier)

This runs the full stack — Redis Stack, FastAPI backend, Next.js frontend,
and an nginx reverse proxy that is the *only* container exposed to the
internet — on a single EC2 instance, with S3 used to back up uploaded
source documents.

Verified locally before writing this: `docker compose -f docker-compose.yml
-f docker-compose.prod.yml up -d --build` builds all four containers,
`nginx` alone answers on port 80, `/api/health` and `/api/query` both work
end-to-end through it, and redis/backend have no published ports (confirmed
via `docker compose ... config`).

## Read this first: the memory budget is real

Measured with `docker stats` during the local test:

| container | RSS      |
|-----------|----------|
| backend   | ~800 MB  |
| redis     | ~126 MB  |
| frontend  | ~31 MB   |
| nginx     | ~9 MB    |
| **total** | **~965 MB** |

The backend alone is close to the 900 MB `mem_limit` set in
`docker-compose.prod.yml`, because it loads two transformer models into
memory (`bge-small-en-v1.5` embedder + `bge-reranker-base` cross-encoder) on
top of FastAPI/uvicorn.

A `t2.micro`/`t3.micro` (AWS free tier) has **1 GB total RAM**. ~965 MB of
containers leaves nothing for the Linux kernel, sshd, Docker daemon, etc.
Expect OOM kills without the swap file in Step 4 below. If it's still
unstable after adding swap, the honest fix is a `t3.small` (2 GB, ~$15/mo,
not free-tier) — swap on a micro instance buys headroom, not more real
throughput, so under real concurrent load it will be slow.

## What you'll need

- An AWS account (you said you have one)
- This repo pushed somewhere the instance can pull from (GitHub, etc.) — or you `scp` it up
- Your Groq API key
- Nothing else needs external credentials; embeddings/reranking run locally, no S3 required for the app to function (S3 is optional, see Step 7)

## Step 1 — Launch the EC2 instance

1. AWS Console → **EC2** → **Launch instance**.
2. Name: `legal-rag`.
3. AMI: **Ubuntu Server 24.04 LTS** (free tier eligible).
4. Instance type: **t2.micro** or **t3.micro** (free tier eligible — pick whichever your account shows as free-tier for your region).
5. Key pair: create a new one (e.g. `legal-rag-key`), download the `.pem`, keep it — it's your only way in.
6. Network settings → **Edit**:
   - Allow SSH (port 22) from **My IP** (not `0.0.0.0/0` — no reason to expose SSH to the world).
   - Allow HTTP (port 80) from **Anywhere** (`0.0.0.0/0`) — this is the app.
7. Storage: bump from the default 8 GB to **20 GB** gp3 (the two HF models + Docker images + redis data need room; still within the free-tier 30 GB).
8. **Launch instance**.

## Step 2 — Connect

```bash
chmod 400 ~/Downloads/legal-rag-key.pem
ssh -i ~/Downloads/legal-rag-key.pem ubuntu@<EC2_PUBLIC_IP>
```

Get `<EC2_PUBLIC_IP>` from the instance's detail page in the console.

## Step 3 — Install Docker

Run on the instance:

```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo \"$VERSION_CODENAME\") stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
sudo usermod -aG docker ubuntu
```

Log out and back in (so the `docker` group membership takes effect):

```bash
exit
ssh -i ~/Downloads/legal-rag-key.pem ubuntu@<EC2_PUBLIC_IP>
docker ps   # should run with no "permission denied"
```

## Step 4 — Add swap (do this before running anything)

```bash
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
free -h   # confirm ~2 GB swap shows up
```

This won't make the app fast under memory pressure, but it turns "container
gets SIGKILL'd" into "container gets slow," which is the difference between
the stack staying up and silently dying.

## Step 5 — Get the code onto the instance

Simplest path, if the repo is on GitHub:

```bash
git clone <your-repo-url> legal-rag
cd legal-rag
```

If it's not on a git remote yet, `scp` the whole directory instead (from
your laptop, not the instance):

```bash
scp -i ~/Downloads/legal-rag-key.pem -r /Users/snehvijayvergiya/claude/legal-rag ubuntu@<EC2_PUBLIC_IP>:~/legal-rag
```

## Step 6 — Configure environment

```bash
cd ~/legal-rag
cp .env.example .env
nano .env   # or vim
```

At minimum set `GROQ_API_KEY=<your real key>`. Leave `REDIS_URL` alone —
`docker-compose.yml` overrides it to `redis://redis:6379` for the container
network regardless of what's in `.env`. Leave `LANGFUSE_*` blank unless you
want tracing wired up.

## Step 7 — (Optional) S3 for uploaded document backups

Right now, uploaded documents live only in the `hf-cache`/`data` Docker
volumes on this one instance — if the instance is terminated, they're gone.
If you want them durable, the lowest-effort option is periodic backup, not
a code change:

1. Console → **S3** → **Create bucket**, name it e.g. `legal-rag-uploads-<yourname>`, keep defaults (block all public access — this is your data, not a public asset).
2. Console → **IAM** → **Roles** → **Create role** → AWS service → EC2 → attach policy `AmazonS3FullAccess` scoped down later if you care, or a custom policy limited to that one bucket → attach the role to the EC2 instance (Instance settings → Security → Modify IAM role).
3. On the instance, install the CLI (`sudo apt-get install -y awscli`) and back up the ingested-docs volume periodically:
   ```bash
   docker run --rm -v legal-rag_hf-cache:/data -v $(pwd):/backup alpine tar czf /backup/hf-cache.tgz -C /data .
   aws s3 cp hf-cache.tgz s3://legal-rag-uploads-<yourname>/
   ```
   Put that in a cron job (`crontab -e`) if you want it automatic, e.g. nightly at 2am: `0 2 * * * cd /home/ubuntu/legal-rag && ./backup.sh`.

This is genuinely optional — skip it if losing uploaded docs on instance
termination is acceptable. Note this is only about *your own uploads*: the
~100+ document base corpus (Indian Kanoon judgments + core statutes) is
**not** in the git repo — it lives in Redis, populated by the scraper
scripts in Step 8.5 below. It has to be reseeded on every fresh Redis
volume (including a fresh instance), same as your uploads would be.

## Step 8 — Build and start

```bash
cd ~/legal-rag
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

First build takes a while (downloading the two HF models + building the
frontend). Watch it:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml logs -f backend
```

Wait for `Application startup complete` before testing.

## Step 8.5 — Seed the corpus (do this before Step 9 — a fresh Redis has nothing in it)

A brand-new `redis-data` volume is empty — none of the base legal corpus
exists until you populate it. Skipping this step doesn't error, it just
means every real question returns "No indexed document appears relevant."
Run these inside the backend container, in order (fastest first, so you
can sanity-check retrieval before committing to the long scrape):

```bash
cd ~/legal-rag
# 5 landmark cases used by the eval dataset - seconds, not minutes.
docker compose -f docker-compose.yml -f docker-compose.prod.yml exec backend python -m app.ingestion.seed_corpus

# 8 core statutes (Constitution, IPC, CrPC, Evidence Act, Contract Act,
# IT Act, CPC, Advocates Act) - a couple of minutes.
docker compose -f docker-compose.yml -f docker-compose.prod.yml exec backend python -m app.ingestion.bulk_seed_statutes

# ~100+ judgments across ~20 legal topics scraped from Indian Kanoon -
# the long one. Each document is scraped, chunked, and embedded on this
# instance's single throttled vCPU (see BOTTLENECKS.md) - expect this to
# take a while. Run it detached so a dropped SSH session doesn't kill it:
nohup docker compose -f docker-compose.yml -f docker-compose.prod.yml exec -T backend \
  python -m app.ingestion.bulk_seed_indiankanoon > seed_indiankanoon.log 2>&1 &
disown
```

Watch progress with `tail -f seed_indiankanoon.log`. When it's done, confirm
the corpus actually landed:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml exec redis redis-cli SCARD corpus:known_titles
```

Should read 100+ once the full scrape finishes (13 immediately after the
statutes+sample step above). If you tested queries before seeding finished,
also clear the semantic cache — it will have cached "no relevant document"
answers for real questions, and those stale entries will keep being served
even after the corpus is populated:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml exec redis redis-cli --scan --pattern "qacache:*" | \
  xargs -r docker compose -f docker-compose.yml -f docker-compose.prod.yml exec -T redis redis-cli DEL
```

## Step 9 — Verify

```bash
curl http://localhost/api/health
```

Then from your own laptop browser: `http://<EC2_PUBLIC_IP>/` — you should
see the same frontend you tested locally.

## Step 10 — Keep it running across reboots

Already handled: every service in `docker-compose.prod.yml` has
`restart: unless-stopped`, so a `sudo reboot` (or an instance stop/start)
brings everything back automatically once Docker's daemon starts.

## Updating later

```bash
cd ~/legal-rag
git pull
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

## Known limitations of this setup

- **No HTTPS.** nginx here is plain HTTP on port 80. Fine for a demo/portfolio
  project; if you want a real domain with TLS, the free option is Caddy
  instead of nginx (auto Let's Encrypt) or an AWS Application Load Balancer
  with ACM (not free-tier).
- **No horizontal scaling / no managed Redis.** This is one box, one Redis
  process holding vectors + cache + memory + queues. That's an intentional
  scope choice for a free-tier demo, not an oversight — call it out if asked
  in an interview context, don't pretend it's production-grade HA.
- **Rate limits are still whatever's in `.env`** (`RPM_LIMIT_*`,
  `DAILY_TOKEN_BUDGET_*`) — those are Groq-side and unrelated to hosting.
