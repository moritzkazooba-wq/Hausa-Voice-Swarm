# Infrastructure

## Terraform
- All infrastructure as code — no manual GCP console changes
- Modular structure: one module per resource group
- Default: CockroachDB Serverless (free tier for dev)

## GKE
- Custom node pools: voice-agents (high-CPU), api (standard), monitoring
- Custom-metric HPA using prometheus-adapter
- Scale on `active_voice_sessions` metric

## Modules
- `gke/` — GKE cluster and node pool configuration
- `cockroachdb/` — CockroachDB Serverless provisioning
- `redis/` — Memorystore Redis instance
- `kafka/` — Redpanda/Kafka cluster
- `monitoring/` — Prometheus, Grafana, alerting rules
- `networking/` — VPC, subnets, firewall rules
