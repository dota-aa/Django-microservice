from uuid import UUID
from dataclasses import dataclass

from django.db import IntegrityError, transaction

from .models import InventoryItem, StockReservation


@dataclass
class StockReservationInput:
    reservation_id: UUID
    product_id: int
    quantity: int


@dataclass
class StockReservationResult:
    reservation: StockReservation
    was_db_updated: bool


class InsufficientStockError(Exception):
    """Raised when inventory has less amount of item than quantity of requested item"""
    pass


class ReservationConflictError(Exception):
    """
    In 2 scenario we may raise this error:
        1. Tring to use one reservation ID for 2 different request
         (user tries to use the same reservation ID for another request or TWO user get the same reservation ID)
        2. Reuse released/confirmed reservation ID
    """
    pass


# ========================================================
# Reserve Stock
# ========================================================
@transaction.atomic
def _reserve_stock(input_data: StockReservationInput) -> StockReservationResult:
    """
    Reserve stock for a given item in an idempotence manner.

    This function achieve idempotence in 2 ways
        1. reservation ID
        2. Lock database record for the given item with select_for_update

    """
    item = InventoryItem.objects.select_for_update().get(product_id=input_data.product_id)
    existing = StockReservation.objects.select_for_update().filter(
        reservation_id=input_data.reservation_id
    ).first()

    if existing:
        # Check if reservation ID exists in db.
        # if it exists return the existing record without updating db

        same_request = (existing.inventory_item.id == item.pk and existing.quantity == input_data.quantity)
        if not same_request:
            # Make sure reservation ID is not for another request.
            raise ReservationConflictError('This Reservation ID belongs to another request.')

        if not existing.status == StockReservation.Status.RESERVED:
            # Check if the reserved stocked is not released or confirmed before.
            raise ReservationConflictError('A released/confirmed reservation ID cannot be reused.')

        return StockReservationResult(reservation=existing, was_db_updated=False)

    if item.quantity < input_data.quantity:
        # Check if inventory has enough stock.
        raise InsufficientStockError('Not enough available stock.')

    item.quantity -= input_data.quantity
    item.save(update_fields=['quantity', 'updated'])

    reservation = StockReservation.objects.create(
        reservation_id=input_data.reservation_id, inventory_item=item,
        quantity=input_data.quantity, status=StockReservation.Status.RESERVED
    )
    return StockReservationResult(reservation=reservation, was_db_updated=True)


def reserve_stock(input_data: StockReservationInput) -> StockReservationResult:
    """a wrapper for _reserve_stock (protected function) to manage IntegrityError"""
    try:
        return _reserve_stock(input_data)
    except IntegrityError:
        # One user has the same reservation ID that has been used before by another user.
        # User sending the same request multiple times.

        existing = StockReservation.objects.select_related('inventory_item').filter(
            reservation_id=input_data.reservation_id
        ).first()

        if not existing:
            # Two user getting the same reservation ID and tring to reserve an item at the same time
            #  Another Integrity error.
            raise

        first_condition = (
                existing.inventory_item.product_id == input_data.product_id and existing.quantity == input_data.quantity
        )

        second_condition = existing.status in StockReservation.Status.RESERVED, StockReservation.Status.CONFIRMED

        if first_condition and second_condition:
            # User sending the same request multiple times
            return StockReservationResult(reservation=existing, was_db_updated=False)

        raise ReservationConflictError('This reservation ID has already been used.')


# ========================================================
# Release Stock
# ========================================================
@transaction.atomic
def release_stock(reservation_id: UUID) -> StockReservationResult:
    """
    Release an item in a safe manner.

    if it has already been released, it sends the old data without changing database record.
    """
    reservation_ref = StockReservation.objects.only('inventory_item_id').get(reservation_id=reservation_id)

    item = InventoryItem.objects.select_for_update().get(pk=reservation_ref.inventory_item.id)
    reservation = StockReservation.objects.select_for_update().get(reservation_id=reservation_id)

    if reservation.status == StockReservation.Status.RELEASE:
        return StockReservationResult(reservation=reservation, was_db_updated=False)

    if reservation.status == StockReservation.Status.CONFIRMED:
        raise ReservationConflictError('A Confirmed reservation cannot be released.')

    item.quantity += reservation.quantity
    item.save(update_fields=['quantity', 'updated'])

    reservation.status = StockReservation.Status.RELEASE
    reservation.save(update_fields=['status', 'updated'])

    return StockReservationResult(reservation=reservation, was_db_updated=True)


# ========================================================
# Confirm Stock
# ========================================================
@transaction.atomic
def confirm_stock(reservation_id: UUID) -> StockReservationResult:
    """
    Confirm an item in a safe manner.
    """
    reservation_ref = StockReservation.objects.only('inventory_item_id').get(reservation_id=reservation_id)

    InventoryItem.objects.select_for_update().get(pk=reservation_ref.inventory_item.id)
    reservation = StockReservation.objects.select_for_update().get(reservation_id=reservation_id)

    if reservation.status == StockReservation.Status.RELEASE:
        raise ReservationConflictError('A released reservation cannot be confirmed.')

    if reservation.status == StockReservation.Status.CONFIRMED:
        return StockReservationResult(reservation=reservation, was_db_updated=False)

    reservation.status = StockReservation.Status.CONFIRMED
    reservation.save(update_fields=['status', 'updated'])

    return StockReservationResult(reservation=reservation, was_db_updated=True)
