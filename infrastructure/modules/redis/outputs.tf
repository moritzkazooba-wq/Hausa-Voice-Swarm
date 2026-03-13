output "redis_host" {
  description = "Redis instance host"
  value       = google_redis_instance.session_cache.host
}

output "redis_port" {
  description = "Redis instance port"
  value       = google_redis_instance.session_cache.port
}

output "redis_connection_string" {
  description = "Redis connection string"
  value       = "redis://${google_redis_instance.session_cache.host}:${google_redis_instance.session_cache.port}/0"
}
