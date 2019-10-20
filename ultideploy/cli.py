#!/usr/bin/env python3
import argparse
import sys

from ultideploy import cache, commands


def main():
    cache.init_cache()

    args = parse_args()
    args.func(args)


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
    bootstrap_parser.set_defaults(func=commands.bootstrap)

    deploy_parser = subparsers.add_parser(
        "deploy",
        help="Deploy the UltiManager infrastructure."
    )
    deploy_parser.add_argument(
        "-d",
        "--destroy",
        action='store_true',
        default=False,
        help="Destroy the resources that are currently deployed."
    )
    deploy_parser.add_argument(
        "organization_id",
        help=(
            "The ID of the main UltiManager organization in GCP. This can be "
            "discovered with 'gcloud organizations list'"
        ),
        metavar="organization-id"
    )
    deploy_parser.set_defaults(func=commands.deploy)

    return parser.parse_args()


def default_command(_):
    print("\nError: A subcommand is required.")
    sys.exit(1)


if __name__ == "__main__":
    main()
