import uuid
from django.db import models


class Order(models.Model):
    class Status(models.TextChoices):
        PROCESSING = 'processing', 'Processing'
        AWAITING_PAYMENT = 'awaiting_payment', 'Awaiting Payment'
        PAID = 'paid', 'Paid'
        CANCELLED = 'cancelled', 'Cancelled'
        FAILED = 'failed', 'Failed'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer_id = models.BigIntegerField(db_index=True)
    idempotency_key = models.CharField(max_length=128)
    status = models.CharField(max_length=32, choices=Status.choices, default=Status.PROCESSING)
    total_amount = models.IntegerField(default=0)
    failer_reason = models.TextField(blank=True)
    updated = models.DateTimeField(auto_now=True)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created']
        constraints = [
            models.UniqueConstraint(
                fields=('customer_id', 'idempotency_key'),
                name='unique_customer_order_idempotency_key'
            )
        ]

    def __str__(self):
        return f'Order {self.id} - {self.status}'


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product_id = models.PositiveBigIntegerField()
    product_name = models.CharField(max_length=256)
    unit_price = models.IntegerField()
    quantity = models.PositiveIntegerField()
    reservation_id = models.UUIDField(unique=True, default=uuid.uuid4, editable=False)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f'{self.product_name} X {self.quantity} for order {self.order}'

    def sub_total(self):
        return self.quantity * self.unit_price
