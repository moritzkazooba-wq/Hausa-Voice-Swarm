project_id  = "hsv-staging" # replace with your GCP project ID
region      = "us-central1"
environment = "staging"

cluster_name     = "hsv-staging"
preemptible      = false
regional_cluster = false

# GPU pool enabled with 1 node
enable_gpu_pool        = true
voice_gpu_pool_size    = 1
voice_gpu_machine_type = "n1-standard-4"

# Medium node pools
agent_cpu_pool_size    = 2
agent_cpu_machine_type = "e2-standard-4"
database_pool_size     = 2
database_machine_type  = "e2-standard-4"

redis_memory_size_gb = 2

# CockroachDB Serverless
cockroachdb_self_hosted = false
