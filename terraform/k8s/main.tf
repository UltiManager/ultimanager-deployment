terraform {
  backend "gcs" {
    bucket = "ultimanager-terraform-admin"
    prefix = "k8s"
  }
}

provider "google" {
  version = "~> 2.17"
}

provider "kubernetes" {
  version = "~> 1.9"

  client_certificate     = data.terraform_remote_state.cluster.outputs.cluster_auth_certificate
  client_key             = data.terraform_remote_state.cluster.outputs.cluster_auth_key
  cluster_ca_certificate = data.terraform_remote_state.cluster.outputs.cluster_auth_ca_certificate
  host                   = data.terraform_remote_state.cluster.outputs.cluster_host
  load_config_file       = false

  // The token is what lets us use IAM permissions to authorize Kubernetes
  // operations.
  // https://stackoverflow.com/questions/51200159/how-to-bootstrap-rbac-privileges-when-bringing-up-a-gke-cluster-with-terraform
  token = data.google_client_config.default.access_token
}

data "terraform_remote_state" "cluster" {
  backend = "gcs"

  config = {
    bucket = "ultimanager-terraform-admin"
    prefix = "cluster"
  }
}

data "google_client_config" "default" {}
