variable "billing_account" {
  description = "The name of the billing account to bill resource usage to."
}

variable "gcp_region" {
  default     = "us-east1"
  description = "The region to create GCP resources in."
}

variable "organization_id" {
  description = "The ID of the main GCP organization to create resources in."
}
