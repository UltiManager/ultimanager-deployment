resource "google_sourcerepo_repository" "cluster_state" {
  name    = "ultimanager-cluster-state"
  project = local.root_project_id
}

resource "google_project_iam_member" "cloudbuild" {
  member  = "serviceAccount:${data.terraform_remote_state.project.outputs.root_project.number}@cloudbuild.gserviceaccount.com"
  project = local.root_project_id
  role    = "roles/source.writer"
}

resource "google_service_account" "flux" {
  account_id = "fluxcd"
  project    = local.root_project_id
}

resource "google_project_iam_member" "flux_source_writer" {
  member  = "serviceAccount:${google_service_account.flux.email}"
  project = local.root_project_id
  role    = "roles/source.writer"
}

output "cluster_state_repo" {
  value = google_sourcerepo_repository.cluster_state
}

output "cluster_state_repo_url" {
  value = google_sourcerepo_repository.cluster_state.url
}

output "flux_service_account" {
  value = google_service_account.flux
}
