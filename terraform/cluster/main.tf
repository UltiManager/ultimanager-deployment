terraform {
  backend "gcs" {
    bucket = "ultimanager-terraform-admin"
    prefix = "cluster"
  }
}

data "terraform_remote_state" "network" {
  backend = "gcs"

  config = {
    bucket = "ultimanager-terraform-admin"
    prefix = "network"
  }
}

data "terraform_remote_state" "project" {
  backend = "gcs"

  config = {
    bucket = "ultimanager-terraform-admin"
    prefix = "project"
  }
}

provider "google" {
  version = "~> 2.17"

  region = var.gcp_region
}

provider "google-beta" {
  version = "~> 2.17"

  region = var.gcp_region
}

provider "random" {
  version = "~> 2.2"
}

locals {
  root_project_id = data.terraform_remote_state.project.outputs.root_project.id
}

data "google_container_engine_versions" "latest_patch" {
  location       = var.gcp_region
  project        = local.root_project_id
  version_prefix = "1.14."
}

resource "google_container_cluster" "primary" {
  location           = var.gcp_region
  min_master_version = data.google_container_engine_versions.latest_patch.latest_master_version
  name               = "ultimanager"
  network            = data.terraform_remote_state.network.outputs.vpc.name
  project            = local.root_project_id

  # We can't create a cluster with no node pool defined, but we want to only use
  # separately managed node pools. So we create the smallest possible default
  # node pool and immediately delete it.
  remove_default_node_pool = true
  initial_node_count       = 1

  ip_allocation_policy {
    use_ip_aliases = true
  }

  master_auth {
    username = ""
    password = ""

    client_certificate_config {
      issue_client_certificate = false
    }
  }
}

resource "google_container_node_pool" "primary_preemptible_nodes" {
  cluster    = google_container_cluster.primary.name
  location   = var.gcp_region
  name       = "ultimanager-primary-node-pool"
  node_count = 1
  project    = local.root_project_id
  version    = data.google_container_engine_versions.latest_patch.latest_node_version

  autoscaling {
    max_node_count = 6
    min_node_count = 1
  }

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
      # For deploying from cluster state repository
      "https://www.googleapis.com/auth/source.read_write",
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

output "cluster_name" {
  value = google_container_cluster.primary.name
}

output "cluster_region" {
  value = google_container_cluster.primary.region
}
