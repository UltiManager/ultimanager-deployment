variable "dns_project_id" {
  description = "The ID of the project that DNS records are stored in."
}

variable "gcp_region" {
  default     = "us-east1"
  description = "The region to create GCP resources in."
}

variable "root_domain" {
  description = "The root domain for the application."
}
