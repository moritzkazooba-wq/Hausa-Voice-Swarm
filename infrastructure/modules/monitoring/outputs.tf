output "prometheus_endpoint" {
  description = "Prometheus endpoint inside the cluster"
  value       = "http://kube-prometheus-stack-prometheus.monitoring.svc:9090"
}

output "grafana_endpoint" {
  description = "Grafana endpoint inside the cluster"
  value       = "http://kube-prometheus-stack-grafana.monitoring.svc:80"
}
