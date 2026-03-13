# Infrastructure

## Terraform — All infrastructure as code

### Root Files
- `versions.tf` — Terraform >= 1.5, providers: google, google-beta, helm, kubernetes
- `backend.tf` — GCS state backend (`hsv-terraform-state` bucket)
- `variables.tf` — All root variables (project, region, pool sizes, toggles)
- `main.tf` — Wires 6 modules, configures providers from GKE outputs
- `outputs.tf` — Cluster endpoint, connection strings, kubeconfig command

### Modules (`modules/`)

| Module | Purpose | Key Resources |
|---|---|---|
| `networking` | VPC, subnets, NAT, firewall | VPC, subnet (pods/services ranges), Cloud NAT, 3 firewall rules, private service access |
| `gke` | GKE cluster + 3 node pools | Cluster (Workload Identity, VPA, managed Prometheus), voice-gpu/agent-cpu/database pools |
| `redis` | Memorystore Redis | STANDARD_HA instance, private service access, volatile-lru eviction |
| `kafka` | Confluent Cloud placeholder | Commented resources, outputs bootstrap_servers |
| `monitoring` | kube-prometheus-stack Helm | Prometheus + Grafana + Alertmanager, discovers ServiceMonitors |
| `cockroachdb` | Dual mode DB | Serverless (default) or self-hosted via Helm on database node pool |

### Environments (`environments/`)
- `dev.tfvars` — Preemptible, no GPU, 1 node/pool, 1GB Redis, CockroachDB Serverless
- `staging.tfvars` — Standard VMs, 1 GPU node, 2 nodes/pool, 2GB Redis, Serverless
- `production.tfvars` — Regional cluster, 2 GPU nodes, 3 nodes/pool, 5GB Redis, self-hosted CockroachDB

### Usage
```bash
cd infrastructure
terraform init
terraform plan -var-file=environments/dev.tfvars
terraform apply -var-file=environments/dev.tfvars
```

### Node Pool Design
- **voice-gpu**: n1-standard-4/8 + nvidia-tesla-t4, taint `nvidia.com/gpu=present:NoSchedule`
- **agent-cpu**: e2-standard-2/4, spot-capable
- **database**: e2-standard-4, **never preemptible**, taint `workload=database:NoSchedule`
