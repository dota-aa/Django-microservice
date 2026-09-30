from django.urls import path
from rest_framework.routers import DefaultRouter

from . import views


app_name = 'catalog'
urlpatterns = [
    path('health/', views.HealthCheckView.as_view()),
]


router = DefaultRouter()
router.register('category', views.CategoryViewSet)
router.register('product', views.ProductViewSet)

urlpatterns += router.urls
