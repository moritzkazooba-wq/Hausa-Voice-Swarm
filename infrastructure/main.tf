data "google_client_config" "default" {}

provider "google" {
  project = var.project_id
  region  = var.region
}

provider "google-beta" {
  project = var.project_id
  region  = var.region
}

provider "kubernetes" {
  host                   = "https://${module.gke.cluster_endpoint}"
  token                  = data.google_client_config.default.access_token
  cluster_ca_certificate = base64decode(module.gke.cluster_ca_certificate)
}

provider "helm" {
  kubernetes {
    host                   = "https://${module.gke.cluster_endpoint}"
    token                  = data.google_client_config.default.access_token
    cluster_ca_certificate = base64decode(module.gke.cluster_ca_certificate)
  }
}

# ── Networking ───────────────────────────────────────────────────────

module "networking" {
  source = "./modules/networking"

  project_id  = var.project_id
  region      = var.region
  vpc_name    = var.vpc_name
  environment = var.environment
}

# ── GKE Cluster ──────────────────────────────────────────────────────

module "gke" {
  source = "./modules/gke"

  project_id          = var.project_id
  region              = var.region
  cluster_name        = var.cluster_name
  environment         = var.environment
  network_id          = module.networking.network_id
  subnetwork_id       = module.networking.subnetwork_id
  pods_range_name     = module.networking.pods_range_name
  services_range_name = module.networking.services_range_name

  enable_gpu_pool        = var.enable_gpu_pool
  voice_gpu_machine_type = var.voice_gpu_machine_type
  voice_gpu_pool_size    = var.voice_gpu_pool_size
  voice_gpu_max_nodes    = var.voice_gpu_max_nodes
  agent_cpu_machine_type = var.agent_cpu_machine_type
  agent_cpu_pool_size    = var.agent_cpu_pool_size
  agent_cpu_max_nodes    = var.agent_cpu_max_nodes
  database_machine_type  = var.database_machine_type
  database_pool_size     = var.database_pool_size
  database_max_nodes     = var.database_max_nodes
  preemptible            = var.preemptible
  regional_cluster       = var.regional_cluster
}

# ── Redis (Memorystore) ─────────────────────────────────────────────

module "redis" {
  source = "./modules/redis"

  project_id     = var.project_id
  region         = var.region
  network_id     = module.networking.network_id
  memory_size_gb = var.redis_memory_size_gb
  environment    = var.environment

  depends_on = [module.networking]
}

# ── Kafka (Confluent Cloud) ─────────────────────────────────────────

module "kafka" {
  source = "./modules/kafka"

  environment                 = var.environment
  region                      = var.region
  confluent_api_key           = var.confluent_api_key
  confluent_api_secret        = var.confluent_api_secret
  confluent_environment_id    = var.confluent_environment_id
  confluent_bootstrap_servers = var.confluent_bootstrap_servers
}

# ── Monitoring (kube-prometheus-stack) ───────────────────────────────

module "monitoring" {
  source = "./modules/monitoring"

  environment = var.environment

  depends_on = [module.gke]
}

# ── CockroachDB ─────────────────────────────────────────────────────

module "cockroachdb" {
  source = "./modules/cockroachdb"

  self_hosted                         = var.cockroachdb_self_hosted
  cockroachdb_cloud_connection_string = var.cockroachdb_cloud_connection_string
  environment                         = var.environment
  region                              = var.region

  depends_on = [module.gke]
}
