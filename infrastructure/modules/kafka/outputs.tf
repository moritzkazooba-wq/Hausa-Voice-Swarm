output "bootstrap_servers" {
  description = "Kafka bootstrap servers"
  value       = var.confluent_bootstrap_servers != "" ? var.confluent_bootstrap_servers : "placeholder-not-configured"
}
