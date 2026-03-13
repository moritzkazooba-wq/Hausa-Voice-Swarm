output "network_id" {
  description = "VPC network ID"
  value       = google_compute_network.vpc.id
}

output "network_self_link" {
  description = "VPC network self link"
  value       = google_compute_network.vpc.self_link
}

output "subnetwork_id" {
  description = "GKE subnet ID"
  value       = google_compute_subnetwork.gke_subnet.id
}

output "subnetwork_self_link" {
  description = "GKE subnet self link"
  value       = google_compute_subnetwork.gke_subnet.self_link
}

output "pods_range_name" {
  description = "Name of the secondary IP range for pods"
  value       = "pods"
}

output "services_range_name" {
  description = "Name of the secondary IP range for services"
  value       = "services"
}
