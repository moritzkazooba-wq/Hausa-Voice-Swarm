---
description: Deploy Hausa Voice Swarm voice pipeline to GKE or Pipecat Cloud
---

# /pipecat:deploy — Deploy Voice Pipeline

You are helping deploy the Hausa Voice Swarm Pipecat voice pipeline.

## Step 1: Determine Deployment Target

Use AskUserQuestion to ask where to deploy:
- **Docker Compose (local)** — run full stack locally
- **GKE (Kubernetes)** — deploy to Google Kubernetes Engine via Terraform
- **Pipecat Cloud** — deploy to Pipecat's managed platform

## Step 2: Pre-deployment Checks

Before any deployment, run these checks:

1. Run the verification suite: `/verify`
2. Check Docker builds: `docker build -t hsv-voice .`
3. Verify environment variables are set (check `.env.example` for required vars)
4. Check the Dockerfile at project root

## Docker Compose (Local)

```bash
docker compose up --build
```

Verify:
- `curl http://localhost:8000/health` returns `{"status": "ok"}`
- `curl http://localhost:8000/metrics` returns Prometheus metrics
- Redis, CockroachDB, Redpanda are healthy

## GKE Deployment

Read infrastructure files first:
- `infrastructure/CLAUDE.md` — Terraform module structure
- `k8s/CLAUDE.md` — Kubernetes manifest conventions
- `k8s/` — deployment, service, HPA, PDB manifests

Steps:
1. `cd infrastructure && terraform plan` — review changes
2. `cd infrastructure && terraform apply` — apply infrastructure
3. Build and push container: `docker build -t gcr.io/<project>/hsv-voice . && docker push gcr.io/<project>/hsv-voice`
4. Apply k8s manifests: `kubectl apply -f k8s/`
5. Verify: `kubectl get pods -l app=hsv-voice`
6. Check HPA: `kubectl get hpa` — should scale on `hsv_active_voice_sessions` custom metric

## Pipecat Cloud

Prerequisites — check these first:
1. Verify `pc` CLI is installed: `which pc || uv tool install pipecat-ai-cli`
2. Verify cloud auth: `pc cloud auth whoami`
3. Verify Docker daemon is running: `docker info`

Steps:
1. If `pcc-deploy.toml` exists, read it for config
2. If not, create one with project settings
3. Manage secrets from `.env` via `pc cloud secrets`
4. Build and push: `pc cloud build` (use 5-minute timeout)
5. Deploy: `pc cloud deploy`
6. Monitor: `pc cloud status`

## Post-Deployment Verification

After any deployment:
1. Hit `/health` endpoint — expect `{"status": "ok"}`
2. Hit `/metrics` endpoint — expect Prometheus exposition format with `hsv_` prefixed metrics
3. Check logs for startup errors
4. If GKE: verify custom-metric HPA is receiving `hsv_active_voice_sessions`

## Rollback

- Docker Compose: `docker compose down && docker compose up --build`
- GKE: `kubectl rollout undo deployment/hsv-voice`
- Pipecat Cloud: `pc cloud rollback`
