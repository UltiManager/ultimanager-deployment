#!/usr/bin/env python3
import argparse
import base64
import os
import subprocess
import sys
import time
from pprint import pprint

import googleapiclient.discovery
import googleapiclient.errors
from oauth2client.client import GoogleCredentials


BASE_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CREDENTIALS_CACHE = os.path.join(BASE_PATH, ".credentials")
CREDENTIALS_TERRAFORM = os.path.join(CREDENTIALS_CACHE, "terraform.json")


TERRAFORM_ADMIN_PROJECT_ID = "ultimanager-terraform-admin"
TERRAFORM_ADMIN_PROJECT_NAME = "UltiManager Terraform Admin"

TERRAFORM_ADMIN_PROJECT_SERVICES = [
    "cloudbilling",
    "cloudresourcemanager",
    "iam",
    "serviceusage",
    "storage-api",
]

TERRAFORM_SERVICE_ACCOUNT_ID = 'terraform'
TERRAFORM_SERVICE_ACCOUNT_NAME = 'Terraform'

TERRAFORM_BUCKET_NAME = TERRAFORM_ADMIN_PROJECT_ID

TERRAFORM_CLUSTER_DIR = os.path.join(BASE_PATH, 'terraform', 'cluster')


def main():
    parse_args()


def parse_args():
    parser = argparse.ArgumentParser()
    parser.set_defaults(func=default_command)

    subparsers = parser.add_subparsers()

    bootstrap_parser = subparsers.add_parser(
        "bootstrap",
        description=(
            "Perform the initial setup required to use Terraform with GCP. "
            "Before running this ensure you have authenticated with \"gcloud "
            "auth login\"."
        ),
        help="Bootstrap GCP for Terraform usage.",
    )
    bootstrap_parser.add_argument(
        "organization_id",
        help=(
            "The ID of the main UltiManager organization in GCP. This can be "
            "discovered with 'gcloud organizations list'"
        ),
        metavar="organization-id"
    )
    bootstrap_parser.set_defaults(func=bootstrap)

    deploy_parser = subparsers.add_parser(
        "deploy",
        help="Deploy the UltiManager infrastructure."
    )
    deploy_parser.add_argument(
        "organization_id",
        help=(
            "The ID of the main UltiManager organization in GCP. This can be "
            "discovered with 'gcloud organizations list'"
        ),
        metavar="organization-id"
    )
    deploy_parser.set_defaults(func=deploy)

    args = parser.parse_args()
    args.func(args)


def default_command(_):
    print("\nError: A subcommand is required.")
    sys.exit(1)


def bootstrap(args):
    credentials = GoogleCredentials.get_application_default()

    organization = get_organization(
        f"organizations/{args.organization_id}", credentials
    )

    projects_service = googleapiclient.discovery.build(
        'cloudresourcemanager',
        'v1',
        credentials=credentials
    )

    print(f"Looking for existing '{TERRAFORM_ADMIN_PROJECT_ID}' project...")
    request = projects_service.projects().list(
        filter=f"id:{TERRAFORM_ADMIN_PROJECT_ID}"
    )
    response = request.execute()
    projects = response.get("projects", [])

    if len(projects) == 0:
        print(f"The '{TERRAFORM_ADMIN_PROJECT_ID}' project does not exist.\n")
        project = create_terraform_admin_project(
            projects_service, args.organization_id
        )
    elif len(projects) == 1:
        print(f"The '{TERRAFORM_ADMIN_PROJECT_ID}' project already exists.\n")
        project = projects[0]
    else:
        print(
            f"Received {len(projects)} projects matching the query when 0 or "
            f"1 were expected."
        )
        sys.exit(1)

    print(f"Project Number: {project['projectNumber']}\n")

    billing_account = get_billing_account(credentials)
    set_project_billing_account(
        project.get('projectId'), billing_account.get('name'), credentials
    )

    enable_admin_services(project['projectNumber'], credentials)

    service_account = create_service_account(credentials)
    bootstrap_credentials(service_account.get('name'), credentials)

    bootstrap_organization_privileges(
        organization.get('name'),
        service_account.get('email'),
        credentials
    )
    bootstrap_admin_project_privileges(
        project.get('projectId'),
        service_account.get('email'),
        credentials
    )

    bootstrap_storage_bucket(
        project.get('projectId'), TERRAFORM_BUCKET_NAME, credentials
    )


def get_organization(organization_name, credentials):
    """
    Get an organization by name.

    Args:
        organization_name:
            The name of the organization to retrieve.
        credentials:
            The credentials authorizing the operation.

    Returns:
        An object containing information about the organization.
    """
    print(f"Retrieving organization info for '{organization_name}'...")
    service = googleapiclient.discovery.build(
        "cloudresourcemanager", "v1", credentials=credentials
    )

    request = service.organizations().get(name=organization_name)
    response = request.execute()

    print("Done.\n")

    return response


