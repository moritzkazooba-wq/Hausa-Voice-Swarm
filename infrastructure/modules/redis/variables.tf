variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "region" {
  description = "GCP region"
  type        = string
}

variable "network_id" {
  description = "VPC network ID for private service access"
  type        = string
}

variable "memory_size_gb" {
  description = "Redis memory size in GB"
  type        = number
  default     = 2
}

variable "environment" {
  description = "Environment name"
  type        = string
}

variable "redis_version" {
  description = "Redis version"
  type        = string
  default     = "REDIS_7_0"
}
