terraform {
  backend "gcs" {
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

  project = data.terraform_remote_state.project.outputs.root_project.id
  region  = var.gcp_region
}

resource "google_compute_network" "vpc" {
  auto_create_subnetworks = true
  name                    = "ultimanager-vpc"
  routing_mode            = "REGIONAL"
}

output "vpc" {
  description = "The main VPC network for the project."
  value       = google_compute_network.vpc
}
