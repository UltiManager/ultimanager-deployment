# UltiManager Deployment

The tools and infrastructure configurations used to deploy the UltiManager
application to the internet.

## Prerequisites

* You must have Python 3 installed.
* You must have Terraform version 0.12 or higher installed.

## Usage

We use a Python script to wrap our usage of Terraform. The python script handles
bootstrapping the environment with the resources that Terraform requires. To get
started, install the CLI tool:

```
pip install -e .
```

*__Note:__ Providing the `-e` flag ensures that any upstream changes to the
deployment tool will be applied as soon as they are pulled and without requiring
a reinstall.*

This will install a command line tool that is used to manage the UltiManager
deployment.

### Bootstrapping

Before the project infrastructure can be provisioned with Terraform, there are a
few resources that must be created so Terraform gets the authorization to create
resources and store state. Roughly, the bootstrapping process does the
following:

1. Ensure the Terraform admin project exists. This is the project that contains
   the resources Terraform needs to operate.
2. Create a service account for Terraform to use. This account has permission to
   access the Terraform admin project and to create new projects.
3. Create a Google Cloud Storage bucket to store Terraform state in.

To run the bootstrapping process, first obtain the ID of the GCP organization
resources will be created under:

```bash
gcloud organizations list
```

Next, run the deployment tool:

```bash
ultideploy bootstrap <GCP Organization ID>
```

#### Bootstrap Usage

```
usage: ultideploy bootstrap [-h] organization-id

Perform the initial setup required to use Terraform with GCP. Before running
this ensure you have authenticated with "gcloud auth login".

positional arguments:
  organization-id  The ID of the main UltiManager organization in GCP. This
                   can be discovered with 'gcloud organizations list'

optional arguments:
  -h, --help       show this help message and exit
```

### Deployment

To actually deploy the UltiManager infrastructure, use the `deploy` subcommand
of the deployment tool:

```bash
ultideploy deploy <GCP Organization ID>
```

#### Deploy Usage

```
usage: ultideploy deploy [-h] [-d] organization-id

positional arguments:
  organization-id  The ID of the main UltiManager organization in GCP. This
                   can be discovered with 'gcloud organizations list'

optional arguments:
  -h, --help       show this help message and exit
  -d, --destroy    Destroy the resources that are currently deployed.
```

## Service Registration

Services deployed to the `default` namespace of the provisioned cluster have
access to Istio. This makes routing a service easy and defers all routing logic
to the service itself. Services have access to two different gateways:

* `api-ingress.istio-system.svc.cluster.local` which handles traffic on the
  hostname `api.$ROOT_DOMAIN`, and
* `default-ingress.istio-system.svc.cluster.local` which handles traffic on
  `$ROOT_DOMAIN`.
  
Services also have access to the `domains-config` Config Map in the `default`
namespace. It contains the domain names mapped to the above ingresses:

| Key               | Value                                          |
| ----------------- | ---------------------------------------------- |
| __`API_DOMAIN`__  | The domain that the API is made accessible at. |
| __`ROOT_DOMAIN`__ | The domain for the default ingress.            |

## License

This project is licensed under the [MIT License](LICENSE).
