from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views


router = DefaultRouter()
router.register('items', views.InventoryItemViewSet, basename='inventory-item')


app_name = 'inventory'
urlpatterns = [
    path('health/', views.HealthCheckView.as_view()),
    path('', include(router.urls)),
]
