import os
import httpx

from .common import DownstreamUnavailable, InventoryReservationRejected


INVENTORY_SERVICE_URL = os.getenv('INVENTORY_SERVICE_URL', 'http://inventory-service:8003')


def reserve_stock(reservation_id, product_id, quantity, authorization):
    url = f'{INVENTORY_SERVICE_URL}/api/inventory/reservations/'
    payload = {'reservation_id': reservation_id, 'product_id': product_id, 'quantity': quantity}
    headers = {'Authorization': authorization}

    try:
        response = httpx.post(url, json=payload, headers=headers)
    except httpx.RequestError as exc:
        raise DownstreamUnavailable("Inventory service is not available.")

    if response.status_code in (200, 201):
        return response.json()

    if response.status_code in (404, 409):
        raise InventoryReservationRejected("Inventory service rejected the reservation")

    raise DownstreamUnavailable("Could not reserve the stock.")


def release_stock(reservation_id, authorization):
    url = f'{INVENTORY_SERVICE_URL}/api/inventory/reservations/{reservation_id}/release/'
    headers = {'Authorization': authorization}

    try:
        response = httpx.post(url, headers=headers)
    except httpx.RequestError as exc:
        raise DownstreamUnavailable("Inventory service is not available.") from exc

    # return the same thing for 404 bc there is no actual inventory item to be released
    if response.status_code in (200, 404):
        return

    raise DownstreamUnavailable("Could not release an inventory reservation.")
