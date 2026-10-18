from django.db import models


class InventoryItem(models.Model):
    product_id = models.PositiveBigIntegerField(unique=True)
    quantity = models.PositiveIntegerField(default=0)
    updated = models.DateTimeField(auto_now=True)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['product_id']

    def __str__(self):
        return f'Product {self.product_id}: {self.quantity}'


class StockReservation(models.Model):
    class Status(models.TextChoices):
        RESERVED = 'reserved', 'Reserved'
        RELEASE = 'release', 'Release'
        CONFIRMED = 'confirmed', 'Confirmed'

    reservation_id = models.UUIDField(unique=True, editable=False)
    inventory_item = models.ForeignKey(InventoryItem, on_delete=models.PROTECT, related_name='reservation')
    quantity = models.PositiveIntegerField()
    status = models.CharField(choices=Status.choices, default=Status.RESERVED)
    updated = models.DateTimeField(auto_now=True)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('-created',)

    def __str__(self):
        return f'{self.reservation_id} - {self.inventory_item.product_id} - {self.status}'

