terraform {
  backend "gcs" {
    bucket = "ultimanager-terraform-admin"
    prefix = "database"
  }
}

provider "google" {
  version = "~> 2.17"

  project = data.terraform_remote_state.project.outputs.root_project.id
  region  = var.gcp_region
}

provider "google-beta" {
  version = "~> 2.17"

  project = data.terraform_remote_state.project.outputs.root_project.id
  region  = var.gcp_region
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

resource "google_compute_global_address" "db_private_ip" {
  provider = "google-beta"

  name          = "ultimanager-db-private-ip"
  purpose       = "VPC_PEERING"
  address_type  = "INTERNAL"
  prefix_length = 16
  network       = data.terraform_remote_state.network.outputs.vpc.self_link
}

resource "google_service_networking_connection" "db_vpc_connection" {
  network = data.terraform_remote_state.network.outputs.vpc.self_link
  service = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [
  google_compute_global_address.db_private_ip.name]
}


resource "google_sql_database_instance" "db" {
  depends_on = [google_service_networking_connection.db_vpc_connection]

  database_version = "POSTGRES_11"

  settings {
    availability_type = "ZONAL"
    disk_autoresize   = false
    tier              = "db-f1-micro"

    ip_configuration {
      ipv4_enabled    = false
      private_network = data.terraform_remote_state.network.outputs.vpc.self_link
    }
  }
}

resource "google_sql_user" "admin" {
  instance = google_sql_database_instance.db.name
  name     = "admin"
  password = random_string.admin_password.result
}

resource "random_string" "admin_password" {
  length = 32
}

output "admin" {
  value = google_sql_user.admin
}

output "db" {
  description = "The main database instance."
  value       = google_sql_database_instance.db
}
