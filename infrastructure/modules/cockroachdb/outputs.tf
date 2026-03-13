output "connection_string" {
  description = "CockroachDB connection string"
  value = var.self_hosted ? (
    "postgresql://root@cockroachdb-public.cockroachdb.svc:26257/hsv?sslmode=verify-full"
  ) : var.cockroachdb_cloud_connection_string
  sensitive = true
}