def create_terraform_admin_project(service, organization_id):
    """
    Create the Terraform admin project.

    Args
        service:
            The cloud resource manager client to use when creating the
            project.
    """
    project_body = {
        "name": TERRAFORM_ADMIN_PROJECT_NAME,
        "parent": {
            "type": "organization",
            "id": organization_id
        },
        "projectId": TERRAFORM_ADMIN_PROJECT_ID
    }

    print(f"Creating '{TERRAFORM_ADMIN_PROJECT_ID}' project...")
    request = service.projects().create(body=project_body)
    response = request.execute()
    project = wait_for_operation('cloudresourcemanager', response.get('name'))
    print("Successfully created project.\n")

    return project


def get_billing_account(credentials):
    """
    Get the billing account to use for the admin project.

    Args:
        credentials:
            The credentials used to authenticate the call.

    Returns:
        The billing account to use.
    """
    service = googleapiclient.discovery.build(
        "cloudbilling", "v1", credentials=credentials
    )
    print("Retrieving billing account for admin project...")
    request = service.billingAccounts().list()
    response = request.execute()

    if len(response.get("billingAccounts", [])) != 1:
        raise RuntimeError(
            f"Expected to find 1 billing account, but found "
            f"{len(response.get('billingAccounts'))} accounts instead:\n\n"
            f"{response.get('billingAccounts')}"
        )

    account = response.get('billingAccounts')[0]
    print(
        f"Found billing account: {account.get('name')} "
        f"({account.get('displayName')})\n"
    )

    return account


def set_project_billing_account(project_id, billing_account_name, credentials):
    service = googleapiclient.discovery.build(
        "cloudbilling", "v1", credentials=credentials
    )

    print(
        f"Assigning billing account '{billing_account_name}' to project"
        f" '{project_id}'"
    )
    billing_account_info = {"billingAccountName": billing_account_name}
    request = service.projects().updateBillingInfo(
        body=billing_account_info, name=f"projects/{project_id}"
    )
    response = request.execute()
    print("Billing account assignment successful.\n")

    return response


def enable_admin_services(project_number, credentials):
    """
    Enable the required services for the admin project.

    Args:
        project_number:
            The numeric identifier of the admin project.
        credentials:
            The credentials to use to authenticate the operation.

    Returns:
        The result of the operation.
    """
    service = googleapiclient.discovery.build(
        "serviceusage", "v1", credentials=credentials
    )

    print(f"Enabling services for '{TERRAFORM_ADMIN_PROJECT_ID}':")
    for s in TERRAFORM_ADMIN_PROJECT_SERVICES:
        print(f"  - {s}.googleapis.com")

    request = service.services().batchEnable(
        body={
            'serviceIds': [
                f'{s}.googleapis.com' for s in TERRAFORM_ADMIN_PROJECT_SERVICES
            ]
        },
        parent=f"projects/{project_number}"
    )
    response = request.execute()
    results = wait_for_operation("serviceusage", response['name'])

    print("Services enabled.\n")

    for result in results.get('services'):
        if result.get('state') != 'ENABLED':
            print(f"Error enabling '{result.get('name')}':")
            pprint(result)
            sys.exit(1)


def create_service_account(credentials):
    """
    Create the ``terraform`` service account if it does not already
    exist.

    Args:
        credentials:
            The credentials to use to create the account.

    Returns:
        The service account's information.
    """
    print(
        f"Searching for existing '{TERRAFORM_SERVICE_ACCOUNT_ID}' service "
        f"account..."
    )

    service = googleapiclient.discovery.build(
        "iam", "v1", credentials=credentials
    )
    project = f"projects/{TERRAFORM_ADMIN_PROJECT_ID}"
    email = f"{TERRAFORM_SERVICE_ACCOUNT_ID}@{TERRAFORM_ADMIN_PROJECT_ID}.iam.gserviceaccount.com"

    request = service.projects().serviceAccounts().list(name=project)
    while request is not None:
        response = request.execute()

        for account in response.get('accounts', []):
            if account.get("email") == email:
                print(
                    f"Found existing '{TERRAFORM_SERVICE_ACCOUNT_ID}' account."
                    f"\n"
                )
                return account

        request = service.projects().serviceAccounts().list_next(
            previous_request=request, previous_response=response
        )

    print(f"Could not find existing account. Creating a new one...")

    request_body = {
        "accountId": TERRAFORM_SERVICE_ACCOUNT_ID,
        "serviceAccount": {
            "displayName": TERRAFORM_SERVICE_ACCOUNT_NAME,
        },
    }
    request = service.projects().serviceAccounts().create(
        body=request_body,
        name=project
    )
    response = request.execute()

    print(
        f"Successfully created the '{TERRAFORM_SERVICE_ACCOUNT_ID}' service "
        f"account.\n"
    )

    return response


