project_id  = "hsv-dev" # replace with your GCP project ID
region      = "us-central1"
environment = "dev"

cluster_name     = "hsv-dev"
preemptible      = true
regional_cluster = false

# No GPU pool in dev (cost savings)
enable_gpu_pool     = false
voice_gpu_pool_size = 0

# Minimal node pools
agent_cpu_pool_size    = 1
agent_cpu_machine_type = "e2-standard-2"
database_pool_size     = 1
database_machine_type  = "e2-standard-2"

# Small Redis
redis_memory_size_gb = 1

# CockroachDB Serverless (free tier)
cockroachdb_self_hosted = false
