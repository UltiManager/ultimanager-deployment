locals {
  flux_service_account = data.terraform_remote_state.cluster.outputs.flux_service_account.email
}

// Adapted from the output of 'fluxctl install'

resource "kubernetes_namespace" "flux" {
  metadata {
    name = var.flux_namespace

    labels = {
      app = "flux"
    }
  }
}

# The service account, cluster roles, and cluster role binding are
# only needed for Kubernetes with role-based access control (RBAC).
resource "kubernetes_service_account" "flux" {
  metadata {
    name      = "flux"
    namespace = var.flux_namespace

    labels = {
      name = "flux"
    }
  }
}

resource "kubernetes_cluster_role" "flux" {
  metadata {
    name = "flux"

    labels = {
      name = "flux"
    }
  }

  rule {
    api_groups = ["*"]
    resources  = ["*"]
    verbs      = ["*"]
  }

  rule {
    non_resource_urls = ["*"]
    verbs             = ["*"]
  }
}

resource "kubernetes_cluster_role_binding" "flux" {
  metadata {
    name = "flux"

    labels = {
      name = "flux"
    }
  }

  role_ref {
    api_group = "rbac.authorization.k8s.io"
    kind      = "ClusterRole"
    name      = "flux"
  }

  subject {
    kind      = "ServiceAccount"
    name      = kubernetes_service_account.flux.metadata.0.name
    namespace = var.flux_namespace
  }
}

resource "kubernetes_config_map" "flux_git_config" {
  metadata {
    name      = "flux-git-config"
    namespace = var.flux_namespace
  }

  data = {
    gitconfig = <<EOF
[credential "https://source.developers.google.com"]
    helper = /root/google-cloud-sdk/bin/git-credential-gcloud.sh
    username = ${local.flux_service_account}
EOF
  }
}

resource "kubernetes_deployment" "flux" {
  timeouts {
    create = "2m"
  }

  metadata {
    name      = "flux"
    namespace = var.flux_namespace
  }

  spec {
    replicas = 1

    selector {
      match_labels = {
        name = "flux"
      }
    }

    strategy {
      type = "Recreate"
    }

    template {
      metadata {
        annotations = {
          "prometheus.io/port" = "3031"
        }

        labels = {
          name = "flux"
        }
      }

      spec {
        # GCP apparently defaults this to false despite literally everyone else
        # defaulting it to true. Go figure.
        automount_service_account_token = true
        service_account_name            = kubernetes_service_account.flux.metadata.0.name

        container {
          args = [
            "--memcached-service=",
            "--git-url=${data.terraform_remote_state.cluster.outputs.cluster_state_repo.url}",
            "--git-branch=master",
            "--git-label=flux",
            "--git-user=flux",
            "--git-email=flux@ultimanager.com",
            "--listen-metrics=:3031"
          ]
          image             = "docker.io/ultimanager/flux:${var.flux_version}"
          image_pull_policy = "IfNotPresent"
          name              = "flux"

          liveness_probe {
            initial_delay_seconds = 5
            timeout_seconds       = 5

            http_get {
              path = "/api/flux/v6/identity.pub"
              port = "3030"
            }
          }

          port {
            container_port = "3030"
          }

          readiness_probe {
            initial_delay_seconds = 5
            timeout_seconds       = 5

            http_get {
              path = "/api/flux/v6/identity.pub"
              port = "3030"
            }
          }

          resources {
            requests {
              cpu    = "50m"
              memory = "64Mi"
            }
          }

          volume_mount {
            mount_path = "/root/.gitconfig"
            name       = "git-config"
            sub_path   = "gitconfig"
          }
        }

        volume {
          name = "git-config"

          config_map {
            name = kubernetes_config_map.flux_git_config.metadata.0.name
          }
        }
      }
    }
  }
}

resource "kubernetes_deployment" "flux_memcached" {
  metadata {
    name      = "memcached"
    namespace = var.flux_namespace
  }

  spec {
    replicas = 1

    selector {
      match_labels = {
        name = "memcached"
      }
    }

    template {
      metadata {
        labels = {
          name = "memcached"
        }
      }

      spec {
        container {
          args = [
            "-m 512",
            "-I 5m",
            "-p 11211"
          ]
          image             = "memcached:${var.memcached_version}"
          image_pull_policy = "IfNotPresent"
          name              = "memcached"

          port {
            container_port = 11211
            name           = "clients"
          }

          security_context {
            allow_privilege_escalation = false
            run_as_group               = 11211
            run_as_user                = 11211
          }
        }
      }
    }
  }
}

resource "kubernetes_service" "memcached" {
  metadata {
    name      = "memcached"
    namespace = var.flux_namespace
  }

  spec {
    selector = {
      name = "memcached"
    }

    port {
      name = "memcached"
      port = 11211
    }

  }
}
