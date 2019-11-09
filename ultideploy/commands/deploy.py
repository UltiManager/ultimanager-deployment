import os
import pathlib
import subprocess
import sys

from ultideploy import constants, credentials, resources


PROJECT_ROOT = pathlib.Path(__file__).parents[2]

TERRAFORM_CLUSTER_CONFIG = PROJECT_ROOT / 'terraform' / 'cluster'
TERRAFORM_K8S_CONFIG = PROJECT_ROOT / 'terraform' / 'k8s'


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

    terraform_paths = [TERRAFORM_CLUSTER_CONFIG, TERRAFORM_K8S_CONFIG]
    if args.destroy:
        terraform_paths.reverse()

    for terraform_config in terraform_paths:
        subprocess.run(
            ['terraform', 'init'],
            check=True,
            cwd=terraform_config,
            env=subprocess_env,
        )

        plan_args = ['terraform', 'plan', '-out', 'tfplan']
        if args.destroy:
            plan_args.append('-destroy')

        subprocess.run(
            plan_args,
            check=True,
            cwd=terraform_config,
            env=subprocess_env,
        )

        # TODO: Check if plan does anything
        # terraform show -json tfplan | jq .resource_changes[].change.actions[]

        if not prompt_yes_no("Would you like to apply the above plan"):
            print("Not applying plan. Exiting.\n")
            sys.exit(0)

        subprocess.run(
            ['terraform', 'apply', 'tfplan'],
            check=True,
            cwd=terraform_config,
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
