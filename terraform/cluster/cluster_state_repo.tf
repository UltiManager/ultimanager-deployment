resource "google_sourcerepo_repository" "cluster_state" {
  name    = "ultimanager-cluster-state"
  project = google_project.ultimanager.id

  depends_on = [google_project_service.sourcerepo]
}

resource "google_project_iam_member" "cloudbuild" {
  member  = "serviceAccount:${google_project.ultimanager.number}@cloudbuild.gserviceaccount.com"
  project = google_project.ultimanager.id
  role    = "roles/source.writer"
}

resource "google_service_account" "flux" {
  account_id = "fluxcd"
  project    = google_project.ultimanager.id
}

resource "google_project_iam_member" "flux_source_writer" {
  member  = "serviceAccount:${google_service_account.flux.email}"
  project = google_project.ultimanager.id
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
