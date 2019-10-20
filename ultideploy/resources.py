import googleapiclient.discovery


def get_billing_account(google_credentials):
    """
    Get the billing account to use for the admin project.

    Args:
        google_credentials:
            The credentials used to authenticate the call.

    Returns:
        The billing account to use.
    """
    service = googleapiclient.discovery.build(
        "cloudbilling", "v1", credentials=google_credentials
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


def get_or_create_service_account(
        project_id,
        account_id,
        account_name,
        google_credentials
):
    """
    Get a service account or create it if it does not exist.
    
    Args:
        project_id:
            The ID of the project the service account is contained in.
        account_id:
            The ID of the service account to get. 
        account_name:
            The display name of the service account.
        google_credentials:
            The Google credentials authorizing the operation.

    Returns:
        The existing or newly created service account.
    """
    print(f"Searching for existing '{account_id}' service account...")

    service = googleapiclient.discovery.build(
        "iam", "v1", credentials=google_credentials
    )
    project = f"projects/{project_id}"
    email = f"{account_id}@{project_id}.iam.gserviceaccount.com"

    request = service.projects().serviceAccounts().list(name=project)
    while request is not None:
        response = request.execute()

        for account in response.get('accounts', []):
            if account.get("email") == email:
                print(
                    f"Found existing '{account_id}' account."
                    f"\n"
                )
                return account

        request = service.projects().serviceAccounts().list_next(
            previous_request=request, previous_response=response
        )

    print(f"Could not find existing account. Creating a new one...")

    request_body = {
        "accountId": account_id,
        "serviceAccount": {
            "displayName": account_name,
        },
    }
    request = service.projects().serviceAccounts().create(
        body=request_body,
        name=project
    )
    response = request.execute()

    print(
        f"Successfully created the '{account_id}' service account.\n"
    )

    return response
