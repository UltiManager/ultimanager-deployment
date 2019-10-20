from google.oauth2 import service_account
from oauth2client.client import GoogleCredentials

from ultideploy import cache


def default_google_credentials():
    return GoogleCredentials.get_application_default()


def google_service_account_credentials(service_account_name):
    file = google_service_account_credentials_path(service_account_name)

    return service_account.Credentials.from_service_account_file(file)


def google_service_account_credentials_path(service_account_name):
    return cache.get_cache_location(
        'credentials', f'{service_account_name}.json'
    )
