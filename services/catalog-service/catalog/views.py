from rest_framework.views import APIView
from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from django.core.cache import cache

from .models import Category, Product
from .serializers import CategorySerializer, ProductSerializer


# ========================================================
# Service Health check
# ========================================================
class HealthCheckView(APIView):
    permission_classes = [AllowAny]
    def get(self, request):
        return Response({'service': 'catalog-service', 'status': 'ok'})


# ========================================================
# Categories
# ========================================================
class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer


# ========================================================
# Products
# ========================================================
class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.select_related('category').all()
    serializer_class = ProductSerializer
    filter_backends = [
        DjangoFilterBackend,
        SearchFilter,
        OrderingFilter
    ]

    filterset_fields = [
        'name',
        'category',
    ]

    search_fields = [
        'name',
        'description',
    ]

    order_fields = [
        'price',
        'updated',
        'created'
    ]

    def perform_create(self, serializer):
        serializer.save()
        cache.delete('product:product_list')

    def perform_update(self, serializer):
        product = serializer.save()

        cache.delete(f'product:{product.id}')
        cache.delete('product:product_list')

    def perform_destroy(self, instance):
        product_id = instance.id
        instance.delete()

        cache.delete(f'product:{product_id}')
        cache.delete('product:product_list')

    def list(self, request, *args, **kwargs):
        cache_key = 'product:product_list'

        cache_data = cache.get(cache_key)
        if cache_data:
            """
            Cache hit
            """
            return Response(data=cache_data)
        # cache miss
        qs = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(qs, many=True)

        # set cache
        cache.set(cache_key, serializer.data)
        return Response(data=serializer.data)

    def retrieve(self, request, *args, **kwargs):
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
        product_id = kwargs.get(lookup_url_kwarg) or request.query_params.get("id")
        cache_key = f'product:{product_id}'

        cache_data = cache.get(cache_key)
        if cache_data:
            """
            Cache hit
            """
            return Response(data=cache_data)

        # cache miss
        product = self.get_object()
        serializer = self.get_serializer(product)
        # set cache
        cache.set(cache_key, serializer.data)
        return Response(data=serializer.data)
