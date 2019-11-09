terraform {
  backend "gcs" {
    bucket = "ultimanager-terraform-admin"
    prefix = "project"
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

  // Since the project ID must be unique and projects can't be truly destroyed
  // for 90 days, we must add a little randomness to the ID to ensure the
  // project ID is unique every time.
  project_id = random_id.project_id.hex
}

// Add everyone in the 'ultimanager.com' domain as project editors.
resource "google_project_iam_member" "editors" {
  member  = "domain:ultimanager.com"
  project = google_project.ultimanager.id
  role    = "roles/editor"
}

output "root_project" {
  description = "The root project that all other resources are provisioned in."
  value       = google_project.ultimanager
}