def bootstrap_credentials(service_account_name, credentials):
    """
    Ensure that there are local credentials for the provided service
    account. If the credentials don't exist, create a new key for the
    service account and store the credentials.

    Args:
        service_account_name:
            The name of the service account to bootstrap credentials
            for.
        credentials:
            The credentials authorizing the creation of a new key for
            the service account.
    """
    print("Checking for cached credentials...")
    if os.path.isfile(CREDENTIALS_TERRAFORM):
        print(f"Credentials found in: {CREDENTIALS_TERRAFORM}\n")
        return

    if not os.path.isdir(os.path.dirname(CREDENTIALS_TERRAFORM)):
        os.makedirs(os.path.dirname(CREDENTIALS_TERRAFORM))
        print("Created credentials cache directory.")

    print("No credentials found. Creating a new key...")

    service = googleapiclient.discovery.build(
        "iam", "v1", credentials=credentials
    )

    request_body = {
        "keyAlgorithm": "KEY_ALG_RSA_2048",
        "privateKeyType": "TYPE_GOOGLE_CREDENTIALS_FILE"
    }
    request = service.projects().serviceAccounts().keys().create(
        body=request_body, name=service_account_name
    )
    response = request.execute()

    key_data = response.get('privateKeyData')
    decoded = base64.b64decode(key_data.encode())

    with open(CREDENTIALS_TERRAFORM, 'wb') as f:
        f.write(decoded)

    print(f"Stored new credentials in: {CREDENTIALS_TERRAFORM}\n")


def bootstrap_organization_privileges(
        organization_id, service_account_email, credentials
):
    """
    Bootstrap the IAM policy required to grant Terraform access to the
    organization resources it needs.

    Args:
        organization_id:
            The ID of the organization Terraform resources are created
            in.
        service_account_email:
            The email identifying the Terraform service account.
        credentials:
            The credentials authorizing the modification of the IAM
            policy.
    """
    print("Getting current IAM policy for organization...")
    service = googleapiclient.discovery.build(
        "cloudresourcemanager", "v1", credentials=credentials
    )

    request = service.organizations().getIamPolicy(
        body={}, resource=organization_id
    )
    policy = request.execute()

    print("Fetched current IAM policy. Comparing to desired state...")

    bindings = policy.get('bindings', [])
    service_account = f"serviceAccount:{service_account_email}"

    is_modified = False
    found_billing_policy = False
    found_project_policy = False
    for binding in bindings:
        if binding.get('role') == 'roles/billing.user':
            found_billing_policy = True

            if service_account not in binding['members']:
                is_modified = True
                binding['members'].append(service_account)
                print(f"Adding '{service_account}' to 'roles/billing.user'")

        elif binding['role'] == 'roles/resourcemanager.projectCreator':
            found_project_policy = True

            if service_account not in binding['members']:
                is_modified = True
                binding['members'].append(service_account)
                print(
                    f"Adding '{service_account}' to "
                    f"'roles/resourceManager.projectCreator'"
                )

    if not found_billing_policy:
        is_modified = True
        bindings.append({
            "members": [service_account],
            "role": "roles/billing.user"
        })
        print("Adding new 'roles/billing.user' binding")

    if not found_project_policy:
        is_modified = True
        bindings.append({
            "members": [service_account],
            "role": "roles/resourcemanager.projectCreator",
        })
        print("Adding new 'roles/resourcemanager.projectCreator' binding")

    if is_modified:
        print("Changes need to be applied...")

        request = service.organizations().setIamPolicy(
            body={"policy": {"bindings": bindings}},
            resource=organization_id
        )
        request.execute()
        print("Set IAM policy changes.\n")
    else:
        print("No IAM policy changes needed.\n")


