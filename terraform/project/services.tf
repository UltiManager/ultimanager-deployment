// Enable each required project service.
resource "google_project_service" "service" {
  for_each = var.project_services

  project = google_project.ultimanager.id
  service = each.key
}
