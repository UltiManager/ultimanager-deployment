resource "google_compute_address" "cluster" {
  name    = "ultimanager-cluster"
  project = local.root_project_id
}

data "google_project" "dns" {
  project_id = var.dns_project_id
}

data "google_dns_managed_zone" "public" {
  name    = "ultimanager"
  project = data.google_project.dns.id
}

resource "google_dns_record_set" "api" {
  managed_zone = data.google_dns_managed_zone.public.name
  name         = "api.${data.google_dns_managed_zone.public.dns_name}"
  project      = data.google_project.dns.id
  rrdatas      = [google_compute_address.cluster.address]
  ttl          = 60
  type         = "A"
}

resource "google_dns_record_set" "root" {
  managed_zone = data.google_dns_managed_zone.public.name
  name         = data.google_dns_managed_zone.public.dns_name
  project      = data.google_project.dns.id
  rrdatas      = [google_compute_address.cluster.address]
  ttl          = 60
  type         = "A"
}

output "api_domain" {
  value = "api.${var.root_domain}"
}

output "cluster_address" {
  value = google_compute_address.cluster
}

output "root_domain" {
  value = var.root_domain
}
