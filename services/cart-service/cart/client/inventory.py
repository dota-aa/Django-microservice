import os
import httpx


INVENTORY_SERVICE_URL = os.getenv("INVENTORY_SERVICE_URL", 'http://inventory-service:8003')


class InventoryServiceError(Exception):
    """Raised when inventory service cannot be reached or returns invalid data"""
    pass


def get_inventory_item(product_id, authorization=None) -> dict | None:
    url = f'{INVENTORY_SERVICE_URL}/api/inventory/items/{product_id}/'
    header = {}

    if authorization:
        header['Authorization'] = authorization

    try:
        response = httpx.get(url, headers=header)
    except httpx.RequestError:
        raise InventoryServiceError("Inventory service is unreachable.")

    print(response.status_code)

    if response.status_code == 404:
        return None

    if response.status_code != 200:
        raise InventoryServiceError("Inventory service returned Unexpected Error.")

    try:
        data = response.json()
    except ValueError:
        raise InventoryServiceError("Inventory service returned Invalid JSON")

    quantity = data.get('quantity') if isinstance(data, dict) else None

    if type(quantity) is not int or quantity < 0:
        raise InventoryServiceError("Inventory service returned invalid data")

    return data
