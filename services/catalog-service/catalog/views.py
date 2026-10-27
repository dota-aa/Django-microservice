from rest_framework.views import APIView
from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from django.core.cache import cache
from django.db import transaction
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiResponse, OpenApiExample

from .models import Category, Product
from .serializers import CategorySerializer, ProductSerializer
from .messaging.rabbitmq import publish_even


# ========================================================
# Service Health check
# ========================================================
class HealthCheckView(APIView):
    """
    Check service health
    """
    permission_classes = [AllowAny]

    @extend_schema(
        tags=['Catalog'],
        summary='Check catalog service health',
        description='Check whether catalog service api is responding.',
        responses={
            200: OpenApiResponse(description='The service is healthy.')
        },
        examples=[
            OpenApiExample(
                'successful health check',
                value={"service": "", "status": "ok"},
                status_codes=["200"]
            )
        ]
    )
    def get(self, request):
        return Response({'service': 'catalog-service', 'status': 'ok'})


# ========================================================
# Categories
# ========================================================
@extend_schema_view(
    list=extend_schema(
        tags=["Catalog - Category"],
        summary='List categories',
        description='Returns a list of existing categories',
        responses={
            200: CategorySerializer(many=True)
        }
    ),
    retrieve=extend_schema(
        tags=["Catalog - Category"],
        summary='Retrieve a category',
        description='Retrieve a category details',
        responses={
            200: CategorySerializer,
            404: OpenApiResponse(description='Requested category not found.')
        },
    ),
    create=extend_schema(
        tags=["Catalog - Category"],
        summary='Create a category',
        description='Create a category record',
        request=CategorySerializer,
        responses={
            201: CategorySerializer,
            400: OpenApiResponse(description='invalid fields, missing required fields, or invalid data type'),
        },
        examples=[
            OpenApiExample(
                'Create category request',
                value={
                    "name": "laptop amd-64",
                    "slug": "laptop-amd-64",
                },
                request_only=True
            ),
            OpenApiExample(
                'Create category response',
                value={
                    "name": "laptop amd-64",
                    "slug": "laptop-amd-64",
                    "updated": "2026-4-23T12:23:04",
                    "created": "2026-4-21T12:23:04",
                },
                response_only=True
            )
        ]
    ),
    update=extend_schema(
        tags=["Catalog - Category"],
        summary='Replace category fields',
        description='Replace category fields and update the database.',
    ),
    partial_update=extend_schema(
        tags=["Catalog - Category"],
        summary='Update category',
        description='Update a category fields',
    ),
    destroy=extend_schema(
        tags=["Catalog - Category"],
        summary='Delete category',
        description='delete a category record from databasez',
        responses={
            204: OpenApiResponse(description='Category deleted successfully.'),
            404: OpenApiResponse(description='Requested category not found.')
        },
    )
)
class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer


# ========================================================
# Products
# ========================================================
@extend_schema_view(
    list=extend_schema(
        tags=["Catalog - products"],
        summary='List products',
        description='Returns the list of products, this endpoint uses cache to improve response performance',
        responses={
            200: ProductSerializer(many=True),
        },
        examples=[
            OpenApiExample(
                'Product list',
                value={
                    "category": "1",
                    "name": "samsung A23",
                    "description": "good phone",
                    "price": "10000000",
                    "stock": "1",
                    "is_active": True,
                    "updated": "2026-4-23T12:23:04",
                    "created": "2026-4-21T12:23:04",
                },
                status_codes=["200"]
            ),
        ]
    ),
    retrieve=extend_schema(
        tags=["Catalog - products"],
        summary='Retrieve a product',
        description='Returns a product identified by its IDs',
        responses={
            200: ProductSerializer,
            404: OpenApiResponse(description='The requested product not found')
        },
    ),
    create=extend_schema(
        tags=["Catalog - products"],
        summary='Create a product',
        description=('Create a product and invalidate product_list cache'
                    'If product created successfully an event will be published.'),
        request=ProductSerializer,
        responses={
            201: ProductSerializer,
            400: OpenApiResponse(description="invalid fields, missing required fields, or invalid input type")
        },
        examples=[
            OpenApiExample(
                'Create a product request',
                value={
                    "category": "1",
                    "name": "samsung A23",
                    "description": "good phone",
                    "price": "10000000",
                    "stock": "1",
                    "is_active": True,
                },
                request_only=True
            ),
            OpenApiExample(
                'Created product response',
                value={
                    "category": "1",
                    "name": "samsung A23",
                    "description": "good phone",
                    "price": "10000000",
                    "stock": "1",
                    "is_active": True,
                    "updated": "2026-4-23T12:23:04",
                    "created": "2026-4-21T12:23:04",
                },
                response_only=True
            ),
        ]
    ),
    update=extend_schema(
        tags=["Catalog - products"],
        summary='Replace a product fields',
        description='Replace a product fields and invalidate cache',
        request=ProductSerializer,
        responses={
            200: ProductSerializer,
            400: OpenApiResponse(description='invalid fields, or invalid data type.'),
            404: OpenApiResponse(description='product not found.')
        },
        examples=[
            OpenApiExample(
                'Update product request',
                value={
                    "category": "1",
                    "name": "samsung A23",
                    "description": "good phone",
                    "price": "10000000",
                    "stock": "1",
                    "is_active": True,
                },
                request_only=True
            ),
            OpenApiExample(
                'Updated product response',
                value={
                "category": "1",
                    "name": "samsung A23",
                    "description": "good phone",
                    "price": "10000000",
                    "stock": "1",
                    "is_active": True,
                    "updated": "2026-4-23T12:23:04",
                    "created": "2026-4-21T12:23:04",
                },
                response_only=True
            )
        ]
    ),
    partial_update=extend_schema(
        tags=["Catalog - products"],
        summary='Update a product',
        description='Update a product fields and invalidate cache.',
        responses={
            200: ProductSerializer,
            400: OpenApiResponse(description='invalid fields, or invalid data type.'),
            404: OpenApiResponse(description='product not found.')
        },
        examples=[
            OpenApiExample('Update product request', value={"stock": "20"}, request_only=True),
            OpenApiExample('Update product request', value={"name": "Samsung A34"}, request_only=True),
        ],
    ),
    destroy=extend_schema(
        tags=["Catalog - products"],
        summary='Delete product',
        description='Delete a product identified by ID and invalidate cache',
        responses={
            204: OpenApiResponse(description='Product deleted.'),
            404: OpenApiResponse(description='Requested product not found.')
        },
    ),
)
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
        product = serializer.save()
        cache.delete('product:product_list')

        def publish_product_created():
            """
            A wrapper for publish_event func that allows to use on_commit transaction
            """
            publish_even("product.created", {
                "id": product.id,
                "name": product.name,
                "description": product.description,
                "price": str(product.price),
                "stock": product.stock
            })

        transaction.on_commit(publish_product_created)

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
