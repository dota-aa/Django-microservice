from rest_framework import viewsets, status
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .models import InventoryItem, StockReservation
from .serializers import InventoryItemSerializer, StockReservationRequestSerializer, StockReservationSerializer
from .services import (
    InsufficientStockError,
    ReservationConflictError,
    StockReservationInput,
    reserve_stock,
    release_stock,
    confirm_stock
)


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


class StockReservationView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = StockReservationRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        reservation_input = StockReservationInput(
            reservation_id=data['reservation_id'],
            product_id=data['product_id'],
            quantity=data['quantity']
        )

        try:
            result = reserve_stock(reservation_input)
        except InventoryItem.DoesNotExist:
            return Response(
                data={"detail": "Inventory record does not exist for this product"},
                status=status.HTTP_404_NOT_FOUND
            )
        except InsufficientStockError as exc:
            return Response(data={"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        except ReservationConflictError as exc:
            return Response(data={"detail": str(exc)}, status=status.HTTP_409_CONFLICT)

        response_status = status.HTTP_201_CREATED if result.was_db_updated else status.HTTP_200_OK  # Conditional operator
        return Response(data=StockReservationSerializer(result.reservation).data, status=response_status)


class StockReleaseView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, reservation_id):
        try:
            result = release_stock(reservation_id)
        except StockReservation.DoesNotExist:
            return Response(
                data={"detail": "Reservation NOT found"},
                status=status.HTTP_404_NOT_FOUND
            )
        except ReservationConflictError as exc:
            return Response(data={"detail": str(exc)}, status=status.HTTP_409_CONFLICT)

        return Response(data=StockReservationSerializer(result.reservation).data, status=status.HTTP_200_OK)


class StockConfirmationView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, reservation_id):
        try:
            result = confirm_stock(reservation_id)
        except StockReservation.DoesNotExist:
            return Response(
                data={"detail": "Reservation NOT found"},
                status=status.HTTP_404_NOT_FOUND
            )
        except ReservationConflictError as exc:
            return Response(data={"detail": str(exc)}, status=status.HTTP_409_CONFLICT)

        return Response(data=StockReservationSerializer(result.reservation).data, status=status.HTTP_200_OK)
