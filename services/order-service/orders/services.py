import logging

from django.db import IntegrityError, transaction

from .clients.catalog import get_product
from .clients.cart import get_cart, clear_cart
from .clients.inventory import reserve_stock, release_stock
from .clients.common import DownstreamUnavailable, InventoryReservationRejected
from .models import Order, OrderItem


logger = logging.getLogger(__name__)


class CheckOutError(Exception):
    """Raised when any error occurs while processing checkout"""
    def __init__(self, detail, status_code):
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code


def _get_cart_lines(cart: dict) -> dict:
    """
    Generate a dictionary that contains product_id - quantity pair from cart.
    """
    items = cart.get('items')
    if not isinstance(items, list):
        raise CheckOutError("Cart Response has an invalid format.", 502)

    quantities = {}
    for item in items:
        if not isinstance(item, dict):
            raise CheckOutError("Cart item has an invalid format.", 400)

        try:
            product_id = int(item.get('product_id'))
            quantity = int(item.get('quantity'))
        except (TypeError, ValueError):
            raise CheckOutError("Cart contains invalid product or quantity data.", 400)

        quantities[product_id] = quantities.get(product_id, 0) + quantity

    if not quantities:
        raise CheckOutError("Cart cannot be empty.", 400)

    return quantities


def _prepare_order_items(quantities: dict, authorization: str) -> list:
    """
    Complete and validate cart data through `catalog` service.
    """
    prepared = []

    for product_id, quantity in sorted(quantities.items()):
        product = get_product(product_id, authorization)

        if product is None:
            raise CheckOutError(f"Product {product_id} does not exist.", 400)

        if not product.get('is_active'):
            raise CheckOutError(f"Product {product_id} is not active.", 400)

        price = product.get('price')
        if not price.is_finite() and price < 0:
            raise CheckOutError(f"Product {product_id} has an invalid price", 502)

        name = product.get('name')
        if not isinstance(name, str) or not name:
            raise CheckOutError(f"Product {product_id} has an invalid name.", 502)

        prepared.append({
            "product_id": product_id,
            "product_name": name,
            "unit_price": price,
            "quantity": quantity
        })
    return prepared



def _create_order(customer_id, idempotency_key, prepared):
    total = sum(item['unit_price'] * prepared['quantity'] for item in prepared)

    try:
        with transaction.atomic():
            order = Order.objects.create(
                customer_id=customer_id,
                idempotency_key=idempotency_key,
                status=Order.Status.PROCESSING,
                total_amount=total,
            )

            OrderItem.objects.bulk_create(
                [
                    OrderItem(
                        order=order,
                        product_id=item['product_id'],
                        product_name=item['product_name'],
                        unit_price=item['unit_price'],
                        quantity=item['quantity']
                    )
                    for item in prepared
                ]
            )
        return order, True # no need for prefetch related as we have all the instances in the memory

    except IntegrityError:
        # check if we have the same customer ID and idempotence key
        existing = Order.objects.prefetch_related('items').filter(
            customer_id=customer_id, idempotency_key=idempotency_key
        ).first()

        if existing is not None:
            return existing, False
        raise # it will raise the last error (integrity error)


def _compensate_reservation(order, authorization):
    """
    A simple compensation func to release stock in case checkout fails at any point.
    """
    compensation_failed = False

    for item in order.items.all():
        try:
            release_stock(reservation_id=item.reservation_id, authorization=authorization)
        except DownstreamUnavailable:
            compensation_failed = True
            logging.exception(f"Could not compensate reservation {item.reservation_id} for order {order.id}")

    return compensation_failed


def _mark_order_failed(order, authorization, reason):
    """
    Determines order status when it fails and run the compensation funcs(for now we only have one compensation func)
    """
    compensation_failed = _compensate_reservations(order, authorization)
    order.status = Order.Status.FAILED

    if compensation_failed:
        order.failure_reason = f"{reason} Compensation was incomplete; inventory reconciliation is required."
    else:
        order.failure_reason = reason

    order.save(update_fields=["status", "failure_reason", "updated"])


def checkout(customer_id, authorization, idempotency_key):
    """
    Controller for saga transaction
    """
    existing = (Order.objects.filter(customer_id=customer_id, idempotency_key=idempotency_key)
                .prefetch_related("items").first())

    if existing is not None:
        # This order has been processed before, no database update, just send the existing data
        return existing, False

    try:
        cart = get_cart(authorization)
        quantities = _get_cart_lines(cart)
        prepared = _prepare_order_items(quantities, authorization)
    # Unreachable cart or catalog service
    except DownstreamUnavailable as exc:
        raise CheckoutError(str(exc), 503) from exc

    order, created = _create_order(customer_id, idempotency_key, prepared)

    if not created:
        return order, False

    try:
        for item in order.items.all():
            # reservation ID is the actual idempotency key that the origin service provides it to destination service
            reserve_stock(authorization=authorization, reservation_id=item.reservation_id,
                          product_id=item.product_id, quantity=item.quantity)

        clear_cart(authorization)

    except InventoryReservationRejected as exc:
        _mark_order_failed(order, authorization, str(exc))
        raise CheckoutError(str(exc), 409) from exc

    except DownstreamUnavailable as exc:
        _mark_order_failed(order, authorization, str(exc))
        raise CheckoutError(str(exc), 503) from exc

    order.status = Order.Status.AWAITING_PAYMENT
    order.save(update_fields=["status", "updated"])

    return order, True
