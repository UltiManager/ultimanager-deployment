provider "google" {
  project = "ultimanager-prod"
  region  = var.gcp_region
  version = "~> 2.17"
}

provider "google-beta" {
  project = "ultimanager-prod"
  region  = var.gcp_region
  version = "~> 2.17"
}

resource "google_project_service" "cloudbuild" {
  service = "cloudbuild.googleapis.com"
}

resource "google_project_service" "cloudresourcemanager" {
  service = "cloudresourcemanager.googleapis.com"
}

resource "google_cloudbuild_trigger" "web" {
  provider = "google-beta"

  filename = "cloudbuild.yml"

  substitutions = {
    _K8S_CLUSTER_NAME     = google_container_cluster.primary.name
    _K8S_CLUSTER_LOCATION = google_container_cluster.primary.location
  }

  github {
    owner = "UltiManager"
    name  = "ultimanager-web"

    push {
      branch = "cloud-build"
    }
  }
}

resource "google_container_cluster" "primary" {
  name     = "ultimanager-${terraform.workspace}"
  location = var.gcp_region

  # We can't create a cluster with no node pool defined, but we want to only use
  # separately managed node pools. So we create the smallest possible default
  # node pool and immediately delete it.
  remove_default_node_pool = true
  initial_node_count       = 1

  master_auth {
    username = ""
    password = ""

    client_certificate_config {
      issue_client_certificate = false
    }
  }
}

resource "google_container_node_pool" "primary_preemptible_nodes" {
  name       = "default-node-pool"
  location   = var.gcp_region
  cluster    = google_container_cluster.primary.name
  node_count = 1

  node_config {
    preemptible  = true
    machine_type = "n1-standard-1"

    metadata = {
      disable-legacy-endpoints = "true"
    }

    oauth_scopes = [
      "https://www.googleapis.com/auth/devstorage.read_only",
      "https://www.googleapis.com/auth/logging.write",
      "https://www.googleapis.com/auth/monitoring",
    ]
  }
}

resource "google_compute_global_address" "ultimanager_web" {
  name = "ultimanager-web"
}

resource "google_dns_record_set" "ultimanager_web" {
  managed_zone = data.google_dns_managed_zone.main.name
  name         = data.google_dns_managed_zone.main.dns_name
  project      = "ultimanager-dns"
  rrdatas      = [google_compute_global_address.ultimanager_web.address]
  ttl          = 300
  type         = "A"
}

data "google_dns_managed_zone" "main" {
  name    = "ultimanager"
  project = "ultimanager-dns"
}
