from typing import Any
import os

import httpx
from .common import DownstreamUnavailable


CATALOG_SERVICE_URL = os.getenv('CATALOG_SERVICE_URL', 'http://catalog-service:8001')


def get_product(product_id, authorization) -> dict[Any, Any] | None:
    """
    Checks a product with the given product_id exists.
    returns the data of the product if it exists else returns None.
    """
    try:
        response = httpx.get(
            f'{CATALOG_SERVICE_URL}/api/catalog/product/{product_id}/',
            headers={"Authorization": authorization},
            timeout=5.0
        )
    except httpx.RequestError as exc:
        raise DownstreamUnavailable("Catalog service is not available.") from exc

    if response.status_code == 404:
        return None

    if response.status_code != 200:
        raise DownstreamUnavailable("Unexpected error occurred while reaching catalog service.")

    try:
        data = response.json()
    except ValueError as exc:
        raise DownstreamUnavailable("Catalog service returned invalid JSON.")

    if not isinstance(data, dict):
        raise DownstreamUnavailable("Catalog service returned invalid data type.")

    return data
