terraform {
  backend "gcs" {
    bucket = "ultimanager-terraform-admin"
    prefix = "cluster"
  }
}

provider "google" {
  region  = var.gcp_region
  version = "~> 2.17"
}

provider "google-beta" {
  region  = var.gcp_region
  version = "~> 2.17"
}

resource "google_project" "ultimanager" {
  name       = "UltiManager - ${terraform.workspace}"
  org_id     = var.organization_id
  project_id = "ultimanager-${terraform.workspace}"
}
