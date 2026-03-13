# ── Node Service Account ─────────────────────────────────────────────

resource "google_service_account" "gke_nodes" {
  account_id   = "hsv-gke-nodes-${var.environment}"
  display_name = "HSV GKE Node Service Account (${var.environment})"
  project      = var.project_id
}

resource "google_project_iam_member" "node_log_writer" {
  project = var.project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.gke_nodes.email}"
}

resource "google_project_iam_member" "node_metric_writer" {
  project = var.project_id
  role    = "roles/monitoring.metricWriter"
  member  = "serviceAccount:${google_service_account.gke_nodes.email}"
}

resource "google_project_iam_member" "node_monitoring_viewer" {
  project = var.project_id
  role    = "roles/monitoring.viewer"
  member  = "serviceAccount:${google_service_account.gke_nodes.email}"
}

resource "google_project_iam_member" "node_artifact_reader" {
  project = var.project_id
  role    = "roles/artifactregistry.reader"
  member  = "serviceAccount:${google_service_account.gke_nodes.email}"
}

# ── GKE Cluster ──────────────────────────────────────────────────────

resource "google_container_cluster" "primary" {
  provider = google-beta

  name     = var.cluster_name
  project  = var.project_id
  location = var.regional_cluster ? var.region : "${var.region}-a"

  network    = var.network_id
  subnetwork = var.subnetwork_id

  # Remove default node pool — we manage our own
  remove_default_node_pool = true
  initial_node_count       = 1

  ip_allocation_policy {
    cluster_secondary_range_name  = var.pods_range_name
    services_secondary_range_name = var.services_range_name
  }

  workload_identity_config {
    workload_pool = "${var.project_id}.svc.id.goog"
  }

  vertical_pod_autoscaling {
    enabled = true
  }

  release_channel {
    channel = "REGULAR"
  }

  monitoring_config {
    enable_components = ["SYSTEM_COMPONENTS", "WORKLOADS"]
    managed_prometheus {
      enabled = true
    }
  }

  logging_config {
    enable_components = ["SYSTEM_COMPONENTS", "WORKLOADS"]
  }

  private_cluster_config {
    enable_private_nodes    = true
    enable_private_endpoint = false
    master_ipv4_cidr_block  = "172.16.0.0/28"
  }

  master_authorized_networks_config {
    cidr_blocks {
      cidr_block   = "0.0.0.0/0"
      display_name = "All networks"
    }
  }

  deletion_protection = var.environment == "production" ? true : false
}

# ── Voice GPU Node Pool ──────────────────────────────────────────────

resource "google_container_node_pool" "voice_gpu" {
  count = var.enable_gpu_pool ? 1 : 0

  name     = "voice-gpu"
  project  = var.project_id
  location = google_container_cluster.primary.location
  cluster  = google_container_cluster.primary.name

  initial_node_count = var.voice_gpu_pool_size

  autoscaling {
    min_node_count = 0
    max_node_count = var.voice_gpu_max_nodes
  }

  node_config {
    machine_type    = var.voice_gpu_machine_type
    service_account = google_service_account.gke_nodes.email
    oauth_scopes    = ["https://www.googleapis.com/auth/cloud-platform"]
    spot            = var.preemptible

    guest_accelerator {
      type  = "nvidia-tesla-t4"
      count = 1
      gpu_driver_installation_config {
        gpu_driver_version = "LATEST"
      }
    }

    taint {
      key    = "nvidia.com/gpu"
      value  = "present"
      effect = "NO_SCHEDULE"
    }

    labels = {
      "node-pool"   = "voice-gpu"
      "environment" = var.environment
    }

    workload_metadata_config {
      mode = "GKE_METADATA"
    }
  }

  management {
    auto_repair  = true
    auto_upgrade = true
  }
}

# ── Agent CPU Node Pool ──────────────────────────────────────────────

resource "google_container_node_pool" "agent_cpu" {
  name     = "agent-cpu"
  project  = var.project_id
  location = google_container_cluster.primary.location
  cluster  = google_container_cluster.primary.name

  initial_node_count = var.agent_cpu_pool_size

  autoscaling {
    min_node_count = 1
    max_node_count = var.agent_cpu_max_nodes
  }

  node_config {
    machine_type    = var.agent_cpu_machine_type
    service_account = google_service_account.gke_nodes.email
    oauth_scopes    = ["https://www.googleapis.com/auth/cloud-platform"]
    spot            = var.preemptible

    labels = {
      "node-pool"   = "agent-cpu"
      "environment" = var.environment
    }

    workload_metadata_config {
      mode = "GKE_METADATA"
    }
  }

  management {
    auto_repair  = true
    auto_upgrade = true
  }
}

# ── Database Node Pool ───────────────────────────────────────────────

resource "google_container_node_pool" "database" {
  name     = "database"
  project  = var.project_id
  location = google_container_cluster.primary.location
  cluster  = google_container_cluster.primary.name

  initial_node_count = var.database_pool_size

  autoscaling {
    min_node_count = 1
    max_node_count = var.database_max_nodes
  }

  node_config {
    machine_type    = var.database_machine_type
    service_account = google_service_account.gke_nodes.email
    oauth_scopes    = ["https://www.googleapis.com/auth/cloud-platform"]
    # Database pool is never preemptible — stateful workloads
    spot = false

    taint {
      key    = "workload"
      value  = "database"
      effect = "NO_SCHEDULE"
    }

    labels = {
      "node-pool"   = "database"
      "environment" = var.environment
    }

    workload_metadata_config {
      mode = "GKE_METADATA"
    }
  }

  management {
    auto_repair  = true
    auto_upgrade = true
  }
}
