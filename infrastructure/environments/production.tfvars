project_id  = "hsv-production" # replace with your GCP project ID
region      = "us-central1"
environment = "production"

cluster_name     = "hsv-production"
preemptible      = false
regional_cluster = true # multi-zone HA

# GPU pool for voice pipeline
enable_gpu_pool        = true
voice_gpu_pool_size    = 2
voice_gpu_machine_type = "n1-standard-8"

# Production node pools
agent_cpu_pool_size    = 3
agent_cpu_machine_type = "e2-standard-4"
database_pool_size     = 3
database_machine_type  = "e2-standard-4"

redis_memory_size_gb = 5

# Self-hosted CockroachDB on dedicated database nodes
cockroachdb_self_hosted = true
