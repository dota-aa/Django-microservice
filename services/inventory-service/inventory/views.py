from rest_framework import viewsets
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .models import InventoryItem
from .serializers import InventoryItemSerializer


# ========================================================
# Service Health check
# ========================================================
class HealthCheckView(APIView):
    """
    Check service status
    """
    permission_classes = [AllowAny]

    def get(self, request):
        return Response(data={"service": "inventory-service", "status": "ok"})


# ========================================================
# Inventory
# ========================================================
class InventoryItemViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]

    queryset = InventoryItem.objects.all()
    serializer_class = InventoryItemSerializer

    lookup_field = "product_id"
    lookup_value_regex = r"\d+" # d -> digit, + -> at least one number
