variable "flux_namespace" {
  default     = "flux"
  description = "The name of the Kubernetes namespace to create Flux resources in."
}

variable "flux_version" {
  default     = "1.15.0"
  description = "The version of Flux to deploy."
}

variable "memcached_version" {
  default     = "1.5.15"
  description = "The version of memcached to run alongside Flux."
}

