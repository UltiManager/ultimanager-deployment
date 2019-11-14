data "terraform_remote_state" "db" {
  backend = "gcs"

  config = {
    bucket = "ultimanager-terraform-admin"
    prefix = "database"
  }
}

resource "kubernetes_secret" "db_creds" {
  metadata {
    name = "db-creds"
  }

  data = {
    host     = data.terraform_remote_state.db.outputs.db.private_ip_address
    password = data.terraform_remote_state.db.outputs.admin.password
    port     = 5432
    username = data.terraform_remote_state.db.outputs.admin.name
  }
}
