import requests
from urllib.parse import urlparse
import logging

logger = logging.getLogger(__name__)




def validate_url(url):
    """
    Validates if a URL is accessible.

    Args:
        url (str): The URL to validate.

    Returns:
        bool: True if the URL is accessible, False otherwise.
    """
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()  
        return True
    except requests.exceptions.RequestException:
        logger.error(f"Error validating URL: {url}")
        return False


def validate_urls(urls):
    """
    Validates a list of URLs and returns the accessible ones.

    Args:
        urls (list): A list of URLs to validate.
    """
    return [url for url in urls if validate_url(url)]

