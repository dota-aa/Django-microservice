from rest_framework import serializers
from .models import InventoryItem, StockReservation


class InventoryItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = InventoryItem
        fields = ('product_id', 'quantity', 'updated', 'created')
        read_only_fields = fields


class StockReservationRequestSerializer(serializers.Serializer):
    reservation_id = serializers.UUIDField()
    product_id = serializers.IntegerField()
    quantity = serializers.IntegerField()


class StockReservationSerializer(serializers.ModelSerializer):
    product_id = serializers.IntegerField(source='inventory_item.product_id', read_only=True)

    class Meta:
        model = StockReservation
        fields = (
            'reservation_id',
            'product_id',
            'quantity',
            'status',
            'updated',
            'created',
        )
