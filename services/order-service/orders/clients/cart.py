from typing import Any
import os

import httpx

from .common import DownstreamUnavailable


CART_SERVICE_URL = os.getenv('CART_SERVICE_URL', 'http://cart-service:8002')


def get_cart(authorization) -> dict[Any, Any]:
    """
    Get user cart from cart service and validate the returned data.
    """
    try:
        response = httpx.get(f'{CART_SERVICE_URL}/api/cart/', headers={"Authorization": authorization}, timeout=5.0)
    except httpx.RequestError as exc:
        raise DownstreamUnavailable("Cart service is not available.") from exc

    if response.status_code != 200:
        raise DownstreamUnavailable("Could not retrieve the cart.")

    try:
        data = response.json()
    except ValueError:
        raise DownstreamUnavailable("Cart service returned invalid JSON.")

    if not isinstance(data, dict):
        raise DownstreamUnavailable("Cart service returned invalid data type")

    return data


def clear_cart(authorization) -> None:
    """
    Clear user's cart through cart service.
    """
    try:
        response = httpx.delete(f'{CART_SERVICE_URL}/api/cart/clear/', headers={"Authorization": authorization}, timeout=5.0)
    except httpx.RequestError as exc:
        raise DownstreamUnavailable("Cart service is not available.") from exc

    if response.status_code != 200:
        raise DownstreamUnavailable("Unexpected error occurred while trying to reach cart service.")
