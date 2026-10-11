from rest_framework import serializers
from .models import InventoryItem


class InventoryItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = InventoryItem
        fields = ('product_id', 'quantity', 'updated', 'created')
        read_only_fields = fields
