from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from django.urls import path
from . import views


app_name = 'cart'
urlpatterns = [
    path('health/', views.HealthCheckView.as_view()),
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    path("docs/", SpectacularSwaggerView.as_view(url_name="cart:schema"), name="swagger-ui"),
    path('', views.CartView.as_view()),
    path('items/', views.CartItemView.as_view()),
    path('items/<int:product_id>/', views.CartItemDetailView.as_view()),
    path('clear/', views.CartClearView.as_view()),
]
