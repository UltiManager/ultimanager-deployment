import os
import pathlib
import sys

from ultideploy import constants, credentials, resources
from ultideploy.steps import InstallIstio, LinkGithub, TerraformStep


PROJECT_ROOT = pathlib.Path(__file__).parents[2]

TERRAFORM_CLUSTER_CONFIG = PROJECT_ROOT / 'terraform' / 'cluster'
TERRAFORM_DATABASE_CONFIG = PROJECT_ROOT / 'terraform' / 'database'
TERRAFORM_K8S_CONFIG = PROJECT_ROOT / 'terraform' / 'k8s'
TERRAFORM_NETWORK_CONFIG = PROJECT_ROOT / 'terraform' / 'network'
TERRAFORM_PROJECT_CONFIG = PROJECT_ROOT / 'terraform' / 'project'


def deploy(args):
    """
    Deploy the infrastructure.

    Args:
        args:
            The parsed CLI arguments.
    """
    google_creds = credentials.google_service_account_credentials(
        constants.TERRAFORM_SERVICE_ACCOUNT_ID
    )
    billing_account = resources.get_billing_account(google_creds)

    subprocess_env = os.environ.copy()
    subprocess_env['GOOGLE_APPLICATION_CREDENTIALS'] = credentials.google_service_account_credentials_path(
        constants.TERRAFORM_SERVICE_ACCOUNT_ID
    )
    subprocess_env['TF_VAR_billing_account'] = billing_account.get('name')
    subprocess_env['TF_VAR_dns_project_id'] = constants.DNS_PROJECT_ID
    subprocess_env['TF_VAR_organization_id'] = args.organization_id
    subprocess_env['TF_VAR_root_domain'] = constants.ROOT_DOMAIN

    steps = [
        TerraformStep(
            "project",
            TERRAFORM_PROJECT_CONFIG,
            env=subprocess_env,
            outputs=["root_project.id"],
        ),
        LinkGithub(),
        TerraformStep(
            "network",
            TERRAFORM_NETWORK_CONFIG,
            env=subprocess_env,
        ),
        TerraformStep(
            "database",
            TERRAFORM_DATABASE_CONFIG,
            env=subprocess_env,
        ),
        TerraformStep(
            "cluster",
            TERRAFORM_CLUSTER_CONFIG,
            env=subprocess_env,
            outputs=[
                "api_domain",
                "cluster_address.address",
                "cluster_auth_ca_certificate",
                "cluster_auth_certificate",
                "cluster_auth_key",
                "cluster_host",
                "cluster_name",
                "cluster_region",
                "root_domain",
            ]
        ),
        InstallIstio(),
        TerraformStep("k8s", TERRAFORM_K8S_CONFIG, subprocess_env),
    ]

    if args.destroy:
        steps.reverse()

    step_results = {}
    for step in steps:
        step.pre_run()
        should_continue, results = step.run(
            args.destroy, previous_step_results=step_results
        )

        if not should_continue:
            print(f"\n\nStep '{step.name}' stopped execution. Exiting.")
            sys.exit(0)

        step_results[step.name] = results or {}
