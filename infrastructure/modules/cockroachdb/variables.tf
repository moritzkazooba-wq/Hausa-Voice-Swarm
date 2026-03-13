variable "self_hosted" {
  description = "Deploy self-hosted CockroachDB (true) or use Serverless (false)"
  type        = bool
  default     = false
}

variable "cockroachdb_cloud_connection_string" {
  description = "CockroachDB Serverless connection string (when self_hosted = false)"
  type        = string
  default     = ""
  sensitive   = true
}

variable "environment" {
  description = "Environment name"
  type        = string
}

variable "region" {
  description = "GCP region"
  type        = string
}

variable "operator_chart_version" {
  description = "CockroachDB Helm chart version"
  type        = string
  default     = "13.0.0"
}

variable "cockroachdb_replicas" {
  description = "Number of CockroachDB replicas (self-hosted mode)"
  type        = number
  default     = 3
}

variable "cockroachdb_storage_size" {
  description = "Persistent volume size per CockroachDB node"
  type        = string
  default     = "100Gi"
}

variable "serverless_spend_limit" {
  description = "CockroachDB Serverless spend limit (USD)"
  type        = number
  default     = 0
}
