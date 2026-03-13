variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "region" {
  description = "GCP region"
  type        = string
  default     = "us-central1"
}

variable "environment" {
  description = "Environment name (dev, staging, production)"
  type        = string
  default     = "dev"
}

variable "cluster_name" {
  description = "GKE cluster name"
  type        = string
  default     = "hsv-cluster"
}

variable "vpc_name" {
  description = "VPC network name"
  type        = string
  default     = "hsv-vpc"
}

# ── GKE Node Pools ──────────────────────────────────────────────────

variable "enable_gpu_pool" {
  description = "Whether to create the GPU node pool for voice pipeline"
  type        = bool
  default     = false
}

variable "voice_gpu_pool_size" {
  description = "Initial node count for voice-gpu pool"
  type        = number
  default     = 1
}

variable "voice_gpu_max_nodes" {
  description = "Max nodes for voice-gpu pool autoscaler"
  type        = number
  default     = 10
}

variable "voice_gpu_machine_type" {
  description = "Machine type for voice-gpu pool (must be n1 for GPU)"
  type        = string
  default     = "n1-standard-4"
}

variable "agent_cpu_pool_size" {
  description = "Initial node count for agent-cpu pool"
  type        = number
  default     = 1
}

variable "agent_cpu_max_nodes" {
  description = "Max nodes for agent-cpu pool autoscaler"
  type        = number
  default     = 20
}

variable "agent_cpu_machine_type" {
  description = "Machine type for agent-cpu pool"
  type        = string
  default     = "e2-standard-4"
}

variable "database_pool_size" {
  description = "Initial node count for database pool"
  type        = number
  default     = 1
}

variable "database_max_nodes" {
  description = "Max nodes for database pool autoscaler"
  type        = number
  default     = 5
}

variable "database_machine_type" {
  description = "Machine type for database pool"
  type        = string
  default     = "e2-standard-4"
}

variable "preemptible" {
  description = "Use preemptible/spot VMs for non-database pools"
  type        = bool
  default     = true
}

variable "regional_cluster" {
  description = "Create regional (multi-zone) cluster instead of zonal"
  type        = bool
  default     = false
}

# ── Redis ────────────────────────────────────────────────────────────

variable "redis_memory_size_gb" {
  description = "Memorystore Redis memory size in GB"
  type        = number
  default     = 2
}

# ── Kafka (Confluent Cloud) ─────────────────────────────────────────

variable "confluent_api_key" {
  description = "Confluent Cloud API key"
  type        = string
  default     = ""
}

variable "confluent_api_secret" {
  description = "Confluent Cloud API secret"
  type        = string
  default     = ""
  sensitive   = true
}

variable "confluent_environment_id" {
  description = "Confluent Cloud environment ID"
  type        = string
  default     = ""
}

variable "confluent_bootstrap_servers" {
  description = "Confluent Cloud bootstrap servers (if pre-provisioned)"
  type        = string
  default     = ""
}

# ── CockroachDB ─────────────────────────────────────────────────────

variable "cockroachdb_self_hosted" {
  description = "Deploy self-hosted CockroachDB instead of Serverless"
  type        = bool
  default     = false
}

variable "cockroachdb_cloud_connection_string" {
  description = "CockroachDB Serverless connection string (when not self-hosted)"
  type        = string
  default     = ""
  sensitive   = true
}
