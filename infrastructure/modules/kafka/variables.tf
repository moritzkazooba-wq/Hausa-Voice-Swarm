variable "environment" {
  description = "Environment name"
  type        = string
}

variable "region" {
  description = "GCP region for Kafka cluster"
  type        = string
}

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
  description = "Pre-provisioned bootstrap servers (bypasses resource creation)"
  type        = string
  default     = ""
}
