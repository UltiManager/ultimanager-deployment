resource "google_project_service" "cloudbuild" {
  project = local.root_project_id
  service = "cloudbuild.googleapis.com"
}

resource "google_cloudbuild_trigger" "web" {
  provider = "google-beta"

  filename = "cloudbuild.yml"
  project  = local.root_project_id

  substitutions = {
    _K8S_CLUSTER_NAME     = google_container_cluster.primary.name
    _K8S_CLUSTER_LOCATION = google_container_cluster.primary.location
    _K8S_STATE_REPO_NAME  = google_sourcerepo_repository.cluster_state.name
  }

  github {
    owner = "UltiManager"
    name  = "ultimanager-web"

    push {
      branch = "cloud-build"
    }
  }

  depends_on = [google_project_service.cloudbuild]
}

