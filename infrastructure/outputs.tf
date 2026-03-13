output "cluster_endpoint" {
  description = "GKE cluster endpoint"
  value       = module.gke.cluster_endpoint
}

output "cluster_name" {
  description = "GKE cluster name"
  value       = module.gke.cluster_name
}

output "redis_host" {
  description = "Memorystore Redis host"
  value       = module.redis.redis_host
}

output "redis_port" {
  description = "Memorystore Redis port"
  value       = module.redis.redis_port
}

output "redis_connection_string" {
  description = "Redis connection string for application config"
  value       = "redis://${module.redis.redis_host}:${module.redis.redis_port}/0"
}

output "kafka_bootstrap_servers" {
  description = "Kafka bootstrap servers"
  value       = module.kafka.bootstrap_servers
}

output "cockroachdb_connection_string" {
  description = "CockroachDB connection string"
  value       = module.cockroachdb.connection_string
  sensitive   = true
}

output "prometheus_endpoint" {
  description = "Prometheus endpoint inside the cluster"
  value       = module.monitoring.prometheus_endpoint
}

output "kubeconfig_command" {
  description = "Command to configure kubectl"
  value       = "gcloud container clusters get-credentials ${module.gke.cluster_name} --region ${var.region} --project ${var.project_id}"
}