def bootstrap_admin_project_privileges(
        project_id, service_account_email, credentials
):
    """
    Bootstrap the IAM policy required to grant Terraform access to the
    admin project resources it needs.

    Args:
        project_id:
            The ID of the Terraform admin project..
        service_account_email:
            The email identifying the Terraform service account.
        credentials:
            The credentials authorizing the modification of the IAM
            policy.
    """
    print("Getting current IAM policy for project...")
    service = googleapiclient.discovery.build(
        "cloudresourcemanager", "v1", credentials=credentials
    )

    request = service.projects().getIamPolicy(
        body={}, resource=project_id
    )
    policy = request.execute()

    print("Fetched current IAM policy. Comparing to desired state...")

    bindings = policy.get('bindings', [])
    service_account = f"serviceAccount:{service_account_email}"

    is_modified = False
    found_storage_policy = False
    found_viewer_policy = False
    for binding in bindings:
        if binding.get('role') == 'roles/storage.admin':
            found_storage_policy = True

            if service_account not in binding['members']:
                is_modified = True
                binding['members'].append(service_account)
                print(f"Adding '{service_account}' to 'roles/storage.admin'")

        elif binding['role'] == 'roles/viewer':
            found_viewer_policy = True

            if service_account not in binding['members']:
                is_modified = True
                binding['members'].append(service_account)
                print(f"Adding '{service_account}' to 'roles/viewer'")

    if not found_storage_policy:
        is_modified = True
        bindings.append({
            "members": [service_account],
            "role": "roles/storage.admin"
        })
        print("Adding new 'roles/storage.admin' binding")

    if not found_viewer_policy:
        is_modified = True
        bindings.append({
            "members": [service_account],
            "role": "roles/viewer",
        })
        print("Adding new 'roles/viewer' binding")

    if is_modified:
        print("Changes need to be applied...")

        request = service.projects().setIamPolicy(
            body={"policy": {"bindings": bindings}},
            resource=project_id
        )
        request.execute()
        print("Set IAM policy changes.\n")
    else:
        print("No IAM policy changes needed.\n")


def bootstrap_storage_bucket(project_id, bucket_name, credentials):
    """
    Bootstrap the bucket used to store Terraform state for projects.

    Args:
        project_id:
            The ID of the project to create the bucket in.
        bucket_name:
            The name of the bucket to create.
        credentials:
            The credentials authorizing the creation of the bucket.

    Returns:
        An object containing information about the bucket.
    """
    print(f"Attempting to retrieve existing bucket: {bucket_name}'")

    service = googleapiclient.discovery.build(
        "storage", "v1", credentials=credentials
    )
    request = service.buckets().get(bucket=bucket_name)

    try:
        bucket = request.execute()
        print("Bucket exists.\n")
        return bucket
    except googleapiclient.errors.HttpError as e:
        if e.resp['status'] != '404':
            raise

    print("Bucket does not exist yet. Creating it...")

    bucket_body = {
        "name": bucket_name,
        "versioning": {
            "enabled": True,
        },
    }

    request = service.buckets().insert(
        body=bucket_body,
        predefinedAcl="projectPrivate",
        predefinedDefaultObjectAcl="projectPrivate",
        project=project_id
    )
    bucket = request.execute()
    print("Done.\n")

    return bucket


def wait_for_operation(service_type, operation_ref):
    POLL_SECONDS = 5
    SPINNER_SPEED = .25

    spinners = ['|', '/', '-', '\\']
    spinner_index = 0

    service = googleapiclient.discovery.build(
        service_type,
        'v1',
        credentials=GoogleCredentials.get_application_default()
    )

    status_request = service.operations().get(name=operation_ref)
    status = status_request.execute()

    print()
    while not status.get('done', False):
        for _ in range(int(POLL_SECONDS / SPINNER_SPEED)):
            print(f"\rWaiting for operation... {spinners[spinner_index]}", end="")
            spinner_index = (spinner_index + 1) % len(spinners)
            time.sleep(SPINNER_SPEED)

        status_request = service.operations().get(name=operation_ref)
        status = status_request.execute()
    print("\rWaiting for operation... Done.\n")

    if isinstance(status, str) or status.get('error'):
        raise RuntimeError(status)

    return status.get('response', {})


def deploy(args):
    """
    Deploy the infrastructure.

    Args:
        args:
            The parsed CLI arguments.
    """
    subprocess_env = os.environ.copy()
    subprocess_env['GOOGLE_APPLICATION_CREDENTIALS'] = CREDENTIALS_TERRAFORM
    subprocess_env['TF_VAR_organization_id'] = args.organization_id

    subprocess.run(
        ['terraform', 'init'],
        check=True,
        cwd=TERRAFORM_CLUSTER_DIR,
        env=subprocess_env,
    )

    subprocess.run(
        ['terraform', 'plan', '-out', 'tfplan'],
        check=True,
        cwd=TERRAFORM_CLUSTER_DIR,
        env=subprocess_env,
    )

    if not prompt_yes_no("Would you like to apply the above plan"):
        print("Not applying plan. Exiting.\n")
        sys.exit(0)

    subprocess.run(
        ['terraform', 'apply', 'tfplan'],
        check=True,
        cwd=TERRAFORM_CLUSTER_DIR,
        env=subprocess_env,
    )


def prompt_yes_no(question, default=False):
    if default:
        options = "[Y]/n"
    else:
        options = "y/[N]"

    prompt = f"{question} ({options}): "

    while True:
        answer = input(prompt)

        if not answer:
            return default

        if answer.lower().startswith('y'):
            return True
        elif answer.lower().startswith('n'):
            return False

        print("Please answer with 'y' or 'n'.")


if __name__ == "__main__":
    main()
