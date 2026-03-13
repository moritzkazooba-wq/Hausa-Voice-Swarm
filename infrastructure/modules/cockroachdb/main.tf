# CockroachDB — Dual Mode Module
#
# Default (self_hosted = false): CockroachDB Serverless via Cockroach Cloud.
#   Provide connection string via var.cockroachdb_cloud_connection_string.
#
#   To manage via Terraform, add the cockroach provider to versions.tf:
#     cockroach = {
#       source  = "cockroachdb/cockroach"
#       version = "~> 1.0"
#     }
#
# resource "cockroach_cluster" "hsv" {
#   name           = "hsv-${var.environment}"
#   cloud_provider = "GCP"
#   serverless {
#     spend_limit = var.serverless_spend_limit
#   }
#   regions = [{ name = var.region }]
# }

# Self-hosted mode: deploys CockroachDB via Helm on the database node pool.

resource "kubernetes_namespace" "cockroachdb" {
  count = var.self_hosted ? 1 : 0

  metadata {
    name = "cockroachdb"
    labels = {
      "app.kubernetes.io/part-of" = "hausa-voice-swarm"
    }
  }
}

resource "helm_release" "cockroachdb" {
  count = var.self_hosted ? 1 : 0

  name       = "cockroachdb"
  repository = "https://charts.cockroachdb.com/"
  chart      = "cockroachdb"
  version    = var.operator_chart_version
  namespace  = kubernetes_namespace.cockroachdb[0].metadata[0].name

  set {
    name  = "statefulset.replicas"
    value = tostring(var.cockroachdb_replicas)
  }

  set {
    name  = "conf.single-node"
    value = var.cockroachdb_replicas == 1 ? "true" : "false"
  }

  set {
    name  = "storage.persistentVolume.size"
    value = var.cockroachdb_storage_size
  }

  # Schedule on database node pool
  set {
    name  = "nodeSelector.node-pool"
    value = "database"
  }

  set {
    name  = "tolerations[0].key"
    value = "workload"
  }

  set {
    name  = "tolerations[0].value"
    value = "database"
  }

  set {
    name  = "tolerations[0].effect"
    value = "NoSchedule"
  }
}
