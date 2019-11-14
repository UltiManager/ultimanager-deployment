TERRAFORM_ADMIN_PROJECT_ID = 'ultimanager-terraform-admin'
TERRAFORM_ADMIN_PROJECT_NAME = 'UltiManager Terraform Admin'
TERRAFORM_ADMIN_PROJECT_SERVICES = [
    "cloudbilling",
    "cloudbuild",
    "cloudresourcemanager",
    "container",
    "iam",
    "servicenetworking",
    "serviceusage",
    "sqladmin",
    "storage-api",
]

TERRAFORM_SERVICE_ACCOUNT_ID = 'terraform'
TERRAFORM_SERVICE_ACCOUNT_NAME = 'Terraform'

TERRAFORM_BUCKET_NAME = TERRAFORM_ADMIN_PROJECT_ID

# TODO: Make DNS settings configurable
DNS_PROJECT_ID = 'ultimanager-dns'
ROOT_DOMAIN = 'ultimanager.com'

LETSENCRYPT_EMAIL = 'admin@ultimanager.com'
