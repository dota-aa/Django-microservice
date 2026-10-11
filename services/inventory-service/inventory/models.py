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
