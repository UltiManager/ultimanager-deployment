import os
import pathlib
import subprocess
import tempfile

import yaml

from ultideploy import credentials, constants
from .base import BaseStep


class InstallIstio(BaseStep):
    """
    Step to install Istio in a cluster.
    """
    ISTIO_VERSION = '1.3.4'

    name = 'istio'

    def __init__(self):
        self._previous_gcloud_user = None

    def run(self, destroy=False, previous_step_results=None):
        """
        Either add or remove Istio from the cluster.

        Args:
            destroy:
                A boolean indicating if Istio should be removed instead
                of installed.
            previous_step_results:
                The results of the previous steps in the deployment
                process.
        """
        # A destroy is a no-op since we just let the cluster destruction
        # do the removal.
        if destroy:
            return True, None

        previous_step_results = previous_step_results or {}
        project_results = previous_step_results['project']
        cluster_results = previous_step_results['cluster']

        project_id = project_results['root_project_id']
        address = cluster_results['cluster_address_address']

        try:
            self._gcloud_login()

            with tempfile.TemporaryDirectory() as temp_dir:
                config = self._write_cluster_auth(
                    project_id, cluster_results, temp_dir
                )
                self._install_istio(config, address)
        finally:
            self._gcloud_logout()

        return True, None

    def _gcloud_login(self):
        current_user_result = subprocess.run(
            ['gcloud', 'config', 'get-value', 'account'],
            check=True,
            encoding='utf8',
            stdout=subprocess.PIPE,
        )
        user = current_user_result.stdout.strip()
        self._previous_gcloud_user = user if user != '(unset)' else None

        service_account = ''.join([
            constants.TERRAFORM_SERVICE_ACCOUNT_ID,
            '@',
            constants.TERRAFORM_ADMIN_PROJECT_ID,
            '.iam.gserviceaccount.com',
        ])
        credentials_path = credentials.google_service_account_credentials_path(
            constants.TERRAFORM_SERVICE_ACCOUNT_ID,
        )

        subprocess.run(
            [
                'gcloud',
                'auth',
                'activate-service-account',
                service_account,
                '--key-file',
                credentials_path,
            ],
            check=True,
        )

    def _gcloud_logout(self):
        service_account = ''.join([
            constants.TERRAFORM_SERVICE_ACCOUNT_ID,
            '@',
            constants.TERRAFORM_ADMIN_PROJECT_ID,
            '.iam.gserviceaccount.com',
        ])

        subprocess.run(
            [
                'gcloud',
                'auth',
                'revoke',
                service_account,
            ],
            check=True,
        )

        if self._previous_gcloud_user is not None:
            subprocess.run(
                [
                    'gcloud',
                    'config',
                    'set',
                    'account',
                    self._previous_gcloud_user,
                ],
                check=True,
            )

    def _write_cluster_auth(self, project, cluster_results, dest_dir):
        cluster_name = cluster_results['cluster_name']
        region = cluster_results['cluster_region']

        config_file = os.path.join(dest_dir, 'config')
        with open(config_file, 'w') as f:
            pass

        subprocess_env = os.environ.copy()
        subprocess_env['GOOGLE_APPLICATION_CREDENTIALS'] = credentials.google_service_account_credentials_path(
            constants.TERRAFORM_SERVICE_ACCOUNT_ID
        )
        subprocess_env['KUBECONFIG'] = config_file

        subprocess.run(
            [
                'gcloud',
                'container',
                'clusters',
                'get-credentials',
                cluster_name,
                '--region',
                region,
                '--project',
                project,
            ],
            check=True,
            env=subprocess_env,
        )

        return config_file

    def _install_istio(self, config, address):
        istio_root = self._get_istio_directory()

        subprocess_env = os.environ.copy()
        subprocess_env['GOOGLE_APPLICATION_CREDENTIALS'] = credentials.google_service_account_credentials_path(
            constants.TERRAFORM_SERVICE_ACCOUNT_ID
        )
        subprocess_env['KUBECONFIG'] = config

        namespace = {
            'apiVersion': 'v1',
            'kind': 'Namespace',
            'metadata': {
                'name': 'istio-system',
            },
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            namespace_manifest = os.path.join(temp_dir, 'namespace.yaml')
            with open(namespace_manifest, 'w') as f:
                yaml.safe_dump(namespace, f)

            subprocess.run(
                ['kubectl', 'apply', '-f', namespace_manifest],
                check=True,
                cwd=istio_root,
                env=subprocess_env,
            )

        subprocess.run(
            [
                'helm',
                'upgrade',
                '--install',
                '--namespace',
                'istio-system',
                'istio-init',
                istio_root / 'install' / 'kubernetes' / 'helm' / 'istio-init',
            ],
            check=True,
            cwd=istio_root,
            env=subprocess_env,
        )

        subprocess.run(
            [
                'helm',
                'upgrade',
                '--install',
                '--namespace',
                'istio-system',
                '-f',
                istio_root.parents[0] / 'values.yaml',
                '--set',
                f'gateways.istio-ingressgateway.loadBalancerIP={address}',
                'istio',
                istio_root / 'install' / 'kubernetes' / 'helm' / 'istio'
            ],
            check=True,
            cwd=istio_root,
            env=subprocess_env,
        )

        subprocess.run(
            [
                'kubectl',
                'label',
                'namespace',
                'default',
                'istio-injection=enabled',
            ],
            check=True,
            cwd=istio_root,
            env=subprocess_env,
        )

        subprocess.run(
            ['kubectl', 'apply', '-f', istio_root.parents[0] / 'gateway.yaml'],
            check=True,
            cwd=istio_root,
            env=subprocess_env,
        )

    def _get_istio_directory(self):
        project_root = pathlib.Path(__file__).parents[2]
        istio_root = project_root / 'istio' / f'istio-{self.ISTIO_VERSION}'

        return istio_root