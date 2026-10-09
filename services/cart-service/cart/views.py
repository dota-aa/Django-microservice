from typing import TypedDict, List
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework import status
from django.core.cache import cache


# only for showcase, not using them in code for now
class CartItem(TypedDict):
    """
    CartItem = {
        product_id: 1,
        quantity: 1
    }
    """
    product_id: int
    quantity: int


class Cart(TypedDict):
    """
    cart = {
        "items": [CartItem1, CartItem2, ...]
    }
    """
    items: List[CartItem]


def get_user_id(request: Request) -> int | None:
    user_id = request.headers.get('X-User-ID')
    if user_id is None:
        return None
    return user_id


def get_cart_key(user_id: int) -> str:
    return f'cart:user:{user_id}'


# ========================================================
# Service Health check
# ========================================================
class HealthCheckView(APIView):
    """
    Check service status
    """
    permission_classes = [AllowAny]
    def get(self, request):
        return Response(data={"service": "cart-service", "status": "ok"})


# ========================================================
# Cart
# ========================================================
class CartView(APIView):
    """
    Show a user's cart
    """
    def get(self, request):
        user_id = get_user_id(request)

        if not user_id:
            return Response(data={"detail": "X-User-ID header is required."}, status=status.HTTP_400_BAD_REQUEST)

        key = get_cart_key(user_id)
        cart = cache.get(key, default={"items": []})

        return Response(data=cart)


class CartItemView(APIView):
    """
    Add new item to cart. if item already exists in cart, add quantities.
    """
    def post(self, request):
        user_id = get_user_id(request)

        if not user_id:
            return Response(data={"detail": "X-User-ID header is required."}, status=status.HTTP_400_BAD_REQUEST)

        product_id = request.data.get('product_id')
        quantity = request.data.get('quantity', 1)

        if not product_id:
            return Response(data={"detail": "product_id is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            product_id = int(product_id)
            quantity = int(quantity)
        except (TypeError, ValueError):
            return Response(data={"detail": "product and quantity must be integers."}, status=status.HTTP_400_BAD_REQUEST)

        if quantity <= 0:
            return Response(data={"detail": "quantity must be greater than zero"}, status=status.HTTP_400_BAD_REQUEST)

        key = get_cart_key(user_id)
        cart = cache.get(key, {"items": []})

        for item in cart['items']:
            if item['product_id'] == product_id:
                item['quantity'] += quantity
                break

        else:
            cart['items'].append({"product_id": product_id, "quantity": quantity})

        cache.set(key, cart)
        return Response(cart, status=status.HTTP_201_CREATED)


class CartItemDetailView(APIView):
    def patch(self, request, product_id):
        """
        Update quantity of an item of cart
        """
        user_id = get_user_id(request)

        if not user_id:
            return Response(data={"detail": "x-User-ID is required."}, status=status.HTTP_400_BAD_REQUEST)

        quantity = request.data.get('quantity')

        if not quantity:
            return Response(data={"detail": "quantity is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            quantity = int(quantity)
        except (TypeError, ValueError):
            return Response(data={"detail": "quantity must be an integer."}, status=status.HTTP_400_BAD_REQUEST)

        if quantity <= 0:
            return Response(data={"detail": "quantity must be greater than zero."}, status=status.HTTP_400_BAD_REQUEST)

        key = get_cart_key(user_id)
        cart = cache.get(key, default={"items": []})

        for item in cart['items']:
            if item['product_id'] == product_id:
                item['quantity'] = quantity
                cache.set(key, cart)
                return Response(data=cart)
        return Response(data={"detail": "Product is not in cart"}, status=status.HTTP_404_NOT_FOUND)

    def delete(self, request, product_id):
        """
        Delete an item of a user's cart
        """
        user_id = get_user_id(request)

        if not user_id:
            return Response(data={"detail": "x-User-ID is required."}, status=status.HTTP_400_BAD_REQUEST)

        key = get_cart_key(user_id)
        cart = cache.get(key, default={"items": []})

        cart['items'] = [item for item in cart['items'] if item['product_id'] != product_id]
        cache.set(key, cart)

        return Response(data=cart)


class CartClearView(APIView):
    """
    Delete all items from user's cart
    """
    def delete(self, request):
        user_id = get_user_id(request)

        if not user_id:
            return Response(data={"detail": "x-User-ID is required."}, status=status.HTTP_400_BAD_REQUEST)

        cache.delete(get_cart_key(user_id))
        return Response(data={"items": []})
