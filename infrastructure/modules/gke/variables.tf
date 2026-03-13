variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "region" {
  description = "GCP region"
  type        = string
}

variable "cluster_name" {
  description = "GKE cluster name"
  type        = string
}

variable "environment" {
  description = "Environment name"
  type        = string
}

variable "network_id" {
  description = "VPC network ID"
  type        = string
}

variable "subnetwork_id" {
  description = "Subnet ID"
  type        = string
}

variable "pods_range_name" {
  description = "Secondary range name for pods"
  type        = string
}

variable "services_range_name" {
  description = "Secondary range name for services"
  type        = string
}

# ── Voice GPU Pool ───────────────────────────────────────────────────

variable "enable_gpu_pool" {
  description = "Whether to create the GPU node pool"
  type        = bool
  default     = false
}

variable "voice_gpu_machine_type" {
  description = "Machine type for GPU pool (must be n1 for GPUs)"
  type        = string
  default     = "n1-standard-4"
}

variable "voice_gpu_pool_size" {
  description = "Initial node count for GPU pool"
  type        = number
  default     = 1
}

variable "voice_gpu_max_nodes" {
  description = "Max nodes for GPU pool autoscaler"
  type        = number
  default     = 10
}

# ── Agent CPU Pool ───────────────────────────────────────────────────

variable "agent_cpu_machine_type" {
  description = "Machine type for agent-cpu pool"
  type        = string
  default     = "e2-standard-4"
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

# ── Database Pool ────────────────────────────────────────────────────

variable "database_machine_type" {
  description = "Machine type for database pool"
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

# ── Cluster Options ──────────────────────────────────────────────────

variable "preemptible" {
  description = "Use spot VMs for non-database pools"
  type        = bool
  default     = true
}

variable "regional_cluster" {
  description = "Create regional cluster (multi-zone)"
  type        = bool
  default     = false
}
