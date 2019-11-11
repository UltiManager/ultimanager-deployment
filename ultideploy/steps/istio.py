import json
import os
import pathlib
import subprocess
import tempfile

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
        api_domain = cluster_results['api_domain']
        root_domain = cluster_results['root_domain']

        try:
            self._gcloud_login()

            with tempfile.TemporaryDirectory() as temp_dir:
                config = self._write_cluster_auth(
                    project_id, cluster_results, temp_dir
                )
                self._install_istio(config, address, root_domain, api_domain)
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

    def _install_istio(self, config, address, root_domain, api_domain):
        istio_root = self._get_istio_directory()

        subprocess_env = os.environ.copy()
        subprocess_env['GOOGLE_APPLICATION_CREDENTIALS'] = credentials.google_service_account_credentials_path(
            constants.TERRAFORM_SERVICE_ACCOUNT_ID
        )
        subprocess_env['KUBECONFIG'] = config

        cert_namespace = {
            'apiVersion': 'v1',
            'kind': 'Namespace',
            'metadata': {
                'name': 'cert-manager',
            },
        }
        istio_namespace = {
            'apiVersion': 'v1',
            'kind': 'Namespace',
            'metadata': {
                'name': 'istio-system',
            },
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            cert_namespace_manifest = os.path.join(temp_dir, 'cert-namespace.json')
            with open(cert_namespace_manifest, 'w') as f:
                json.dump(cert_namespace, f)

            istio_namespace_manifest = os.path.join(temp_dir, 'istio-namespace.json')
            with open(istio_namespace_manifest, 'w') as f:
                json.dump(istio_namespace, f)

            subprocess.run(
                [
                    'kubectl',
                    'apply',
                    '-f',
                    cert_namespace_manifest,
                    '-f',
                    istio_namespace_manifest,
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
                'istio-init',
                istio_root / 'install' / 'kubernetes' / 'helm' / 'istio-init',
            ],
            check=True,
            cwd=istio_root,
            env=subprocess_env,
        )

        # TODO: Wait for CRDs to become available

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
                f'certmanager.email={constants.LETSENCRYPT_EMAIL}',
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
                '--overwrite',
                'istio-injection=enabled',
            ],
            check=True,
            cwd=istio_root,
            env=subprocess_env,
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            api_gateway_manifest = os.path.join(temp_dir, 'api-gateway.json')
            with open(api_gateway_manifest, 'w') as f:
                manifest = self.gateway_manifest('api-ingress', api_domain, cert_name='api-cert')
                json.dump(manifest, f)

            default_gateway_manifest = os.path.join(
                temp_dir, 'default-gateway.json'
            )
            with open(default_gateway_manifest, 'w') as f:
                manifest = self.gateway_manifest('default-ingress', root_domain, cert_name='root-cert')
                json.dump(manifest, f)

            api_certificate_manifest = os.path.join(temp_dir, 'api-certificate.json')
            with open(api_certificate_manifest, 'w') as f:
                manifest = self.certificate_manifest('api-cert', api_domain)
                json.dump(manifest, f)

            root_certificate_manifest = os.path.join(temp_dir, 'root-certificate.json')
            with open(root_certificate_manifest, 'w') as f:
                manifest = self.certificate_manifest('root-cert', root_domain)
                json.dump(manifest, f)

            https_redirect_shenanigans = os.path.join(temp_dir, 'redirect.json')
            with open(https_redirect_shenanigans, 'w') as f:
                f.write(self.https_redirect_config(api_domain, root_domain))

            subprocess.run(
                [
                    'kubectl',
                    'apply',
                    '-f',
                    default_gateway_manifest,
                    '-f',
                    api_gateway_manifest,
                    '-f',
                    root_certificate_manifest,
                    '-f',
                    api_certificate_manifest,
                    '-f',
                    https_redirect_shenanigans,
                ],
                check=True,
                cwd=istio_root,
                env=subprocess_env,
            )

    def _get_istio_directory(self):
        project_root = pathlib.Path(__file__).parents[2]
        istio_root = project_root / 'istio' / f'istio-{self.ISTIO_VERSION}'

        return istio_root

    @staticmethod
    def certificate_manifest(cert_name, primary_domain, *additional_domains):
        return {
            'apiVersion': 'certmanager.k8s.io/v1alpha1',
            'kind': 'Certificate',
            'metadata': {
                'name': cert_name,
                'namespace': 'istio-system',
            },
            'spec': {
                'secretName': cert_name,
                'issuerRef': {
                    'name': 'letsencrypt',
                    'kind': 'ClusterIssuer',
                },
                'commonName': primary_domain,
                'dnsNames': [primary_domain] + list(additional_domains),
                'acme': {
                    'config': [
                        {
                            'http01': {
                                'ingressClass': 'istio',
                            },
                            'domains': [primary_domain] + list(additional_domains),
                        },
                    ],
                },
            },
        }

    @staticmethod
    def gateway_manifest(gateway_name, *hosts, cert_name=None):
        """
        Create a manifest for a gateway.

        Args:
            gateway_name:
                The name of the gateway.
            *hosts:
                The host names that the gateway should accept.
            cert_name:
                The name of the TLS certificate to use.

        Returns:
            A dictionary representing the gateway. This can be converted
            to JSON and fed directly to ``kubectl``.
        """
        return {
            'apiVersion': 'networking.istio.io/v1alpha3',
            'kind': 'Gateway',
            'metadata': {
                'name': gateway_name,
                'namespace': 'istio-system',
            },
            'spec': {
                'selector': {
                    'app': 'istio-ingressgateway',
                },
                'servers': [
                    {
                        'hosts': hosts,
                        'port': {
                            'name': 'https',
                            'number': 443,
                            'protocol': 'HTTPS',
                        },
                        'tls': {
                            'credentialName': cert_name,
                            'mode': 'SIMPLE',
                            'privateKey': 'sds',
                            'serverCertificate': 'sds',
                        }
                    },
                ],
            },
        }

    @staticmethod
    def https_redirect_config(*redirected_hosts):
        manifests = [
            # NGINX config for the redirect
            {
                "apiVersion": "v1",
                "kind": "ConfigMap",
                "metadata": {
                    "name": "https-redirect-nginx-config",
                    "namespace": "istio-system",
                },
                "data": {
                    "nginx.conf": "\n".join([
                        "server {",
                        "  listen 80 default_server;",
                        "  server_name _;",
                        "  return 301 https://$host$request_uri;"
                        "}"
                    ])
                }
            },
            # Redirect service
            {
                "apiVersion": "v1",
                "kind": "Service",
                "metadata": {
                    "name": "https-redirect",
                    "namespace": "istio-system",
                    "labels": {
                        "app": "https-redirect",
                    },
                },
                "spec": {
                    "ports": [
                        {
                            "name": "http",
                            "port": 80,
                        },
                    ],
                    "selector": {
                        "app": "https-redirect",
                    },
                },
            },
            # NGINX deployment for HTTPS redirect
            {
                "apiVersion": "apps/v1",
                "kind": "Deployment",
                "metadata": {
                    "name": "https-redirect",
                    "namespace": "istio-system",
                },
                "spec": {
                    "replicas": 2,
                    "selector": {
                        "matchLabels": {
                            "app": "https-redirect",
                        },
                    },
                    "template": {
                        "metadata": {
                            "labels": {
                                "app": "https-redirect",
                            },
                        },
                        "spec": {
                            "containers": [
                                {
                                    "name": "https-redirect",
                                    "image": "nginx:stable",
                                    "imagePullPolicy": "IfNotPresent",
                                    "ports": [
                                        {
                                            "containerPort": 80,
                                            "name": "http",
                                        },
                                    ],
                                    "resources": {
                                        "requests": {
                                            "cpu": "100m",
                                        },
                                    },
                                    "volumeMounts": [
                                        {
                                            "mountPath": "/etc/nginx/conf.d",
                                            "name": "config",
                                        },
                                    ],
                                },
                            ],
                            "volumes": [
                                {
                                    "name": "config",
                                    "configMap": {
                                        "name": "https-redirect-nginx-config",
                                    },
                                },
                            ],
                        },
                    },
                },
            },
            # Virtual service determining which hosts get redirected
            {
                "apiVersion": "networking.istio.io/v1alpha3",
                "kind": "VirtualService",
                "metadata": {
                    "name": "https-redirect",
                    "namespace": "istio-system",
                },
                "spec": {
                    "hosts": redirected_hosts,
                    "gateways": ["istio-autogenerated-k8s-ingress"],
                    "http": [
                        {
                            "route": [
                                {
                                    "destination": {
                                        "host": "https-redirect",
                                        "port": {
                                            "number": 80,
                                        },
                                    },
                                },
                            ],
                        },
                    ],
                },
            },
        ]

        # If there are multiple JSON objects in a K8s manifest, they are placed
        # back-to-back with no separators (except a newline).
        return "\n".join([json.dumps(manifest) for manifest in manifests])
