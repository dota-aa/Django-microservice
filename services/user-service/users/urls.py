from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from . import views



app_name = 'users'
urlpatterns = [
    path('health', views.HealthCheckView.as_view()),
    path('register/', views.UserRegisterView.as_view()),
    path('login/', views.UserLoginView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('me/', views.MeView.as_view()),
]
