resource "google_redis_instance" "session_cache" {
  name               = "hsv-redis-${var.environment}"
  project            = var.project_id
  region             = var.region
  tier               = "STANDARD_HA"
  memory_size_gb     = var.memory_size_gb
  redis_version      = var.redis_version
  display_name       = "HSV Session Cache (${var.environment})"
  authorized_network = var.network_id
  connect_mode       = "PRIVATE_SERVICE_ACCESS"

  redis_configs = {
    maxmemory-policy = "volatile-lru"
  }

  labels = {
    app         = "hausa-voice-swarm"
    environment = var.environment
  }
}
