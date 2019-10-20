from pathlib import Path


CACHE_DIRECTORY = Path.home() / '.ultideploy'

CREDENTIALS_CACHE = CACHE_DIRECTORY / 'credentials'


def init_cache():
    """
    Ensure the cache directory exists.
    """
    CACHE_DIRECTORY.mkdir(exist_ok=True, parents=True)


def get_cache_location(item_type, item_name):
    """
    Get the path to a cache item.

    Args:
        item_type:
            The category of the cached item.
        item_name:
            The name of the cached item.

    Returns:
        The full path to the item.
    """
    return CACHE_DIRECTORY / item_type / item_name
