import sys

import googleapiclient.discovery

from ultideploy import constants, credentials, resources


def bootstrap(args):
    google_credentials = credentials.default_google_credentials()

    organization = resources.get_organization(
        f"organizations/{args.organization_id}", google_credentials
    )

    projects_service = googleapiclient.discovery.build(
        'cloudresourcemanager',
        'v1',
        credentials=google_credentials
    )

    print(f"Looking for existing '{constants.TERRAFORM_ADMIN_PROJECT_ID}' project...")
    request = projects_service.projects().list(
        filter=f"id:{constants.TERRAFORM_ADMIN_PROJECT_ID}"
    )
    response = request.execute()
    projects = response.get("projects", [])

    if len(projects) == 0:
        print(f"The '{constants.TERRAFORM_ADMIN_PROJECT_ID}' project does not exist.\n")
        project = resources.create_terraform_admin_project(
            projects_service, args.organization_id
        )
    elif len(projects) == 1:
        print(f"The '{constants.TERRAFORM_ADMIN_PROJECT_ID}' project already exists.\n")
        project = projects[0]
    else:
        print(
            f"Received {len(projects)} projects matching the query when 0 or "
            f"1 were expected."
        )
        sys.exit(1)

    print(f"Project Number: {project['projectNumber']}\n")

    billing_account = resources.get_billing_account(google_credentials)
    resources.set_project_billing_account(
        project.get('projectId'), billing_account.get('name'), google_credentials
    )

    resources.enable_admin_services(project['projectNumber'], google_credentials)

    service_account = resources.get_or_create_service_account(
        constants.TERRAFORM_ADMIN_PROJECT_ID,
        constants.TERRAFORM_SERVICE_ACCOUNT_ID,
        constants.TERRAFORM_SERVICE_ACCOUNT_NAME,
        google_credentials
    )
    resources.bootstrap_credentials(service_account.get('name'), google_credentials)

    resources.bootstrap_organization_privileges(
        organization.get('name'),
        service_account.get('email'),
        google_credentials
    )
    resources.bootstrap_admin_project_privileges(
        project.get('projectId'),
        service_account.get('email'),
        google_credentials
    )

    resources.bootstrap_storage_bucket(
        project.get('projectId'), constants.TERRAFORM_BUCKET_NAME, google_credentials
    )
