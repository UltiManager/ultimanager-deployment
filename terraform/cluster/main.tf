terraform {
  backend "gcs" {
    bucket = "ultimanager-terraform-admin"
    prefix = "cluster"
  }
}

provider "google" {
  version = "~> 2.17"

  region = var.gcp_region
}

provider "random" {
  version = "~> 2.2"
}

data "google_billing_account" "billing_account" {
  billing_account = var.billing_account
}

resource "random_id" "project_id" {
  byte_length = 4
  prefix      = "ultimanager-${terraform.workspace}-"
}

resource "google_project" "ultimanager" {
  billing_account = data.google_billing_account.billing_account.id
  name            = "UltiManager - ${terraform.workspace}"
  org_id          = var.organization_id
  project_id      = random_id.project_id.hex
}

resource "google_project_service" "container" {
  project = google_project.ultimanager.id
  service = "container.googleapis.com"
}

resource "google_project_iam_member" "viewers" {
  member  = "domain:ultimanager.com"
  project = google_project.ultimanager.id
  role    = "roles/viewer"
}

resource "google_container_cluster" "primary" {
  location = var.gcp_region
  name     = "ultimanager"
  project  = google_project.ultimanager.id

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

  depends_on = [
    google_project_service.container
  ]
}

resource "google_container_node_pool" "primary_preemptible_nodes" {
  cluster    = google_container_cluster.primary.name
  location   = var.gcp_region
  name       = "ultimanager-primary-node-pool"
  node_count = 1
  project    = google_project.ultimanager.id

  node_config {
    preemptible  = true
    machine_type = "n1-standard-1"

    metadata = {
      disable-legacy-endpoints = "true"
    }

    oauth_scopes = [
      # Required for pulling images from GCR
      "https://www.googleapis.com/auth/devstorage.read_only",
      "https://www.googleapis.com/auth/logging.write",
      "https://www.googleapis.com/auth/monitoring",
    ]
  }
}

output "cluster_auth_ca_certificate" {
  sensitive = true
  value     = base64decode(google_container_cluster.primary.master_auth.0.cluster_ca_certificate)
}

output "cluster_auth_certificate" {
  sensitive = true
  value     = base64decode(google_container_cluster.primary.master_auth.0.client_certificate)
}

output "cluster_auth_key" {
  sensitive = true
  value     = base64decode(google_container_cluster.primary.master_auth.0.client_key)
}

output "cluster_host" {
  value = google_container_cluster.primary.endpoint
}
